from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.main import create_app
from app.models import Base, User, Group, Chat, Message, RunTelemetry
from app.security import hash_password
from app.db import get_session
from app.sessions import SessionStore
from app.deps import get_session_store


@pytest.fixture
async def seeded():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis = fakeredis.aioredis.FakeRedis()
    store = SessionStore(redis)

    async with sm() as s:
        g = Group(name="default"); s.add(g); await s.flush()
        admin = User(username="admin", email="a@x", password_hash=hash_password("pw"),
                     group_id=g.id, is_admin=True)
        bob = User(username="bob", email="b@x", password_hash=hash_password("pw"), group_id=g.id)
        s.add(admin); s.add(bob); await s.flush()
        c1 = Chat(owner_id=bob.id, title="Tenerife")
        c2 = Chat(owner_id=admin.id, title="Roma")
        s.add(c1); s.add(c2); await s.flush()
        s.add(Message(chat_id=c1.id, role="user", content="ciao"))
        s.add(Message(chat_id=c1.id, role="assistant", content="ecco"))
        await s.flush()
        s.add(RunTelemetry(chat_id=c1.id, user_id=bob.id, node_path=["intake", "scout"],
                           prompt_tokens=10, completion_tokens=4, total_tokens=14, latency_ms=200,
                           model="gpt-5.4", ok=True))
        s.add(RunTelemetry(chat_id=c1.id, user_id=bob.id, node_path=["intake", "scout"],
                           prompt_tokens=20, completion_tokens=6, total_tokens=26, latency_ms=400,
                           model="gpt-x", ok=True))
        s.add(RunTelemetry(chat_id=c2.id, user_id=admin.id, node_path=["intake"],
                           prompt_tokens=5, completion_tokens=5, total_tokens=10, latency_ms=600,
                           model="gpt-x", ok=False, error="boom"))
        await s.commit()
        ids = {"bob": bob.id, "c1": c1.id, "c2": c2.id}

    app = create_app()
    async def _get_session():
        async with sm() as ses:
            yield ses
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_session_store] = lambda: store
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://t") as c:
        c._ids = ids
        c._sessionmaker = sm
        yield c
    await redis.aclose()
    await engine.dispose()


async def _login(c, email):
    return await c.post("/api/auth/login", json={"email": email, "password": "pw"})


@pytest.mark.asyncio
async def test_overview(seeded):
    await _login(seeded, "a@x")
    r = await seeded.get("/api/admin/analytics/overview")
    assert r.status_code == 200
    d = r.json()
    assert d["total_chats"] == 2
    assert d["total_users"] == 2
    assert d["total_messages"] == 2
    assert d["total_runs"] == 3
    assert d["total_prompt_tokens"] == 35
    assert d["total_completion_tokens"] == 15
    assert d["total_tokens"] == 50
    assert d["avg_latency_ms"] == 400  # (200+400+600)/3
    assert d["total_successes"] == 2
    assert d["total_errors"] == 1
    assert d["total_cancelled"] == 0
    assert d["success_rate"] == round(2 / 3, 4)
    assert d["error_rate"] == round(1 / 3, 4)
    assert isinstance(d["by_day"], list) and len(d["by_day"]) == 30
    assert all({"successes", "errors", "cancelled", "estimated_cost_usd", "has_unpriced"} <= row.keys()
               for row in d["by_day"])


@pytest.mark.asyncio
async def test_paths(seeded):
    await _login(seeded, "a@x")
    r = await seeded.get("/api/admin/analytics/paths")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert paths[0]["path"] == ["intake", "scout"]
    assert paths[0]["count"] == 2
    assert paths[0]["avg_latency_ms"] == 300
    assert paths[0]["avg_tokens"] == 20
    assert any(p["path"] == ["intake"] and p["count"] == 1 for p in paths)


