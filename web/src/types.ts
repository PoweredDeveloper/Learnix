export type Task = {
  id: string;
  title: string;
  due_date: string;
  status: string;
  estimated_minutes: number;
};

export type Streak = {
  streak_current: number;
  streak_best: number;
  today_completed_minutes: number;
  today_quota_minutes: number;
  progress_ratio: number;
  streak_eligible_today: boolean;
};

export type CourseStatus = "generating" | "ready" | "archived";
export type LessonType = "theory" | "practice" | "exam";
export type LessonStatus = "locked" | "active" | "completed";

export type Course = {
  id: string;
  name: string;
  description: string;
  duration_label: string;
  status: CourseStatus;
  total_lessons: number;
  completed_lessons: number;
  created_at: string;
};

export type Lesson = {
  id: string;
  course_id: string;
  section_index: number;
  lesson_index: number;
  title: string;
  lesson_type: LessonType;
  status: LessonStatus;
  sort_order: number;
  content: LessonContent | null;
};

export type LessonContent = {
  body: string;
  task?: string;
  rubric?: string;
  questions?: ExamQuestion[];
};

export type ExamQuestion = {
  question: string;
  rubric: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type Me = {
  id: string;
  name: string | null;
  telegram_id: number;
  streak_current: number;
  streak_best: number;
  onboarding_completed: boolean;
  web_session_expires_at: string | null;
};

export type CustomReminder = {
  id: string;
  date: string;
  time: string;
  message: string;
  enabled: boolean;
};

export type NotificationSettings = {
  timezone: string;
  daily_enabled: boolean;
  daily_time: string;
  custom_reminders: CustomReminder[];
};
