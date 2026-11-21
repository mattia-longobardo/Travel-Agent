# AGENTS.md — Travel-Agent

Git, PR and deploy rules: skill `git-policy`. Here only the data of this repo and the exceptions.

Remote: `git@github-personal:mattia-longobardo/Travel-Agent.git`. The Next.js rules for the frontend are in `frontend/AGENTS.md`.

## Coding hygiene

Follow skill `coding-hygiene` and the "Coding hygiene" section of `/home/mattia/docker/AGENTS.md` (HARD rules, defaults, end-of-task checklist).

## Commands

| Target | What it runs |
|---|---|
| `make install` | `npm ci --legacy-peer-deps` in `frontend/` |
| `make lint` | ESLint on the frontend |
| `make test` | backend pytest (SQLite + fakeredis, through uv) and frontend vitest |
| `make ci` | install, lint, test: the only step of `.github/workflows/ci.yml` |

## Repo

- Main branch: `main`
- Local tests that must pass before each push: selection of `test-policy` §1. Before a deploy: selection of `test-policy` §6 on `PREV..SHA`.
- Full suite: `make test` (only for a reason in the diff, `test-policy` §6 point 3)
- Smoke after the deploy: health check 3 below (the repo has no `@smoke` tests)
- Services deployed from this repo: `travel-agent`
- Tag filter per service: not necessary
- Work across more runs on `main`: not necessary

## Module map

| Changed files | Module | Command | Used by |
|---|---|---|---|
| `backend/**` | `backend/tests/` | `cd backend && uv run --no-project --python 3.12 --with-editable '.[dev]' pytest -q` | — |
| `frontend/**` | `frontend/__tests__/` | `cd frontend && npm test` | — |

## Critical or shared code

A file in this list starts the full suite:

- Data: `backend/alembic/**`, `backend/app/models.py`
- Auth: `backend/app/security.py`, `backend/app/sessions.py`, `frontend/middleware.ts`
- Dependencies: `backend/pyproject.toml`, `frontend/package.json`, `frontend/package-lock.json`, `Dockerfile`
- CI: `Makefile`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`

## Release and deploy

The server has no checkout of this repo: it runs the image from GHCR, and `make deploy` does not exist any more.

1. Release: tag `vX.Y.Z` on `main` (`git-policy` §9) and push it. `.github/workflows/release.yml` builds the `Dockerfile` and publishes `ghcr.io/mattia-longobardo/travel-agent:vX.Y.Z` and `:sha-<full SHA>` (public package, linked to this repo).
2. Digest: `docker buildx imagetools inspect ghcr.io/mattia-longobardo/travel-agent:vX.Y.Z --format '{{json .Manifest.Digest}}'`.
3. Deploy: in the Homelab repo, set `image: ghcr.io/mattia-longobardo/travel-agent:vX.Y.Z@sha256:<digest>` in `travel/docker-compose.yml` and push a signed commit to `main`: the Homelab GitOps recreates `travel-agent` (Homelab `AGENTS.md` §12).
4. Active version: `docker inspect -f '{{.Config.Image}}' travel-agent` = the `image:` of the Homelab compose.

## Health check

All must pass, with timeout `300s` (GitOps `--wait`):

1. Active version: step 4 above.
2. Essential dependencies: `docker inspect -f '{{.State.Health.Status}}' travel-agent` = `healthy` (the entrypoint stops on a failed migration).
3. Functional flow: `curl -fsS https://travel.longobardo.me/api/health` returns `{"status":"ok"}` and `https://travel.longobardo.me/login` returns `200`.

## Rollback and notification

- Code rollback: revert the Homelab commit that changed the version (the previous version + digest comes back); the GitOps also rolls back by itself when `--wait` fails.
- Data: shared PostgreSQL, no backup of its own; a migration is restored only from a dump taken before the deploy (`git-policy` §6 #1).
- Notification: `homelab-notify travel-agent "<text>"`

## Exceptions to the skill

- None.
