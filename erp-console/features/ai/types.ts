// Kiểu dùng chung của module AI (02b §6).
// Chép contract ở doc/features/2026-09-28-ai-digital-worker/02b-tech-design.md. BE đổi thì sửa ở đây.

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

// ---- S03 GET /api/audit-logs/ (màn Nhật ký hoạt động — module features/audit dùng) ----
export type AuditActorKind = "user" | "system" | "ai";

export type AuditLogRow = {
  id: number;
  actor_kind: AuditActorKind;
  /** Dòng AI: "ai:<tên user>" (S03-AC2); dòng user/system: tên như cũ. */
  actor_display: string;
  /** Chỉ có ở dòng AI — thông tin người dùng mà AI đại diện. */
  ai_actor: { id: number; username: string; display_name: string } | null;
  /** Động từ hành động (vd "create", "update", "execute_command"). */
  action: string;
  model_name: string;
  object_id: number | null;
  object_repr: string | null;
  /** JSON thay đổi — KHÔNG chứa tên/SĐT/địa chỉ khách (S03-AC4). */
  changes: Record<string, unknown> | null;
  note: string | null;
  proposal_ref: string | null;
  created_at: string;
};

export type AuditLogParams = {
  actor_kind?: "" | AuditActorKind;
  action?: string;
};

// ---- DW-07 & DW-09 Chỉ mục lệnh & Mô tả lệnh (02b §6.1, §6.2) ----
export type AiCommandGroup = "thu_mua" | "ban_hang" | "cskh";
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
  sensitivity: "cao" | "trung_binh" | "thap";
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
};

export type AiActionDetail = AiActionRow & {
  confirm_nonce?: string;
  viewable_from?: string;
  viewed_at?: string | null;
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
  limits: {
    kg?: { mine: string | null; cap: string | null };
    vnd?: { mine: string | null; cap: string | null };
  } | null;
};

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

export type AiPolicy = {
  version: number;
  global_mode: "on" | "c_only" | "off";
  env: string;
  production_ready: boolean;
  red_zone: AiPolicyRedZoneItem[];
  caps: Array<{
    command: string;
    max_level: AiCommandLevel;
    kg: string;
    vnd: string;
    daily: number;
  }>;
  users: AiPolicyUserSummary[];
};
