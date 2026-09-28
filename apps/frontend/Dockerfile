# syntax=docker/dockerfile:1
# Transit-AI frontend - Vite build -> nginx serve.

FROM node:20-slim AS builder

ENV YARN_VERSION=4.5.0
RUN corepack enable && corepack prepare yarn@4.5.0 --activate

# T-122: провайдер карты и ключ Яндекс.Карт. Vite инлайнит VITE_* на этапе
# сборки, поэтому передаём через build-args (см. docker-compose.yml frontend.build.args).
# Без ключа карта работает на Leaflet/OSM (VITE_MAP_IMPL=osm по умолчанию).
ARG VITE_MAP_IMPL=osm
ARG VITE_YANDEX_MAPS_API_KEY=""
ENV VITE_MAP_IMPL=$VITE_MAP_IMPL
ENV VITE_YANDEX_MAPS_API_KEY=$VITE_YANDEX_MAPS_API_KEY

WORKDIR /app

# T-236: `.yarnrc.yml` обязателен рядом с package.json/yarn.lock — иначе `yarn install`
# выполняется с дефолтным `nodeLinker: pnp` (создаётся .pnp.cjs, node_modules нет),
# а следующий `COPY apps/frontend ./` приносит `.yarnrc.yml` с `nodeLinker: node-modules`
# и шаг `yarn docker-build` падает: "Couldn't find the node_modules state file".
COPY apps/frontend/package.json apps/frontend/yarn.lock* apps/frontend/.yarnrc.yml ./
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
