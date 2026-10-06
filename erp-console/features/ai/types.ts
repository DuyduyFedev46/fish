// Kiểu dùng chung của module AI (02b §6).
// Chép contract ở doc/features/2026-09-28-ai-digital-worker/02b-tech-design.md. BE đổi thì sửa ở đây.

import type { AiCommandGroup, AiSensitivity } from "./commandGroups";
export type { AiCommandGroup, AiSensitivity };

// ---- S05 GET /api/ai/status/ ----
export type AiModelInfo = {
  /** Tên model (vd "qwen2.5-1.5b-instruct-q4_k_m"). */
  name: string;
  /** Phiên bản — thay đổi tức là đổi file model (đổi GGUF URL). */
  version: string;
  /** URL tải file GGUF (tĩnh, immutable theo version). */
  gguf_url: string;
};

/** Chỉ chu có (quyền ai.view_ai_usage); FE dùng để hiện hạn mức chi phí. */
export type AiBudget = {
  spent_vnd: number;
  limit_vnd: number;
  /** "ok" | "warning" | "blocked" */
  status: string;
};

/**
 * GET /api/ai/status/ luôn 200 (kể cả AI tắt) — AI tắt thì `ai_enabled=false` (S05).
 * `model=null` = chưa chốt model (chờ S17) — FE không tải gì.
 */
export type AiStatus = {
  ai_enabled: boolean;
  cloud_enabled: boolean;
  model: AiModelInfo | null;
  budget: AiBudget | null;
};

// ---- DW-07 & DW-09 Chỉ mục lệnh & Mô tả lệnh (02b §6.1, §6.2) ----
export type AiCommandKind = "read" | "write";
export type AiCommandLevel = "OFF" | "C" | "B" | "A";

export type AiCommandIndexItem = {
  id: string;
  title: string;
  group: AiCommandGroup;
  kind: AiCommandKind;
  level: AiCommandLevel;
  screens: string[];
  keywords: string[];
  target?: "detail";
  red_zone?: boolean;
  form_only?: boolean;
};

export type AiCommandsIndexResponse = {
  index_version: string;
  config_version: number;
  commands: AiCommandIndexItem[];
};

export type AiCommandDescriptor = {
  id: string;
  title: string;
  description: string;
  kind: AiCommandKind;
  level: AiCommandLevel;
  max_level: AiCommandLevel;
  sensitivity: AiSensitivity;
  channel: "local" | "cloud";
  red_zone: boolean;
  target: "detail" | null;
  form_only: boolean;
  schema_tokens_est: number;
  input_schema: Record<string, unknown> | null;
  output_fields: string[];
};

// ---- DW-10 & DW-11 Call Command & Actions (02b §6.3, §6.4) ----
export type CallOutcome = "done" | "proposal" | "scheduled";

export type CallRequest = {
  target_id?: string | number;
  args?: Record<string, unknown>;
  idempotency_key?: string;
  screen?: string;
  client?: string;
};

export type CallResponse = {
  outcome: CallOutcome;
  level: AiCommandLevel;
  action_id: string;
  result?: {
    rows?: Array<Record<string, unknown>>;
    total?: number;
    truncated?: boolean;
    [key: string]: unknown;
  };
  expires_at?: string;
  execute_after?: string;
  undo_until?: string;
  downgrade_reason?: {
    code: string;
    text: string;
  } | null;
  preview?: {
    target?: {
      type: string;
      code: string;
    };
  };
};

export type AiActionStatus =
  | "PENDING"
  | "CONFIRMED"
  | "REJECTED"
  | "EXPIRED"
  | "SCHEDULED"
  | "DONE"
  | "UNDONE"
  | "CANCELLED"
  | "ESCALATED"
  | "FAILED";

export type AiActionRow = {
  id: string;
  command: string;
  title: string;
  level: AiCommandLevel;
  status: AiActionStatus;
  owner_display: string;
  created_at: string;
  expires_at: string | null;
  execute_after: string | null;
  undo_until: string | null;
  target: {
    type: string;
    code: string;
  } | null;
  args_preview: Record<string, unknown> | null;
  downgrade_reason: {
    code: string;
    text: string;
  } | null;
  result_ref: Record<string, unknown> | null;
  assignee_group?: string | null;
};

