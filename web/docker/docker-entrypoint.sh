#!/bin/sh
set -e
if [ -n "$WEB_ADMIN_PASSWORD" ]; then
	HASH=$(caddy hash-password --plaintext "$WEB_ADMIN_PASSWORD")
	sed "s|__HASH__|${HASH}|g" /etc/caddy/Caddyfile.admin.tpl > /etc/caddy/Caddyfile
else
	cp /etc/caddy/Caddyfile.plain /etc/caddy/Caddyfile
fi
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
