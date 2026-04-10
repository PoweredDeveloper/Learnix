const LS_WEB_KEY = "sethack_web_key";
const LS_TID = "telegram_user_id";

export const API_PREFIX = "/api";

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

export function jsonHeaders(): HeadersInit {
  return { ...webHeaders(), "Content-Type": "application/json" };
}

async function handleResponse<T>(r: Response): Promise<T> {
  if (!r.ok) {
    const text = await r.text().catch(() => "Request failed");
    throw new Error(text);
  }
  return r.json();
}

export const api = {
  get: <T>(path: string) =>
    fetch(`${API_PREFIX}${path}`, { headers: webHeaders() }).then((r) =>
      handleResponse<T>(r),
    ),

  post: <T>(path: string, body?: unknown) =>
    fetch(`${API_PREFIX}${path}`, {
      method: "POST",
      headers: jsonHeaders(),
      body: body != null ? JSON.stringify(body) : undefined,
    }).then((r) => handleResponse<T>(r)),

  patch: <T>(path: string, body: unknown) =>
    fetch(`${API_PREFIX}${path}`, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    }).then((r) => handleResponse<T>(r)),

  put: <T>(path: string, body: unknown) =>
    fetch(`${API_PREFIX}${path}`, {
      method: "PUT",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
    }).then((r) => handleResponse<T>(r)),

  delete: <T>(path: string) =>
    fetch(`${API_PREFIX}${path}`, {
      method: "DELETE",
      headers: webHeaders(),
    }).then((r) => handleResponse<T>(r)),

  upload: <T>(path: string, formData: FormData) =>
    fetch(`${API_PREFIX}${path}`, {
      method: "POST",
      headers: webHeaders(),
      body: formData,
    }).then((r) => handleResponse<T>(r)),
};
