# Mihomo sidecar: generates /config/config.yaml from PROXY_SUBSCRIPTION_* then runs mihomo.
# Use with Docker Compose profile `proxy` and point the bot at http://mihomo:7890.

FROM python:3.12-alpine

RUN apk add --no-cache ca-certificates curl gzip \
  && set -eux \
  && ARCH="$(uname -m)" \
  && VER=v1.18.10 \
  && case "$ARCH" in \
       x86_64) U="https://github.com/MetaCubeX/mihomo/releases/download/${VER}/mihomo-linux-amd64-compatible-${VER}.gz" ;; \
       aarch64) U="https://github.com/MetaCubeX/mihomo/releases/download/${VER}/mihomo-linux-arm64-${VER}.gz" ;; \
       *) echo "unsupported arch: $ARCH"; exit 1 ;; \
     esac \
  && curl -fsSL "$U" | gzip -dc > /usr/local/bin/mihomo \
  && chmod +x /usr/local/bin/mihomo

RUN pip install --no-cache-dir pyyaml

WORKDIR /app
COPY build_config.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV MIHOMO_HOME=/config
EXPOSE 7890

ENTRYPOINT ["/entrypoint.sh"]
