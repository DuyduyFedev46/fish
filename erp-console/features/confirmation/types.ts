export type ConfirmationState =
  | "PENDING"
  | "CALLBACK"
  | "ESCALATED"
  | "REFUND_CALL"
  | "DONE";

export type ConfirmationQueueItem = {
  note_id: number;
  order_id: number;
  order_code: string;
  note_status: string;
  paid_at: string | null;
  confirm_state: ConfirmationState | null;
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
  /**
   * Dữ liệu khách chỉ có khi `in_scope` (bất biến 9): ngoài phạm vi BE trả null và chỉ kèm `phone_masked`.
   * FE không tự che hay ghép số điện thoại: hiện đúng chuỗi BE trả.
   */
  customer_name: string | null;
  phone: string | null;
  address: string | null;
  /** Số đã che sẵn bởi BE (vd "09xx xxx 123"); luôn có, kể cả trong phạm vi. */
  phone_masked: string;
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
  /** BE trả null khi người ghi cuộc gọi đã bị xoá. */
  by: { id: number; display_name: string } | null;
  result: string;
  result_label: string;
  note: string;
};

/** Dòng của danh sách: `usePagedList` cần khoá `id`; ở đây `id` chính là `note_id` (phiếu giao). */
export type ConfirmationQueueRow = ConfirmationQueueItem & { id: number };

export type ConfirmationQueueDetail = ConfirmationQueueItem & {
  /** Mã phiếu giao ("Phiếu giao" ở chi tiết). BE (02b R1) chưa trả trường này: thiếu thì hiện "—" (lệch hợp đồng, ghi ở 03-dev-notes). */
  note_code?: string | null;
  calls: CustomerCall[];
  available_actions: string[];
  guidance?: string | null;
  /** CS-18: kịch bản gọi hợp với đơn này (chỉ kịch bản đang bật, chỉ khi người xem có quyền xem kịch bản; không thì rỗng hoặc thiếu). */
  scripts?: QueueScript[];
  /** Lý do quyết định của Chủ/Quản lý (BR-GH-19). BE trả "" khi chưa có hoặc phiếu ngoài phạm vi. Thiếu (BE cũ) = không hiện. */
  decision_note?: string;
};

export type ConfirmationQueueResponse = {
  count: number;
  next: string | null;
  previous: string | null;
  results: ConfirmationQueueItem[];
};

export type CustomerSearchResultItem = {
  note_id: number;
  order_code: string;
  status_label: string;
  in_scope: boolean;
  customer_name?: string;
  phone?: string;
  phone_masked?: string;
};

export type CustomerSearchResponse = {
  results: CustomerSearchResultItem[];
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
}> = [
  {
    value: "CONFIRMED",
    label: "Đã xác nhận",
    tone: "good",
  },
  {
    value: "CALLBACK",
    label: "Hẹn gọi lại",
    tone: "warn",
  },
  {
    value: "UNREACHABLE",
    label: "Không nghe máy",
    tone: "crit",
  },
  {
    value: "WRONG_NUMBER",
    label: "Sai số điện thoại",
    tone: "crit",
  },
  {
    value: "WANT_CHANGE",
    label: "Khách muốn đổi món",
    tone: "info",
  },
  {
    value: "WANT_CANCEL",
    label: "Khách muốn huỷ đơn",
    tone: "info",
  },
  {
    value: "NOTIFIED",
    label: "Đã báo hoàn tiền",
    tone: "good",
  },
];

export type ConfirmationDecision = "DELIVER_WITHOUT_CONFIRM" | "EXTEND" | "CANCEL";

export type DecidePayload = {
  decision: ConfirmationDecision;
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
  { key: "REFUND_CALL", label: "Gọi báo hoàn tiền", stateParam: "REFUND_CALL" },
  { key: "PENDING", label: "Chờ gọi", stateParam: "PENDING" },
  { key: "ALL", label: "Tất cả" },
];

// ---- CS-18: kịch bản gọi soạn sẵn ----
/** FIRST_ORDER khách mua lần đầu · RETURNING khách quen · COMBO đơn có combo · GENERAL lời dặn chung. */
export type CallScriptSituation = "FIRST_ORDER" | "RETURNING" | "COMBO" | "GENERAL";

export type CallScript = {
  situation: CallScriptSituation;
  situation_label: string;
  content: string;
  is_active: boolean;
};

export type QueueScript = Pick<CallScript, "situation" | "situation_label" | "content">;

export type CallScriptsResponse = { results: CallScript[] };

export type CallScriptCreatePayload = { situation: CallScriptSituation; content: string; is_active: boolean };
export type CallScriptUpdatePayload = { content?: string; is_active?: boolean };
