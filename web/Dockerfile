# Debian/glibc: Tailwind v4 → lightningcss native bindings are more reliable than on Alpine/musl
# (avoids missing/wrong optional package + detect-libc edge cases during `vite build`).
#
# Build diagnostics: `DOCKER_BUILDKIT=1 docker build --progress=plain ...` shows full vite output.
# If the Node step OOMs in CI, set e.g. `NODE_OPTIONS=--max-old-space-size=2048` on the build stage.
FROM node:22-bookworm-slim AS build
WORKDIR /app
# More resilient to slow registry (same class of issue as PyPI timeouts in Docker)
ENV NPM_CONFIG_FETCH_RETRIES=5 \
    NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=20000 \
    NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=120000
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_SECRET=dev-secret-change-me
ENV VITE_API_SECRET=${VITE_API_SECRET}
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY docker/Caddyfile.plain /etc/caddy/Caddyfile.plain
COPY docker/Caddyfile.admin.tpl /etc/caddy/Caddyfile.admin.tpl
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
