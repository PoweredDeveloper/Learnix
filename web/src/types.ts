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
