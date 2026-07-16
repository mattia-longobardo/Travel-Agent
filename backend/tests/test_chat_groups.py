import pytest
async def _login(c, email="b@x"): await c.post("/api/auth/login", json={"email": email, "password": "pw"})


@pytest.mark.asyncio
async def test_group_crud_and_delete_trashes_chats(app_client):
    await _login(app_client)
    g = await app_client.post("/api/chat-groups", json={"name": "Estate"})
    assert g.status_code == 201
    gid = g.json()["id"]
    assert any(x["name"] == "Estate" for x in (await app_client.get("/api/chat-groups")).json())
    r = await app_client.patch(f"/api/chat-groups/{gid}", json={"name": "Estate 2026"})
    assert r.json()["name"] == "Estate 2026"
    cid = (await app_client.post("/api/chats", json={"title": "Mare"})).json()["id"]
    await app_client.patch(f"/api/chats/{cid}", json={"chat_group_id": gid})
    d = await app_client.delete(f"/api/chat-groups/{gid}")
    assert d.status_code == 200
    assert all(x["id"] != gid for x in (await app_client.get("/api/chat-groups")).json())
    assert any(c["id"] == cid for c in (await app_client.get("/api/chats?status=trashed")).json())


@pytest.mark.asyncio
async def test_group_owner_isolation(app_client):
    await _login(app_client)
    gid = (await app_client.post("/api/chat-groups", json={"name": "Mia"})).json()["id"]
    await _login(app_client, "a@x")
    assert all(x["id"] != gid for x in (await app_client.get("/api/chat-groups")).json())
    assert (await app_client.delete(f"/api/chat-groups/{gid}")).status_code == 404
