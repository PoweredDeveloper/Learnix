FROM node:20-alpine AS build
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
