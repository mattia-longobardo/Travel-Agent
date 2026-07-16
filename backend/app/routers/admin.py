import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.deps import require_admin, get_session_store
from app.models import Chat, ChatGroup, ChatShare, Group, Message, RunTelemetry, User, UserSettings
from app.pricing import MODEL_PRICING, cost_usd
from app.schemas import BulkResult, BulkUsersIn, GroupIn, UserCreate, UserOut, UsersPage, UserUpdate, UsersStats
from app.security import hash_password, normalize_email
from app.sessions import SessionStore

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s and s[0] in ("=", "+", "-", "@", "\t", "\r") else s


def _users_query(q: str | None, status: str, role: str, group_id: int | None):
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(User.username.ilike(like) | User.email.ilike(like))
    if status == "active":
        stmt = stmt.where(User.is_active == True)  # noqa: E712
    elif status == "inactive":
        stmt = stmt.where(User.is_active == False)  # noqa: E712
    if role == "admin":
        stmt = stmt.where(User.is_admin == True)  # noqa: E712
    elif role == "user":
        stmt = stmt.where(User.is_admin == False)  # noqa: E712
    if group_id is not None:
        stmt = stmt.where(User.group_id == group_id)
    return stmt


_SORT_COLS = {"username": User.username, "email": User.email,
              "created_at": User.created_at, "is_active": User.is_active}


