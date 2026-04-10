import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/api'
import type { Lesson, ChatMessage } from '@/types'
import { Button } from '@/components/ui/button'
import { ShiningText } from '@/components/ui/shining-text'
import { sanitizeLlmMarkdown } from '@/lib/sanitizeLlmMarkdown'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { ArrowLeft, BookOpen, PenLine, ClipboardCheck, CheckCircle2, Send, ChevronRight, Lock } from 'lucide-react'

function typeBadge(type: string) {
  switch (type) {
    case 'theory':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium">
          <BookOpen className="h-3 w-3" /> Theory
        </span>
      )
    case 'practice':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 text-warning px-2.5 py-0.5 text-xs font-medium">
          <PenLine className="h-3 w-3" /> Practice
        </span>
      )
    case 'exam':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 text-destructive px-2.5 py-0.5 text-xs font-medium">
          <ClipboardCheck className="h-3 w-3" /> Exam
        </span>
      )
    default:
      return null
  }
}

function stripCodeFences(s: string): string {
  let t = s.trim()
  const m = t.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/im)
  if (m) t = m[1].trim()
  return t
}

function extractQuotedFieldValue(text: string, label: string, quote: "'" | '"'): string | null {
  const idx = text.indexOf(label)
  if (idx < 0) return null
  let i = idx + label.length
  while (i < text.length && /\s/.test(text[i])) i++
  if (text[i] !== quote) return null
  i++
  let out = ''
  while (i < text.length) {
    const c = text[i]
    if (c === '\\' && i + 1 < text.length) {
      out += text[i + 1]
      i += 2
      continue
    }
    if (c === quote) return out
    out += c
    i++
  }
  return null
}

/**
 * Parse grading replies: strict JSON, or a JSON slice, or Python-style {'correct': False, 'feedback': '...'}.
 * Never use a loose "correct" substring match (matches inside "incorrect").
 */
function parseGradingReply(raw: unknown): { correct: boolean; feedbackText: string } {
  if (raw !== null && typeof raw === 'object' && 'correct' in raw) {
    const p = raw as { correct: unknown; feedback?: unknown }
    if (typeof p.correct === 'boolean') {
      const fb = typeof p.feedback === 'string' ? p.feedback : JSON.stringify(raw)
      return { correct: p.correct, feedbackText: sanitizeLlmMarkdown(fb) }
    }
  }

  const text = typeof raw === 'string' ? stripCodeFences(raw) : stripCodeFences(String(raw))

  const tryJson = (s: string): { correct: boolean; feedback: string } | null => {
    try {
      const p = JSON.parse(s) as { correct?: unknown; feedback?: unknown }
      if (p && typeof p === 'object' && typeof p.correct === 'boolean') {
        return {
          correct: p.correct,
          feedback: typeof p.feedback === 'string' ? p.feedback : s,
        }
      }
    } catch {
      /* ignore */
    }
    return null
  }

  let parsed = tryJson(text)
  if (parsed) {
    return { correct: parsed.correct, feedbackText: sanitizeLlmMarkdown(parsed.feedback) }
  }

  const i = text.indexOf('{')
  const j = text.lastIndexOf('}')
  if (i >= 0 && j > i) {
    parsed = tryJson(text.slice(i, j + 1))
    if (parsed) {
      return { correct: parsed.correct, feedbackText: sanitizeLlmMarkdown(parsed.feedback) }
    }
  }

  const py = text.match(/'correct'\s*:\s*(True|False|true|false)\b/)
  if (py) {
    const correct = py[1].toLowerCase() === 'true'
    const fb = extractQuotedFieldValue(text, "'feedback':", "'") ?? extractQuotedFieldValue(text, '"feedback":', '"') ?? text
    return { correct, feedbackText: sanitizeLlmMarkdown(fb) }
  }

  const dq = text.match(/"correct"\s*:\s*(true|false)\b/i)
  if (dq) {
    const correct = dq[1].toLowerCase() === 'true'
    const fb = extractQuotedFieldValue(text, '"feedback":', '"') ?? text
    return { correct, feedbackText: sanitizeLlmMarkdown(fb) }
  }

  return { correct: false, feedbackText: sanitizeLlmMarkdown(text) }
}

