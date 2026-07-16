from app.agent import telemetry


def test_accumulates_usage():
    tok = telemetry.start_run()
    telemetry.add_usage(10, 5)
    telemetry.add_usage(3, 2)
    snap = telemetry.snapshot()
    assert snap == {"prompt_tokens": 13, "completion_tokens": 7, "total_tokens": 20}
    telemetry.reset(tok)


def test_snapshot_without_run_is_zero():
    snap = telemetry.snapshot()
    assert snap == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def test_add_usage_outside_run_is_noop():
    telemetry.add_usage(5, 5)
    assert telemetry.snapshot()["total_tokens"] == 0
