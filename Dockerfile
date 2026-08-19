# ==============================================================================
# Stage 1: Build Next.js Frontend
# ==============================================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Unified App Runner (Python 3.12 + Node.js 22 runtime)
# ==============================================================================
FROM python:3.12-slim AS runner
WORKDIR /app

# Install curl + ca-certificates for NodeSource, then Node.js 22
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates bash && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Pre-install mcp-remote globally so npx doesn't download it at runtime
RUN npm install -g mcp-remote

# Create a writable home directory for the non-root user (1000:1000)
RUN mkdir -p /home/app && chown -R 1000:1000 /home/app

# Point HOME and npm cache to the writable directory
ENV HOME=/home/app
ENV NPM_CONFIG_CACHE=/home/app/.npm
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
ENV BACKEND_URL=http://127.0.0.1:8000

# Install Python backend dependencies and code
COPY backend/pyproject.toml ./backend/
COPY backend/app ./backend/app
COPY backend/alembic ./backend/alembic
COPY backend/alembic.ini ./backend/
RUN pip install --no-cache-dir -e ./backend

# Copy frontend standalone build
COPY --from=frontend-builder /app/.next/standalone ./frontend/
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/public ./frontend/public

# Copy entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh && chown -R 1000:1000 /app

EXPOSE 3000 8000
USER 1000:1000

CMD ["./entrypoint.sh"]
