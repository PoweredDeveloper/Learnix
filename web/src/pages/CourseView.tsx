import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "@/api";
import type { Lesson, Course } from "@/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  BookOpen,
  PenLine,
  ClipboardCheck,
  CheckCircle2,
  Lock,
  ChevronRight,
  Menu,
  X,
  Trash2,
} from "lucide-react";

type CourseData = Course & { lessons: Lesson[] };

function lessonIcon(type: string, status: string) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-success" />;
  if (status === "locked") return <Lock className="h-4 w-4 text-muted-foreground/50" />;
  if (type === "theory") return <BookOpen className="h-4 w-4 text-primary" />;
  if (type === "practice") return <PenLine className="h-4 w-4 text-warning" />;
  if (type === "exam") return <ClipboardCheck className="h-4 w-4 text-destructive" />;
  return <BookOpen className="h-4 w-4" />;
}

function groupBySections(lessons: Lesson[]) {
  const sections: { index: number; title: string; lessons: Lesson[] }[] = [];
  for (const l of lessons) {
    let sec = sections.find((s) => s.index === l.section_index);
    if (!sec) {
      const secTitle = l.title.split(":")[0]?.trim() || `Section ${l.section_index + 1}`;
      sec = { index: l.section_index, title: secTitle, lessons: [] };
      sections.push(sec);
    }
    sec.lessons.push(l);
  }
  sections.sort((a, b) => a.index - b.index);
  for (const sec of sections) {
    sec.lessons.sort((a, b) => a.sort_order - b.sort_order);
  }
  return sections;
}

export default function CourseView() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<CourseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    if (!courseId) return;
    try {
      const res = await api.get<CourseData>(`/web-courses/${courseId}`);
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load course");
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-muted-foreground">Loading course...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-destructive">{error ?? "Course not found"}</p>
        <Button variant="outline" onClick={() => navigate("/")}>
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const sections = groupBySections(data.lessons ?? []);
  const completedCount = (data.lessons ?? []).filter(
    (l) => l.status === "completed",
  ).length;
  const totalCount = data.lessons?.length ?? 0;
  const progress =
    totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const activeLesson = (data.lessons ?? []).find((l) => l.status === "active");

  return (
    <div className="flex gap-6">
      {/* Mobile sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed bottom-4 right-4 z-50 md:hidden bg-primary text-primary-foreground rounded-full p-3 shadow-lg"
      >
        {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-72 bg-card/80 backdrop-blur-xl border-r border-border/50 pt-20 pb-6 overflow-y-auto transition-transform md:static md:translate-x-0 md:pt-0 md:w-72 md:min-w-[18rem] md:flex-shrink-0 md:rounded-xl md:border md:border-border/50 md:p-4",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="px-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Dashboard
          </button>
          <h2 className="text-lg font-semibold mb-1">{data.name}</h2>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
            <span>
              {completedCount}/{totalCount} lessons
            </span>
            <span className="font-medium text-foreground">{progress}%</span>
          </div>
          <div className="h-1.5 bg-secondary rounded-full overflow-hidden mb-6">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <nav className="px-2">
          {sections.map((sec) => (
            <div key={sec.index} className="mb-4">
              <h3 className="px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                {sec.title}
              </h3>
              <ul className="space-y-0.5">
                {sec.lessons.map((lesson) => {
                  const isActive = lesson.status === "active";
                  const isLocked = lesson.status === "locked";
                  return (
                    <li key={lesson.id}>
                      {isLocked ? (
                        <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-muted-foreground/50 rounded-md">
                          {lessonIcon(lesson.lesson_type, lesson.status)}
                          <span className="truncate flex-1">
                            {lesson.title}
                          </span>
                        </div>
                      ) : (
                        <Link
                          to={`/course/${courseId}/lesson/${lesson.id}`}
                          onClick={() => setSidebarOpen(false)}
                          className={cn(
                            "flex items-center gap-2 px-2 py-1.5 text-sm rounded-md transition-colors",
                            isActive
                              ? "bg-primary/10 text-primary font-medium"
                              : "text-foreground hover:bg-accent",
                          )}
                        >
                          {lessonIcon(lesson.lesson_type, lesson.status)}
                          <span className="truncate flex-1">
                            {lesson.title}
                          </span>
                          {isActive && (
                            <ChevronRight className="h-3 w-3 flex-shrink-0" />
                          )}
                        </Link>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="rounded-lg border border-border/50 bg-card/60 backdrop-blur-sm p-6">
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="min-w-0 flex-1 text-left">
              <h2 className="text-xl font-semibold">{data.name}</h2>
              {data.description && (
                <p className="text-muted-foreground mt-2 text-sm sm:text-base">
                  {data.description}
                </p>
              )}
            </div>
            <button
              type="button"
              disabled={deleting}
              onClick={async () => {
                if (!courseId || !confirm(`Delete "${data.name}"? This cannot be undone.`)) return;
                setDeleting(true);
                try {
                  await api.delete(`/web-courses/${courseId}`);
                  navigate("/");
                } catch {
                  setDeleting(false);
                }
              }}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border/60 bg-background/80 px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-destructive/50 hover:bg-destructive/10 hover:text-destructive disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleting ? "…" : "Delete"}
            </button>
          </div>
          <div className="text-center">
          <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          {activeLesson ? (
            <Button
              onClick={() =>
                navigate(`/course/${courseId}/lesson/${activeLesson.id}`)
              }
            >
              Continue: {activeLesson.title}
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : completedCount === totalCount && totalCount > 0 ? (
            <p className="text-success font-medium">
              Congratulations! Course complete!
            </p>
          ) : (
            <p className="text-muted-foreground">
              Select a lesson from the sidebar to begin.
            </p>
          )}
          </div>
        </div>
      </div>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
