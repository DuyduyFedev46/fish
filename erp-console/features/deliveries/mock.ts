import { mockRequireUser } from "@/features/auth/mock";
import { hasLimitedCourierScope } from "@/shared/lib/personalData";
import { DeliveryListResponse, DeliveryNoteDetail, DeliveryNoteItem, LabelData, PrintDeliveryLabelResponse, VoidLabelResponse } from "./types";

/** ISO giờ VN (+07:00) của `daysAgo` ngày trước, lúc `hour` giờ. */
function vnIsoDaysAgo(daysAgo: number, hour: number): string {
  const d = new Date(Date.now() - daysAgo * 86_400_000 + 7 * 3600_000);
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}T${p2(hour)}:00:00+07:00`;
}
/** Số ngày NV giao còn xem được dữ liệu khách của phiếu đã kết thúc (BE `DELIVERY_PII_RECENT_DAYS`, mặc định 7). */
const PII_RECENT_DAYS = 7;

export const MOCK_DELIVERY_NOTES: DeliveryNoteDetail[] = [
  {
    id: 30,
    code: "GH-HD-0030-CONF",
    status: "CONFIRMING",
    status_label: "Chờ xác nhận",
    sales_invoice: 10,
    invoice_code: "HD-0030",
    order: { id: 130, code: "DH-260928-0030" },
    paid_at: "2026-09-28T09:10:00+07:00",
    confirmed_at: null,
    confirm_skipped: false,
    assigned_to: null,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T09:10:05+07:00",
    completed_at: null,
    lines_summary: "Cá thu Côn Đảo 1,500 kg",
    total_kg: "1.500",
    label: { printed: false, valid_print_no: null, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử B",
    address: "Số 2 Đường Thử, Phường 2, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Cá thu Côn Đảo",
        qty_kg: "1.500",
        batch_id: "CA-THU-260928-VT01",
        expiry_date: "2027-09-28",
      },
    ],
  },
  {
    id: 31,
    code: "GH-HD-0031-PREP",
    status: "PREPARING",
    status_label: "Soạn hàng",
    sales_invoice: 7,
    invoice_code: "HD-0031",
    order: { id: 101, code: "DH-260928-0001" },
    paid_at: "2026-09-28T08:05:00+07:00",
    confirmed_at: "2026-09-28T08:20:00+07:00",
    confirm_skipped: false,
    assigned_to: null,
    failed_attempts: 0,
    note: "Giao trước 11h trưa",
    created_at: "2026-09-28T08:05:01+07:00",
    completed_at: null,
    lines_summary: "Tôm sú loại 1 2,000 kg · Mực lá Phan Thiết 1,000 kg",
    total_kg: "3.000",
    label: { printed: false, valid_print_no: null, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử A",
    address: "Số 1 Đường Thử, P. Thử, Lâm Đồng",
    available_actions: ["set_status:READY", "print_label"],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Tôm sú loại 1",
        qty_kg: "2.000",
        batch_id: "TOM-SU-1-260920-AB12C",
        expiry_date: "2027-09-20",
      },
      {
        item_name: "Mực lá Phan Thiết",
        qty_kg: "1.000",
        batch_id: "MUC-LA-260925-CD34E",
        expiry_date: "2027-09-25",
      },
    ],
  },
  {
    id: 32,
    code: "GH-HD-0032-READY",
    status: "READY",
    status_label: "Chờ lấy",
    sales_invoice: 8,
    invoice_code: "HD-0032",
    order: { id: 102, code: "DH-260928-0002" },
    paid_at: "2026-09-28T07:45:00+07:00",
    confirmed_at: "2026-09-28T08:00:00+07:00",
    confirm_skipped: false,
    assigned_to: 14,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T07:45:10+07:00",
    completed_at: null,
    lines_summary: "Cua Cà Mau Y4 2,500 kg",
    total_kg: "2.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử C",
    address: "Số 3 Đường Thử, Q. Ninh Kiều, Cần Thơ",
    available_actions: ["reprint_label"],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Cua Cà Mau Y4",
        qty_kg: "2.500",
        batch_id: "CUA-CM-Y4-260926-EF56",
        expiry_date: "2027-09-26",
      },
    ],
  },
  {
    id: 33,
    code: "GH-HD-0033-DELI",
    status: "DELIVERING",
    status_label: "Đang giao",
    sales_invoice: 9,
    invoice_code: "HD-0033",
    order: { id: 103, code: "DH-260928-0003" },
    paid_at: "2026-09-28T07:30:00+07:00",
    confirmed_at: "2026-09-28T07:40:00+07:00",
    confirm_skipped: false,
    assigned_to: 14,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T07:30:00+07:00",
    completed_at: null,
    lines_summary: "Cá chẽm phi lê 1,000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử D",
    address: "Số 4 Đường Thử, TP. Hồ Chí Minh",
    available_actions: ["set_status:COMPLETED", "set_status:FAILED"],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Cá chẽm phi lê",
        qty_kg: "1.000",
        batch_id: "CA-CHEM-260927-GH78",
        expiry_date: "2027-09-27",
      },
    ],
  },
  {
    id: 34,
    code: "GH-HD-0034-FAIL",
    status: "FAILED",
    status_label: "Giao thất bại",
    sales_invoice: 11,
    invoice_code: "HD-0034",
    order: { id: 104, code: "DH-260928-0004" },
    paid_at: "2026-09-28T07:00:00+07:00",
    confirmed_at: "2026-09-28T07:15:00+07:00",
    confirm_skipped: false,
    assigned_to: 14,
    failed_attempts: 1,
    note: "Không gọi được người nhận",
    created_at: "2026-09-28T07:00:00+07:00",
    completed_at: null,
    lines_summary: "Bạch tuộc tươi 2,000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử E",
    address: "Số 5 Đường Thử, TP. Biên Hoà",
    available_actions: ["set_status:DELIVERING"],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Bạch tuộc tươi",
        qty_kg: "2.000",
        batch_id: "BACH-TUOC-260925-JK90",
        expiry_date: "2027-09-25",
      },
    ],
  },
  {
    id: 35,
    code: "GH-HD-0035-DONE",
    status: "COMPLETED",
    status_label: "Hoàn tất",
    sales_invoice: 12,
    invoice_code: "HD-0035",
    order: { id: 105, code: "DH-260928-0005" },
    paid_at: "2026-09-28T06:30:00+07:00",
    confirmed_at: "2026-09-28T06:45:00+07:00",
    confirm_skipped: false,
    assigned_to: 14,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T06:30:00+07:00",
    completed_at: "2026-09-28T09:30:00+07:00",
    lines_summary: "Tôm sú loại 1 1,000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử F",
    address: "Số 6 Đường Thử, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [
      {
        item_name: "Tôm sú loại 1",
        qty_kg: "1.000",
        batch_id: "TOM-SU-1-260920-AB12C",
        expiry_date: "2027-09-20",
      },
    ],
  },
  // SR-PII-02: hai phiếu hoàn tất của giao1 (id 4). Phiếu 40 kết thúc 10 ngày trước → giao1 thấy tên/địa chỉ/ghi chú = null;
  // phiếu 41 kết thúc hôm qua → giao1 vẫn thấy đủ. Vai khác thấy đủ cả hai.
  {
    id: 40,
    code: "GH-HD-0040-OLD",
    status: "COMPLETED",
    status_label: "Hoàn tất",
    sales_invoice: 20,
    invoice_code: "HD-0040",
    order: { id: 143, code: "DH-OLD-0143" },
    paid_at: vnIsoDaysAgo(10, 8),
    confirmed_at: vnIsoDaysAgo(10, 8),
    confirm_skipped: false,
    assigned_to: 4,
    failed_attempts: 0,
    note: "Gọi trước khi tới",
    created_at: vnIsoDaysAgo(10, 8),
    completed_at: vnIsoDaysAgo(10, 11),
    lines_summary: "Cá thu Côn Đảo 2,000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử H",
    address: "Số 8 Đường Thử, Phường 8, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [{ item_name: "Cá thu Côn Đảo", qty_kg: "2.000", batch_id: "CA-THU-260918-VT02", expiry_date: "2027-09-18" }],
  },
  {
    id: 41,
    code: "GH-HD-0041-NEW",
    status: "COMPLETED",
    status_label: "Hoàn tất",
    sales_invoice: 21,
    invoice_code: "HD-0041",
    order: { id: 144, code: "DH-NEW-0144" },
    paid_at: vnIsoDaysAgo(1, 8),
    confirmed_at: vnIsoDaysAgo(1, 8),
    confirm_skipped: false,
    assigned_to: 4,
    failed_attempts: 0,
    note: "",
    created_at: vnIsoDaysAgo(1, 8),
    completed_at: vnIsoDaysAgo(1, 11),
    lines_summary: "Tôm sú loại 1 1,500 kg",
    total_kg: "1.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử I",
    address: "Số 9 Đường Thử, Phường 9, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [{ item_name: "Tôm sú loại 1", qty_kg: "1.500", batch_id: "TOM-SU-1-260920-AB12C", expiry_date: "2027-09-20" }],
  },
  {
    id: 42,
    code: "GH-HD-0042-OLD",
    status: "COMPLETED",
    status_label: "Hoàn tất",
    sales_invoice: 22,
    invoice_code: "HD-0042",
    order: { id: 142, code: "DH-OLD-0142" },
    paid_at: vnIsoDaysAgo(11, 8),
    confirmed_at: vnIsoDaysAgo(11, 8),
    confirm_skipped: false,
    assigned_to: 12,
    failed_attempts: 0,
    note: "Gọi trước khi tới",
    created_at: vnIsoDaysAgo(11, 8),
    completed_at: vnIsoDaysAgo(11, 11),
    lines_summary: "Cá thu Côn Đảo 2,000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử K",
    address: "Số 11 Đường Thử, Phường 11, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [{ item_name: "Cá thu Côn Đảo", qty_kg: "2.000", batch_id: "CA-THU-260918-VT02", expiry_date: "2027-09-18" }],
  },
  {
    id: 43,
    code: "GH-HD-0043-NEW",
    status: "COMPLETED",
    status_label: "Hoàn tất",
    sales_invoice: 23,
    invoice_code: "HD-0043",
    order: { id: 145, code: "DH-NEW-0145" },
    paid_at: vnIsoDaysAgo(1, 8),
    confirmed_at: vnIsoDaysAgo(1, 8),
    confirm_skipped: false,
    assigned_to: 12,
    failed_attempts: 0,
    note: "",
    created_at: vnIsoDaysAgo(1, 8),
    completed_at: vnIsoDaysAgo(1, 11),
    lines_summary: "Tôm sú loại 1 1,500 kg",
    total_kg: "1.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử L",
    address: "Số 12 Đường Thử, Phường 12, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    recipient_phone: null,
    lines: [{ item_name: "Tôm sú loại 1", qty_kg: "1.500", batch_id: "TOM-SU-1-260920-AB12C", expiry_date: "2027-09-20" }],
  },
];

/**
 * SR-PII-02: bản nhìn của người có phạm vi giao hạn chế (nv_giao không kèm chủ/quản lý/NV kho). Phiếu COMPLETED/CANCELLED kết thúc trước đầu ngày (hôm nay − 7)
 * → customer_name, address, note, recipient_name = null (khoá vẫn có). Vai khác: nguyên bản.
 */
function viewFor<T extends DeliveryNoteItem>(me: ReturnType<typeof mockRequireUser>, note: T): T {
  if (!me || !hasLimitedCourierScope(me)) return note;
  if (note.status !== "COMPLETED" && note.status !== "CANCELLED") return note;
  const cutoffDay = vnIsoDaysAgo(PII_RECENT_DAYS, 0).slice(0, 10);
  const endedDay = (note.completed_at || note.created_at).slice(0, 10);
  if (endedDay >= cutoffDay) return note;
  const hidden: T = { ...note, customer_name: null, address: null, note: null };
  if ("recipient_name" in hidden) (hidden as unknown as DeliveryNoteDetail).recipient_name = null;
  return hidden;
}

/** Người có phạm vi giao hạn chế chỉ thấy phiếu gán cho mình (BR-PQ-12). */
function inCourierScope(me: ReturnType<typeof mockRequireUser>, note: DeliveryNoteItem): boolean {
  return !me || !hasLimitedCourierScope(me) || note.assigned_to === me.id;
}

export function getMockDeliveryNotes(params?: {
  status?: string;
  completed_from?: string;
  page?: number;
}): DeliveryListResponse {
  let filtered = [...MOCK_DELIVERY_NOTES];
  if (params?.status) {
    const statuses = params.status.split(",").map((s) => s.trim());
    filtered = filtered.filter((n) => statuses.includes(n.status));
  }
  return {
    count: filtered.length,
    next: null,
    previous: null,
    results: filtered,
  };
}

export function getMockDeliveryNoteDetail(id: number): DeliveryNoteDetail {
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) {
    throw new Error("Không tìm thấy phiếu giao hàng");
  }
  return item;
}

export function mockPackDeliveryNote(
  id: number,
  fromStatus?: string
): { note: DeliveryNoteDetail; already: boolean } {
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) {
    throw new Error("Không tìm thấy phiếu giao hàng");
  }
  if (item.status === "READY" && fromStatus === "PREPARING") {
    return { note: item, already: true };
  }
  if (item.status === "CONFIRMING") {
    throw new Error("BR-GH-11: Chưa xác nhận với khách, chưa soạn được.");
  }
  if (item.status === "CANCELLED") {
    throw new Error("BR-GH-07: Đơn đã huỷ, không soạn.");
  }
  if (item.status !== "PREPARING" && item.status !== "READY") {
    throw new Error(`STALE_STATE: Phiếu đang ở ${item.status_label}, tải lại để xem.`);
  }

  item.status = "READY";
  item.status_label = "Chờ lấy";
  item.available_actions = ["reprint_label"];
  return { note: item, already: false };
}

export function mockListDeliveryNotes(req: any): { status: number; body: DeliveryListResponse } {
  let status: string | undefined;
  let completed_from: string | undefined;
  if (req?.url) {
    try {
      const u = new URL(req.url, "http://localhost");
      status = u.searchParams.get("status") || undefined;
      completed_from = u.searchParams.get("completed_from") || undefined;
    } catch {
      // ignore
    }
  }
  const me = mockRequireUser(req);
  const base = getMockDeliveryNotes({ status, completed_from });
  const results = base.results.filter((n) => inCourierScope(me, n)).map((n) => viewFor(me, n));
  return { status: 200, body: { ...base, count: results.length, results } };
}

export function mockGetDeliveryNoteDetail(req: any): { status: number; body: DeliveryNoteDetail | { detail: string } } {
  const match = req?.url ? String(req.url).match(/\/api\/delivery\/notes\/(\d+)\//) : null;
  const id = match ? parseInt(match[1], 10) : 31;
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  const me = mockRequireUser(req);
  if (!item || !inCourierScope(me, item)) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  }
  return { status: 200, body: viewFor(me, item) };
}

export function mockPostDeliveryNoteStatus(req: any): { status: number; body: any } {
  const match = req?.url ? String(req.url).match(/\/api\/delivery\/notes\/(\d+)\/status\//) : null;
  const id = match ? parseInt(match[1], 10) : 31;
  let body = req?.body as { to_status?: string; from_status?: string } | undefined;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      // ignore
    }
  }
  try {
    const res = mockPackDeliveryNote(id, body?.from_status);
    return { status: 200, body: { ...res.note, already: res.already } };
  } catch (err: any) {
    return { status: 400, body: { detail: err.message, code: err.message.split(":")[0] } };
  }
}

export function mockGetDeliveryLabel(
  req: any,
  id: number,
  printNo?: number
): { status: number; body: LabelData | { detail: string; code?: string } } {
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  }
  if (item.status === "CONFIRMING") {
    return {
      status: 400,
      body: { code: "BR-GH-09", detail: "Chưa xác nhận với khách, chưa in tem." },
    };
  }
  if (item.status === "CANCELLED") {
    return {
      status: 400,
      body: { code: "BR-GH-07", detail: "Đơn đã huỷ, không in tem." },
    };
  }

  const pNo = printNo || item.label.valid_print_no || 1;
  const isReprint = pNo > 1 || (item.label.printed && pNo === item.label.valid_print_no);

  const data: LabelData = {
    note_code: item.code,
    order_code: item.order?.code || "DH-260928-0001",
    print_no: pNo,
    next_print_no: (item.label.valid_print_no || 1) + 1,
    is_reprint: isReprint,
    reprint_reason: isReprint ? "REPRINT" : null,
    barcode_value: `${item.code}.${pNo}`,
    recipient_name: item.recipient_name || item.customer_name || "",
    recipient_phone_masked: "09xx xxx 123",
    address: item.address || "",
    packages: "1/1",
    total_kg: item.total_kg,
    earliest_expiry: item.lines[0]?.expiry_date || "2027-09-20",
    paid_text: "ĐÃ THANH TOÁN – không thu thêm",
  };
  return { status: 200, body: data };
}

export function mockPostDeliveryLabelPrint(
  req: any,
  id: number
): { status: number; body: PrintDeliveryLabelResponse | { detail: string; code?: string } } {
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  }
  if (item.status === "CONFIRMING") {
    return {
      status: 400,
      body: { code: "BR-GH-09", detail: "Chưa xác nhận với khách, chưa in tem." },
    };
  }
  if (item.status === "CANCELLED") {
    return {
      status: 400,
      body: { code: "BR-GH-07", detail: "Đơn đã huỷ, không in tem." },
    };
  }

  const isReprint = item.label.printed;
  const oldPrintNo = item.label.valid_print_no;
  const printNo = (item.label.valid_print_no || 0) + 1;
  if (isReprint && oldPrintNo && !item.label.to_void.includes(oldPrintNo)) {
    item.label.to_void.push(oldPrintNo);
    item.label.needs_void = item.label.to_void.length;
  }
  item.label.printed = true;
  item.label.valid_print_no = printNo;
  if (!item.available_actions.includes("reprint_label")) {
    item.available_actions.push("reprint_label");
  }

  return {
    status: isReprint ? 200 : 201,
    body: {
      print_no: printNo,
      printed_at: new Date().toISOString(),
      is_reprint: isReprint,
      duplicate: false,
    },
  };
}

export function mockPostDeliveryLabelVoid(
  req: any,
  id: number
): { status: number; body: VoidLabelResponse | { detail: string; code?: string } } {
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  }
  const body = req?.body || {};
  const printNo = Number(body.print_no);
  if (!printNo) {
    return { status: 400, body: { detail: "Thiếu print_no" } };
  }
  if (item.status !== "CANCELLED" && item.label.valid_print_no === printNo && !item.label.to_void.includes(printNo)) {
    return {
      status: 400,
      body: { code: "BR-GH-16", detail: `Tem lần ${printNo} đang có hiệu lực, không huỷ được.` },
    };
  }
  if (!item.label.to_void.includes(printNo)) {
    return {
      status: 200,
      body: {
        print_no: printNo,
        voided_at: new Date().toISOString(),
        already: true,
      },
    };
  }
  item.label.to_void = item.label.to_void.filter((p) => p !== printNo);
  item.label.needs_void = item.label.to_void.length;
  return {
    status: 200,
    body: {
      print_no: printNo,
      voided_at: new Date().toISOString(),
      already: false,
    },
  };
}


