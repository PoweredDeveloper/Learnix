import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, API_PREFIX, webHeaders } from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Switch, SwitchControl } from '@/components/ui/inline-radio'
import { ShiningText } from '@/components/ui/shining-text'
import { ShaderLines } from '@/components/ui/shader-lines'
import { ArrowLeft, Sparkles, Upload, FileText, X, CheckCircle2, Loader2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const DURATION_OPTIONS = [
  { value: '2h', label: '2h' },
  { value: '12h', label: '12h' },
  { value: '1d', label: '1 day' },
  { value: '3d', label: '3 days' },
  { value: '1w', label: '1 week' },
  { value: '1month', label: '1 month' },
]

interface LogEntry {
  text: string
  done?: boolean
}

export default function CreateCourse() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [duration, setDuration] = useState('1w')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])

  const [uploadedFile, setUploadedFile] = useState<{
    name: string
    text: string
    chars: number
  } | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)

  function scrollLogs() {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.upload<{
        filename: string
        extracted_chars: number
        text: string
      }>('/web-courses/upload-file', fd)
      setUploadedFile({
        name: res.filename,
        text: res.text,
        chars: res.extracted_chars,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function removeFile() {
    setUploadedFile(null)
  }

  async function handleCreate() {
    if (!description.trim() && !uploadedFile) {
      setError('Please describe what you want to learn or upload a file.')
      return
    }
    setLoading(true)
    setError(null)
    setLogs([])

    try {
      const body = {
        name: name.trim() || description.trim().slice(0, 60) || uploadedFile?.name || 'My Course',
        description: description.trim(),
        duration_label: duration,
        file_text: uploadedFile?.text || null,
      }

      const resp = await fetch(`${API_PREFIX}/web-courses/create-stream`, {
        method: 'POST',
        headers: { ...webHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!resp.ok) {
        const text = await resp.text().catch(() => 'Request failed')
        throw new Error(text)
      }

      const reader = resp.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''
      let streamFinished = false

      const processDataPayload = (raw: string) => {
        if (!raw) return
        try {
          const evt = JSON.parse(raw) as {
            log?: string
            done?: boolean
            result?: { error?: string; id?: string; course?: { id?: string } }
          }
          if (evt.log) {
            setLogs((prev) => [...prev, { text: evt.log }])
            setTimeout(scrollLogs, 50)
          }
          if (evt.done && evt.result) {
            if (evt.result.error) {
              setError(evt.result.error)
              setLoading(false)
              streamFinished = true
              return
            }
            const courseId = evt.result.course?.id ?? evt.result.id
            if (courseId) {
              streamFinished = true
              navigate(`/course/${courseId}`)
              return
            }
          }
        } catch {
          // skip malformed SSE
        }
      }

      const drainCompleteLines = (chunk: string): string => {
        let buf = chunk
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''
        for (const line of lines) {
          if (streamFinished) return ''
          const t = line.replace(/\r$/, '')
          if (!t.startsWith('data:')) continue
          const raw = t.startsWith('data: ') ? t.slice(6).trim() : t.slice(5).trim()
          processDataPayload(raw)
        }
        return buf
      }

      while (true) {
        const { value, done } = await reader.read()
        if (value?.byteLength) {
          buffer += decoder.decode(value, { stream: !done })
        } else if (done) {
          buffer += decoder.decode()
        }
        buffer = drainCompleteLines(buffer)
        if (streamFinished) return
        if (done) {
          const tail = buffer.replace(/\r$/, '').trim()
          if (tail.startsWith('data:')) {
            const raw = tail.startsWith('data: ') ? tail.slice(6).trim() : tail.slice(5).trim()
            processDataPayload(raw)
          }
          break
        }
      }

      if (!streamFinished) {
        setError('Stream ended without result.')
        setLoading(false)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create course')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="relative -mx-4 -mt-4 min-h-[80vh] flex items-center justify-center overflow-hidden rounded-xl">
        <ShaderLines className="z-0 h-full w-full" />
        <div className="relative z-10 w-full max-w-2xl mx-auto px-4">
          <Card className="bg-black/60 backdrop-blur-md border-border/30 overflow-hidden">
            <CardContent className="pt-8 pb-6 space-y-6">
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <Sparkles className="h-10 w-10 text-primary" />
                </div>
                <ShiningText className="text-lg font-semibold">Building your course...</ShiningText>
              </div>

              <div className="relative bg-black/50 rounded-lg border border-border/20 p-4 max-h-[300px] overflow-y-auto font-mono text-sm">
                <AnimatePresence>
                  {logs.map((log, i) => (
                    <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.2 }} className="flex items-start gap-2 py-0.5">
                      {log.text.startsWith('✓') ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                      ) : log.text.startsWith('ERROR') ? (
                        <X className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
                      ) : (
                        <Loader2 className="h-3.5 w-3.5 text-primary animate-spin mt-0.5 shrink-0" />
                      )}
                      <span className={log.text.startsWith('✓') ? 'text-muted-foreground' : log.text.startsWith('ERROR') ? 'text-destructive' : 'text-foreground'}>{log.text.replace(/^✓\s*/, '')}</span>
                    </motion.div>
                  ))}
                </AnimatePresence>
                <div ref={logsEndRef} />
              </div>

              {error && <p className="text-sm text-destructive text-center">{error}</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-10rem)] flex-col items-center justify-center py-10 px-4">
      <div className="w-full max-w-2xl">
        <button onClick={() => navigate('/')} className="mb-6 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </button>

        <Card className="border-border/50 bg-card/70 shadow-xl backdrop-blur-sm">
          <CardHeader className="space-y-2 px-8 pb-2 pt-10 text-center sm:text-left">
            <CardTitle className="text-2xl font-bold tracking-tight">New course</CardTitle>
            <CardDescription className="text-base leading-relaxed">Tell us what you want to learn. Optionally add a file — we’ll build theory, practice, and exam lessons for the study length you choose.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-8 px-8 pb-10 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground mb-2" htmlFor="cc-topic">
                Topic or goal
              </label>
              <Textarea
                id="cc-topic"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g. Integral calculus for my exam, React Server Components, beginner Spanish…"
                className="min-h-[128px] resize-none text-base"
              />
              <p className="text-xs text-muted-foreground">Be specific — the AI uses this to shape your syllabus.</p>
            </div>

            <div className="space-y-3">
              <span className="text-sm font-medium text-foreground mb-2">Study length</span>
              <Switch name="duration" size="medium" defaultValue={duration} onChange={setDuration} className="w-fit">
                {DURATION_OPTIONS.map((opt) => (
                  <SwitchControl key={opt.value} value={opt.value} label={opt.label} />
                ))}
              </Switch>
              <p className="text-xs text-muted-foreground">Shorter plans are denser; longer ones add more depth and sections.</p>
            </div>

            <div className="space-y-2">
              <span className="text-sm font-medium text-foreground mb-2">Materials (optional)</span>
              <div className="flex flex-wrap items-center gap-3 w-full">
                {uploadedFile ? (
                  <div className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-4 py-2.5 text-sm">
                    <FileText className="h-4 w-4 shrink-0 text-primary" />
                    <span className="max-w-[200px] truncate">{uploadedFile.name}</span>
                    <span className="text-xs text-muted-foreground">({uploadedFile.chars.toLocaleString()} chars)</span>
                    <button type="button" onClick={removeFile} className="text-muted-foreground hover:text-foreground">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    className="flex items-center gap-2 rounded-lg border border-dashed border-border/60 px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                  >
                    {uploading ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Upload className="h-4 w-4" />}
                    {uploading ? 'Reading file…' : 'Upload PDF, TXT, or Markdown'}
                  </button>
                )}
                <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md" onChange={handleFileUpload} className="hidden" />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground" htmlFor="cc-name">
                Course title <span className="font-normal text-muted-foreground">(optional)</span>
              </label>
              <input
                id="cc-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Leave blank to auto-name from your topic"
                className="w-full rounded-md border border-input bg-background px-3 py-2.5 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button onClick={handleCreate} size="lg" className="w-full text-base">
              <Sparkles className="mr-2 h-4 w-4" />
              Generate course
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
