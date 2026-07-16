from app.agent.geo import nearest_airports, airports_within, haversine_km

def test_haversine_known_distance():
    # Milano (MXP) ~ Roma (FCO) ≈ 480 km
    d = haversine_km(45.63, 8.72, 41.80, 12.25)
    assert 400 < d < 560

def test_nearest_airports_from_milan_centre():
    res = nearest_airports(45.46, 9.19, k=2)
    assert res[0]["iata"] in {"MXP", "LIN", "BGY"}
    assert len(res) == 2
    assert res[0]["km"] <= res[1]["km"]

def test_airports_within_milan_keeps_close_excludes_far():
    res = airports_within(45.46, 9.19, radius_km=80.0)
    iatas = {a["iata"] for a in res}
    # Milan-area airports are within 80 km
    assert {"MXP", "LIN", "BGY"} <= iatas
    # Rome (FCO) is ~480 km away — must be excluded
    assert "FCO" not in iatas
    # sorted by distance ascending
    kms = [a["km"] for a in res]
    assert kms == sorted(kms)

def test_airports_within_caps_max_n():
    res = airports_within(45.46, 9.19, radius_km=2000.0, max_n=4)
    assert len(res) == 4

def test_airports_within_falls_back_to_single_nearest():
    # Mid-Atlantic: nothing within 80 km → fall back to exactly the nearest 1
    res = airports_within(0.0, -30.0, radius_km=80.0)
    assert len(res) == 1


def test_airports_within_returns_nearest_when_none_in_radius():
    # Mid-Atlantic: nothing within 80 km, must still return exactly the closest one.
    res = airports_within(40.0, -30.0, 80.0)
    assert len(res) == 1
    assert "iata" in res[0]


def test_airports_within_keeps_radius_when_some_in_range():
    # Near Milano: should return multiple within 80 km, not just one.
    res = airports_within(45.46, 9.18, 80.0)
    assert len(res) >= 2
    assert all(a["km"] <= 80.0 for a in res)