@pytest.mark.asyncio
async def test_chats_list_sort_and_filter(seeded):
    await _login(seeded, "a@x")
    r = await seeded.get("/api/admin/analytics/chats?sort=last_message_at&order=desc")
    assert r.status_code == 200
    rows = r.json()["items"]
    assert len(rows) == 2
    c1 = next(x for x in rows if x["title"] == "Tenerife")
    assert c1["owner_username"] == "bob"
    assert c1["message_count"] == 2
    assert c1["run_count"] == 2
    assert c1["total_tokens"] == 40
    assert c1["avg_latency_ms"] == 300
    assert c1["estimated_cost_usd"] == pytest.approx(0.000085)
    assert c1["has_unpriced"] is True
    assert c1["success_count"] == 2
    assert c1["error_count"] == 0
    assert c1["cancelled_count"] == 0
    assert c1["success_rate"] == 1

    # filter by user
    r2 = await seeded.get(f"/api/admin/analytics/chats?user_id={seeded._ids['bob']}")
    rows2 = r2.json()["items"]
    assert len(rows2) == 1 and rows2[0]["title"] == "Tenerife"


@pytest.mark.asyncio
async def test_chat_detail(seeded):
    await _login(seeded, "a@x")
    cid = seeded._ids["c1"]
    r = await seeded.get(f"/api/admin/analytics/chats/{cid}")
    assert r.status_code == 200
    d = r.json()
    assert d["range"] == "30d"
    assert d["chat"]["title"] == "Tenerife"
    assert d["chat"]["owner_username"] == "bob"
    assert len(d["messages"]) == 2
    assert d["messages"][0]["role"] == "user"
    assert len(d["runs"]) == 2
    assert d["runs"][0]["node_path"] == ["intake", "scout"]
    assert d["stats"]["run_count"] == 2
    assert d["stats"]["total_tokens"] == 40
    assert d["stats"]["prompt_tokens"] == 30
    assert d["stats"]["completion_tokens"] == 10
    assert d["stats"]["avg_latency_ms"] == 300
    assert d["stats"]["estimated_cost_usd"] == pytest.approx(0.000085)
    assert d["stats"]["has_unpriced"] is True
    assert d["stats"]["success_count"] == 2
    assert d["stats"]["error_count"] == 0
    assert d["stats"]["cancelled_count"] == 0
    assert d["stats"]["success_rate"] == 1
    assert all(r["outcome"] == "success" for r in d["runs"])
    assert d["runs"][0]["cost_usd"] == pytest.approx(0.000085)
    assert d["runs"][1]["cost_usd"] is None


@pytest.mark.asyncio
async def test_chat_detail_respects_range_while_chat_metadata_stays_lifetime(seeded):
    old = datetime.now(timezone.utc) - timedelta(days=100)
    async with seeded._sessionmaker() as s:
        s.add(Message(chat_id=seeded._ids["c1"], role="user", content="messaggio storico", created_at=old))
        s.add(RunTelemetry(
            chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"],
            node_path=["intake"], prompt_tokens=3, completion_tokens=2,
            total_tokens=5, latency_ms=100, model="gpt-5.4", ok=True,
            created_at=old,
        ))
        await s.commit()

    await _login(seeded, "a@x")
    chat_id = seeded._ids["c1"]
    scoped = (await seeded.get(f"/api/admin/analytics/chats/{chat_id}?range=7d")).json()
    lifetime = (await seeded.get(f"/api/admin/analytics/chats/{chat_id}?range=all")).json()

    assert scoped["range"] == "7d"
    assert scoped["chat"] == lifetime["chat"]
    assert [message["content"] for message in scoped["messages"]] == ["ciao", "ecco"]
    assert scoped["stats"]["message_count"] == 2
    assert scoped["stats"]["run_count"] == 2
    assert scoped["stats"]["total_tokens"] == 40
    assert lifetime["range"] == "all"
    assert lifetime["stats"]["message_count"] == 3
    assert lifetime["stats"]["run_count"] == 3
    assert lifetime["stats"]["total_tokens"] == 45
    assert any(message["content"] == "messaggio storico" for message in lifetime["messages"])


@pytest.mark.asyncio
async def test_non_admin_forbidden(seeded):
    await _login(seeded, "b@x")
    r = await seeded.get("/api/admin/analytics/overview")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_overview_has_cost_and_errors(seeded):
    await _login(seeded, "a@x")
    ov = (await seeded.get("/api/admin/analytics/overview")).json()
    assert ov["total_errors"] == 1
    assert "estimated_cost_usd" in ov
    assert ov["estimated_cost_usd"] == 0.000085
    assert ov["has_unpriced"] is True
    assert all("errors" in d for d in ov["by_day"])


