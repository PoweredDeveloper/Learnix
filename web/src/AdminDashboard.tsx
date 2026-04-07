import { useCallback, useEffect, useState } from "react";
import { adminHeaders, API_PREFIX } from "./api";
import type { Task, Streak } from "./types";

export default function AdminDashboard() {
  const [tidInput, setTidInput] = useState(localStorage.getItem("telegram_user_id") || "1000001");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [streak, setStreak] = useState<Streak | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const [tr, sr] = await Promise.all([
        fetch(`${API_PREFIX}/tasks/today`, { headers: adminHeaders() }),
        fetch(`${API_PREFIX}/streak`, { headers: adminHeaders() }),
      ]);
      if (!tr.ok) throw new Error(await tr.text());
      if (!sr.ok) throw new Error(await sr.text());
      setTasks(await tr.json());
      setStreak(await sr.json());
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
        headers: { ...adminHeaders(), "Content-Type": "application/json" },
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

  return (
    <>
      <h1>Dev admin</h1>
      <p style={{ color: "#64748b" }}>
        Local dev dashboard: impersonate a user via Telegram id + API secret.
      </p>
      <div style={{ marginBottom: "1rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <input
          value={tidInput}
          onChange={(e) => setTidInput(e.target.value)}
          placeholder="Telegram user id"
          style={{ padding: "0.4rem 0.6rem" }}
        />
        <button
          type="button"
          onClick={() => {
            localStorage.setItem("telegram_user_id", tidInput);
            load();
          }}
        >
          Save ID & reload
        </button>
      </div>

      {err && <p style={{ color: "#b91c1c" }}>{err}</p>}

      {streak && (
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
    </>
  );
}
