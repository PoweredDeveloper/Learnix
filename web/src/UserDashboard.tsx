import { useCallback, useEffect, useState } from "react";
import { API_PREFIX, captureKeyFromQuery, getWebSessionKey, webHeaders } from "./api";
import type { Task, Streak } from "./types";

type Me = {
  name: string | null;
  web_session_expires_at: string | null;
};

export default function UserDashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    captureKeyFromQuery();
  }, []);

  const load = useCallback(async () => {
    setErr(null);
    if (!getWebSessionKey()) {
      setErr("Open this app using the link from the Telegram bot (menu Web app or /web).");
      setTasks([]);
      setStreak(null);
      setMe(null);
      return;
    }
    try {
      const h = webHeaders();
      const [tr, sr, mr] = await Promise.all([
        fetch(`${API_PREFIX}/tasks/today`, { headers: h }),
        fetch(`${API_PREFIX}/streak`, { headers: h }),
        fetch(`${API_PREFIX}/users/me`, { headers: h }),
      ]);
      if (!tr.ok) throw new Error(await tr.text());
      if (!sr.ok) throw new Error(await sr.text());
      if (!mr.ok) throw new Error(await mr.text());
      setTasks(await tr.json());
      setStreak(await sr.json());
      setMe(await mr.json());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function markTask(id: string, status: "done" | "skipped") {
    try {
      const r = await fetch(`${API_PREFIX}/tasks/${id}`, {
        method: "PATCH",
        headers: { ...webHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!r.ok) {
        setErr(await r.text());
        return;
      }
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    }
  }

  const exp = me?.web_session_expires_at
    ? new Date(me.web_session_expires_at).toLocaleString()
    : null;

  const hasKey = !!getWebSessionKey();

  return (
    <>
      <h1>Smart Study Assistant</h1>
      <p style={{ color: "#64748b" }}>
        Your web session (no password). Use the Telegram bot again when it expires.
      </p>
      {exp && (
        <p style={{ color: "#475569", fontSize: "0.9rem" }}>
          Session active until <strong>{exp}</strong> (local time display).
        </p>
      )}
      {me?.name && (
        <p style={{ color: "#475569" }}>
          Hi, <strong>{me.name}</strong>
        </p>
      )}

      {err && <p style={{ color: "#b91c1c" }}>{err}</p>}

      {streak && hasKey && (
        <section style={{ marginBottom: "1.5rem", padding: "1rem", background: "#fff", borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Streak</h2>
          <p>
            Current: <strong>{streak.streak_current}</strong> · Best: {streak.streak_best}
          </p>
          <p>
            Today: {streak.today_completed_minutes} / {streak.today_quota_minutes} min (
            {Math.round(streak.progress_ratio * 100)}%) — 20% goal:{" "}
            {streak.streak_eligible_today ? "met ✅" : "not yet"}
          </p>
        </section>
      )}

      {hasKey && (
        <section style={{ padding: "1rem", background: "#fff", borderRadius: 8 }}>
          <h2 style={{ marginTop: 0 }}>Today&apos;s tasks</h2>
          {tasks.length === 0 ? (
            <p>No tasks due today.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {tasks.map((t) => (
                <li
                  key={t.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "0.5rem",
                    padding: "0.5rem 0",
                    borderBottom: "1px solid #e2e8f0",
                  }}
                >
                  <span>
                    [{t.status}] {t.title} (~{t.estimated_minutes}m)
                  </span>
                  <span style={{ display: "flex", gap: "0.25rem" }}>
                    <button type="button" onClick={() => markTask(t.id, "done")}>
                      Done
                    </button>
                    <button type="button" onClick={() => markTask(t.id, "skipped")}>
                      Skip
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}
