import type {
  CskhQueueDetail,
  CskhQueueItem,
  CskhQueueResponse,
  CskhSearchResponse,
  CskhSearchResultItem,
  ClaimTaskResponse,
  RecordCallPayload,
  RecordCallResponse,
  UnconfirmPayload,
  UnconfirmResponse,
  ChangeRecipientPayload,
  ChangeRecipientResponse,
} from "./types";

export const MOCK_CSKH_ITEMS: CskhQueueDetail[] = [
  {
    note_id: 31,
    order_id: 101,
    order_code: "DH-260928-0001",
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
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Tôm sú loại 1 2,000 kg · Mực lá Phan Thiết 1,000 kg",
    total_kg: "3.000",
    total_amount: "540000",
    in_scope: true,
    customer_name: "Khách Thử A",
    phone: "0900000123",
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
    order_code: "DH-260928-0030",
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
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Cá thu Côn Đảo 1,500 kg",
    total_kg: "1.500",
    total_amount: "320000",
    in_scope: true,
    customer_name: "Khách Thử B",
    phone: "0900000456",
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
    order_code: "DH-260928-0035",
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
    claimed_by: null,
    claimed_until: null,
    lines_summary: "Cua Cà Mau Y4 2,500 kg",
    total_kg: "2.500",
    total_amount: "750000",
    in_scope: true,
    customer_name: "Khách Thử D",
    phone: "0900000789",
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
];

export function getMockCskhQueue(params?: { state?: string; page?: number }): CskhQueueResponse {
  let list = [...MOCK_CSKH_ITEMS];
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
    results: list.map((item) => ({ ...item })),
  };
}

export function mockGetCskhQueue(req: any): { status: number; body: CskhQueueResponse } {
  let state: string | undefined;
  let page: number | undefined;
  if (req?.url) {
    try {
      const u = new URL(req.url, "http://localhost");
      state = u.searchParams.get("state") || undefined;
      const p = u.searchParams.get("page");
      if (p) page = parseInt(p, 10);
    } catch {
      // ignore
    }
  }
  return {
    status: 200,
    body: getMockCskhQueue({ state, page }),
  };
}

export function mockGetCskhDetail(
  req: any,
  noteId: number
): { status: number; body: CskhQueueDetail | { detail: string; code?: string } } {
  const item = MOCK_CSKH_ITEMS.find((i) => i.note_id === noteId);
  if (!item || !item.in_scope) {
    return {
      status: 404,
      body: { detail: "Không tìm thấy phiếu trong phạm vi CSKH." },
    };
  }
  return { status: 200, body: { ...item } };
}

export function mockClaimCskhTask(
  req: any,
  noteId: number
): { status: number; body: ClaimTaskResponse | { code: string; detail: string; claimed_until?: string } } {
  const item = MOCK_CSKH_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }

  const now = Date.now();
  if (item.claimed_by && item.claimed_until) {
    const until = new Date(item.claimed_until).getTime();
    if (until > now && item.claimed_by.id !== 12) {
      return {
        status: 409,
        body: {
          code: "CLAIMED",
          detail: `Đơn đang được ${item.claimed_by.display_name} xử lý tới ${item.claimed_until.slice(11, 16)}.`,
          claimed_until: item.claimed_until,
        },
      };
    }
  }

  const untilIso = new Date(now + 5 * 60 * 1000).toISOString();
  item.claimed_by = { id: 12, display_name: "CSKH Thử" };
  item.claimed_until = untilIso;

  return {
    status: 200,
    body: {
      claimed_by: item.claimed_by,
      claimed_until: untilIso,
    },
  };
}

export function mockRecordCskhCall(
  req: any,
  noteId: number,
  payload: RecordCallPayload
): { status: number; body: RecordCallResponse | { code: string; detail: string } } {
  const item = MOCK_CSKH_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }

  if (item.note_status === "CANCELLED") {
    return { status: 400, body: { code: "BR-GH-07", detail: "Đơn đã huỷ." } };
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
    by: { id: 12, display_name: "CSKH Thử" },
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
        : "Đã thông báo",
    note: payload.note || "",
  };
  item.calls.unshift(newCall);

  // Clear soft lock
  item.claimed_by = null;
  item.claimed_until = null;

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
    item.escalation_label = payload.result === "WANT_CHANGE" ? "Khách muốn đổi món" : "Khách muốn huỷ";
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
  const item = MOCK_CSKH_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
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
  const item = MOCK_CSKH_ITEMS.find((i) => i.note_id === noteId);
  if (!item) {
    return { status: 404, body: { code: "NOT_FOUND", detail: "Không tìm thấy phiếu." } };
  }
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

export function mockSearchCskh(
  req: any,
  q: string
): { status: number; body: CskhSearchResponse | { code: string; detail: string } } {
  const normalized = q.replace(/[\s.\-]/g, "").replace(/^\+84/, "0");
  const isDigits = /^\d+$/.test(normalized);

  if (isDigits && normalized.length < 9) {
    return {
      status: 400,
      body: { code: "INVALID_QUERY", detail: "Nhập đủ số điện thoại hoặc đúng mã đơn." },
    };
  }

  const results: CskhSearchResultItem[] = [];

  for (const item of MOCK_CSKH_ITEMS) {
    let matched = false;
    if (isDigits) {
      if (item.phone === normalized || item.recipient_phone === normalized) {
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
          status_label: item.note_status === "CONFIRMING" ? "Chờ xác nhận" : "Soạn hàng",
          in_scope: true,
          customer_name: item.customer_name,
          phone: item.phone,
        });
      } else {
        const masked = item.phone.length >= 7
          ? item.phone.slice(0, 2) + "xx xxx " + item.phone.slice(-3)
          : item.phone;
        results.push({
          note_id: item.note_id,
          order_code: item.order_code,
          status_label: "Đang giao",
          in_scope: false,
          phone_masked: masked,
        });
      }
    }
  }

  return {
    status: 200,
    body: { results },
  };
}
