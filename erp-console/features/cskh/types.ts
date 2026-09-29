export type CskhConfirmState =
  | "PENDING"
  | "CALLBACK"
  | "ESCALATED"
  | "REFUND_CALL"
  | "DONE";

export type CskhQueueItem = {
  note_id: number;
  order_id: number;
  order_code: string;
  note_status: string;
  paid_at: string | null;
  confirm_state: CskhConfirmState | null;
  escalation_reason: string | null;
  escalation_label: string | null;
  attempts: number;
  max_attempts: number;
  next_call_after: string | null;
  window_ends_at: string | null;
  callback_at: string | null;
  escalated_at: string | null;
  decide_deadline: string | null;
  auto_cancel_blocked: string | null;
  claimed_by: { id: number; display_name: string } | null;
  claimed_until: string | null;
  lines_summary: string;
  total_kg: string;
  total_amount: string;
  in_scope: boolean;
  customer_name: string;
  phone: string;
  address: string;
  recipient_name: string | null;
  recipient_phone: string | null;
  cancelled_at?: string | null;
  guidance?: string | null;
  refund?: {
    id: number;
    amount: string;
    status: string;
    status_label: string;
    deadline: string;
    refunded_at: string | null;
  } | null;
};

export type CustomerCall = {
  id: number;
  at: string;
  by: { id: number; display_name: string };
  result: string;
  result_label: string;
  note: string;
};

export type CskhQueueDetail = CskhQueueItem & {
  calls: CustomerCall[];
  available_actions: string[];
  guidance?: string | null;
};

export type CskhQueueResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: CskhQueueItem[];
};

export type CskhSearchResultItem = {
  note_id: number;
  order_code: string;
  status_label: string;
  in_scope: boolean;
  customer_name?: string;
  phone?: string;
  phone_masked?: string;
};

export type CskhSearchResponse = {
  results: CskhSearchResultItem[];
};

export type CallResult =
  | "CONFIRMED"
  | "CALLBACK"
  | "UNREACHABLE"
  | "WRONG_NUMBER"
  | "WANT_CHANGE"
  | "WANT_CANCEL"
  | "NOTIFIED";

export const CALL_RESULT_OPTIONS: Array<{
  value: CallResult;
  label: string;
  tone: "good" | "warn" | "crit" | "info" | "mute";
  hint: string;
}> = [
  {
    value: "CONFIRMED",
    label: "Đã xác nhận",
    tone: "good",
    hint: "Khách đồng ý nhận hàng. Đơn sẽ chuyển sang Soạn hàng để kho đóng gói.",
  },
  {
    value: "CALLBACK",
    label: "Hẹn gọi lại",
    tone: "warn",
    hint: "Khách bận hoặc nhờ gọi lại sau. Chọn thời gian hẹn gọi lại.",
  },
  {
    value: "UNREACHABLE",
    label: "Không nghe máy",
    tone: "crit",
    hint: "Thuê bao / máy bận / không trả lời.",
  },
  {
    value: "WRONG_NUMBER",
    label: "Sai số điện thoại",
    tone: "crit",
    hint: "Số không có thực hoặc nhầm người. Chuyển ngay sang Quản lý.",
  },
  {
    value: "WANT_CHANGE",
    label: "Khách muốn đổi món",
    tone: "info",
    hint: "Khách muốn đổi hàng. Chuyển Quản lý xử lý huỷ + hoàn tiền để đặt lại.",
  },
  {
    value: "WANT_CANCEL",
    label: "Khách muốn huỷ đơn",
    tone: "info",
    hint: "Khách đổi ý không lấy nữa. Chuyển Quản lý xử lý huỷ đơn.",
  },
  {
    value: "NOTIFIED",
    label: "Đã báo hoàn tiền",
    tone: "good",
    hint: "Đã liên hệ với khách để thông báo đơn bị huỷ và chính sách hoàn tiền.",
  },
];

export type CskhDecision = "DELIVER_WITHOUT_CONFIRM" | "EXTEND" | "CANCEL";

export type DecidePayload = {
  decision: CskhDecision;
  reason?: string;
  until?: string | null;
  reason_code?: string;
  note?: string;
};

export type DecideResponse = {
  note_status: string;
  confirm_state: string | null;
  order_id: number;
  suggest_refund_amount: string | null;
};

export type RecordCallPayload = {
  result: CallResult;
  note?: string;
  callback_at?: string | null;
  request_id: string;
};

export type RecordCallResponse = {
  call_id: number;
  note_status: string;
  confirm_state: string | null;
  attempts: number;
  duplicate: boolean;
};

export type ClaimTaskResponse = {
  claimed_by: { id: number; display_name: string };
  claimed_until: string;
};

export type UnconfirmPayload = {
  reason: string;
};

export type UnconfirmResponse = {
  note_status: string;
  confirm_state: string;
};

export type ChangeRecipientPayload = {
  delivery_address?: string;
  recipient_name?: string;
  recipient_phone?: string;
};

export type ChangeRecipientResponse = {
  changed: string[];
  label_invalidated: boolean;
};

export type QueueTabKey = "DEFAULT" | "PENDING" | "CALLBACK" | "ESCALATED" | "REFUND_CALL" | "ALL";

export const QUEUE_TABS: Array<{ key: QueueTabKey; label: string; stateParam?: string }> = [
  { key: "DEFAULT", label: "Cần gọi ngay" },
  { key: "CALLBACK", label: "Hẹn gọi lại", stateParam: "CALLBACK" },
  { key: "ESCALATED", label: "Cần quyết định", stateParam: "ESCALATED" },
  { key: "REFUND_CALL", label: "Báo hoàn tiền", stateParam: "REFUND_CALL" },
  { key: "PENDING", label: "Chờ gọi", stateParam: "PENDING" },
  { key: "ALL", label: "Tất cả" },
];