@pytest.mark.asyncio
async def test_overview_range_all_vs_default(seeded):
    await _login(seeded, "a@x")
    # all three fixture runs are "now" -> both 30d default and all include them
    a = (await seeded.get("/api/admin/analytics/overview?range=all")).json()
    d = (await seeded.get("/api/admin/analytics/overview?range=7d")).json()
    assert a["total_runs"] == 3 and d["total_runs"] == 3


@pytest.mark.asyncio
async def test_paths_accepts_range(seeded):
    await _login(seeded, "a@x")
    r = await seeded.get("/api/admin/analytics/paths?range=30d")
    assert r.status_code == 200 and "paths" in r.json()


@pytest.mark.asyncio
async def test_chats_envelope_and_metrics(seeded):
    await _login(seeded, "a@x")
    body = (await seeded.get("/api/admin/analytics/chats")).json()
    assert set(body) == {"items", "total", "page", "page_size"}
    assert body["total"] == 2
    c1 = next(i for i in body["items"] if i["title"] == "Tenerife")
    # one aggregated query must not double-count: c1 has 2 messages and 2 runs
    assert c1["message_count"] == 2 and c1["run_count"] == 2 and c1["total_tokens"] == 40
    assert c1["estimated_cost_usd"] == pytest.approx(0.000085) and c1["has_unpriced"] is True


@pytest.mark.asyncio
async def test_chats_search_and_user_filter(seeded):
    await _login(seeded, "a@x")
    only = (await seeded.get("/api/admin/analytics/chats?q=tener")).json()["items"]
    assert [i["title"] for i in only] == ["Tenerife"]
    bob_id = seeded._ids["bob"]
    byuser = (await seeded.get(f"/api/admin/analytics/chats?user_id={bob_id}")).json()["items"]
    assert all(i["owner_id"] == bob_id for i in byuser)


@pytest.mark.asyncio
async def test_chats_sort_by_tokens(seeded):
    await _login(seeded, "a@x")
    items = (await seeded.get("/api/admin/analytics/chats?sort=total_tokens&order=desc")).json()["items"]
    assert items[0]["title"] == "Tenerife"  # 40 tokens vs Roma 10


@pytest.mark.asyncio
async def test_models_breakdown(seeded):
    await _login(seeded, "a@x")
    body = (await seeded.get("/api/admin/analytics/models")).json()
    row = next(i for i in body["items"] if i["model"] == "gpt-x")
    assert row["runs"] == 2 and row["successes"] == 1 and row["errors"] == 1
    assert row["cancelled"] == 0 and row["success_rate"] == 0.5
    assert row["cost_usd"] is None          # gpt-x is unpriced
    priced = next(i for i in body["items"] if i["model"] == "gpt-5.4")
    assert priced["runs"] == 1 and priced["cost_usd"] == pytest.approx(0.000085)
    assert priced["cost_per_run_usd"] == pytest.approx(0.000085)
    assert body["has_unpriced"] is True
    assert body["total_cost_usd"] == 0.000085


@pytest.mark.asyncio
async def test_errors_list(seeded):
    await _login(seeded, "a@x")
    body = (await seeded.get("/api/admin/analytics/errors")).json()
    assert body["total"] == 1
    e = body["items"][0]
    assert e["error"] == "boom" and e["chat_title"] == "Roma" and e["model"] == "gpt-x"
    # model filter that excludes the only error -> empty
    assert (await seeded.get("/api/admin/analytics/errors?model=nope")).json()["total"] == 0


@pytest.mark.asyncio
async def test_chats_export_csv(seeded):
    await _login(seeded, "a@x")
    r = await seeded.get("/api/admin/analytics/chats/export.csv?q=tener")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    import csv as _csv, io as _io
    rows = list(_csv.reader(_io.StringIO(r.text)))
    assert rows[0] == ["chat_id", "title", "owner", "created_at", "last_message_at",
                       "messages", "runs", "tokens", "avg_latency_ms",
                       "estimated_cost_usd", "has_unpriced", "successes",
                       "errors", "cancelled", "success_rate"]
    assert len(rows) == 2 and rows[1][1] == "Tenerife"