const PRACTICE_SKIP_USER_MARKER = 'The student chose to skip attempting this practice task'

const EXAM_SKIP_MARKER = 'The student chose to skip answering exam question'

/** API stores `ts`; UI uses `created_at`. */
function normalizeApiChatMessages(raw: unknown[] | undefined): ChatMessage[] {
  if (!raw?.length) return []
  return raw.map((m) => {
    const o = m as Record<string, unknown>
    const role = o.role === 'assistant' ? 'assistant' : 'user'
    const content = typeof o.content === 'string' ? o.content : String(o.content ?? '')
    const created_at =
      typeof o.created_at === 'string' ? o.created_at : typeof o.ts === 'string' ? o.ts : new Date().toISOString()
    return { role, content, created_at }
  })
}

/** Unwrap model JSON (possibly nested `reply`) into markdown for the reference solution panel. */
function parseSolutionReply(raw: string): string {
  let solution = stripCodeFences(raw)
  for (let depth = 0; depth < 3; depth++) {
    try {
      const parsed = JSON.parse(solution) as { reply?: unknown }
      if (parsed && typeof parsed === 'object' && typeof parsed.reply === 'string') {
        solution = parsed.reply
        continue
      }
    } catch {
      break
    }
    break
  }
  return solution
}

function derivePracticeFromMessages(messages: ChatMessage[]): {
  answer: string
  feedback: string | null
  taskSolved: boolean
  taskSkipped: boolean
} {
  let answer = ''
  let feedback: string | null = null
  let taskSolved = false
  let taskSkipped = false

  for (let i = 0; i < messages.length - 1; i++) {
    const u = messages[i]
    const a = messages[i + 1]
    if (u.role !== 'user' || a.role !== 'assistant') continue

    if (u.content.includes(PRACTICE_SKIP_USER_MARKER)) {
      taskSkipped = true
      taskSolved = false
      answer = ''
      feedback = parseSolutionReply(a.content)
      continue
    }

    const ma = u.content.match(/^My answer:\s*([\s\S]*)$/)
    if (ma) {
      taskSkipped = false
      answer = ma[1] ?? ''
      const graded = parseGradingReply(a.content)
      taskSolved = graded.correct
      feedback = graded.correct ? null : graded.feedbackText
    }
  }

  return { answer, feedback, taskSolved, taskSkipped }
}

function deriveExamFromMessages(
  messages: ChatMessage[],
  nQuestions: number,
): { answers: string[]; feedback: (string | null)[]; solved: boolean[]; skipped: boolean[] } {
  const answers = Array.from({ length: nQuestions }, () => '')
  const feedback: (string | null)[] = Array.from({ length: nQuestions }, () => null)
  const solved = Array.from({ length: nQuestions }, () => false)
  const skipped = Array.from({ length: nQuestions }, () => false)

  for (let i = 0; i < messages.length - 1; i++) {
    const u = messages[i]
    const a = messages[i + 1]
    if (u.role !== 'user' || a.role !== 'assistant') continue

    if (u.content.includes(EXAM_SKIP_MARKER)) {
      const sm = u.content.match(/exam question (\d+)\b/)
      if (sm) {
        const qi = parseInt(sm[1], 10) - 1
        if (qi >= 0 && qi < nQuestions) {
          skipped[qi] = true
          solved[qi] = false
          answers[qi] = ''
          feedback[qi] = parseSolutionReply(a.content)
        }
      }
      continue
    }

    const m = u.content.match(/^Q(\d+) answer:\s*([\s\S]*)$/)
    if (!m) continue
    const qi = parseInt(m[1], 10) - 1
    if (qi < 0 || qi >= nQuestions) continue
    answers[qi] = m[2] ?? ''
    const graded = parseGradingReply(a.content)
    solved[qi] = graded.correct
    skipped[qi] = false
    feedback[qi] = graded.correct ? null : graded.feedbackText
  }

  return { answers, feedback, solved, skipped }
}

