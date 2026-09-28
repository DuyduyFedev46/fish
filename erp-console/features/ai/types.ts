// Kiểu dùng chung của module AI (S05 catalog/status, S01 catalog, S02 execute/propose, S03 audit-logs).
// Chép contract ở doc/features/2026-09-27-ai-native-erp/02b-tech-design.md mục 3. BE đổi thì sửa ở đây.

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

// ---- S01 GET /api/commands/catalog/ ----
export type CommandChannel = "local" | "cloud";
/** sensitivity: "cao" | "trung_binh" | "thap" */
export type CommandSensitivity = "cao" | "trung_binh" | "thap";

/**
 * Lệnh trong catalog — chỉ lệnh `active`, đã lọc theo `min_permissions` của người gọi (S01-AC2).
 * `context_fields` KHÔNG được trả ra ngoài (02b S01).
 */
export type CommandSpec = {
  name: string;
  channel: CommandChannel;
  sensitivity: CommandSensitivity;
  min_permissions: string[];
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  /** Mô tả tiếng Việt. */
  description: string;
  /** Tầng 2: cần người xác nhận (BR-AI-06). */
  needs_confirmation: boolean;
  /** Lệnh cấm chạy qua kênh AI: null | "ai" (BR-AI-07). */
  forbidden_channel: null | "ai";
};

export type CommandCatalog = {
  commands: CommandSpec[];
};

// ---- S02 POST /api/commands/execute/ · propose/ · proposals/<id>/confirm/ ----
export type ExecuteRequest = {
  command: string;
  args: Record<string, unknown>;
  channel: "ui" | "ai_local" | "ai_cloud";
  proposal_id?: number;
};

export type ExecuteResponse = {
  command: string;
  result: unknown;
};

export type ProposeRequest = {
  command: string;
  args: Record<string, unknown>;
  reason: string;
  channel: "ai_local" | "ai_cloud";
};

export type ProposeResponse = {
  proposal_id: number;
  /** ISO datetime — TTL 15 phút. */
  expires_at: string;
};

export type Proposal = {
  id: number;
  command: string;
  args: Record<string, unknown>;
  reason: string;
  channel: "ai_local" | "ai_cloud";
  status: string;
  created_by_display: string;
  created_at: string;
  expires_at: string;
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
  max_level: string;
  sensitivity: string;
  channel: string;
  red_zone: boolean;
  target: string | null;
  form_only: boolean;
  schema_tokens_est: number;
  input_schema: Record<string, unknown> | null;
  output_fields: string[];
};

// ---- DW-10 POST /api/ai/commands/<id>/call/ (02b §6.3) ----
export type CallRequest = {
  args?: Record<string, unknown>;
  target_id?: string | number;
  idempotency_key?: string;
  screen?: string;
  client?: string;
};

export type CallResponse = {
  outcome: "done" | "proposal" | "scheduled";
  level: string;
  action_id: string;
  result?: {
    rows: unknown[];
    total: number;
    truncated: boolean;
  };
  expires_at?: string;
  downgrade_reason?: { code: string; text: string } | null;
  preview?: {
    target: { type: string; code: string };
  };
};

// ---- DW-11 GET /api/ai/actions/ & POST confirm/reject (02b §6.4) ----
export type AiActionRow = {
  id: string;
  command: string;
  title: string;
  kind: "read" | "write";
  level: string;
  status:
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
  owner_display: string;
  created_at: string;
  expires_at: string | null;
  execute_after: string | null;
  undo_until: string | null;
  viewed_at: string | null;
  target: { type: string; code: string };
  args_preview: Record<string, unknown>;
  downgrade_reason: { code: string; text: string } | null;
  confirm_nonce?: string;
};

// ---- DW-12 GET & PUT /api/ai/my-config/ (02b §6.5) ----
export type MyConfigCommandItem = {
  id: string;
  title: string;
  kind: "read" | "write";
  level: string;
  source: "default" | "group" | "override";
  choices: string[];
  max_level: string;
  locked_reason: { code: string; text: string } | null;
  red_zone: boolean;
  limits: Record<string, unknown> | null;
};

export type MyConfigGroup = {
  group: string;
  label: string;
  read_level: string;
  write_level: string;
  commands: MyConfigCommandItem[];
};

export type MyConfig = {
  ai_enabled: boolean;
  version: number;
  killed: boolean;
  updated_at: string | null;
  global_mode: string;
  write_levels_allowed: string[];
  groups: MyConfigGroup[];
};

// ---- DW-13 GET & PUT /api/ai/policy/ (02b §6.6) ----
export type AiPolicyUserSummary = {
  user_id: number;
  display_name: string;
  groups: string[];
  killed: boolean;
  config_version: number;
  counts: { A: number; B: number; C: number; OFF: number };
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
  caps: Record<string, unknown>;
  users: AiPolicyUserSummary[];
};


