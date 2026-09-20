# syntax=docker/dockerfile:1
# Transit-AI frontend — Vite build → nginx serve.
# Build context: репо-корень (для yarn workspaces).

# ─── Stage 1: build ─────────────────────────────────────────────────────────
FROM node:20-slim AS builder

ENV YARN_VERSION=4.5.0
RUN corepack enable && corepack prepare yarn@${YARN_VERSION} --activate

WORKDIR /app

# Копируем манифесты для кэширования
COPY package.json yarn.lock* .yarnrc.yml* ./
COPY apps/frontend/package.json ./apps/frontend/

# Install
RUN --mount=type=cache,target=/root/.yarn/berry/cache \
    yarn install --immutable

# Build
COPY apps/frontend ./apps/frontend
RUN yarn workspace @transit-ai/frontend build

# ─── Stage 2: serve via nginx ────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# nginx config для SPA (history mode)
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { try_files $uri $uri/ /index.html; } \
    location /api/ { proxy_pass http://backend:8000\; } \
}' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/apps/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD wget -qO- http://localhost/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