@router.get("/users", response_model=UsersPage)
async def list_users(
    q: str | None = None,
    status_: str = Query("all", alias="status"),
    role: str = Query("all"),
    group_id: int | None = None,
    sort: str = Query("username"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    base = _users_query(q, status_, role, group_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    col = _SORT_COLS.get(sort, User.username)
    col = col.desc() if order == "desc" else col.asc()
    rows = (await db.execute(
        base.order_by(col).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return {"items": rows, "total": int(total), "page": page, "page_size": page_size}


@router.get("/users/export.csv")
async def export_users_csv(
    q: str | None = None,
    status_: str = Query("all", alias="status"),
    role: str = Query("all"),
    group_id: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    rows = (await db.execute(
        _users_query(q, status_, role, group_id).order_by(User.username))).scalars().all()
    groups = {g.id: g.name for g in (await db.execute(select(Group))).scalars().all()}
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["id", "username", "email", "role", "active", "group"])
    for u in rows:
        w.writerow([_csv_safe(c) for c in (
            u.id, u.username, u.email, "admin" if u.is_admin else "user",
            "true" if u.is_active else "false", groups.get(u.group_id, ""))])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=users.csv"})


@router.get("/users/stats", response_model=UsersStats)
async def users_stats(db: AsyncSession = Depends(get_session)):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    active = (await db.execute(select(func.count()).select_from(User)
                               .where(User.is_active == True))).scalar_one()  # noqa: E712
    admins = (await db.execute(select(func.count()).select_from(User)
                               .where(User.is_admin == True))).scalar_one()  # noqa: E712
    return {"total": int(total), "active": int(active),
            "inactive": int(total) - int(active), "admins": int(admins)}


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_session)):
    if (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none():
        raise HTTPException(409, "Username taken")
    email = normalize_email(body.email)
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(409, "Email già in uso")
    u = User(username=body.username, email=email, password_hash=hash_password(body.password),
             group_id=body.group_id, is_admin=body.is_admin)
    db.add(u); await db.commit(); await db.refresh(u)
    return u


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate,
                      db: AsyncSession = Depends(get_session),
                      store: SessionStore = Depends(get_session_store)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Not found")
    if body.username is not None and body.username != u.username:
        dup = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
        if dup:
            raise HTTPException(409, "Username già in uso")
        u.username = body.username
    if body.email is not None:
        email = normalize_email(body.email)
        if email != u.email:
            dup = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if dup:
                raise HTTPException(409, "Email già in uso")
            u.email = email
    if body.group_id is not None: u.group_id = body.group_id
    if body.is_admin is not None:
        if body.is_admin is False and u.is_admin:
            admin_count = (await db.execute(
                select(func.count()).select_from(User).where(User.is_admin == True))).scalar_one()
            if admin_count <= 1:
                raise HTTPException(400, "Deve restare almeno un amministratore")
        u.is_admin = body.is_admin
    if body.password is not None: u.password_hash = hash_password(body.password)
    if body.is_active is not None:
        u.is_active = body.is_active
        if body.is_active is False:
            await store.delete_user_sessions(u.id)
    await db.commit(); await db.refresh(u)
    return u


async def _purge_user_data(db: AsyncSession, user_ids: list[int]) -> None:
    if not user_ids:
        return
    owned_chat_ids = (await db.execute(
        select(Chat.id).where(Chat.owner_id.in_(user_ids)))).scalars().all()
    await db.execute(delete(RunTelemetry).where(
        (RunTelemetry.user_id.in_(user_ids)) | (RunTelemetry.chat_id.in_(owned_chat_ids))))
    if owned_chat_ids:
        await db.execute(delete(Message).where(Message.chat_id.in_(owned_chat_ids)))
    await db.execute(delete(ChatShare).where(
        (ChatShare.user_id.in_(user_ids)) | (ChatShare.chat_id.in_(owned_chat_ids))))
    await db.execute(delete(Chat).where(Chat.owner_id.in_(user_ids)))
    await db.execute(delete(ChatGroup).where(ChatGroup.owner_id.in_(user_ids)))
    await db.execute(delete(UserSettings).where(UserSettings.user_id.in_(user_ids)))
    await db.execute(delete(User).where(User.id.in_(user_ids)))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int,
                      me: User = Depends(require_admin),
                      db: AsyncSession = Depends(get_session),
                      store: SessionStore = Depends(get_session_store)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(404, "Not found")
    if u.id == me.id:
        raise HTTPException(400, "Non puoi eliminare il tuo stesso account")
    if u.is_admin:
        admin_count = (await db.execute(
            select(func.count()).select_from(User).where(User.is_admin == True))).scalar_one()  # noqa: E712
        if admin_count <= 1:
            raise HTTPException(400, "Deve restare almeno un amministratore")

    await _purge_user_data(db, [user_id])
    await db.commit()
    await store.delete_user_sessions(user_id)


@router.post("/users/bulk", response_model=BulkResult)
async def bulk_users(body: BulkUsersIn,
                     me: User = Depends(require_admin),
                     db: AsyncSession = Depends(get_session),
                     store: SessionStore = Depends(get_session_store)):
    if body.action not in {"activate", "deactivate", "set_group", "set_admin", "delete"}:
        raise HTTPException(400, "Azione non valida")
    if body.all_matching:
        f = body.filters or {}
        stmt = _users_query(f.get("q"), f.get("status", "all"),
                            f.get("role", "all"), f.get("group_id"))
        ids = (await db.execute(stmt.with_only_columns(User.id))).scalars().all()
    else:
        ids = list(body.user_ids or [])

    users = {u.id: u for u in (await db.execute(
        select(User).where(User.id.in_(ids)))).scalars().all()}
    total_admins = (await db.execute(
        select(func.count()).select_from(User).where(User.is_admin == True))).scalar_one()  # noqa: E712

    remaining_admins = int(total_admins)
    skipped: list[dict] = []
    targets: list[User] = []
    for uid in ids:
        u = users.get(uid)
        if u is None:
            continue
        if u.id == me.id:
            skipped.append({"id": uid, "reason": "self"}); continue
        removes_admin = u.is_admin and (
            body.action == "delete" or (body.action == "set_admin" and body.value is False))
        if removes_admin:
            if remaining_admins <= 1:
                skipped.append({"id": uid, "reason": "last_admin"}); continue
            remaining_admins -= 1
        targets.append(u)

    target_ids = [u.id for u in targets]
    if body.action == "activate":
        for u in targets: u.is_active = True
    elif body.action == "deactivate":
        for u in targets:
            u.is_active = False
    elif body.action == "set_group":
        for u in targets: u.group_id = body.group_id
    elif body.action == "set_admin":
        for u in targets: u.is_admin = bool(body.value)
    elif body.action == "delete":
        await _purge_user_data(db, target_ids)

    await db.commit()
    if body.action in {"deactivate", "delete"}:
        for uid in target_ids:
            await store.delete_user_sessions(uid)
    return {"affected": len(target_ids), "skipped": skipped}


@router.get("/groups")
async def list_groups(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(select(Group))).scalars().all()
    return [{"id": g.id, "name": g.name} for g in rows]


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(body: GroupIn, db: AsyncSession = Depends(get_session)):
    g = Group(name=body.name)
    db.add(g); await db.commit(); await db.refresh(g)
    return {"id": g.id, "name": g.name}


# --- Analytics (admin-only, behind require_admin via the router dependency) ----------------


def _iso(dt):
    return dt.isoformat() if dt is not None else None


_RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}
_CANCELLED_ERRORS = ("stopped_by_user", "superseded")
_FANOUT_ORDER = ("flight", "hotel", "package")


def _analytics_cutoff(range_: str):
    if range_ == "all":
        return None
    days = _RANGE_DAYS.get(range_, 30)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=days - 1)


def _is_cancelled_condition():
    return and_(RunTelemetry.ok == False, RunTelemetry.error.in_(_CANCELLED_ERRORS))  # noqa: E712


def _is_technical_error_condition():
    return and_(
        RunTelemetry.ok == False,  # noqa: E712
        or_(RunTelemetry.error.is_(None), RunTelemetry.error.notin_(_CANCELLED_ERRORS)),
    )


def _success_expr():
    return case((RunTelemetry.ok == True, 1), else_=0)  # noqa: E712


def _technical_error_expr():
    return case((_is_technical_error_condition(), 1), else_=0)


def _cancelled_expr():
    return case((_is_cancelled_condition(), 1), else_=0)


def _run_outcome(ok: bool, error: str | None) -> str:
    if not ok and error in _CANCELLED_ERRORS:
        return "cancelled"
    return "success" if ok else "error"


def _canonical_node_path(node_path) -> list[str]:
    """Normalize the parallel search fan-out without reordering the other graph stages."""
    canonical: list[str] = []
    fanout: set[str] = set()

    def flush_fanout() -> None:
        for node in _FANOUT_ORDER:
            if node in fanout:
                canonical.append(node)
        fanout.clear()

    for raw_node in node_path or []:
        node = str(raw_node)
        if node in _FANOUT_ORDER:
            fanout.add(node)
        else:
            flush_fanout()
            canonical.append(node)
    flush_fanout()
    return canonical


def _filter_run_stmt(stmt, cutoff, user_id: int | None):
    if cutoff is not None:
        stmt = stmt.where(RunTelemetry.created_at >= cutoff)
    if user_id is not None:
        stmt = stmt.where(Chat.owner_id == user_id)
    return stmt


def _chat_scope_stmt(cutoff, user_id: int | None):
    stmt = select(Chat.id.label("chat_id"), Chat.owner_id.label("owner_id"))
    if cutoff is not None:
        has_message = select(Message.id).where(
            Message.chat_id == Chat.id, Message.created_at >= cutoff,
        ).correlate(Chat).exists()
        has_run = select(RunTelemetry.id).where(
            RunTelemetry.chat_id == Chat.id, RunTelemetry.created_at >= cutoff,
        ).correlate(Chat).exists()
        stmt = stmt.where(or_(Chat.created_at >= cutoff, has_message, has_run))
    if user_id is not None:
        stmt = stmt.where(Chat.owner_id == user_id)
    return stmt


def _run_cost_expr():
    whens = [
        (RunTelemetry.model == model,
         (func.coalesce(RunTelemetry.prompt_tokens, 0) * rates["input"]
          + func.coalesce(RunTelemetry.completion_tokens, 0) * rates["output"]) / 1_000_000)
        for model, rates in MODEL_PRICING.items()
    ]
    return case(*whens, else_=None)


def _run_unpriced_expr():
    whens = [(RunTelemetry.model == model, 0) for model in MODEL_PRICING]
    return case(*whens, else_=1)


async def _model_cost_rows(db: AsyncSession, cutoff, user_id: int | None = None) -> list[dict]:
    stmt = select(
        RunTelemetry.model,
        func.count(),
        func.coalesce(func.sum(RunTelemetry.prompt_tokens), 0),
        func.coalesce(func.sum(RunTelemetry.completion_tokens), 0),
        func.coalesce(func.sum(RunTelemetry.total_tokens), 0),
        func.coalesce(func.avg(RunTelemetry.latency_ms), 0),
        func.coalesce(func.sum(_success_expr()), 0),
        func.coalesce(func.sum(_technical_error_expr()), 0),
        func.coalesce(func.sum(_cancelled_expr()), 0),
    ).select_from(RunTelemetry).join(Chat, RunTelemetry.chat_id == Chat.id).group_by(RunTelemetry.model)
    stmt = _filter_run_stmt(stmt, cutoff, user_id)
    out = []
    for model, runs, p, c, t, lat, successes, errors, cancelled in (await db.execute(stmt)).all():
        run_cost = cost_usd(model, int(p), int(c))
        decided = int(successes) + int(errors)
        out.append({
            "model": model, "runs": int(runs), "prompt_tokens": int(p),
            "completion_tokens": int(c), "total_tokens": int(t),
            "avg_latency_ms": round(float(lat or 0)), "successes": int(successes),
            "errors": int(errors), "cancelled": int(cancelled),
            "success_rate": round(int(successes) / decided, 4) if decided else 0.0,
            "cost_usd": run_cost,
            "cost_per_run_usd": round(run_cost / int(runs), 6) if run_cost is not None and runs else None,
        })
    return out


@router.get("/analytics/overview")
async def analytics_overview(
    range: str = Query("30d"),
    user_id: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    cutoff = _analytics_cutoff(range)
    chat_scope = _chat_scope_stmt(cutoff, user_id).subquery()
    total_chats = (await db.execute(select(func.count()).select_from(chat_scope))).scalar_one()
    total_users = (await db.execute(
        select(func.count(func.distinct(chat_scope.c.owner_id))).select_from(chat_scope)
    )).scalar_one()

    messages_q = select(func.count()).select_from(Message).join(Chat, Message.chat_id == Chat.id)
    if cutoff is not None:
        messages_q = messages_q.where(Message.created_at >= cutoff)
    if user_id is not None:
        messages_q = messages_q.where(Chat.owner_id == user_id)
    total_messages = (await db.execute(messages_q)).scalar_one()

    agg_q = select(
        func.count(),
        func.coalesce(func.sum(RunTelemetry.prompt_tokens), 0),
        func.coalesce(func.sum(RunTelemetry.completion_tokens), 0),
        func.coalesce(func.sum(RunTelemetry.total_tokens), 0),
        func.coalesce(func.avg(RunTelemetry.latency_ms), 0),
        func.coalesce(func.sum(_success_expr()), 0),
        func.coalesce(func.sum(_technical_error_expr()), 0),
        func.coalesce(func.sum(_cancelled_expr()), 0),
    ).select_from(RunTelemetry).join(Chat, RunTelemetry.chat_id == Chat.id)
    agg_q = _filter_run_stmt(agg_q, cutoff, user_id)
    total_runs, p_tok, c_tok, t_tok, avg_lat, successes, errors, cancelled = (
        await db.execute(agg_q)
    ).one()
    decided_runs = int(successes) + int(errors)
    success_rate = (int(successes) / decided_runs) if decided_runs else 0.0
    error_rate = (int(errors) / decided_runs) if decided_runs else 0.0

    cost_rows = await _model_cost_rows(db, cutoff, user_id)
    estimated_cost = round(sum(r["cost_usd"] or 0.0 for r in cost_rows), 6)
    has_unpriced = any(r["cost_usd"] is None and r["runs"] > 0 for r in cost_rows)

    by_day_q = select(
        func.date(RunTelemetry.created_at).label("day"),
        func.count(),
        func.coalesce(func.sum(RunTelemetry.total_tokens), 0),
        func.coalesce(func.avg(RunTelemetry.latency_ms), 0),
        func.coalesce(func.sum(_success_expr()), 0),
        func.coalesce(func.sum(_technical_error_expr()), 0),
        func.coalesce(func.sum(_cancelled_expr()), 0),
        func.coalesce(func.sum(_run_cost_expr()), 0),
        func.coalesce(func.max(_run_unpriced_expr()), 0),
    ).select_from(RunTelemetry).join(Chat, RunTelemetry.chat_id == Chat.id).group_by("day").order_by("day")
    by_day_q = _filter_run_stmt(by_day_q, cutoff, user_id)
    by_day_rows = {
        str(day): {
            "day": str(day), "runs": int(runs), "tokens": int(tokens),
            "avg_latency_ms": round(float(avg_latency or 0)),
            "successes": int(day_successes), "errors": int(day_errors),
            "cancelled": int(day_cancelled),
            "estimated_cost_usd": round(float(day_cost or 0), 6),
            "has_unpriced": bool(day_unpriced),
        }
        for day, runs, tokens, avg_latency, day_successes, day_errors, day_cancelled, day_cost, day_unpriced
        in (await db.execute(by_day_q)).all()
    }
    if cutoff is None:
        by_day = list(by_day_rows.values())
    else:
        by_day = []
        day = cutoff.date()
        today = datetime.now(timezone.utc).date()
        while day <= today:
            key = day.isoformat()
            by_day.append(by_day_rows.get(key, {
                "day": key, "runs": 0, "tokens": 0, "avg_latency_ms": 0,
                "successes": 0, "errors": 0, "cancelled": 0,
                "estimated_cost_usd": 0.0, "has_unpriced": False,
            }))
            day += timedelta(days=1)

    return {
        "total_chats": int(total_chats), "total_users": int(total_users),
        "total_messages": int(total_messages), "total_runs": int(total_runs),
        "total_prompt_tokens": int(p_tok), "total_completion_tokens": int(c_tok),
        "total_tokens": int(t_tok), "avg_latency_ms": round(float(avg_lat or 0)),
        "total_successes": int(successes), "total_errors": int(errors),
        "total_cancelled": int(cancelled), "success_rate": round(float(success_rate), 4),
        "error_rate": round(float(error_rate), 4),
        "estimated_cost_usd": estimated_cost, "has_unpriced": has_unpriced,
        "by_day": by_day,
    }


@router.get("/analytics/models")
async def analytics_models(
    range: str = Query("30d"),
    user_id: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    rows = await _model_cost_rows(db, _analytics_cutoff(range), user_id)
    total = round(sum(r["cost_usd"] or 0.0 for r in rows), 6)
    has_unpriced = any(r["cost_usd"] is None and r["runs"] > 0 for r in rows)
    rows.sort(key=lambda r: r["total_tokens"], reverse=True)
    return {"items": rows, "total_cost_usd": total, "has_unpriced": has_unpriced}


@router.get("/analytics/paths")
async def analytics_paths(
    range: str = Query("30d"),
    user_id: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    cutoff = _analytics_cutoff(range)
    base = select(
        RunTelemetry.node_path, RunTelemetry.latency_ms, RunTelemetry.total_tokens,
    ).select_from(RunTelemetry).join(Chat, RunTelemetry.chat_id == Chat.id)
    base = _filter_run_stmt(base, cutoff, user_id)
    rows = (await db.execute(base)).all()
    # Group by node_path in Python (JSON column grouping is awkward across engines).
    buckets: dict[tuple, dict] = {}
    for node_path, latency, tokens in rows:
        key = tuple(_canonical_node_path(node_path))
        b = buckets.setdefault(key, {"count": 0, "lat": 0, "tok": 0})
        b["count"] += 1
        b["lat"] += int(latency or 0)
        b["tok"] += int(tokens or 0)
    paths = [{
        "path": list(key),
        "count": b["count"],
        "avg_latency_ms": round(b["lat"] / b["count"]) if b["count"] else 0,
        "avg_tokens": round(b["tok"] / b["count"]) if b["count"] else 0,
    } for key, b in buckets.items()]
    paths.sort(key=lambda p: p["count"], reverse=True)
    return {"paths": paths}


def _chats_query(cutoff, q: str | None, user_id: int | None):
    msg_agg_stmt = select(
        Message.chat_id.label("cid"),
        func.count().label("mc"),
        func.max(Message.created_at).label("last"),
    ).group_by(Message.chat_id)
    if cutoff is not None:
        msg_agg_stmt = msg_agg_stmt.where(Message.created_at >= cutoff)
    msg_agg = msg_agg_stmt.subquery()

    run_agg_stmt = select(
        RunTelemetry.chat_id.label("cid"),
        func.count().label("rc"),
        func.coalesce(func.sum(RunTelemetry.total_tokens), 0).label("tok"),
        func.coalesce(func.avg(RunTelemetry.latency_ms), 0).label("lat"),
        func.coalesce(func.sum(_run_cost_expr()), 0).label("cost"),
        func.coalesce(func.max(_run_unpriced_expr()), 0).label("has_unpriced"),
        func.coalesce(func.sum(_success_expr()), 0).label("successes"),
        func.coalesce(func.sum(_technical_error_expr()), 0).label("errors"),
        func.coalesce(func.sum(_cancelled_expr()), 0).label("cancelled"),
    ).group_by(RunTelemetry.chat_id)
    if cutoff is not None:
        run_agg_stmt = run_agg_stmt.where(RunTelemetry.created_at >= cutoff)
    run_agg = run_agg_stmt.subquery()

    mc = func.coalesce(msg_agg.c.mc, 0).label("message_count")
    last = msg_agg.c.last.label("last_message_at")
    rc = func.coalesce(run_agg.c.rc, 0).label("run_count")
    tok = func.coalesce(run_agg.c.tok, 0).label("total_tokens")
    lat = func.coalesce(run_agg.c.lat, 0).label("avg_latency_ms")
    cost = func.coalesce(run_agg.c.cost, 0).label("estimated_cost_usd")
    has_unpriced = func.coalesce(run_agg.c.has_unpriced, 0).label("has_unpriced")
    successes = func.coalesce(run_agg.c.successes, 0).label("success_count")
    errors = func.coalesce(run_agg.c.errors, 0).label("error_count")
    cancelled = func.coalesce(run_agg.c.cancelled, 0).label("cancelled_count")
    decided = successes + errors
    success_rate = case(
        (decided > 0, successes * 1.0 / decided), else_=0.0,
    ).label("success_rate")

    # Fixed column order: 0 id, 1 title, 2 owner_id, 3 username, 4 created_at,
    # 5 message_count, 6 last_message_at, 7 run_count, 8 total_tokens,
    # 9 avg_latency_ms, 10 estimated_cost_usd, 11 has_unpriced,
    # 12 successes, 13 errors, 14 cancelled, 15 success_rate
    base = (select(
        Chat.id, Chat.title, Chat.owner_id, User.username, Chat.created_at,
        mc, last, rc, tok, lat, cost, has_unpriced,
        successes, errors, cancelled, success_rate,
    ).join(User, Chat.owner_id == User.id)
     .join(msg_agg, msg_agg.c.cid == Chat.id, isouter=True)
     .join(run_agg, run_agg.c.cid == Chat.id, isouter=True))
    if q:
        like = f"%{q}%"
        base = base.where(Chat.title.ilike(like) | User.username.ilike(like))
    if user_id is not None:
        base = base.where(Chat.owner_id == user_id)
    if cutoff is not None:
        base = base.where(or_(
            Chat.created_at >= cutoff,
            msg_agg.c.cid.is_not(None),
            run_agg.c.cid.is_not(None),
        ))
    labels = {"created_at": Chat.created_at, "last_message_at": last,
              "message_count": mc, "run_count": rc, "total_tokens": tok,
              "avg_latency_ms": lat, "estimated_cost_usd": cost}
    return base, labels


@router.get("/analytics/chats")
async def analytics_chats(
    q: str | None = None,
    user_id: int | None = None,
    range: str = Query("30d"),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    base, labels = _chats_query(_analytics_cutoff(range), q, user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    col = labels.get(sort, Chat.created_at)
    col = col.desc() if order == "desc" else col.asc()
    rows = (await db.execute(
        base.order_by(col).offset((page - 1) * page_size).limit(page_size))).all()
    items = [{
        "chat_id": r[0], "title": r[1], "owner_id": r[2], "owner_username": r[3],
        "created_at": _iso(r[4]), "last_message_at": _iso(r[6]),
        "message_count": int(r[5]), "run_count": int(r[7]),
        "total_tokens": int(r[8]), "avg_latency_ms": round(float(r[9] or 0)),
        "estimated_cost_usd": round(float(r[10] or 0), 6),
        "has_unpriced": bool(r[11]),
        "success_count": int(r[12]), "error_count": int(r[13]),
        "cancelled_count": int(r[14]), "success_rate": round(float(r[15] or 0), 4),
    } for r in rows]
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


@router.get("/analytics/chats/export.csv")
async def analytics_chats_export(
    q: str | None = None,
    user_id: int | None = None,
    range: str = Query("30d"),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_session),
):
    base, labels = _chats_query(_analytics_cutoff(range), q, user_id)
    col = labels.get(sort, Chat.created_at)
    col = col.desc() if order == "desc" else col.asc()
    rows = (await db.execute(base.order_by(col))).all()
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["chat_id", "title", "owner", "created_at", "last_message_at",
                "messages", "runs", "tokens", "avg_latency_ms",
                "estimated_cost_usd", "has_unpriced", "successes",
                "errors", "cancelled", "success_rate"])
    for r in rows:
        w.writerow([_csv_safe(c) for c in (
            r[0], r[1], r[3], _iso(r[4]), _iso(r[6]),
            int(r[5]), int(r[7]), int(r[8]), round(float(r[9] or 0)),
            round(float(r[10] or 0), 6), bool(r[11]), int(r[12]), int(r[13]),
            int(r[14]), round(float(r[15] or 0), 4))])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=chats.csv"})


@router.get("/analytics/chats/{chat_id}")
async def analytics_chat_detail(
    chat_id: int,
    range: str = Query("30d"),
    db: AsyncSession = Depends(get_session),
):
    chat = await db.get(Chat, chat_id)
    if chat is None:
        raise HTTPException(404, "Not found")
    owner = await db.get(User, chat.owner_id)

    cutoff = _analytics_cutoff(range)
    messages_stmt = select(Message).where(Message.chat_id == chat_id)
    runs_stmt = select(RunTelemetry).where(RunTelemetry.chat_id == chat_id)
    if cutoff is not None:
        messages_stmt = messages_stmt.where(Message.created_at >= cutoff)
        runs_stmt = runs_stmt.where(RunTelemetry.created_at >= cutoff)
    msgs = (await db.execute(messages_stmt.order_by(Message.id))).scalars().all()
    runs = (await db.execute(runs_stmt.order_by(RunTelemetry.id))).scalars().all()

    run_count = len(runs)
    total_tokens = sum(int(r.total_tokens or 0) for r in runs)
    prompt_tokens = sum(int(r.prompt_tokens or 0) for r in runs)
    completion_tokens = sum(int(r.completion_tokens or 0) for r in runs)
    avg_latency_ms = round(sum(int(r.latency_ms or 0) for r in runs) / run_count) if run_count else 0
    run_costs = [cost_usd(r.model, int(r.prompt_tokens or 0), int(r.completion_tokens or 0)) for r in runs]
    estimated_cost_usd = round(sum(c or 0.0 for c in run_costs), 6)
    has_unpriced = any(c is None for c in run_costs)
    outcomes = [_run_outcome(bool(r.ok), r.error) for r in runs]
    success_count = outcomes.count("success")
    error_count = outcomes.count("error")
    cancelled_count = outcomes.count("cancelled")
    decided_count = success_count + error_count

    return {
        "range": range,
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "owner_username": owner.username if owner else None,
            "created_at": _iso(chat.created_at),
        },
        "messages": [{"role": m.role, "content": m.content, "created_at": _iso(m.created_at),
                      "tool_calls": m.tool_calls_json} for m in msgs],
        "runs": [{
            "created_at": _iso(r.created_at),
            "node_path": _canonical_node_path(r.node_path),
            "total_tokens": int(r.total_tokens or 0),
            "latency_ms": int(r.latency_ms or 0),
            "model": r.model,
            "cost_usd": run_costs[i],
            "ok": bool(r.ok),
            "error": r.error,
            "outcome": outcomes[i],
        } for i, r in enumerate(runs)],
        "stats": {
            "message_count": len(msgs),
            "run_count": run_count,
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "has_unpriced": has_unpriced,
            "success_count": success_count,
            "error_count": error_count,
            "cancelled_count": cancelled_count,
            "success_rate": round(success_count / decided_count, 4) if decided_count else 0.0,
        },
    }


@router.get("/analytics/owners")
async def analytics_owners(db: AsyncSession = Depends(get_session)):
    rows = (await db.execute(
        select(User.id, User.username).join(Chat, Chat.owner_id == User.id)
        .group_by(User.id, User.username).order_by(User.username))).all()
    return [{"id": uid, "username": name} for uid, name in rows]


@router.get("/analytics/errors")
async def analytics_errors(
    range: str = Query("30d"),
    model: str | None = None,
    user_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    cutoff = _analytics_cutoff(range)
    base = (select(
        RunTelemetry.created_at, RunTelemetry.chat_id, Chat.title, User.username,
        RunTelemetry.model, RunTelemetry.error, RunTelemetry.latency_ms,
    ).join(Chat, RunTelemetry.chat_id == Chat.id)
     .join(User, Chat.owner_id == User.id)
     .where(_is_technical_error_condition()))
    if cutoff is not None:
        base = base.where(RunTelemetry.created_at >= cutoff)
    if model:
        base = base.where(RunTelemetry.model == model)
    if user_id is not None:
        base = base.where(Chat.owner_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (await db.execute(
        base.order_by(RunTelemetry.created_at.desc())
            .offset((page - 1) * page_size).limit(page_size))).all()
    items = [{
        "created_at": _iso(r[0]), "chat_id": r[1], "chat_title": r[2],
        "owner_username": r[3], "model": r[4], "error": r[5], "latency_ms": int(r[6] or 0),
    } for r in rows]
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}
