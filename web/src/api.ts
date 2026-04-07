const LS_WEB_KEY = "sethack_web_key";
const LS_TID = "telegram_user_id";

export const API_PREFIX = "/api";

/** If `?key=` is present, store it and strip it from the address bar. */
export function captureKeyFromQuery(): void {
  const sp = new URLSearchParams(window.location.search);
  const k = sp.get("key");
  if (k?.trim()) {
    localStorage.setItem(LS_WEB_KEY, k.trim());
    const path = window.location.pathname || "/";
    window.history.replaceState({}, "", path);
  }
}

export function getWebSessionKey(): string | null {
  return localStorage.getItem(LS_WEB_KEY);
}

export function adminHeaders(): HeadersInit {
  const tid = localStorage.getItem(LS_TID) || "1000001";
  const key = import.meta.env.VITE_API_SECRET || "dev-secret-change-me";
  return {
    "X-Telegram-User-Id": tid,
    "X-API-Key": key,
  };
}

export function webHeaders(): HeadersInit {
  const w = getWebSessionKey();
  if (!w) return {};
  return { "X-Web-Session-Key": w };
}
