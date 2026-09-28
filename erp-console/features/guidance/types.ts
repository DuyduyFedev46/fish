// Định nghĩa kiểu dữ liệu cho khối Tiếp theo · Đã làm (02b §6.7, DW-03).
// Contract API: GET /api/guidance/<loại>/<id>/ (order | refund | payment | batch).

export type GuidanceMissing = {
  code: string;
  text: string;
};

export type GuidanceWhy = {
  br: string;
  text: string;
};

export type GuidanceNextStep = {
  key: string;
  label: string;
  actor: "user" | "system";
  allowed: boolean;
  who: string[];
  missing: GuidanceMissing[];
  deadline: string | null;
  why: GuidanceWhy | null;
  command: string | null;
  ai: { level: string; label: string } | null;
};

export type GuidanceWarning = {
  code: string;
  text: string;
};

export type GuidanceTimelineActor = {
  kind: "system" | "user" | "ai";
  display: string;
  level?: string;
  config_version?: number;
};

export type GuidanceTimelineEntry = {
  at: string;
  kind: string;
  label: string;
  doc: string;
  actor: GuidanceTimelineActor;
};

export type GuidanceRelatedDoc = {
  type: string;
  code: string;
};

export type GuidanceDoc = {
  type: string;
  id: number | string;
  code: string;
  status: string;
  status_label: string;
};

export type GuidanceData = {
  doc: GuidanceDoc;
  next_steps: GuidanceNextStep[];
  warnings: GuidanceWarning[];
  timeline: GuidanceTimelineEntry[];
  related: GuidanceRelatedDoc[];
};