export type AiActionDetail = AiActionRow & {
  confirm_nonce?: string;
  viewable_from?: string;
  viewed_at?: string | null;
};

// ---- DW-22 Báo cáo AI cuối ngày cho Chủ (02b §6.6) ----
export type AiDailyReportUserStat = {
  user_id: number;
  display_name: string;
  A: number;
  B: number;
  C_confirmed: number;
  C_expired: number;
  undone: number;
  escalated: number;
};

export type AiDailyReportItem = {
  id: string;
  command: string;
  title: string;
  level: AiCommandLevel;
  status: AiActionStatus;
  owner_display: string;
  created_at: string;
  target: { type: string; code: string } | null;
  result_ref: Record<string, unknown> | null;
};

export type AiDailyReport = {
  date: string;
  by_user: AiDailyReportUserStat[];
  items: AiDailyReportItem[];
};

// ---- DW-12 & DW-13 Cấu hình người dùng & Chính sách AI của Chủ (02b §6.5, §6.6) ----
export type MyConfigCommandItem = {
  id: string;
  title: string;
  kind: AiCommandKind;
  level: AiCommandLevel;
  source: "default" | "group" | "override";
  choices: AiCommandLevel[];
  max_level: AiCommandLevel;
  locked_reason: { code: string; text: string } | null;
  red_zone: boolean;
  /**
   * Ngưỡng RIÊNG của người dùng cho lệnh này, dạng PHẲNG như BE thật trả (`AiConfigVersion.limits[id]`, chuỗi thập phân),
   * `null` khi chưa đặt. BE KHÔNG trả trần của Chủ ở đây (02b §6.5 vẽ dạng lồng `{mine, cap}` nhưng BE không làm vậy).
   */
  limits: MyCommandLimits | null;
  /**
   * BE báo lệnh này CÓ khai ngưỡng (kg, vnd) hay không, bất kể người dùng đã đặt hay chưa. Ô ngưỡng vẽ theo cờ này, không theo
   * việc `limits` đang có khoá (xoá ngưỡng xong BE trả `limits` null nhưng ô vẫn phải còn để nhập lại). Cờ mới: BE cũ chưa trả
   * (undefined) thì FE tạm theo khoá `limits` đang có.
   */
  supports_limits?: boolean;
};

export type MyCommandLimits = { kg?: string | null; vnd?: string | null };

export type MyConfigGroup = {
  group: AiCommandGroup;
  label: string;
  read_level: AiCommandLevel;
  write_level: AiCommandLevel;
  commands: MyConfigCommandItem[];
};

export type MyConfig = {
  ai_enabled: boolean;
  version: number;
  killed: boolean;
  updated_at: string;
  global_mode: "on" | "c_only" | "off";
  write_levels_allowed: AiCommandLevel[];
  groups: MyConfigGroup[];
};

export type AiPolicyUserSummary = {
  user_id: number;
  display_name: string;
  groups: string[];
  killed: boolean;
  config_version: number;
  counts: {
    A: number;
    B: number;
    C: number;
    OFF: number;
  };
};

export type AiPolicyRedZoneItem = {
  perm: string;
  label: string;
  open: boolean;
  commands: string[];
  can_do: string;
  cannot_do: string;
  legal_note: string;
  delay_minutes: number;
};

export interface CommandCapConfig {
  max_level?: AiCommandLevel;
  kg?: string | number | null;
  vnd?: string | number | null;
  daily?: number | null;
}

export type PolicyCaps = Record<string, CommandCapConfig>;

export type AiPolicy = {
  version: number;
  global_mode: "on" | "c_only" | "off";
  env: string;
  production_ready: boolean;
  red_zone: AiPolicyRedZoneItem[];
  caps: PolicyCaps;
  users: AiPolicyUserSummary[];
};
