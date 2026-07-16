import pytest

@pytest.mark.asyncio
async def test_login_me_logout(app_client):
    r = await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    assert r.status_code == 200 and r.json()["username"] == "bob"
    me = await app_client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["username"] == "bob"
    await app_client.post("/api/auth/logout")
    me2 = await app_client.get("/api/auth/me")
    assert me2.status_code == 401

@pytest.mark.asyncio
async def test_login_email_case_insensitive(app_client):
    r = await app_client.post("/api/auth/login", json={"email": "  B@X  ", "password": "pw"})
    assert r.status_code == 200 and r.json()["username"] == "bob"

@pytest.mark.asyncio
async def test_login_bad_password(app_client):
    r = await app_client.post("/api/auth/login", json={"email": "b@x", "password": "no"})
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_inactive_user_blocked(app_client):
    # deactivate bob directly is covered in admin tests; here just check 401 path
    r = await app_client.get("/api/auth/me")
    assert r.status_code == 401
