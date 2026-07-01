export type ApiError = {
  error_code: string;
  message: string;
  request_id?: string;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  priority: string | null;
  estimated_duration: number | null;
  status: string;
};

export type DailyPlan = {
  id: string;
  plan_date: string;
  status: string;
  source: string;
  explanation?: string | null;
};

