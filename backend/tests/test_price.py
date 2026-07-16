from app.agent.price import parse_price


def test_european_decimal_comma():
    assert parse_price("266,54 €") == 266.54


def test_european_thousands_dot_and_decimal_comma():
    assert parse_price("1.266,54 €") == 1266.54


def test_plain_dot_decimal():
    assert parse_price("266.54") == 266.54


def test_numeric_passthrough():
    assert parse_price(266.54) == 266.54
    assert parse_price(266) == 266.0


def test_unparseable_and_none():
    assert parse_price(None) is None
    assert parse_price("") is None
    assert parse_price("n/d") is None
