import pytest


EMAILS = {"admin": "a@x", "bob": "b@x"}
async def _login(c, u, p="pw"):
    await c.post("/api/auth/login", json={"email": EMAILS[u], "password": p})


@pytest.mark.asyncio
async def test_create_get_share_chat(app_client):
    await _login(app_client, "bob")
    r = await app_client.post("/api/chats", json={"title": "Roma", "params": {"budget": 500}})
    assert r.status_code == 201
    cid = r.json()["id"]
    got = await app_client.get(f"/api/chats/{cid}")
    assert got.json()["params_json"]["budget"] == 500
    # share with admin
    sh = await app_client.post(f"/api/chats/{cid}/share", json={"email": "a@x", "permission": "read"})
    assert sh.status_code == 200
    # admin sees it in list
    await _login(app_client, "admin")
    lst = await app_client.get("/api/chats")
    assert any(c["id"] == cid for c in lst.json())
    # admin cannot delete (not owner)
    d = await app_client.delete(f"/api/chats/{cid}")
    assert d.status_code == 403


@pytest.mark.asyncio
async def test_no_access_returns_404(app_client):
    await _login(app_client, "bob")
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    await _login(app_client, "admin")  # admin has no share here unless granted
    # admin is admin but chat access is ownership/share-based, not admin override
    got = await app_client.get(f"/api/chats/{cid}")
    assert got.status_code == 404
