#!/usr/bin/env python3
"""
Build a static Mihomo (Clash Meta) config from a subscription URL or raw payload.

Decodes common base64 subscription bodies, picks the first vless:// line, maps query
parameters into Mihomo's schema. Avoids subscription-provider remote parsing bugs.
Does not pass unknown values into the `encryption` field (use explicit none / omit).
"""

from __future__ import annotations

import base64
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


def _decode_subscription_blob(blob: str) -> str:
    blob = blob.strip()
    if not blob:
        raise ValueError("empty subscription body")
    if "\nvless://" in blob or blob.startswith("vless://"):
        return blob
    for pad in ("", "=", "==", "===", "===="):
        try:
            raw = base64.b64decode(blob + pad, validate=False)
            text = raw.decode("utf-8", errors="replace")
            if "://" in text:
                return text
        except Exception:
            continue
    raise ValueError("subscription is not base64-encoded URIs and has no vless:// line")


def load_subscription_text() -> str:
    url = (os.environ.get("PROXY_SUBSCRIPTION_URL") or "").strip()
    path = (os.environ.get("PROXY_SUBSCRIPTION_FILE") or "").strip()
    raw = os.environ.get("PROXY_SUBSCRIPTION_RAW")
    if path:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    if raw is not None and str(raw).strip():
        return _decode_subscription_blob(str(raw))
    if url:
        req = urllib.request.Request(url, headers={"User-Agent": "Learnix-mihomo/1"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return _decode_subscription_blob(body)
    raise ValueError(
        "Set one of: PROXY_SUBSCRIPTION_URL, PROXY_SUBSCRIPTION_FILE, PROXY_SUBSCRIPTION_RAW"
    )


def first_vless_uri(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vless://"):
            return line
    raise ValueError("no vless:// entry found in subscription")


def _qget(qs: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
    vals = qs.get(key)
    if not vals:
        return default
    v = (vals[0] or "").strip()
    return v if v else default


def vless_uri_to_proxy(uri: str) -> dict:
    if not uri.startswith("vless://"):
        raise ValueError("expected vless:// URI")
    rest = uri[8:]
    if "?" in rest:
        main, query_s = rest.split("?", 1)
    else:
        main, query_s = rest, ""
    if "@" not in main:
        raise ValueError("invalid vless authority")
    uuid, hostport = main.rsplit("@", 1)
    uuid = uuid.strip()
    hostport = hostport.strip()
    if ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        port = int(port_s)
    else:
        host, port = hostport, 443

    qs = urllib.parse.parse_qs(query_s, keep_blank_values=True)
    name = (os.environ.get("MIHOMO_PROXY_NAME") or "sub-vless").strip() or "sub-vless"

    proxy: dict = {
        "name": name,
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": uuid,
        "udp": True,
    }

    enc = (_qget(qs, "encryption") or "none").lower()
    if enc in ("none", ""):
        proxy["encryption"] = "none"
    elif enc in ("auto",):
        proxy["encryption"] = "auto"
    else:
        # Do not forward opaque provider tokens (e.g. pqv) into encryption.
        proxy["encryption"] = "none"

    net = (_qget(qs, "type") or "tcp").lower()
    if net == "ws":
        proxy["network"] = "ws"
        path = urllib.parse.unquote(_qget(qs, "path") or "/")
        ws_opts: dict = {"path": path}
        h = _qget(qs, "host")
        if h:
            ws_opts["headers"] = {"Host": h}
        proxy["ws-opts"] = ws_opts
    elif net == "grpc":
        proxy["network"] = "grpc"
        proxy["grpc-opts"] = {"grpc-service-name": _qget(qs, "serviceName") or ""}
    else:
        proxy["network"] = "tcp"

    security = (_qget(qs, "security") or "none").lower()
    if security == "tls":
        proxy["tls"] = True
        sni = _qget(qs, "sni") or _qget(qs, "serverName") or host
        if sni:
            proxy["servername"] = sni
        fp = _qget(qs, "fp")
        if fp:
            proxy["client-fingerprint"] = fp
        if _qget(qs, "allowInsecure") == "1":
            proxy["skip-cert-verify"] = True
    elif security == "reality":
        proxy["tls"] = True
        pbk = _qget(qs, "pbk") or ""
        sid = _qget(qs, "sid") or ""
        if not pbk:
            raise ValueError("reality security requires pbk= in subscription URI")
        proxy["reality-opts"] = {"public-key": pbk, "short-id": sid}
        sni = _qget(qs, "sni") or host
        if sni:
            proxy["servername"] = sni
        fp = _qget(qs, "fp")
        if fp:
            proxy["client-fingerprint"] = fp
    else:
        proxy["tls"] = False

    return proxy


def build_config() -> dict:
    text = load_subscription_text()
    uri = first_vless_uri(text)
    proxy = vless_uri_to_proxy(uri)
    mixed = int(os.environ.get("MIHOMO_MIXED_PORT") or "7890")
    return {
        "mixed-port": mixed,
        "bind-address": "*",
        "mode": "rule",
        "log-level": (os.environ.get("MIHOMO_LOG_LEVEL") or "info").lower(),
        "proxies": [proxy],
        "proxy-groups": [
            {
                "name": "learnix-out",
                "type": "select",
                "proxies": [proxy["name"], "DIRECT"],
            }
        ],
        "rules": ["MATCH,learnix-out"],
    }


def main() -> int:
    try:
        cfg = build_config()
    except (urllib.error.URLError, ValueError, OSError) as e:
        print(f"build_config: {e}", file=sys.stderr)
        return 1
    out_path = sys.argv[1] if len(sys.argv) > 1 else "-"
    dump = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
    if out_path in ("-", ""):
        sys.stdout.write(dump)
    else:
        Path(out_path).write_text(dump, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
