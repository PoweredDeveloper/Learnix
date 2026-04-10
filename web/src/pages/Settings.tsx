import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { format } from "date-fns"
import { api, getWebSessionKey } from "@/api"
import type { CustomReminder, NotificationSettings } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Calendar } from "@/components/ui/calendar"
import { Checkbox } from "@/components/ui/checkbox"
import { ArrowLeft, Bell, Plus, Trash2 } from "lucide-react"

const TZ_PRESETS = ["UTC", "Europe/London", "Europe/Berlin", "Europe/Paris", "America/New_York", "America/Los_Angeles", "Asia/Tokyo"]

export default function Settings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [timezone, setTimezone] = useState("UTC")
  const [dailyEnabled, setDailyEnabled] = useState(false)
  const [dailyTime, setDailyTime] = useState("09:00")
  const [customReminders, setCustomReminders] = useState<CustomReminder[]>([])
  const [pickDate, setPickDate] = useState<Date | undefined>(() => new Date())
  const [newTime, setNewTime] = useState("12:00")
  const [newMessage, setNewMessage] = useState("Time to study!")

  const load = useCallback(async () => {
    if (!getWebSessionKey()) {
      setErr("Open this app from the Telegram bot link first.")
      setLoading(false)
      return
    }
    try {
      const data = await api.get<NotificationSettings>("/users/me/notifications")
      setTimezone(data.timezone || "UTC")
      setDailyEnabled(data.daily_enabled)
      setDailyTime(data.daily_time || "09:00")
      setCustomReminders(data.custom_reminders ?? [])
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load settings")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function save() {
    setSaving(true)
    setErr(null)
    try {
      await api.put<NotificationSettings>("/users/me/notifications", {
        timezone,
        daily_enabled: dailyEnabled,
        daily_time: dailyTime,
        custom_reminders: customReminders,
      })
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Save failed")
    } finally {
      setSaving(false)
    }
  }

  function addReminder() {
    if (!pickDate) return
    const id = crypto.randomUUID()
    setCustomReminders((prev) => [
      ...prev,
      {
        id,
        date: format(pickDate, "yyyy-MM-dd"),
        time: newTime.slice(0, 5),
        message: newMessage.trim() || "Study reminder",
        enabled: true,
      },
    ])
  }

  function removeReminder(id: string) {
    setCustomReminders((prev) => prev.filter((r) => r.id !== id))
  }

  function toggleReminder(id: string) {
    setCustomReminders((prev) =>
      prev.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)),
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20 text-muted-foreground">Loading settings…</div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-8 px-1 sm:px-0">
      <div>
        <Link
          to="/"
          className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="mt-2 text-muted-foreground">
          Telegram reminders use your timezone. The bot checks every minute.
        </p>
      </div>

      {err && <p className="text-sm text-destructive">{err}</p>}

      <Card className="border-border/50 bg-card/60 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Bell className="h-5 w-5 text-primary" />
            Notifications
          </CardTitle>
          <CardDescription>
            Daily nudge at a fixed time, plus optional one-off reminders on dates you pick below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Timezone</label>
            <input
              list="tz-presets"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              placeholder="e.g. Europe/Berlin"
            />
            <datalist id="tz-presets">
              {TZ_PRESETS.map((tz) => (
                <option key={tz} value={tz} />
              ))}
            </datalist>
            <p className="text-xs text-muted-foreground">
              IANA name (same as in your OS). Wrong zone = reminders at the wrong local time.
            </p>
          </div>

          <div className="rounded-xl border border-border/40 bg-muted/15 p-4">
            <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
              <Checkbox checked={dailyEnabled} onChange={setDailyEnabled} className="text-sm font-medium sm:pb-0.5">
                Daily Telegram reminder
              </Checkbox>
              <div className="flex items-center gap-2 sm:justify-end">
                <span className="text-sm text-muted-foreground whitespace-nowrap">Time</span>
                <input
                  type="time"
                  value={dailyTime}
                  onChange={(e) => setDailyTime(e.target.value)}
                  disabled={!dailyEnabled}
                  className="w-full min-w-0 max-w-[9rem] rounded-md border border-input bg-background px-2 py-2 text-sm disabled:opacity-50 sm:w-auto"
                />
              </div>
            </div>
          </div>

          <div className="space-y-4 border-t border-border/40 pt-6">
            <div>
              <h3 className="text-sm font-medium">Custom reminders</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Pick a day on the calendar, set time and message. We’ll message you on Telegram once that
                local minute matches (same timezone as above).
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-[auto_minmax(0,1fr)] lg:items-start">
              <div className="flex justify-center lg:justify-start">
                <Calendar mode="single" selected={pickDate} onSelect={setPickDate} className="rounded-md border border-border/40" />
              </div>
              <div className="space-y-3 min-w-0">
                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <input
                    type="time"
                    value={newTime}
                    onChange={(e) => setNewTime(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-2 py-2 text-sm sm:w-auto sm:min-w-[7rem]"
                  />
                  <Button type="button" size="sm" onClick={addReminder} disabled={!pickDate} className="w-full sm:w-auto">
                    <Plus className="h-4 w-4 mr-1" />
                    Add reminder
                  </Button>
                </div>
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  rows={2}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  placeholder="Reminder text…"
                />
              </div>
            </div>

            {customReminders.length > 0 && (
              <ul className="space-y-2">
                {customReminders.map((r) => (
                  <li
                    key={r.id}
                    className="grid grid-cols-[auto_1fr_auto] gap-3 items-center rounded-lg border border-border/50 bg-background/50 px-3 py-2.5 text-sm"
                  >
                    <Checkbox checked={r.enabled} onChange={() => toggleReminder(r.id)} className="self-start pt-0.5" />
                    <span className={`min-w-0 break-words ${r.enabled ? "" : "text-muted-foreground line-through"}`}>
                      {r.date} {r.time} — {r.message}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeReminder(r.id)}
                      className="shrink-0 text-muted-foreground hover:text-destructive p-1 rounded-md hover:bg-destructive/10"
                      aria-label="Remove"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <Button onClick={save} disabled={saving} size="lg" className="w-full sm:w-auto">
            {saving ? "Saving…" : "Save settings"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
