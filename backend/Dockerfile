FROM python:3.12-slim
WORKDIR /app

# Install curl + ca-certificates for NodeSource, then Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Pre-install mcp-remote globally so npx doesn't download it at runtime
RUN npm install -g mcp-remote

# Create a writable home directory for the non-root user (1000:1000)
RUN mkdir -p /home/app && chown 1000:1000 /home/app

# Point HOME and npm cache to the writable directory
ENV HOME=/home/app
ENV NPM_CONFIG_CACHE=/home/app/.npm

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini entrypoint.sh ./
RUN chmod +x entrypoint.sh
EXPOSE 8000
USER 1000:1000
CMD ["./entrypoint.sh"]