function MarkdownContent({ content }: { content: string }) {
  const cleaned = sanitizeLlmMarkdown(content)
  return (
    <div className="prose max-w-none">
      {/* remarkMath before remarkGfm: GFM otherwise treats \\[4pt] etc. inside math as link refs */}
      <ReactMarkdown remarkPlugins={[remarkMath, remarkGfm]} rehypePlugins={[rehypeKatex]}>
        {cleaned}
      </ReactMarkdown>
    </div>
  )
}

function ExamSection({
  questions,
  courseId,
  lessonId,
  isCompleted,
  examAnswers,
  setExamAnswers,
  examFeedback,
  setExamFeedback,
  examSolved,
  setExamSolved,
  examSubmitting,
  setExamSubmitting,
  examSkipped,
  setExamSkipped,
  chatLoading,
  setChatLoading,
  setMessages,
}: {
  questions: { question: string; rubric: string }[]
  courseId: string
  lessonId: string
  isCompleted: boolean
  examAnswers: string[]
  setExamAnswers: React.Dispatch<React.SetStateAction<string[]>>
  examFeedback: (string | null)[]
  setExamFeedback: React.Dispatch<React.SetStateAction<(string | null)[]>>
  examSolved: boolean[]
  setExamSolved: React.Dispatch<React.SetStateAction<boolean[]>>
  examSubmitting: boolean[]
  setExamSubmitting: React.Dispatch<React.SetStateAction<boolean[]>>
  examSkipped: boolean[]
  setExamSkipped: React.Dispatch<React.SetStateAction<boolean[]>>
  chatLoading: boolean
  setChatLoading: React.Dispatch<React.SetStateAction<boolean>>
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>
}) {
  useEffect(() => {
    if (examAnswers.length !== questions.length) {
      setExamAnswers(new Array(questions.length).fill(''))
      setExamFeedback(new Array(questions.length).fill(null))
      setExamSolved(new Array(questions.length).fill(false))
      setExamSubmitting(new Array(questions.length).fill(false))
      setExamSkipped(new Array(questions.length).fill(false))
    }
  }, [
    questions.length,
    examAnswers.length,
    setExamAnswers,
    setExamFeedback,
    setExamSolved,
    setExamSubmitting,
    setExamSkipped,
  ])

  async function submitQuestion(idx: number) {
    const ans = examAnswers[idx]?.trim()
    if (!ans || examSubmitting[idx] || examSolved[idx] || examSkipped[idx] || chatLoading) return

    setExamSubmitting((prev) => {
      const n = [...prev]
      n[idx] = true
      return n
    })

    const q = questions[idx]
    const msg = `Exam Q${idx + 1}: "${q.question}"\nMy answer: ${ans}\nRubric: ${q.rubric}\n\nRespond with JSON: {"correct": true/false, "feedback": "your feedback"}`

    const userMsg: ChatMessage = {
      role: 'user',
      content: `Q${idx + 1} answer: ${ans}`,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    try {
      const res = await api.post<{ reply: string }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`, { message: msg })

      const graded = parseGradingReply(res.reply)
      const aiMsg: ChatMessage = {
        role: 'assistant',
        content: graded.correct ? `✓ ${graded.feedbackText}` : `✗ ${graded.feedbackText}`,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, aiMsg])
      setExamFeedback((prev) => {
        const n = [...prev]
        n[idx] = graded.feedbackText
        return n
      })

      if (graded.correct) {
        setExamSolved((prev) => {
          const n = [...prev]
          n[idx] = true
          return n
        })
      }
    } catch {
      setExamFeedback((prev) => {
        const n = [...prev]
        n[idx] = 'Error submitting. Please try again.'
        return n
      })
    } finally {
      setExamSubmitting((prev) => {
        const n = [...prev]
        n[idx] = false
        return n
      })
    }
  }

  async function skipQuestion(idx: number) {
    if (chatLoading || examSubmitting[idx] || examSolved[idx] || examSkipped[idx] || !courseId || !lessonId) return
    const q = questions[idx]
    const skipMsg = [
      `The student chose to skip answering exam question ${idx + 1} (not graded as correct or incorrect).`,
      'Provide a clear, complete worked solution or answer key in markdown. Use LaTeX ($...$, $$...$$) for math where helpful.',
      '',
      `Question:\n${q.question}`,
      '',
      `Rubric:\n${q.rubric}`,
      '',
      'Respond with ONLY valid JSON: {"reply": "<your markdown solution>"}',
    ].join('\n')

    setChatLoading(true)
    try {
      const res = await api.post<{ reply: string }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`, { message: skipMsg })
      const rawReply = typeof res.reply === 'string' ? res.reply : String(res.reply ?? '')
      const solution = parseSolutionReply(rawReply)
      setExamFeedback((prev) => {
        const n = [...prev]
        n[idx] = solution
        return n
      })
      setExamSkipped((prev) => {
        const n = [...prev]
        n[idx] = true
        return n
      })
      const ts = new Date().toISOString()
      setMessages((prev) => [...prev, { role: 'user', content: skipMsg, created_at: ts }, { role: 'assistant', content: rawReply, created_at: ts }])
    } catch {
      setExamFeedback((prev) => {
        const n = [...prev]
        n[idx] = 'Could not load a solution. Try again or ask the AI tutor below.'
        return n
      })
    } finally {
      setChatLoading(false)
    }
  }

  const doneCount = examSolved.reduce((n, v, i) => n + (v || examSkipped[i] ? 1 : 0), 0)
  const allDone = examSolved.length > 0 && examSolved.every((v, i) => v || examSkipped[i])

  return (
    <div className="mt-6 space-y-4">
      <h3 className="text-sm font-semibold">
        Exam — {doneCount}/{questions.length} complete
      </h3>
      {questions.map((q, i) => (
        <div key={i} className="rounded-lg bg-accent p-4 space-y-3">
          <div className="flex items-start gap-2">
            <span className="text-sm font-bold text-muted-foreground shrink-0">Q{i + 1}.</span>
            <div className="flex-1">
              <MarkdownContent content={q.question} />
            </div>
            {(examSolved[i] || examSkipped[i]) && (
              <CheckCircle2 className={`h-4 w-4 shrink-0 mt-1 ${examSolved[i] ? 'text-success' : 'text-muted-foreground'}`} />
            )}
          </div>

          {!isCompleted && !examSolved[i] && !examSkipped[i] && (
            <div className="space-y-2">
              <textarea
                value={examAnswers[i] ?? ''}
                onChange={(e) =>
                  setExamAnswers((prev) => {
                    const n = [...prev]
                    n[i] = e.target.value
                    return n
                  })
                }
                placeholder="Type your answer..."
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[60px] placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <div className="flex flex-wrap gap-2">
                <Button size="sm" disabled={!examAnswers[i]?.trim() || examSubmitting[i] || chatLoading} onClick={() => submitQuestion(i)}>
                  {examSubmitting[i] ? 'Checking...' : 'Submit'}
                </Button>
                <Button type="button" variant="outline" size="sm" disabled={chatLoading || examSubmitting[i]} onClick={() => skipQuestion(i)}>
                  Skip & show solution
                </Button>
              </div>
            </div>
          )}

          {examSolved[i] && (
            <p className="text-success text-sm font-medium flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5" /> Correct
            </p>
          )}

          {examSkipped[i] && !examSolved[i] && (
            <p className="text-sm text-muted-foreground">
              You skipped this question. Below is a reference solution — it does not count as a correct attempt.
            </p>
          )}

          {examFeedback[i] && !examSolved[i] && (
            <div className="p-3 rounded-md bg-background border text-sm">
              {examSkipped[i] ? <h4 className="text-sm font-semibold mb-2">Solution</h4> : null}
              <MarkdownContent content={examFeedback[i]!} />
            </div>
          )}
        </div>
      ))}
      {allDone && (
        <div className="text-center py-3 text-success font-medium">
          {examSolved.every(Boolean) ? 'All questions answered correctly! ' : ''}You can now complete this lesson.
        </div>
      )}
    </div>
  )
}

