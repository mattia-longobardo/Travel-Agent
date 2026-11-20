# Travel Agent

Self-hosted AI travel planning assistant on `travel.longobardo.me`. A LangGraph multi-agent backend (FastAPI) and a Next.js 16 frontend, connected through Server-Sent Events, find and compare flights, hotels and flight+hotel packages by dates, budget and preferences. Search data comes from the lastminute MCP through the `mcp-remote` stdio bridge. Multi-user, with per-user chat history, sharing and autosave to PostgreSQL.

## Architecture

- **Backend** (`backend/`, FastAPI): a LangGraph state machine with 7 agents in sequence: Intake (parses the query, origin from browser geolocation), Destination Scout, Flight, Hotel, Package, Budget Optimizer, Presenter. Each agent has a scoped subset of the lastminute tools. Checkpointing uses `MemorySaver` (single instance).
- **SSE contract**: `POST /api/chats/{chat_id}/messages` streams JSON lines: `agent_step`, `question` (stops the stream), `package`, `message`, `done`.
- **Frontend** (`frontend/`, Next.js 16, React 19, Tailwind v4, shadcn/ui): `/login` and the chat at `/` (agent timeline, question chips, package cards).
- **Data**: shared PostgreSQL (`db_internal`) for users, chats, messages and settings; shared Redis (DB index 4) for sessions.
- **Image**: one container (`travel-agent`). `entrypoint.sh` runs the migrations, then FastAPI on `:8000` and Next.js on `:3000`; Next.js proxies `/api` to the backend on loopback. Traefik routes to `:3000` on `proxy_public`.

## Run

```bash
make help      # list the targets
make install   # frontend dependencies (the backend runs through uv)
make lint      # ESLint on the frontend
make test      # backend tests (SQLite + fakeredis, no services) and frontend tests
make deploy    # build and start travel-agent from the parent Compose project (../)
```

The stack belongs to the homelab `travel/` Compose project (`travel/docker-compose.yml` includes this file): deploy from there, never from this folder alone.

## Configure

Copy `.env.example` to `.env` and fill it in. On the homeserver the `.env` is rendered from Infisical (`/travel/travel-agent`).

| Variable | Purpose |
|---|---|
| `TRAVEL_HOST` | Public hostname (Traefik rule) |
| `TZ` | Time zone |
| `SESSION_SECRET` | Session signing key (32+ chars) |
| `POSTGRES_USER`, `POSTGRES_DB`, `DB_TRAVEL_PASSWORD` | Shared PostgreSQL |
| `TRAVEL_AGENT_REDIS_PASSWORD` | Shared Redis |
| `TRAVEL_AGENT_OPENAI_API_KEY`, `OPENAI_MODEL` | LLM calls |
| `LASTMINUTE_MCP_URL` | lastminute MCP endpoint (anonymous search) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | First admin, created at startup |

## License

Copyright (c) 2026 Mattia Longobardo. Licensed under [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/), see [LICENSE](LICENSE): no commercial use and no derivative versions.
