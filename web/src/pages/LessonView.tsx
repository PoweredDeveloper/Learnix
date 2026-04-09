import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/api";
import type { Lesson, ChatMessage } from "@/types";
import { Button } from "@/components/ui/button";
import { ShiningText } from "@/components/ui/shining-text";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import {
  ArrowLeft,
  BookOpen,
  PenLine,
  ClipboardCheck,
  CheckCircle2,
  Send,
  ChevronRight,
} from "lucide-react";

function typeBadge(type: string) {
  switch (type) {
    case "theory":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 text-primary px-2.5 py-0.5 text-xs font-medium">
          <BookOpen className="h-3 w-3" /> Theory
        </span>
      );
    case "practice":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 text-warning px-2.5 py-0.5 text-xs font-medium">
          <PenLine className="h-3 w-3" /> Practice
        </span>
      );
    case "exam":
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 text-destructive px-2.5 py-0.5 text-xs font-medium">
          <ClipboardCheck className="h-3 w-3" /> Exam
        </span>
      );
    default:
      return null;
  }
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="prose max-w-none">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default function LessonView() {
  const { courseId, lessonId } = useParams<{
    courseId: string;
    lessonId: string;
  }>();
  const navigate = useNavigate();

  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    if (!courseId || !lessonId) return;
    try {
      const [lessonData, chatData] = await Promise.all([
        api.get<Lesson>(
          `/web-courses/${courseId}/lessons/${lessonId}`,
        ),
        api.get<{ messages: ChatMessage[] }>(
          `/web-courses/${courseId}/lessons/${lessonId}/chat`,
        ),
      ]);
      setLesson(lessonData);
      setMessages(chatData.messages ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load lesson");
    } finally {
      setLoading(false);
    }
  }, [courseId, lessonId]);

  useEffect(() => {
    setLoading(true);
    setFeedback(null);
    setAnswer("");
    load();
  }, [load]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chatLoading]);

  async function sendChat() {
    if (!input.trim() || chatLoading || !courseId || !lessonId) return;
    const msg = input.trim();
    setInput("");
    const userMsg: ChatMessage = {
      role: "user",
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatLoading(true);

    try {
      const res = await api.post<{ reply: string }>(
        `/web-courses/${courseId}/lessons/${lessonId}/chat`,
        { message: msg },
      );
      const aiMsg: ChatMessage = {
        role: "assistant",
        content: res.reply,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (e) {
      const errMsg: ChatMessage = {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setChatLoading(false);
      inputRef.current?.focus();
    }
  }

  async function handleComplete() {
    if (!courseId || !lessonId || completing) return;
    setCompleting(true);
    try {
      await api.post(
        `/web-courses/${courseId}/lessons/${lessonId}/complete`,
      );
      navigate(`/course/${courseId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to complete lesson");
      setCompleting(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChat();
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading lesson...</p>
      </div>
    );
  }

  if (error || !lesson) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-destructive">{error ?? "Lesson not found"}</p>
        <Button
          variant="outline"
          onClick={() => navigate(courseId ? `/course/${courseId}` : "/")}
        >
          Back to Course
        </Button>
      </div>
    );
  }

  const content = lesson.content;
  const isCompleted = lesson.status === "completed";

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => navigate(`/course/${courseId}`)}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
        >
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
        {!isCompleted && (
          <Button
            onClick={handleComplete}
            disabled={completing}
            size="sm"
            className="ml-auto"
          >
            {completing ? "..." : "Complete & Continue"}
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        )}
      </div>

      {/* Lesson content */}
      <div className="rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm p-6">
        {content?.body && <MarkdownContent content={content.body} />}

        {lesson.lesson_type === "practice" && content?.task && (
          <div className="mt-6 rounded-lg bg-accent p-4">
            <h3 className="text-sm font-semibold mb-2">Task</h3>
            <MarkdownContent content={content.task} />
            {!isCompleted && (
              <div className="mt-4">
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  placeholder="Type your answer..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm min-h-[80px] placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
                <Button
                  className="mt-2"
                  size="sm"
                  onClick={async () => {
                    if (!answer.trim() || chatLoading || !courseId || !lessonId)
                      return;
                    const msg = `My answer to the task: ${answer.trim()}`;
                    const userMsg: ChatMessage = {
                      role: "user",
                      content: msg,
                      created_at: new Date().toISOString(),
                    };
                    setMessages((prev) => [...prev, userMsg]);
                    setChatLoading(true);
                    try {
                      const res = await api.post<{ reply: string }>(
                        `/web-courses/${courseId}/lessons/${lessonId}/chat`,
                        { message: msg },
                      );
                      setFeedback(res.reply);
                      const aiMsg: ChatMessage = {
                        role: "assistant",
                        content: res.reply,
                        created_at: new Date().toISOString(),
                      };
                      setMessages((prev) => [...prev, aiMsg]);
                    } catch {
                      setFeedback("Error submitting answer. Please try again.");
                    } finally {
                      setChatLoading(false);
                    }
                  }}
                >
                  Submit Answer
                </Button>
              </div>
            )}
            {feedback && (
              <div className="mt-3 p-3 rounded-md bg-background border">
                <MarkdownContent content={feedback} />
              </div>
            )}
          </div>
        )}

        {lesson.lesson_type === "exam" && content?.questions && (
          <div className="mt-6 space-y-4">
            <h3 className="text-sm font-semibold">Exam Questions</h3>
            {content.questions.map((q, i) => (
              <div key={i} className="rounded-lg bg-accent p-4">
                <p className="font-medium mb-2">
                  Q{i + 1}:{" "}
                  <MarkdownContent content={q.question} />
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Chat Panel */}
      <div className="rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm flex flex-col" style={{ height: "400px" }}>
        <div className="px-4 py-3 border-b flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-success" />
          <span className="text-sm font-medium">AI Tutor</span>
          <span className="text-xs text-muted-foreground">
            Ask questions about this lesson
          </span>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {messages.length === 0 && !chatLoading && (
            <p className="text-sm text-muted-foreground text-center py-8">
              Ask a question about this lesson. The AI tutor is here to help!
            </p>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={cn(
                "flex",
                msg.role === "user" ? "justify-end" : "justify-start",
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-accent",
                )}
              >
                {msg.role === "assistant" ? (
                  <MarkdownContent content={msg.content} />
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
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

          <div ref={chatEndRef} />
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
            <Button
              onClick={sendChat}
              disabled={!input.trim() || chatLoading}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
