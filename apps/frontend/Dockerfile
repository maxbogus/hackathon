# syntax=docker/dockerfile:1
# Transit-AI frontend - Vite build -> nginx serve.

FROM node:20-slim AS builder

ENV YARN_VERSION=4.5.0
RUN corepack enable && corepack prepare yarn@4.5.0 --activate

WORKDIR /app

COPY apps/frontend/package.json apps/frontend/yarn.lock* ./
RUN --mount=type=cache,target=/root/.yarn/berry/cache     yarn install --immutable

COPY apps/frontend ./
RUN yarn docker-build

# Stage 2: serve via nginx
FROM nginx:alpine AS runtime

# Удаляем packaged default.conf
RUN rm -f /etc/nginx/conf.d/default.conf

COPY apps/frontend/nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=5s --retries=5     CMD wget -qO- http://localhost/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