export default function LessonView() {
  const { courseId, lessonId } = useParams<{
    courseId: string
    lessonId: string
  }>()
  const navigate = useNavigate()

  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [taskSolved, setTaskSolved] = useState(false)
  const [taskSkipped, setTaskSkipped] = useState(false)

  const [examAnswers, setExamAnswers] = useState<string[]>([])
  const [examFeedback, setExamFeedback] = useState<(string | null)[]>([])
  const [examSolved, setExamSolved] = useState<boolean[]>([])
  const [examSkipped, setExamSkipped] = useState<boolean[]>([])
  const [examSubmitting, setExamSubmitting] = useState<boolean[]>([])

  const inputRef = useRef<HTMLTextAreaElement>(null)

  const load = useCallback(async () => {
    if (!courseId || !lessonId) return
    try {
      const [lessonData, chatData] = await Promise.all([
        api.get<Lesson>(`/web-courses/${courseId}/lessons/${lessonId}`),
        api.get<{ messages: unknown[] }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`),
      ])
      const messagesNorm = normalizeApiChatMessages(chatData.messages)
      setLesson(lessonData)
      setMessages(messagesNorm)

      if (lessonData.lesson_type === 'practice') {
        const p = derivePracticeFromMessages(messagesNorm)
        setAnswer(p.answer)
        setFeedback(p.feedback)
        setTaskSolved(p.taskSolved)
        setTaskSkipped(p.taskSkipped)
      }

      const nExam = lessonData.content?.questions?.length ?? 0
      if (lessonData.lesson_type === 'exam' && nExam > 0) {
        const ex = deriveExamFromMessages(messagesNorm, nExam)
        setExamAnswers(ex.answers)
        setExamFeedback(ex.feedback)
        setExamSolved(ex.solved)
        setExamSkipped(ex.skipped)
        setExamSubmitting(Array.from({ length: nExam }, () => false))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load lesson')
    } finally {
      setLoading(false)
    }
  }, [courseId, lessonId])

  useEffect(() => {
    setLoading(true)
    setFeedback(null)
    setAnswer('')
    setTaskSolved(false)
    setTaskSkipped(false)
    setExamAnswers([])
    setExamFeedback([])
    setExamSolved([])
    setExamSkipped([])
    setExamSubmitting([])
    load()
  }, [load])

  async function sendChat() {
    if (!input.trim() || chatLoading || !courseId || !lessonId) return
    const msg = input.trim()
    setInput('')
    const userMsg: ChatMessage = {
      role: 'user',
      content: msg,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setChatLoading(true)

    try {
      const res = await api.post<{ reply: string }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`, { message: msg })
      const aiMsg: ChatMessage = {
        role: 'assistant',
        content: res.reply,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, aiMsg])
    } catch (e) {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setChatLoading(false)
      inputRef.current?.focus()
    }
  }

  async function handleComplete() {
    if (!courseId || !lessonId || completing) return
    setCompleting(true)
    try {
      await api.post(`/web-courses/${courseId}/lessons/${lessonId}/complete`)
      navigate(`/course/${courseId}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to complete lesson')
      setCompleting(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendChat()
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading lesson...</p>
      </div>
    )
  }

  if (error || !lesson) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-destructive">{error ?? 'Lesson not found'}</p>
        <Button variant="outline" onClick={() => navigate(courseId ? `/course/${courseId}` : '/')}>
          Back to Course
        </Button>
      </div>
    )
  }

  const content = lesson.content
  const isCompleted = lesson.status === 'completed'

  const isTheory = lesson.lesson_type === 'theory'
  const isPractice = lesson.lesson_type === 'practice'
  const isExam = lesson.lesson_type === 'exam'
  const allExamDone =
    isExam && examSolved.length > 0 && examSolved.every((v, i) => v || (examSkipped[i] ?? false))
  const canComplete = isCompleted || isTheory || (isPractice && (taskSolved || taskSkipped)) || allExamDone

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <button onClick={() => navigate(`/course/${courseId}`)} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0">
          <ArrowLeft className="h-4 w-4" />
          Course
        </button>
        <span className="text-muted-foreground/40">/</span>
        <h1 className="text-lg font-semibold truncate">{lesson.title}</h1>
        {typeBadge(lesson.lesson_type)}
        {isCompleted && (
          <span className="inline-flex items-center gap-1 text-success text-xs">
            <CheckCircle2 className="h-3 w-3" /> Completed
          </span>
        )}
        {!isCompleted && canComplete && (
          <Button onClick={handleComplete} disabled={completing} size="sm" className="ml-auto">
            {completing ? '...' : 'Complete & Continue'}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        )}
        {!isCompleted && !canComplete && (
          <span className="ml-auto inline-flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-md">
            <Lock className="h-3 w-3" />
            {isPractice ? 'Solve the task, or skip to see a solution' : 'Answer or skip each exam question to continue'}
          </span>
        )}
      </div>

      {/* Lesson content */}
      <div className="rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm p-6">
        <h2 className="text-2xl font-bold mb-2">{lesson.title}</h2>
        {content?.body && <MarkdownContent content={content.body} />}

        {isPractice && content?.task && (
          <div className="mt-6 rounded-lg bg-accent p-4">
            <h3 className="text-sm font-semibold mb-2">Task</h3>
            <MarkdownContent content={content.task} />
            {!isCompleted && !taskSolved && !taskSkipped && (
              <div className="mt-4">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your answer..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[80px] placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    disabled={!answer.trim() || chatLoading}
                    onClick={async () => {
                      if (!answer.trim() || chatLoading || !courseId || !lessonId) return
                      const msg = `My answer to the task:\n${answer.trim()}\n\nRubric: ${content.rubric ?? 'Check correctness.'}\n\nRespond with JSON: {"correct": true/false, "feedback": "your feedback"}`
                      const userMsg: ChatMessage = {
                        role: 'user',
                        content: `My answer: ${answer.trim()}`,
                        created_at: new Date().toISOString(),
                      }
                      setMessages((prev) => [...prev, userMsg])
                      setChatLoading(true)
                      try {
                        const res = await api.post<{ reply: string }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`, { message: msg })
                        const graded = parseGradingReply(res.reply)
                        setFeedback(graded.feedbackText)
                        setTaskSolved(graded.correct)
                        const aiMsg: ChatMessage = {
                          role: 'assistant',
                          content: graded.correct ? `✓ ${graded.feedbackText}` : `✗ ${graded.feedbackText}`,
                          created_at: new Date().toISOString(),
                        }
                        setMessages((prev) => [...prev, aiMsg])
                      } catch {
                        setFeedback('Error submitting answer. Please try again.')
                      } finally {
                        setChatLoading(false)
                      }
                    }}
                  >
                    Submit Answer
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={chatLoading}
                    onClick={async () => {
                      if (chatLoading || !courseId || !lessonId || !content?.task) return
                      setChatLoading(true)
                      setFeedback(null)
                      const skipMsg = [
                        'The student chose to skip attempting this practice task (not graded as correct or incorrect).',
                        'Provide a clear, complete worked solution or answer key in markdown. Use LaTeX ($...$, $$...$$) for math where helpful.',
                        '',
                        `Task:\n${content.task}`,
                        '',
                        `Rubric / what a good answer should cover:\n${content.rubric ?? 'Use sound reasoning and any methods that fit the task.'}`,
                        '',
                        'Respond with ONLY valid JSON: {"reply": "<your markdown solution>"}',
                      ].join('\n')
                      try {
                        const res = await api.post<{ reply: string }>(`/web-courses/${courseId}/lessons/${lessonId}/chat`, {
                          message: skipMsg,
                        })
                        const rawReply = typeof res.reply === 'string' ? res.reply : String(res.reply ?? '')
                        const solution = parseSolutionReply(rawReply)
                        setFeedback(solution)
                        setTaskSkipped(true)
                        const ts = new Date().toISOString()
                        setMessages((prev) => [
                          ...prev,
                          { role: 'user', content: skipMsg, created_at: ts },
                          { role: 'assistant', content: rawReply, created_at: ts },
                        ])
                      } catch {
                        setFeedback('Could not load a solution. Try again or ask the AI tutor below.')
                      } finally {
                        setChatLoading(false)
                      }
                    }}
                  >
                    Skip & show solution
                  </Button>
                </div>
              </div>
            )}
            {taskSolved && (
              <div className="mt-3 flex items-center gap-2 text-success text-sm font-medium">
                <CheckCircle2 className="h-4 w-4" /> Correct! You can now continue.
              </div>
            )}
            {taskSkipped && !taskSolved && (
              <div className="mt-3 text-sm text-muted-foreground">
                You skipped this task. Below is a reference solution — you can still use <span className="font-medium text-foreground">Complete & Continue</span> when you are ready.
              </div>
            )}
            {feedback && !taskSolved && (
              <div className="mt-3 p-3 rounded-md bg-background border">
                {taskSkipped ? <h4 className="text-sm font-semibold mb-2">Solution</h4> : null}
                <MarkdownContent content={feedback} />
              </div>
            )}
          </div>
        )}

        {isExam && content?.questions && (
          <ExamSection
            questions={content.questions}
            courseId={courseId!}
            lessonId={lessonId!}
            isCompleted={isCompleted}
            examAnswers={examAnswers}
            setExamAnswers={setExamAnswers}
            examFeedback={examFeedback}
            setExamFeedback={setExamFeedback}
            examSolved={examSolved}
            setExamSolved={setExamSolved}
            examSubmitting={examSubmitting}
            setExamSubmitting={setExamSubmitting}
            examSkipped={examSkipped}
            setExamSkipped={setExamSkipped}
            chatLoading={chatLoading}
            setChatLoading={setChatLoading}
            setMessages={setMessages}
          />
        )}
      </div>

      {/* AI Chat Panel */}
      <div className="rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm flex flex-col" style={{ height: '400px' }}>
        <div className="px-4 py-3 border-b flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-success" />
          <span className="text-sm font-medium">AI Tutor</span>
          <span className="text-xs text-muted-foreground">Ask questions about this lesson</span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {messages.length === 0 && !chatLoading && <p className="text-sm text-muted-foreground text-center py-8">Ask a question about this lesson. The AI tutor is here to help!</p>}

          {messages.map((msg, i) => (
            <div key={i} className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div className={cn('max-w-[80%] rounded-lg px-3 py-2 text-sm', msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-accent')}>
                {msg.role === 'assistant' ? <MarkdownContent content={msg.content} /> : <p className="whitespace-pre-wrap">{msg.content}</p>}
              </div>
            </div>
          ))}

          {chatLoading && (
            <div className="flex justify-start">
              <div className="bg-accent rounded-lg px-3 py-2">
                <ShiningText className="text-sm">Thinking...</ShiningText>
              </div>
            </div>
          )}
        </div>

        <div className="border-t px-4 py-3">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask the AI tutor..."
              rows={1}
              className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button onClick={sendChat} disabled={!input.trim() || chatLoading} size="icon">
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
