import pytest
async def _login(c, email="b@x"): await c.post("/api/auth/login", json={"email": email, "password": "pw"})


@pytest.mark.asyncio
async def test_get_and_update_profile(app_client):
    await _login(app_client)
    assert (await app_client.get("/api/me")).json()["username"] == "bob"
    r = await app_client.patch("/api/me", json={"username": "bobby", "email": "bob2@x"})
    assert r.status_code == 200 and r.json()["username"] == "bobby" and r.json()["email"] == "bob2@x"


@pytest.mark.asyncio
async def test_password_requires_current(app_client):
    await _login(app_client)
    bad = await app_client.patch("/api/me", json={"current_password": "wrong", "new_password": "x123"})
    assert bad.status_code == 400
    ok = await app_client.patch("/api/me", json={"current_password": "pw", "new_password": "x123"})
    assert ok.status_code == 200
    await app_client.post("/api/auth/logout")
    relog = await app_client.post("/api/auth/login", json={"email": "b@x", "password": "x123"})
    assert relog.status_code == 200


@pytest.mark.asyncio
async def test_email_conflict(app_client):
    await _login(app_client)
    r = await app_client.patch("/api/me", json={"email": "a@x"})
    assert r.status_code == 409
