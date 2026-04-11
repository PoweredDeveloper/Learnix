#!/bin/sh
set -eu
DIR="${MIHOMO_HOME:-/config}"
mkdir -p "$DIR"
OUT="$DIR/config.yaml"
python3 /app/build_config.py "$OUT"
exec mihomo -d "$DIR"
