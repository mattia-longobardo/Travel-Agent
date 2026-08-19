# Travel Agent

A self-hosted AI travel planning assistant powered by a **LangGraph multi-agent backend** and **Next.js 16 frontend**, connected via Server-Sent Events (SSE). The assistant helps users find and compare flights, hotels, and flight+hotel packages based on flexible dates, budgets, and preferences. Data sourced from the lastminute MCP via the `mcp-remote` stdio bridge. Multi-user with per-user chat history, read/write-sharing, and autosave to Postgres. Exposed on `travel.longobardo.me` behind Traefik.

## Architecture Overview

### Backend: LangGraph Multi-Agent System (FastAPI)

The backend is a LangGraph state machine that runs 7 specialized agents in orchestrated sequence:

1. **Intake Agent** — Parses user query (dates, budget, preferences, origin city). Infers origin from browser geolocation if not provided.
2. **Destination Scout Agent** — Searches top destinations matching user criteria via lastminute Search tools.
3. **Flight Agent** — Searches outbound and return flights for each candidate destination.
4. **Hotel Agent** — Searches hotels at each destination.
5. **Package Agent** — Combines flight+hotel pairs and calculates total prices.
6. **Budget Optimizer Agent** — Ranks packages by price/rating/reviews and filters by user budget.
7. **Presenter Agent** — Formats final ranked packages as cards with summaries.

Each agent has a scoped subset of lastminute MCP tools (Flight Search, Hotel Search, Package Search). Checkpointing uses `MemorySaver` (single-instance; multi-instance durable checkpointing is deferred).

**SSE Streaming Contract:**

The backend streams events in real-time to the frontend as JSON-per-line (`text/event-stream`):

- `agent_step` — Agent transition (running/done); includes agent name and status label.
- `question` — Pending question requiring user input; stops streaming.
- `package` — One ranked card (outbound flight, hotel, total price, rating, review score).
- `message` — Final summary message.
- `done` — End marker.

Clients listen on `POST /api/chats/{chat_id}/messages` and consume the stream.

### Frontend: Next.js 16 (React 19, TypeScript, Tailwind v4, shadcn/ui)

Single-screen immersive chat:

- **App Router** with `frontend/app/` structure.
- **Login page** at `/login`; redirects authenticated users to root.
- **Chat page** at `/` — one-column layout with message history above, input box below. Receives agents' SSE events and renders:
  - Agent step timeline (each agent running/done transitions).
  - Question chips (if pending question).
  - Package cards (flights + hotels + total, ranked by price).
- No separate admin/settings panels in this redesign.
- Node.js standalone container (`port 3000`), configured via `BACKEND_URL=http://travel-backend:8000`.

### Data Layer

- **PostgreSQL + pgvector** — User, Chat, Message, and admin settings.
- **Redis 7** — Session store.
- **lastminute MCP** — Flight/hotel/package search (no API key required for anonymous search).

### Reverse Proxy

- Traefik (`network/` stack) forwards `https://travel.longobardo.me` to backend `/api` and frontend root.
- TLS terminated upstream by Cloudflare tunnel.

## Running Standalone

This stack runs **standalone** from its own directory; there is no parent `projects/` aggregator compose file (but one can be added later with an `include:`).

### Setup & Environment

1. **Prepare environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in:
   - `POSTGRES_USER`, `DB_TRAVEL_PASSWORD` — Postgres admin credentials
   - `SESSION_SECRET` — Random key for session encryption (32+ chars)
   - `OPENAI_API_KEY` — Your OpenAI API key for LLM calls
   - `OPENAI_MODEL` — Model ID (e.g., `gpt-4o-mini`, `gpt-4-turbo`)
   - `LASTMINUTE_MCP_URL` — `https://mcp.lastminute.com/mcp` (public endpoint)
   - `ADMIN_USERNAME`, `ADMIN_PASSWORD` — Initial admin user credentials
   - `ADMIN_EMAIL` — Admin contact email
   - `TRAVEL_HOST` — Hostname (e.g., `travel.longobardo.me`)
   - `TZ` — Timezone (e.g., `Europe/Rome`)

2. **Create the proxy network** (once, if not already present):
   ```bash
   docker network create proxy_public
   ```

3. **Build and start the stack:**
   ```bash
   docker compose build
   docker compose up -d
   ```

   Expected containers: `travel-redis`, `travel-app`.

### Deploy & Smoke Test

Once running, verify end-to-end operation:

1. **Open the app:**

2. **Log in** with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`.

3. **Send an example query** (e.g., "Flights and hotels to Azores for 5 days around €500/night"):
   - Browser geolocation is requested (origin city).
   - Watch the agent timeline appear in real-time (Intake → Scout → Flight → Hotel → Package → Optimizer → Presenter).
   - Wait for ranked package cards to appear (flights, hotels, total price, ratings).

4. **Check the browser console** for any SSE stream errors or missing events.

5. **Verify Docker health:**
   ```bash
   docker compose ps
   # Expected: all services running (not unhealthy)
   ```

## Layout

- **`Dockerfile`** — Unified multi-stage Docker build combining Next.js frontend standalone build and FastAPI backend in a single container (`travel-app`).
- **`entrypoint.sh`** — Unified entrypoint handling database migrations and launching/supervising both backend and frontend processes.
- **`backend/`** — FastAPI application (auth, chats, LangGraph multi-agent system). Includes Node.js for `npx mcp-remote`.
- **`frontend/`** — Next.js 16 application (login, immersive chat, SSE client).
- **`data/`** — Persistent bind-mount directories for Redis (auto-created at first run).
- **`docker-compose.yml`** — Service stack (`travel-app`, Redis, networks).
- **`docs/`** — Design specs, plans, and smoke-test references.

## Technical Notes

- **Unified Image:** The single container image runs FastAPI backend on port 8000 and Next.js frontend on port 3000, supervised by `entrypoint.sh`. Traefik routes all traffic to Next.js on port 3000, which internally proxies `/api` to the backend on loopback.
- **Network isolation:** Backend talks to Redis over `travel_internal` and to Postgres over `db_internal`; only Traefik (via `proxy_public`) exposes services to the outside.
- **Geolocation:** Browser geolocation is requested on the chat page; if provided, the origin coordinate is sent in the message payload to the Intake agent.
- **Session & auth:** FastAPI sessions (Redis-backed) enforce user boundaries; multi-user safe.

## Future Work

- **Multi-instance durability:** Replace `MemorySaver` with an external LangGraph checkpointer (e.g., PostgreSQL adapter) for HA deployments.
- **Advanced filtering:** User preferences (airline loyalty, hotel chains, etc.) in the Scout and Optimizer agents.
- **Admin settings UI:** Re-enable settings/admin panel if needed.

## Note

If a parent `projects/` aggregator is added later, register `03.Travel Agent/docker-compose.yml` in its `include:` list to fold this stack into the fleet.

## License

Copyright (c) 2026 Mattia Longobardo. All rights reserved where not expressly granted.

This repository is licensed under the [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0)](https://creativecommons.org/licenses/by-nc-nd/4.0/) license — see [LICENSE](LICENSE). You may not use this work for commercial purposes, and you may not distribute modified or derivative versions of it. No rights to run, copy, or reuse the code are granted beyond what the license explicitly allows.
