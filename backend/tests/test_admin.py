import csv as _csv
import io as _io

import pytest


EMAILS = {"admin": "a@x", "bob": "b@x", "carl": "c@x"}
async def _login(c, u, p):
    return await c.post("/api/auth/login", json={"email": EMAILS[u], "password": p})


@pytest.mark.asyncio
async def test_cannot_demote_last_admin(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    admin = next(u for u in users if u["username"] == "admin")
    # only one admin exists -> cannot demote
    r = await app_client.patch(f"/api/admin/users/{admin['id']}", json={"is_admin": False})
    assert r.status_code == 400
    # add a second admin, then demoting the first succeeds
    await app_client.post("/api/admin/users", json={
        "username": "carl", "email": "c@x", "password": "pw", "is_admin": True})
    r2 = await app_client.patch(f"/api/admin/users/{admin['id']}", json={"is_admin": False})
    assert r2.status_code == 200 and r2.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_admin_creates_user_and_lists(app_client):
    await _login(app_client, "admin", "pw")
    r = await app_client.post("/api/admin/users", json={
        "username": "carl", "email": "c@x", "password": "pw", "is_admin": False})
    assert r.status_code == 201
    lst = await app_client.get("/api/admin/users")
    names = [u["username"] for u in lst.json()["items"]]
    assert "carl" in names


@pytest.mark.asyncio
async def test_admin_changes_email(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    bob = next(u for u in users if u["username"] == "bob")
    r = await app_client.patch(f"/api/admin/users/{bob['id']}", json={"email": "newbob@x"})
    assert r.status_code == 200 and r.json()["email"] == "newbob@x"
    dup = await app_client.patch(f"/api/admin/users/{bob['id']}", json={"email": "a@x"})
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_admin_changes_username(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    bob = next(u for u in users if u["username"] == "bob")
    r = await app_client.patch(f"/api/admin/users/{bob['id']}", json={"username": "bobby"})
    assert r.status_code == 200 and r.json()["username"] == "bobby"
    dup = await app_client.patch(f"/api/admin/users/{bob['id']}", json={"username": "admin"})
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_admin_deletes_user(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    bob = next(u for u in users if u["username"] == "bob")
    r = await app_client.delete(f"/api/admin/users/{bob['id']}")
    assert r.status_code == 204
    names = [u["username"] for u in (await app_client.get("/api/admin/users")).json()["items"]]
    assert "bob" not in names


@pytest.mark.asyncio
async def test_admin_cannot_delete_self(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    admin = next(u for u in users if u["username"] == "admin")
    r = await app_client.delete(f"/api/admin/users/{admin['id']}")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_user_cascades_their_chats(app_client):
    # bob creates a chat, then the admin deletes bob -> the chat is gone too.
    await _login(app_client, "bob", "pw")
    chat = await app_client.post("/api/chats", json={"title": "Viaggio di bob"})
    assert chat.status_code in (200, 201)
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    bob = next(u for u in users if u["username"] == "bob")
    assert (await app_client.delete(f"/api/admin/users/{bob['id']}")).status_code == 204
    remaining = (await app_client.get(f"/api/admin/analytics/chats?user_id={bob['id']}")).json()
    assert remaining["items"] == []


@pytest.mark.asyncio
async def test_delete_missing_user_404(app_client):
    await _login(app_client, "admin", "pw")
    r = await app_client.delete("/api/admin/users/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_non_admin_forbidden(app_client):
    await _login(app_client, "bob", "pw")
    r = await app_client.get("/api/admin/users")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_deactivate_and_change_group_and_password(app_client):
    await _login(app_client, "admin", "pw")
    g = await app_client.post("/api/admin/groups", json={"name": "vip"})
    gid = g.json()["id"]
    users = (await app_client.get("/api/admin/users")).json()["items"]
    bob = next(u for u in users if u["username"] == "bob")
    r = await app_client.patch(f"/api/admin/users/{bob['id']}",
                               json={"is_active": False, "group_id": gid, "password": "new"})
    assert r.status_code == 200
    assert r.json()["is_active"] is False and r.json()["group_id"] == gid


@pytest.mark.asyncio
async def test_list_users_paginated_envelope(app_client):
    await _login(app_client, "admin", "pw")
    r = await app_client.get("/api/admin/users?page=1&page_size=1")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total", "page", "page_size"}
    assert body["total"] == 2 and body["page_size"] == 1 and len(body["items"]) == 1


@pytest.mark.asyncio
async def test_list_users_search_and_filters(app_client):
    await _login(app_client, "admin", "pw")
    only_bob = (await app_client.get("/api/admin/users?q=bob")).json()
    assert [u["username"] for u in only_bob["items"]] == ["bob"]
    admins = (await app_client.get("/api/admin/users?role=admin")).json()
    assert [u["username"] for u in admins["items"]] == ["admin"]
    active = (await app_client.get("/api/admin/users?status=active")).json()
    assert active["total"] == 2


@pytest.mark.asyncio
async def test_list_users_sort(app_client):
    await _login(app_client, "admin", "pw")
    desc = (await app_client.get("/api/admin/users?sort=username&order=desc")).json()
    assert [u["username"] for u in desc["items"]] == ["bob", "admin"]


@pytest.mark.asyncio
async def test_bulk_deactivate_excludes_self(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    ids = [u["id"] for u in users]  # includes admin (self) + bob
    r = await app_client.post("/api/admin/users/bulk",
                              json={"action": "deactivate", "user_ids": ids})
    body = r.json()
    assert r.status_code == 200
    assert body["affected"] == 1
    assert any(s["reason"] == "self" for s in body["skipped"])
    after = (await app_client.get("/api/admin/users?q=bob")).json()["items"][0]
    assert after["is_active"] is False


@pytest.mark.asyncio
async def test_bulk_set_admin_protects_last_admin(app_client):
    await _login(app_client, "admin", "pw")
    users = (await app_client.get("/api/admin/users")).json()["items"]
    admin = next(u for u in users if u["username"] == "admin")
    # demoting the only admin (and it's self) -> skipped
    r = await app_client.post("/api/admin/users/bulk",
                              json={"action": "set_admin", "value": False, "user_ids": [admin["id"]]})
    assert r.json()["affected"] == 0


@pytest.mark.asyncio
async def test_bulk_set_group_and_all_matching(app_client):
    await _login(app_client, "admin", "pw")
    gid = (await app_client.post("/api/admin/groups", json={"name": "vip"})).json()["id"]
    # Add a third user (charlie) that does NOT match the filter q=bob
    await app_client.post("/api/admin/users", json={
        "username": "charlie", "email": "charlie@x", "password": "pw"})
    r = await app_client.post("/api/admin/users/bulk", json={
        "action": "set_group", "all_matching": True,
        "filters": {"q": "bob"}, "group_id": gid})
    assert r.json()["affected"] == 1
    bob = (await app_client.get("/api/admin/users?q=bob")).json()["items"][0]
    assert bob["group_id"] == gid
    # charlie must NOT have been affected (cartesian-product bug would wrongly move him too)
    charlie = next(u for u in (await app_client.get("/api/admin/users?q=charlie")).json()["items"]
                   if u["username"] == "charlie")
    assert charlie["group_id"] is None


@pytest.mark.asyncio
async def test_users_stats(app_client):
    await _login(app_client, "admin", "pw")
    s = (await app_client.get("/api/admin/users/stats")).json()
    assert s == {"total": 2, "active": 2, "inactive": 0, "admins": 1}


@pytest.mark.asyncio
async def test_export_users_csv(app_client):
    await _login(app_client, "admin", "pw")
    r = await app_client.get("/api/admin/users/export.csv?q=bob")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(_csv.reader(_io.StringIO(r.text)))
    assert rows[0] == ["id", "username", "email", "role", "active", "group"]
    assert len(rows) == 2 and rows[1][1] == "bob"


@pytest.mark.asyncio
async def test_export_users_csv_neutralizes_formula_injection(app_client):
    await _login(app_client, "admin", "pw")
    await app_client.post("/api/admin/users",
                          json={"username": "=SUM(1+1)", "email": "evil@x", "password": "pw"})
    r = await app_client.get("/api/admin/users/export.csv?q=SUM")
    rows = list(_csv.reader(_io.StringIO(r.text)))
    target = next(row for row in rows[1:] if row[1].endswith("SUM(1+1)"))
    assert target[1] == "'=SUM(1+1)"  # leading apostrophe neutralizes the formula


@pytest.mark.asyncio
async def test_bulk_delete_cascades(app_client):
    await _login(app_client, "bob", "pw")
    await app_client.post("/api/chats", json={"title": "x"})
    await _login(app_client, "admin", "pw")
    bob = next(u for u in (await app_client.get("/api/admin/users")).json()["items"]
               if u["username"] == "bob")
    r = await app_client.post("/api/admin/users/bulk",
                              json={"action": "delete", "user_ids": [bob["id"]]})
    assert r.json()["affected"] == 1
    assert (await app_client.get(f"/api/admin/analytics/chats?user_id={bob['id']}")).json()["items"] == []
