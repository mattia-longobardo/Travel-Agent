from app.security import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("secret")
    assert h != "secret"
    assert verify_password("secret", h) is True
    assert verify_password("wrong", h) is False


def test_verify_malformed_hash_returns_false():
    assert verify_password("x", "not-a-valid-hash") is False
