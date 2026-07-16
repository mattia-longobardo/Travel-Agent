import pytest
async def _login(c): await c.post("/api/auth/login", json={"email": "b@x", "password": "pw"})


@pytest.mark.asyncio
async def test_archive_trash_filter(app_client):
    await _login(app_client)
    cid = (await app_client.post("/api/chats", json={"title": "A"})).json()["id"]
    assert (await app_client.get(f"/api/chats/{cid}")).json()["status"] == "active"
    r = await app_client.patch(f"/api/chats/{cid}", json={"status": "archived"})
    assert r.status_code == 200 and r.json()["status"] == "archived"
    assert all(c["id"] != cid for c in (await app_client.get("/api/chats?status=active")).json())
    assert any(c["id"] == cid for c in (await app_client.get("/api/chats?status=archived")).json())
    await app_client.patch(f"/api/chats/{cid}", json={"status": "trashed"})
    assert any(c["id"] == cid for c in (await app_client.get("/api/chats?status=trashed")).json())


@pytest.mark.asyncio
async def test_invalid_status_rejected(app_client):
    await _login(app_client)
    cid = (await app_client.post("/api/chats", json={"title": "A"})).json()["id"]
    r = await app_client.patch(f"/api/chats/{cid}", json={"status": "weird"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_empty_trash(app_client):
    await _login(app_client)
    a = (await app_client.post("/api/chats", json={"title": "A"})).json()["id"]
    b = (await app_client.post("/api/chats", json={"title": "B"})).json()["id"]
    await app_client.patch(f"/api/chats/{a}", json={"status": "trashed"})
    await app_client.patch(f"/api/chats/{b}", json={"status": "trashed"})
    r = await app_client.post("/api/chats/empty-trash")
    assert r.status_code == 200
    assert (await app_client.get("/api/chats?status=trashed")).json() == []
    c = (await app_client.post("/api/chats", json={"title": "C"})).json()["id"]
    await app_client.post("/api/chats/empty-trash")
    assert any(x["id"] == c for x in (await app_client.get("/api/chats?status=active")).json())
