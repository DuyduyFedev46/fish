import type {
  ConfirmationQueueDetail,
  ConfirmationQueueItem,
  ConfirmationQueueResponse,
  CustomerSearchResponse,
  CustomerSearchResultItem,
  ClaimTaskResponse,
  RecordCallPayload,
  RecordCallResponse,
  UnconfirmPayload,
  UnconfirmResponse,
  ChangeRecipientPayload,
  ChangeRecipientResponse,
  DecidePayload,
  DecideResponse,
} from "./types";
import { mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import { timeHM } from "@/shared/lib/format";
import type { MockRequest } from "@/shared/lib/http";
import { ROLE } from "@/shared/lib/roles";
import { scriptsForQueueItem } from "./mockScripts";

export const MOCK_CONFIRMATION_ITEMS: ConfirmationQueueDetail[] = [
  {
    note_id: 31,
    order_id: 101,
    order_code: "SO260928-3F9A01",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T08:05:00+07:00",
    confirm_state: "PENDING",
    escalation_reason: null,
    escalation_label: null,
    attempts: 1,
    max_attempts: 3,
    next_call_after: "2026-09-28T09:10:00+07:00",
    window_ends_at: "2026-09-28T09:30:00+07:00",
    callback_at: null,
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Tôm sú loại 1 2,000 kg · Mực lá Phan Thiết 1,000 kg",
    total_kg: "3.000",
    total_amount: "540000",
    in_scope: true,
    customer_name: "Khách Thử A",
    phone: "0900000123",

    phone_masked: "09xx xxx 123",
    address: "Số 1 Đường Thử, P. Thử, Lâm Đồng",
    recipient_name: null,
    recipient_phone: null,
    calls: [
      {
        id: 76,
        at: "2026-09-28T08:50:00+07:00",
        by: { id: 12, display_name: "CSKH Thử" },
        result: "UNREACHABLE",
        result_label: "Không nghe máy / thuê bao",
        note: "Chuông đổ 3 hồi không nghe",
      },
    ],
    available_actions: [
      "claim",
      "call:CONFIRMED",
      "call:UNREACHABLE",
      "call:WRONG_NUMBER",
      "call:CALLBACK",
      "call:WANT_CHANGE",
      "call:WANT_CANCEL",
      "change_recipient",
    ],
    guidance: null,
  },
  {
    note_id: 30,
    order_id: 130,
    order_code: "SO260928-B27C30",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T09:10:00+07:00",
    confirm_state: "PENDING",
    escalation_reason: null,
    escalation_label: null,
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Cá thu Côn Đảo 1,500 kg",
    total_kg: "1.500",
    total_amount: "320000",
    in_scope: true,
    customer_name: "Khách Thử B",
    phone: "0900000456",

    phone_masked: "09xx xxx 456",
    address: "Số 2 Đường Thử, Phường 2, TP. Vũng Tàu",
    recipient_name: null,
    recipient_phone: null,
    calls: [],
    available_actions: [
      "claim",
      "call:CONFIRMED",
      "call:UNREACHABLE",
      "call:WRONG_NUMBER",
      "call:CALLBACK",
      "call:WANT_CHANGE",
      "call:WANT_CANCEL",
      "change_recipient",
    ],
    guidance: null,
  },
  {
    note_id: 35,
    order_id: 135,
    order_code: "SO260928-5D1E35",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T07:30:00+07:00",
    confirm_state: "CALLBACK",
    escalation_reason: null,
    escalation_label: null,
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Cua Cà Mau Y4 2,500 kg",
    total_kg: "2.500",
    total_amount: "750000",
    in_scope: true,
    customer_name: "Khách Thử D",
    phone: "0900000789",

    phone_masked: "09xx xxx 789",
    address: "Số 4 Đường Thử, Q. Ninh Kiều, Cần Thơ",
    recipient_name: null,
    recipient_phone: null,
    calls: [
      {
        id: 74,
        at: "2026-09-28T08:00:00+07:00",
        by: { id: 12, display_name: "CSKH Thử" },
        result: "CALLBACK",
        result_label: "Hẹn gọi lại",
        note: "Khách đang bận họp, hẹn gọi lại sau 1 tiếng",
      },
    ],
    available_actions: [
      "claim",
      "call:CONFIRMED",
      "call:UNREACHABLE",
      "call:WRONG_NUMBER",
      "call:CALLBACK",
      "call:WANT_CHANGE",
      "call:WANT_CANCEL",
      "change_recipient",
    ],
    guidance: null,
  },
  {
    note_id: 28,
    order_id: 108,
    order_code: "SO260928-A40F28",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T08:00:00+07:00",
    confirm_state: "ESCALATED",
    escalation_reason: "UNREACHABLE",
    escalation_label: "Không nghe máy",
    attempts: 3,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: "2026-09-28T09:25:00+07:00",
    decide_deadline: "2026-09-28T09:55:00+07:00",
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Tôm sú loại 1 2,000 kg",
    total_kg: "2.000",
    total_amount: "540000",
    in_scope: true,
    customer_name: "Khách Thử E",
    phone: "0900000999",

    phone_masked: "09xx xxx 999",
    address: "Số 5 Đường Thử, Đà Lạt",
    recipient_name: null,
    recipient_phone: null,
    calls: [
      { id: 71, at: "2026-09-28T09:00:00+07:00", by: { id: 12, display_name: "CSKH Thử" }, result: "UNREACHABLE", result_label: "Không nghe máy", note: "" },
      { id: 72, at: "2026-09-28T09:12:00+07:00", by: { id: 12, display_name: "CSKH Thử" }, result: "UNREACHABLE", result_label: "Không nghe máy", note: "" },
      { id: 73, at: "2026-09-28T09:25:00+07:00", by: { id: 12, display_name: "CSKH Thử" }, result: "UNREACHABLE", result_label: "Không nghe máy", note: "" },
    ],
    available_actions: [
      "claim",
      "decide:DELIVER_WITHOUT_CONFIRM",
      "decide:EXTEND",
      "decide:CANCEL",
    ],
    guidance: null,
  },
  {
    note_id: 27,
    order_id: 107,
    order_code: "SO260928-9C6B27",
    note_status: "CANCELLED",
    paid_at: "2026-09-28T07:30:00+07:00",
    confirm_state: "REFUND_CALL",
    escalation_reason: "UNREACHABLE",
    escalation_label: "Không nghe máy",
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: "2026-09-28T08:00:00+07:00",
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Mực lá Phan Thiết 1,000 kg",
    total_kg: "1.000",
    total_amount: "280000",
    in_scope: true,
    customer_name: "Khách Thử F",
    phone: "0900000888",

    phone_masked: "09xx xxx 888",
    address: "Số 6 Đường Thử, Nha Trang",
    recipient_name: null,
    recipient_phone: null,
    cancelled_at: "2026-09-28T08:31:00+07:00",
    refund: {
      id: 5,
      amount: "280000",
      status: "PENDING",
      status_label: "Chờ hoàn tiền",
      deadline: "2026-10-28",
      refunded_at: null,
    },
    calls: [],
    available_actions: [
      "claim",
      "call:NOTIFIED",
      "call:UNREACHABLE",
    ],
    guidance: "Không ghi số tài khoản khách vào hệ thống. Chủ sẽ lấy số tài khoản trực tiếp từ khách khi chuyển khoản.",
  },
  {
    // SR-09-AC4: phiếu "tự huỷ giữa chừng". Mở màn gọi lúc còn CONFIRMING; ngay khi bấm ghi cuộc gọi, mock mô phỏng job
    // `auto_cancel_overdue` đã chạy trước (đơn + phiếu CANCELLED, task REFUND_CALL) nên trả 409 STALE_STATE như BE thật.
    note_id: 36,
    order_id: 136,
    order_code: "SO260928-E83D36",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T06:00:00+07:00",
    confirm_state: "PENDING",
    escalation_reason: null,
    escalation_label: null,
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Cá thu 2,000 kg",
    total_kg: "2.000",
    total_amount: "360000",
    in_scope: true,
    customer_name: "Khách Thử G",
    phone: "0900000777",

    phone_masked: "09xx xxx 777",
    address: "Số 7 Đường Thử, Quy Nhơn",
    recipient_name: null,
    recipient_phone: null,
    calls: [],
    available_actions: [
      "claim",
      "call:CONFIRMED",
      "call:UNREACHABLE",
      "call:WRONG_NUMBER",
      "call:CALLBACK",
      "call:WANT_CHANGE",
      "call:WANT_CANCEL",
      "change_recipient",
    ],
    guidance: null,
  },
  {
    // Ngoài phạm vi (bất biến 9): BE trả null cho tên, SĐT, địa chỉ và chỉ kèm `phone_masked`. Mở chi tiết → 404.
    note_id: 40,
    order_id: 140,
    order_code: "SO260928-1B7A40",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T05:30:00+07:00",
    confirm_state: "PENDING",
    escalation_reason: null,
    escalation_label: null,
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Ghẹ xanh 1,000 kg",
    total_kg: "1.000",
    total_amount: "210000",
    in_scope: false,
    customer_name: null,
    phone: null,
    phone_masked: "09xx xxx 555",
    address: null,
    recipient_name: null,
    recipient_phone: null,
    calls: [],
    available_actions: [],
    guidance: null,
  },
  {
    // Đang có người khác nhận gọi: claim → 409 CLAIMED; không có thao tác nào trong `available_actions` (như BE).
    note_id: 41,
    order_id: 141,
    order_code: "SO260928-C05E41",
    note_status: "CONFIRMING",
    paid_at: "2026-09-28T05:45:00+07:00",
    confirm_state: "PENDING",
    escalation_reason: null,
    escalation_label: null,
    attempts: 0,
    max_attempts: 3,
    next_call_after: null,
    window_ends_at: null,
    callback_at: null,
    escalated_at: null,
    decide_deadline: null,
    auto_cancel_blocked: null,
    auto_cancel_blocked_label: null,
    claimed_by: { id: 99, display_name: "Chị Lan" },
    claimed_until: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    lines_summary: "Tôm thẻ 1,500 kg",
    total_kg: "1.500",
    total_amount: "330000",
    in_scope: true,
    customer_name: "Khách Thử H",
    phone: "0900000666",
    phone_masked: "09xx xxx 666",
    address: "Số 8 Đường Thử, Huế",
    recipient_name: null,
    recipient_phone: null,
    calls: [],
    available_actions: [],
    guidance: null,
  },
];

/** Phiếu mock sẽ bị "job tự huỷ" chạy trước ở lần ghi cuộc gọi đầu tiên (SR-09-AC4). */
export const MOCK_STALE_ON_CALL_IDS = new Set<number>([36]);
/**
 * Dữ liệu thật của phiếu ngoài phạm vi CSKH. Chỉ Chủ/Quản lý (phạm vi đủ, như `has_full_delivery_scope` của BE) và việc tìm
 * kiếm theo số mới đụng tới; CSKH chỉ nhận null + `phone_masked` (bất biến 9).
 */
const OUT_OF_SCOPE_REAL: Record<number, { customer_name: string; phone: string; address: string }> = {
  40: { customer_name: "Khách Thử K", phone: "0900000555", address: "Số 9 Đường Thử, Hải Phòng" },
};

function hasFullScope(me: Me | null): boolean {
  return !!me && (me.groups.includes(ROLE.owner) || me.groups.includes(ROLE.manager));
}

function meOf(req: unknown): Me | null {
  const r = req as MockRequest | undefined;
  return r && "token" in r ? mockRequireUser(r) : null;
}

/** Bản của phiếu đúng như người xem nhận từ BE: ngoài phạm vi thì che dữ liệu khách, Chủ/Quản lý thì thấy đủ. */
function viewFor(item: ConfirmationQueueDetail, me: Me | null): ConfirmationQueueDetail {
  const real = OUT_OF_SCOPE_REAL[item.note_id];
  if (!item.in_scope && real && hasFullScope(me)) return { ...item, in_scope: true, ...real };
  return { ...item };
}

/** `available_actions` theo quyền người xem, mô phỏng `ConfirmationQueueDetailSerializer` của BE. */
function actionsFor(item: ConfirmationQueueDetail, me: Me | null): string[] {
  if (!me) return item.available_actions; // test thuần không có người dùng
  const perms = new Set(me.permissions);
  const claimedByOther = !!item.claimed_by && !!item.claimed_until && new Date(item.claimed_until).getTime() > Date.now() && item.claimed_by.id !== me.id;
  if (claimedByOther) return [];
  const out: string[] = [];
  if (perms.has("delivery.confirm_with_customer")) {
    out.push("claim");
    if (item.note_status === "CONFIRMING") out.push("call:CONFIRMED", "call:UNREACHABLE", "call:WRONG_NUMBER", "call:CALLBACK", "call:WANT_CHANGE", "call:WANT_CANCEL");
    else if (item.confirm_state === "REFUND_CALL") out.push("call:NOTIFIED", "call:UNREACHABLE");
  }
  if (perms.has("delivery.change_recipient") && (item.note_status === "CONFIRMING" || item.note_status === "PREPARING")) out.push("change_recipient");
  if (item.note_status === "PREPARING" && item.confirm_state === null && perms.has("delivery.confirm_with_customer")) out.push("unconfirm");
  if (perms.has("delivery.decide_unconfirmed") && item.confirm_state === "ESCALATED") out.push("decide:DELIVER_WITHOUT_CONFIRM", "decide:EXTEND", "decide:CANCEL");
  return out;
}

const FORBIDDEN = { status: 403, body: { code: "PERMISSION_DENIED", detail: "Bạn không có quyền thực hiện thao tác này." } };

export const STALE_STATE_DETAIL = "Đơn đã bị huỷ — tải lại màn hình.";

/**
 * Lô 7 (nợ Lô 3 L4): phiếu được "gài" để thao tác kế tiếp (đổi người nhận / huỷ xác nhận / quyết định Quản lý) gặp
 * 409 STALE_STATE như BE thật khi job tự huỷ đã chạy giữa chừng. Dùng cho e2e qua `window.__caveMock.confirmationArmStale(noteId)`.
 */
const ARMED_STALE = new Set<number>();

function consumeArmedStale(noteId: number): { status: number; body: { code: string; detail: string } } | null {
  if (!ARMED_STALE.has(noteId)) return null;
  ARMED_STALE.delete(noteId);
  const item = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  if (item) {
    item.note_status = "CANCELLED";
    item.confirm_state = "REFUND_CALL";
  }
  return { status: 409, body: { code: "STALE_STATE", detail: STALE_STATE_DETAIL } };
}

export function getMockConfirmationQueue(params?: { state?: string; page?: number }, me: Me | null = null): ConfirmationQueueResponse {
  let list = [...MOCK_CONFIRMATION_ITEMS];
  const now = new Date().toISOString();

  if (params?.state) {
    list = list.filter((i) => i.confirm_state === params.state);
  } else {
    // Default: PENDING + CALLBACK where callback_at <= now
    list = list.filter((i) => {
      if (i.note_status !== "CONFIRMING") return false;
      if (i.confirm_state === "PENDING") return true;
      if (i.confirm_state === "CALLBACK" && i.callback_at && i.callback_at <= now) return true;
      return false;
    });
  }

  // Sort: PENDING/CALLBACK by paid_at asc
  list.sort((a, b) => {
    const tA = a.paid_at ? new Date(a.paid_at).getTime() : 0;
    const tB = b.paid_at ? new Date(b.paid_at).getTime() : 0;
    return tA - tB;
  });

  return {
    count: list.length,
    next: null,
    previous: null,
    // Như BE: dòng danh sách không kèm lịch sử cuộc gọi hay thao tác; dữ liệu khách theo phạm vi người xem.
    results: list.map((item) => {
      const { calls: _calls, available_actions: _actions, ...row } = viewFor(item, me);
      void _calls;
      void _actions;
      return { ...row, note_code: noteCodeOf(row.order_code) };
    }) as ConfirmationQueueItem[],
  };
}

/** Lô 17b-BE (L5-code): danh sách và chi tiết đều có `note_code` (mã phiếu giao của đơn), không bao giờ null. */
function noteCodeOf(orderCode: string): string {
  return `GH-${orderCode.replace(/^SO/, "")}`;
}

export function mockGetConfirmationQueue(req: any): { status: number; body: ConfirmationQueueResponse } {
  let state: string | undefined;
  let page: number | undefined;
  // MockRequest của apiFetch có `path` (kèm query), không có `url` — trước đây `state` không bao giờ được đọc.
  const rawUrl: string | undefined = req?.url ?? req?.path;
  if (rawUrl) {
    try {
      const u = new URL(rawUrl, "http://localhost");
      state = u.searchParams.get("state") || undefined;
      const p = u.searchParams.get("page");
      if (p) page = parseInt(p, 10);
    } catch {
      // ignore
    }
  }
  return {
    status: 200,
    body: getMockConfirmationQueue({ state, page }, meOf(req)),
  };
}

/** Số lần tải chi tiết kế tiếp trả 500 (công cụ thử `confirmationFailNextDetail`). */
let FAIL_DETAIL_NEXT = 0;

export function mockGetConfirmationDetail(
  req: any,
  noteId: number
): { status: number; body: ConfirmationQueueDetail | { detail: string; code?: string } } {
  if (FAIL_DETAIL_NEXT > 0) {
    FAIL_DETAIL_NEXT -= 1;
    return { status: 500, body: { detail: "Lỗi máy chủ." } };
  }
  const me = meOf(req);
  const found = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  const item = found ? viewFor(found, me) : null;
  if (!item || !item.in_scope) {
    return {
      status: 404,
      body: { detail: "Không tìm thấy phiếu trong phạm vi gọi xác nhận của bạn." },
    };
  }
  return {
    status: 200,
    body: { ...item, decision_note: item.in_scope ? item.decision_note ?? "" : "", note_code: noteCodeOf(item.order_code), available_actions: actionsFor(item, me), scripts: scriptsForQueueItem(item, me) },
  };
}

export function mockClaimConfirmationTask(
  req: any,
  noteId: number
): { status: number; body: ClaimTaskResponse | { code: string; detail: string; claimed_until?: string } } {
  const me = meOf(req);
  const myId = me?.id ?? 12;
  const item = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  if (!item || !item.in_scope) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
  if (me && !me.permissions.includes("delivery.confirm_with_customer")) return FORBIDDEN;

  const now = Date.now();
  if (item.claimed_by && item.claimed_until) {
    const until = new Date(item.claimed_until).getTime();
    if (until > now && item.claimed_by.id !== myId) {
      return {
        status: 409,
        body: {
          code: "CLAIMED",
          detail: `Đơn đang được ${item.claimed_by.display_name} xử lý tới ${timeHM(item.claimed_until)}.`,
          claimed_until: item.claimed_until,
        },
      };
    }
  }

  const untilIso = new Date(now + 5 * 60 * 1000).toISOString();
  item.claimed_by = { id: myId, display_name: me?.display_name ?? "CSKH Thử" };
  item.claimed_until = untilIso;

  return {
    status: 200,
    body: {
      claimed_by: item.claimed_by,
      claimed_until: untilIso,
    },
  };
}

export function mockRecordConfirmationCall(
  req: any,
  noteId: number,
  payload: RecordCallPayload
): { status: number; body: RecordCallResponse | { code: string; detail: string } } {
  const me = meOf(req);
  const item = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  if (!item || (!item.in_scope && !hasFullScope(me))) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
  if (me && !me.permissions.includes("delivery.confirm_with_customer")) return FORBIDDEN;
  if (me && item.claimed_by && item.claimed_until && new Date(item.claimed_until).getTime() > Date.now() && item.claimed_by.id !== me.id) {
    return {
      status: 409,
      body: { code: "CLAIMED", detail: `Đơn đang được ${item.claimed_by.display_name} xử lý tới ${timeHM(item.claimed_until)}.` },
    };
  }

  // Mô phỏng job tự huỷ chạy giữa lúc CSKH mở màn và lúc bấm (SR-09 AC3b).
  if (MOCK_STALE_ON_CALL_IDS.has(noteId) && item.note_status === "CONFIRMING") {
    MOCK_STALE_ON_CALL_IDS.delete(noteId);
    item.note_status = "CANCELLED";
    item.confirm_state = "REFUND_CALL";
    item.escalation_reason = "UNREACHABLE";
    item.escalation_label = "Không nghe máy";
    item.available_actions = ["claim", "call:NOTIFIED", "call:UNREACHABLE"];
  }

  // SR-09 AC1/AC2/02b §3.2: như BE — phiếu đã huỷ mà không phải việc báo hoàn tiền, hoặc việc báo hoàn tiền mà kết quả
  // không phải UNREACHABLE/NOTIFIED → 409 STALE_STATE (màn hình cũ).
  if (item.note_status === "CANCELLED") {
    const refundOnly = item.confirm_state === "REFUND_CALL";
    if (!refundOnly || (payload.result !== "UNREACHABLE" && payload.result !== "NOTIFIED")) {
      return { status: 409, body: { code: "STALE_STATE", detail: STALE_STATE_DETAIL } };
    }
  }

  // Validate note for BR-GH-19: no >= 9 digits
  if (payload.note) {
    if (payload.note.length > 200) {
      return { status: 400, body: { code: "BR-GH-19", detail: "Ghi chú không quá 200 ký tự." } };
    }
    const cleanDigits = payload.note.replace(/[\s.\-]/g, "");
    if (/\d{9,}/.test(cleanDigits)) {
      return {
        status: 400,
        body: { code: "BR-GH-19", detail: "Không ghi SĐT hay số tài khoản vào ghi chú." },
      };
    }
  }

  if (payload.result === "CALLBACK") {
    if (!payload.callback_at || new Date(payload.callback_at).getTime() <= Date.now()) {
      return {
        status: 400,
        body: { code: "INVALID_INPUT", detail: "Giờ hẹn gọi lại phải ở tương lai." },
      };
    }
  }

  const callId = Math.floor(Math.random() * 1000) + 100;
  const newCall = {
    id: callId,
    at: new Date().toISOString(),
    by: { id: me?.id ?? 12, display_name: me?.display_name ?? "CSKH Thử" },
    result: payload.result,
    result_label:
      payload.result === "CONFIRMED"
        ? "Đã xác nhận"
        : payload.result === "CALLBACK"
        ? "Hẹn gọi lại"
        : payload.result === "UNREACHABLE"
        ? "Không nghe máy / thuê bao"
        : payload.result === "WRONG_NUMBER"
        ? "Sai số điện thoại"
        : payload.result === "WANT_CHANGE"
        ? "Khách muốn đổi món"
        : payload.result === "WANT_CANCEL"
        ? "Khách muốn huỷ đơn"
        : payload.result === "NOTIFIED"
        ? "Đã báo hoàn tiền"
        : "Đã thông báo",
    note: payload.note || "",
  };
  item.calls.unshift(newCall);

  // Clear soft lock
  item.claimed_by = null;
  item.claimed_until = null;

  if (payload.result === "NOTIFIED") {
    item.confirm_state = null;
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: item.note_status,
        confirm_state: null,
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  if (payload.result === "CONFIRMED") {
    item.note_status = "PREPARING";
    item.confirm_state = null;
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: "PREPARING",
        confirm_state: null,
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  if (payload.result === "CALLBACK") {
    item.confirm_state = "CALLBACK";
    item.callback_at = payload.callback_at || null;
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: item.note_status,
        confirm_state: "CALLBACK",
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  if (payload.result === "UNREACHABLE") {
    item.attempts += 1;
    if (item.attempts >= item.max_attempts) {
      item.confirm_state = "ESCALATED";
      item.escalation_reason = "UNREACHABLE";
      item.escalation_label = "Không nghe máy quá số lần";
    }
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: item.note_status,
        confirm_state: item.confirm_state,
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  if (payload.result === "WRONG_NUMBER") {
    item.confirm_state = "ESCALATED";
    item.escalation_reason = "WRONG_NUMBER";
    item.escalation_label = "Sai số điện thoại";
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: item.note_status,
        confirm_state: "ESCALATED",
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  if (payload.result === "WANT_CHANGE" || payload.result === "WANT_CANCEL") {
    item.confirm_state = "ESCALATED";
    item.escalation_reason = payload.result;
    item.escalation_label = payload.result === "WANT_CHANGE" ? "Khách muốn đổi món" : "Khách muốn huỷ đơn";
    return {
      status: 201,
      body: {
        call_id: callId,
        note_status: item.note_status,
        confirm_state: "ESCALATED",
        attempts: item.attempts,
        duplicate: false,
      },
    };
  }

  return {
    status: 201,
    body: {
      call_id: callId,
      note_status: item.note_status,
      confirm_state: item.confirm_state,
      attempts: item.attempts,
      duplicate: false,
    },
  };
}

export function mockUnconfirm(
  req: any,
  noteId: number,
  payload: UnconfirmPayload
): { status: number; body: UnconfirmResponse | { code: string; detail: string } } {
  const item = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
  const stale = consumeArmedStale(noteId);
  if (stale) return stale;
  item.note_status = "CONFIRMING";
  item.confirm_state = "PENDING";
  return {
    status: 200,
    body: {
      note_status: "CONFIRMING",
      confirm_state: "PENDING",
    },
  };
}

export function mockChangeRecipient(
  req: any,
  noteId: number,
  payload: ChangeRecipientPayload
): { status: number; body: ChangeRecipientResponse | { code: string; detail: string } } {
  const item = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
  const stale = consumeArmedStale(noteId);
  if (stale) return stale;
  const changed: string[] = [];
  if (payload.delivery_address !== undefined) {
    item.address = payload.delivery_address;
    changed.push("delivery_address");
  }
  if (payload.recipient_name !== undefined) {
    item.recipient_name = payload.recipient_name || null;
    changed.push("recipient_name");
  }
  if (payload.recipient_phone !== undefined) {
    item.recipient_phone = payload.recipient_phone || null;
    changed.push("recipient_phone");
  }
  return {
    status: 200,
    body: {
      changed,
      label_invalidated: true,
    },
  };
}

export function mockSearchCustomers(
  req: any,
  q: string
): { status: number; body: CustomerSearchResponse | { code: string; detail: string } } {
  const normalized = q.replace(/[\s.\-]/g, "").replace(/^\+84/, "0");
  const isDigits = /^\d+$/.test(normalized);

  if (isDigits && normalized.length < 9) {
    return {
      status: 400,
      body: { code: "INVALID_QUERY", detail: "Nhập đủ số điện thoại hoặc đúng mã đơn." },
    };
  }

  const results: CustomerSearchResultItem[] = [];

  for (const item of MOCK_CONFIRMATION_ITEMS) {
    let matched = false;
    if (isDigits) {
      const realPhone = item.phone ?? OUT_OF_SCOPE_REAL[item.note_id]?.phone ?? "";
      if (realPhone === normalized || item.recipient_phone === normalized) {
        matched = true;
      }
    } else {
      if (item.order_code.toLowerCase().includes(q.toLowerCase())) {
        matched = true;
      }
    }

    if (matched) {
      if (item.in_scope) {
        results.push({
          note_id: item.note_id,
          order_code: item.order_code,
          status_label: item.note_status === "CONFIRMING" ? "Chờ gọi xác nhận" : "Đang soạn hàng",
          in_scope: true,
          customer_name: item.customer_name ?? undefined,
          phone: item.phone ?? undefined,
        });
      } else {
        results.push({
          note_id: item.note_id,
          order_code: item.order_code,
          status_label: "Đang giao",
          in_scope: false,
          phone_masked: item.phone_masked,
        });
      }
    }
  }

  return {
    status: 200,
    body: { results },
  };
}

export function mockDecideConfirmation(
  req: any,
  noteId: number,
  payload: DecidePayload
): { status: number; body: DecideResponse | { code: string; detail: string } } {
  const me = meOf(req);
  if (me && !me.permissions.includes("delivery.decide_unconfirmed")) return FORBIDDEN;
  const item = MOCK_CONFIRMATION_ITEMS.find((it) => it.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy mục chờ gọi." } };
  }
  const armed = consumeArmedStale(noteId);
  if (armed) return armed;
  if (item.confirm_state !== "ESCALATED") {
    return {
      status: 409,
      body: {
        code: "STALE_STATE",
        detail: "Đơn đã được xử lý.",
        current_status: item.note_status,
        confirm_state: item.confirm_state,
      } as any,
    };
  }

  // BR-GH-19: lý do / ghi chú quyết định không quá 200 ký tự và không chứa chuỗi ≥ 9 chữ số (SĐT, số tài khoản).
  const decisionText = (payload.decision === "CANCEL" ? payload.note : payload.reason)?.trim() ?? "";
  if (decisionText.length > 200) return { status: 400, body: { code: "BR-GH-19", detail: "Ghi chú không quá 200 ký tự." } };
  if (/\d{9,}/.test(decisionText.replace(/[\s.\-_/]/g, ""))) {
    return { status: 400, body: { code: "BR-GH-19", detail: "Không ghi SĐT hay số tài khoản vào ghi chú." } };
  }
  item.decision_note = decisionText;

  if (payload.decision === "DELIVER_WITHOUT_CONFIRM") {
    if (!payload.reason?.trim()) {
      return { status: 400, body: { code: "INVALID_INPUT", detail: "Lý do bỏ qua xác nhận bắt buộc." } };
    }
    item.note_status = "PREPARING";
    item.confirm_state = null;
    return {
      status: 200,
      body: {
        note_status: "PREPARING",
        confirm_state: null,
        order_id: item.order_id,
        suggest_refund_amount: null,
      },
    };
  } else if (payload.decision === "EXTEND") {
    if (!payload.until) {
      return { status: 400, body: { code: "INVALID_INPUT", detail: "Giờ gia hạn bắt buộc." } };
    }
    item.confirm_state = "CALLBACK";
    item.callback_at = payload.until;
    item.attempts = 0;
    return {
      status: 200,
      body: {
        note_status: "CONFIRMING",
        confirm_state: "CALLBACK",
        order_id: item.order_id,
        suggest_refund_amount: null,
      },
    };
  } else if (payload.decision === "CANCEL") {
    item.note_status = "CANCELLED";
    item.confirm_state = null;
    return {
      status: 200,
      body: {
        note_status: "CANCELLED",
        confirm_state: null,
        order_id: item.order_id,
        suggest_refund_amount: item.total_amount,
      },
    };
  }
  return { status: 400, body: { code: "INVALID_INPUT", detail: "Quyết định không hợp lệ." } };
}

// Công cụ thử trong DevTools/e2e (chỉ có ở mock):
//   window.__caveMock.confirmationArmStale(noteId)         — thao tác kế tiếp trên phiếu này gặp 409 STALE_STATE (job tự huỷ đã chạy)
//   window.__caveMock.confirmationClaimByOther(noteId)     — người khác giữ phiếu: thao tác kế tiếp gặp 409 CLAIMED
//   window.__caveMock.confirmationFailNextDetail(n)        — n lần tải chi tiết kế tiếp trả 500
//   window.__caveMock.confirmationSetStatus(noteId, "PREPARING") — đổi trạng thái phiếu (PREPARING cũng xoá confirm_state) để mở nút "Huỷ xác nhận đơn"
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    confirmationArmStale: (noteId: number) => {
      ARMED_STALE.add(noteId);
      return `Phiếu ${noteId}: thao tác kế tiếp sẽ gặp STALE_STATE`;
    },
    /** Người khác giữ phiếu thêm 10 phút: thao tác tiếp theo của người đang đăng nhập gặp 409 CLAIMED. */
    confirmationClaimByOther: (noteId: number) => {
      const it = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
      if (!it) return "Không có phiếu";
      it.claimed_by = { id: 99, display_name: "Chị Lan" };
      it.claimed_until = new Date(Date.now() + 10 * 60 * 1000).toISOString();
      return `Phiếu ${noteId}: Chị Lan đang giữ`;
    },
    /** n lần tải chi tiết kế tiếp trả 500 (kiểm: tải lại lỗi thì giữ dữ liệu cũ và hiện cảnh báo). */
    confirmationFailNextDetail: (n = 1) => {
      FAIL_DETAIL_NEXT = n;
      return `Chi tiết: ${n} lần tải kế tiếp trả 500`;
    },
    confirmationSetStatus: (noteId: number, status: string) => {
      const it = MOCK_CONFIRMATION_ITEMS.find((i) => i.note_id === noteId);
      if (it) {
        (it as { note_status: string }).note_status = status;
        // Phiếu đã sang Soạn hàng thì không còn nhiệm vụ gọi (confirm_state rỗng), giống BE thật: nhờ vậy mới có "Huỷ xác nhận đơn".
        if (status === "PREPARING") (it as { confirm_state: unknown }).confirm_state = null;
      }
      return it ? `Phiếu ${noteId}: ${status}` : "Không có phiếu";
    },
  };
}