@pytest.mark.asyncio
async def test_analytics_owners(seeded):
    await _login(seeded, "a@x")
    owners = (await seeded.get("/api/admin/analytics/owners")).json()
    names = sorted(o["username"] for o in owners)
    assert names == ["admin", "bob"]  # both own a chat


@pytest.mark.asyncio
async def test_chat_detail_has_error_and_tool_calls(seeded):
    await _login(seeded, "a@x")
    cid = seeded._ids["c2"]  # Roma chat has the failed run with error "boom"
    body = (await seeded.get(f"/api/admin/analytics/chats/{cid}")).json()
    assert body["runs"][0]["error"] == "boom"
    # messages carry a tool_calls key (null when absent)
    cid1 = seeded._ids["c1"]
    d1 = (await seeded.get(f"/api/admin/analytics/chats/{cid1}")).json()
    assert all("tool_calls" in m for m in d1["messages"])


@pytest.mark.asyncio
async def test_range_reconciles_overview_and_chat_rows(seeded):
    """Old chats stay in scope when active; their old activity does not leak into the period."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=100)
    recent = now - timedelta(days=2)
    async with seeded._sessionmaker() as s:
        old_active = Chat(owner_id=seeded._ids["bob"], title="Old but active", created_at=old)
        stale = Chat(owner_id=seeded._ids["bob"], title="Stale", created_at=old)
        recent_empty = Chat(owner_id=seeded._ids["bob"], title="Recent empty", created_at=recent)
        s.add_all([old_active, stale, recent_empty]); await s.flush()
        s.add_all([
            Message(chat_id=old_active.id, role="user", content="old", created_at=old),
            Message(chat_id=old_active.id, role="user", content="recent", created_at=recent),
            Message(chat_id=stale.id, role="user", content="stale", created_at=old),
            RunTelemetry(chat_id=old_active.id, user_id=seeded._ids["bob"], node_path=["intake"],
                         total_tokens=11, latency_ms=100, model="gpt-5.4", ok=True, created_at=old),
            RunTelemetry(chat_id=old_active.id, user_id=seeded._ids["bob"], node_path=["intake"],
                         total_tokens=7, latency_ms=150, model="gpt-5.4", ok=True, created_at=recent),
            RunTelemetry(chat_id=stale.id, user_id=seeded._ids["bob"], node_path=["intake"],
                         total_tokens=13, latency_ms=100, model="gpt-5.4", ok=True, created_at=old),
        ])
        await s.commit()

    await _login(seeded, "a@x")
    bob = seeded._ids["bob"]
    overview = (await seeded.get(f"/api/admin/analytics/overview?range=30d&user_id={bob}")).json()
    chats = (await seeded.get(f"/api/admin/analytics/chats?range=30d&user_id={bob}&page_size=200")).json()
    assert overview["total_chats"] == chats["total"] == 3
    assert overview["total_users"] == 1
    assert overview["total_messages"] == sum(row["message_count"] for row in chats["items"]) == 3
    assert overview["total_runs"] == sum(row["run_count"] for row in chats["items"]) == 3
    names = {row["title"] for row in chats["items"]}
    assert names == {"Tenerife", "Old but active", "Recent empty"}
    active = next(row for row in chats["items"] if row["title"] == "Old but active")
    assert active["message_count"] == 1 and active["run_count"] == 1 and active["total_tokens"] == 7

    all_chats = (await seeded.get(f"/api/admin/analytics/chats?range=all&user_id={bob}&page_size=200")).json()
    assert all_chats["total"] == 4


@pytest.mark.asyncio
async def test_cancelled_runs_are_not_errors_or_success_rate_denominator(seeded):
    async with seeded._sessionmaker() as s:
        s.add_all([
            RunTelemetry(chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"], node_path=["intake"],
                         model="gpt-5.4", ok=False, error="stopped_by_user"),
            RunTelemetry(chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"], node_path=["intake"],
                         model="gpt-5.4", ok=False, error="superseded"),
            # A stale error string on a successful row must not double-count the outcome.
            RunTelemetry(chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"], node_path=["intake"],
                         model="gpt-5.4", ok=True, error="stopped_by_user"),
        ])
        await s.commit()

    await _login(seeded, "a@x")
    overview = (await seeded.get("/api/admin/analytics/overview?range=all")).json()
    assert overview["total_successes"] == 3
    assert overview["total_errors"] == 1
    assert overview["total_cancelled"] == 2
    assert overview["success_rate"] == round(3 / 4, 4)

    bob = seeded._ids["bob"]
    bob_overview = (await seeded.get(f"/api/admin/analytics/overview?range=all&user_id={bob}")).json()
    assert bob_overview["total_successes"] == 3
    assert bob_overview["total_errors"] == 0
    assert bob_overview["total_cancelled"] == 2
    assert bob_overview["success_rate"] == 1
    assert (await seeded.get(f"/api/admin/analytics/errors?range=all&user_id={bob}")).json()["total"] == 0
    assert (await seeded.get("/api/admin/analytics/errors?range=all")).json()["total"] == 1

    chat = (await seeded.get(f"/api/admin/analytics/chats?range=all&user_id={bob}")).json()["items"][0]
    assert chat["success_count"] == 3 and chat["error_count"] == 0
    assert chat["cancelled_count"] == 2 and chat["success_rate"] == 1
    detail = (await seeded.get(f"/api/admin/analytics/chats/{seeded._ids['c1']}")).json()
    assert [run["outcome"] for run in detail["runs"]].count("cancelled") == 2
    assert [run["outcome"] for run in detail["runs"]].count("success") == 3


@pytest.mark.asyncio
async def test_finite_range_zero_fills_every_calendar_day(seeded):
    await _login(seeded, "a@x")
    overview = (await seeded.get("/api/admin/analytics/overview?range=7d")).json()
    assert len(overview["by_day"]) == 7
    assert sum(day["runs"] for day in overview["by_day"]) == overview["total_runs"] == 3
    assert all({"successes", "errors", "cancelled", "estimated_cost_usd", "has_unpriced"} <= day.keys()
               for day in overview["by_day"])


@pytest.mark.asyncio
async def test_user_filter_applies_to_every_analytics_endpoint(seeded):
    await _login(seeded, "a@x")
    bob = seeded._ids["bob"]
    overview = (await seeded.get(f"/api/admin/analytics/overview?range=all&user_id={bob}")).json()
    assert overview["total_chats"] == 1 and overview["total_users"] == 1
    assert overview["total_messages"] == 2 and overview["total_runs"] == 2
    paths = (await seeded.get(f"/api/admin/analytics/paths?range=all&user_id={bob}")).json()["paths"]
    assert sum(path["count"] for path in paths) == 2
    models = (await seeded.get(f"/api/admin/analytics/models?range=all&user_id={bob}")).json()["items"]
    assert sum(model["runs"] for model in models) == 2
    chats = (await seeded.get(f"/api/admin/analytics/chats?range=all&user_id={bob}")).json()["items"]
    assert len(chats) == 1 and chats[0]["owner_id"] == bob
    assert (await seeded.get(f"/api/admin/analytics/errors?range=all&user_id={bob}")).json()["total"] == 0


@pytest.mark.asyncio
async def test_parallel_fanout_path_permutations_are_canonicalized(seeded):
    async with seeded._sessionmaker() as s:
        s.add_all([
            RunTelemetry(chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"],
                         node_path=["intake", "package", "flight", "hotel", "optimizer"],
                         model="gpt-5.4", ok=True),
            RunTelemetry(chat_id=seeded._ids["c1"], user_id=seeded._ids["bob"],
                         node_path=["intake", "flight", "package", "hotel", "optimizer"],
                         model="gpt-5.4", ok=True),
        ])
        await s.commit()

    await _login(seeded, "a@x")
    bob = seeded._ids["bob"]
    paths = (await seeded.get(f"/api/admin/analytics/paths?range=all&user_id={bob}")).json()["paths"]
    canonical = next(path for path in paths if path["path"] == [
        "intake", "flight", "hotel", "package", "optimizer",
    ])
    assert canonical["count"] == 2
