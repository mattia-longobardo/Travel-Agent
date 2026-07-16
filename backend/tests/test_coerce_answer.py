from app.routers.agent import _coerce_answer


def test_bare_numbers_coerce():
    assert _coerce_answer("900") == 900
    assert _coerce_answer("900.5") == 900.5
    assert _coerce_answer(900) == 900  # passthrough for already-numeric values


def test_custom_budget_with_units_and_per_person():
    # The reported bug: a custom budget like "900 a persona" must become 900, not be
    # stored verbatim (which rendered as "NaN EUR a persona" in the brief).
    assert _coerce_answer("900 a persona", "budget_per_person") == 900
    assert _coerce_answer("750 €", "budget_per_person") == 750
    assert _coerce_answer("1.500 EUR", "budget_per_person") == 1500     # IT thousands sep
    assert _coerce_answer("1500,50", "budget_per_person") == 1500.5     # IT decimal sep
    assert _coerce_answer("circa 600 a testa", "budget_per_person") == 600


def test_other_numeric_fields_extract_numbers():
    assert _coerce_answer("7 notti", "trip_nights") == 7
    assert _coerce_answer("4 stelle", "min_stars") == 4


def test_non_numeric_fields_keep_strings():
    # date_from carries an ISO date — numeric extraction must NOT turn it into 2026.
    assert _coerce_answer("2026-08-16", "date_from") == "2026-08-16"
    # an unknown/text field is returned unchanged
    assert _coerce_answer("Lisbona", "destination") == "Lisbona"


def test_numeric_field_without_number_is_unchanged():
    assert _coerce_answer("non so", "budget_per_person") is None


def test_non_numeric_budget_becomes_none():
    assert _coerce_answer("quel che serve", "budget_per_person") is None
    assert _coerce_answer("il necessario", "budget_per_person") is None
    assert _coerce_answer("quanto serve", "trip_nights") is None


def test_numeric_budget_still_parses():
    assert _coerce_answer("900 a persona", "budget_per_person") == 900
    assert _coerce_answer("1.500 EUR", "budget_per_person") == 1500
