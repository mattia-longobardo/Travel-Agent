from app.agent.prompt import build_system_prompt


def test_prompt_includes_flexibility_and_multiple_options():
    p = build_system_prompt({"destination": "Parigi", "destination_flexible": True,
                             "budget": 500, "budget_type": "max", "min_stars": 4,
                             "good_reviews": True})
    assert "Parigi" in p
    assert "alternativ" in p.lower()          # propose alternatives when flexible
    assert "500" in p
    assert "più opzioni" in p.lower() or "multiple" in p.lower()
