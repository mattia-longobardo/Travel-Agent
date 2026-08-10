FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

FROM node:24-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
# Bind the standalone server to all interfaces. Docker sets HOSTNAME to the
# container ID, which resolves to multiple per-network IPs; Next.js would then
# listen on only one of them, leaving Traefik (on proxy_public) unable to reach it.
ENV HOSTNAME=0.0.0.0
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
USER 1000:1000
CMD ["node", "server.js"]
