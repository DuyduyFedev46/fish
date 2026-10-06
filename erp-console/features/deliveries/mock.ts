import { mockRequireUser } from "@/features/auth/mock";
import type { MockRequest } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { hasLimitedCourierScope } from "@/shared/lib/personalData";
import { isDeliveryFinished } from "@/shared/lib/orderCompletion";
import { hasLongDigitRun } from "./deliveryUi";
import type {
  Deliverer,
  DeliveryFailureReason,
  DeliveryListResponse,
  DeliveryNoteDetail,
  DeliveryNoteItem,
  LabelData,
  PrintDeliveryLabelResponse,
  TagLookup,
  VoidLabelResponse,
} from "./types";

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
    lines_summary: "Cá thu Côn Đảo 1.500 kg",
    total_kg: "1.500",
    label: { printed: false, valid_print_no: null, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử B",
    address: "Số 2 Đường Thử, Phường 2, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
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
    lines_summary: "Tôm sú loại 1 2.500 kg · Mực lá Phan Thiết 1.000 kg",
    total_kg: "3.500",
    label: { printed: false, valid_print_no: null, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử A",
    address: "Số 1 Đường Thử, P. Thử, Lâm Đồng",
    available_actions: ["set_status:READY", "print_label"],
    recipient_name: null,
    lines: [
      {
        item_name: "Tôm sú loại 1",
        qty_kg: "2.500",
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
    lines_summary: "Cua Cà Mau Y4 2.500 kg",
    total_kg: "2.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử C",
    address: "Số 3 Đường Thử, Q. Ninh Kiều, Cần Thơ",
    available_actions: ["reprint_label"],
    recipient_name: null,
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
    lines_summary: "Cá chẽm phi lê 1.000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử D",
    address: "Số 4 Đường Thử, TP. Hồ Chí Minh",
    available_actions: ["set_status:COMPLETED", "set_status:FAILED"],
    recipient_name: null,
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
    lines_summary: "Bạch tuộc tươi 2.000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử E",
    address: "Số 5 Đường Thử, TP. Biên Hoà",
    available_actions: ["set_status:DELIVERING"],
    recipient_name: null,
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
    lines_summary: "Tôm sú loại 1 1.000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử F",
    address: "Số 6 Đường Thử, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
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
    lines_summary: "Cá thu Côn Đảo 2.000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử H",
    address: "Số 8 Đường Thử, Phường 8, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
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
    lines_summary: "Tôm sú loại 1 1.500 kg",
    total_kg: "1.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử I",
    address: "Số 9 Đường Thử, Phường 9, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
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
    lines_summary: "Cá thu Côn Đảo 2.000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử K",
    address: "Số 11 Đường Thử, Phường 11, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
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
    lines_summary: "Tôm sú loại 1 1.500 kg",
    total_kg: "1.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử L",
    address: "Số 12 Đường Thử, Phường 12, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    lines: [{ item_name: "Tôm sú loại 1", qty_kg: "1.500", batch_id: "TOM-SU-1-260920-AB12C", expiry_date: "2027-09-20" }],
  },
  // ---- Lô 4 (ED-17, ED-19): việc của giao1 (id 4) và giao2 (id 7); phiếu 45 để thử xung đột khi giao người. ----
  {
    id: 36,
    code: "GH-HD-0036-DELI",
    status: "DELIVERING",
    status_label: "Đang giao",
    sales_invoice: 13,
    invoice_code: "HD-0036",
    order: { id: 106, code: "DH-260928-0006" },
    paid_at: "2026-09-28T07:10:00+07:00",
    confirmed_at: "2026-09-28T07:20:00+07:00",
    confirm_skipped: false,
    assigned_to: 4,
    failed_attempts: 0,
    note: "Gọi trước khi tới",
    created_at: "2026-09-28T07:10:00+07:00",
    completed_at: null,
    lines_summary: "Mực lá Phan Thiết 2.000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử M",
    address: "Số 13 Đường Thử, Phường 3, TP. Vũng Tàu",
    available_actions: ["set_status:COMPLETED", "set_status:FAILED"],
    recipient_name: null,
    lines: [{ item_name: "Mực lá Phan Thiết", qty_kg: "2.000", batch_id: "MUC-LA-260925-CD34E", expiry_date: "2027-09-25" }],
  },
  {
    id: 37,
    code: "GH-HD-0037-READY",
    status: "READY",
    status_label: "Chờ lấy hàng",
    sales_invoice: 14,
    invoice_code: "HD-0037",
    order: { id: 107, code: "DH-260928-0007" },
    paid_at: "2026-09-28T07:50:00+07:00",
    confirmed_at: "2026-09-28T08:00:00+07:00",
    confirm_skipped: false,
    assigned_to: 4,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T07:50:00+07:00",
    completed_at: null,
    lines_summary: "Cua Cà Mau Y4 1.500 kg",
    total_kg: "1.500",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử N",
    address: "Số 14 Đường Thử, Phường 4, TP. Vũng Tàu",
    available_actions: ["reprint_label"],
    recipient_name: null,
    lines: [{ item_name: "Cua Cà Mau Y4", qty_kg: "1.500", batch_id: "CUA-CM-Y4-260926-EF56", expiry_date: "2027-09-26" }],
  },
  {
    id: 38,
    code: "GH-HD-0038-FAIL",
    status: "FAILED",
    status_label: "Giao thất bại",
    sales_invoice: 15,
    invoice_code: "HD-0038",
    order: { id: 108, code: "DH-260928-0008" },
    paid_at: "2026-09-28T06:50:00+07:00",
    confirmed_at: "2026-09-28T07:00:00+07:00",
    confirm_skipped: false,
    assigned_to: 4,
    failed_attempts: 1,
    failure_reason: "NOT_MET",
    failure_reason_label: "Không gặp khách",
    failure_note: "Khách hẹn lại chiều",
    note: "",
    created_at: "2026-09-28T06:50:00+07:00",
    completed_at: null,
    lines_summary: "Tôm sú loại 1 1.000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử O",
    address: "Số 15 Đường Thử, Phường 5, TP. Vũng Tàu",
    available_actions: ["set_status:DELIVERING"],
    recipient_name: null,
    lines: [{ item_name: "Tôm sú loại 1", qty_kg: "1.000", batch_id: "TOM-SU-1-260920-AB12C", expiry_date: "2027-09-20" }],
  },
  {
    id: 39,
    code: "GH-HD-0039-DELI",
    status: "DELIVERING",
    status_label: "Đang giao",
    sales_invoice: 16,
    invoice_code: "HD-0039",
    order: { id: 109, code: "DH-260928-0009" },
    paid_at: "2026-09-28T07:20:00+07:00",
    confirmed_at: "2026-09-28T07:30:00+07:00",
    confirm_skipped: false,
    assigned_to: 7,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T07:20:00+07:00",
    completed_at: null,
    lines_summary: "Cá chẽm phi lê 1.200 kg",
    total_kg: "1.200",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử P",
    address: "Số 16 Đường Thử, Phường 6, TP. Vũng Tàu",
    available_actions: ["set_status:COMPLETED", "set_status:FAILED"],
    recipient_name: null,
    lines: [{ item_name: "Cá chẽm phi lê", qty_kg: "1.200", batch_id: "CA-CHEM-260927-GH78", expiry_date: "2027-09-27" }],
  },
  // Phiếu thử xung đột: lần giao người đầu tiên luôn gặp 409 (như có người khác vừa giao trước, xem mockPostDeliveryAssign).
  {
    id: 45,
    code: "GH-HD-0045-RACE",
    status: "READY",
    status_label: "Chờ lấy hàng",
    sales_invoice: 24,
    invoice_code: "HD-0045",
    order: { id: 146, code: "DH-260928-0046" },
    paid_at: "2026-09-28T08:30:00+07:00",
    confirmed_at: "2026-09-28T08:40:00+07:00",
    confirm_skipped: false,
    assigned_to: null,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T08:30:00+07:00",
    completed_at: null,
    lines_summary: "Cá thu Côn Đảo 1.000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: 1, needs_void: 0, to_void: [] },
    customer_name: "Khách Thử Q",
    address: "Số 17 Đường Thử, Phường 7, TP. Vũng Tàu",
    available_actions: ["reprint_label"],
    recipient_name: null,
    lines: [{ item_name: "Cá thu Côn Đảo", qty_kg: "1.000", batch_id: "CA-THU-260918-VT02", expiry_date: "2027-09-18" }],
  },
  // CS-17: phiếu đã in lại tem lần 2 (tem lần 1 cũ, chờ xé) và phiếu đã huỷ (tem lần 1 chờ xé). Dữ liệu khách là chữ bịa.
  {
    id: 46,
    code: "GH-HD-0046-REPR",
    status: "PREPARING",
    status_label: "Soạn hàng",
    sales_invoice: 25,
    invoice_code: "HD-0046",
    order: { id: 147, code: "DH-260928-0047" },
    paid_at: "2026-09-28T08:40:00+07:00",
    confirmed_at: "2026-09-28T08:50:00+07:00",
    confirm_skipped: false,
    assigned_to: null,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T08:40:00+07:00",
    completed_at: null,
    lines_summary: "Cá thu Côn Đảo 2.000 kg",
    total_kg: "2.000",
    label: { printed: true, valid_print_no: 2, needs_void: 1, to_void: [1] },
    customer_name: "Khách Thử R",
    address: "Số 18 Đường Thử, Phường 8, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    lines: [{ item_name: "Cá thu Côn Đảo", qty_kg: "2.000", batch_id: "CA-THU-260918-VT02", expiry_date: "2027-09-18" }],
  },
  {
    id: 47,
    code: "GH-HD-0047-CANC",
    status: "CANCELLED",
    status_label: "Đã huỷ",
    sales_invoice: 26,
    invoice_code: "HD-0047",
    order: { id: 148, code: "DH-260928-0048" },
    paid_at: "2026-09-28T08:45:00+07:00",
    confirmed_at: "2026-09-28T08:55:00+07:00",
    confirm_skipped: false,
    assigned_to: null,
    failed_attempts: 0,
    note: "",
    created_at: "2026-09-28T08:45:00+07:00",
    completed_at: null,
    lines_summary: "Cá thu Côn Đảo 1.000 kg",
    total_kg: "1.000",
    label: { printed: true, valid_print_no: null, needs_void: 1, to_void: [1] },
    customer_name: "Khách Thử S",
    address: "Số 19 Đường Thử, Phường 9, TP. Vũng Tàu",
    available_actions: [],
    recipient_name: null,
    lines: [{ item_name: "Cá thu Côn Đảo", qty_kg: "1.000", batch_id: "CA-THU-260918-VT02", expiry_date: "2027-09-18" }],
  },
];

type MockMe = ReturnType<typeof mockRequireUser>;

/** Đường dẫn (kèm query) của request mock. Test cũ truyền `url`, request thật của `apiFetch` có `path`. */
function pathOf(req: unknown): string {
  const r = req as { path?: string; url?: string } | null | undefined;
  return String(r?.path ?? r?.url ?? "");
}
function bodyOf(req: unknown): Record<string, unknown> {
  const raw = (req as { body?: unknown } | null | undefined)?.body;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
}
function paramsOf(path: string): URLSearchParams {
  const i = path.indexOf("?");
  return new URLSearchParams(i >= 0 ? path.slice(i + 1) : "");
}
function noteIdOf(path: string, tail: string): number | null {
  const m = path.match(new RegExp(`/api/delivery/notes/(\\d+)/${tail}`));
  return m ? parseInt(m[1], 10) : null;
}
function hasPerm(me: MockMe, perm: string): boolean {
  return !!me && me.permissions.includes(perm);
}

/** Tên hiển thị của người giao (BE: `staff_display_name`). 14 là người giao cũ không có tài khoản mock. */
const COURIER_NAMES: Record<number, string> = { 4: "Anh Phúc", 7: "Anh Lâm", 14: "Anh Khoa" };
/** Người giao có thể chọn ở F2o (nhóm delivery_staff, đang làm). */
const MOCK_DELIVERERS: Array<{ id: number; display_name: string }> = [
  { id: 4, display_name: "Anh Phúc" },
  { id: 7, display_name: "Anh Lâm" },
];
/** SĐT BỊA để thử giao diện (không phải số thật). */
function fakePhone(id: number): string {
  return `0900 000 ${String(id).padStart(3, "0")}`;
}

const FAILURE_REASONS: Record<DeliveryFailureReason, string> = {
  NOT_MET: "Không gặp khách",
  REFUSED: "Khách từ chối nhận",
  WRONG_ADDRESS: "Sai địa chỉ",
  DAMAGED: "Hàng hư khi giao",
  OTHER: "Khác",
};

/** `available_actions` như serializer BE (theo trạng thái + quyền của người xem). */
function actionsFor(me: MockMe, note: DeliveryNoteItem): string[] {
  const out: string[] = [];
  const canPrint = hasPerm(me, PERM.printLabel);
  const canChange = hasPerm(me, "delivery.change_deliverynote");
  switch (note.status) {
    case "CONFIRMING":
      break;
    case "PREPARING":
      if (hasPerm(me, PERM.packDeliveryNote)) out.push("set_status:READY");
      if (canPrint) out.push(note.label.printed ? "reprint_label" : "print_label");
      break;
    case "READY":
      if (canChange) out.push("set_status:DELIVERING");
      if (canPrint) out.push("reprint_label");
      break;
    case "DELIVERING":
      if (canChange) out.push("set_status:COMPLETED", "set_status:FAILED");
      break;
    case "FAILED":
      if (canChange) out.push("set_status:DELIVERING");
      break;
    default:
      break;
  }
  if ((note.status === "CONFIRMING" || note.status === "PREPARING" || note.status === "READY") && hasPerm(me, PERM.assignDelivery)) out.push("assign");
  if (note.label.needs_void > 0 && canPrint) out.push("void_label");
  return out;
}

/**
 * Lô 9: BE thêm `batch_pk` và `returned_qty` vào mỗi dòng của chi tiết phiếu giao. Hai số này thuộc module Hàng hoàn, nên mock của module đó
 * đăng ký hàm tính ở đây (không import ngược để khỏi vòng phụ thuộc). Chưa đăng ký thì dòng không có hai khoá (giống BE cũ).
 */
type LineExtras = Record<string, unknown>;
let lineExtras: ((noteId: number, line: { batch_id: string }) => LineExtras) | null = null;
export function registerDeliveryLineExtras(fn: (noteId: number, line: { batch_id: string }) => LineExtras): void {
  lineExtras = fn;
}

/**
 * Bản nhìn của một phiếu cho người gọi: (1) SR-PII-02 — người có phạm vi giao hạn chế (delivery_staff không kèm chủ/quản lý/NV kho)
 * thấy phiếu COMPLETED/CANCELLED kết thúc trước đầu ngày (hôm nay − 7) với customer_name, address, note, recipient_name,
 * phone, failure_note = null (khoá vẫn có); (2) tên người giao, SĐT và hành động theo quyền như BE (R4).
 */
function plusHours(iso: string, hours: number): string {
  return new Date(Date.parse(iso) + hours * 3_600_000).toISOString();
}

function viewFor<T extends DeliveryNoteItem>(me: MockMe, note: T, asDetail = false): T {
  const base: T = {
    ...note,
    assigned_to_name: note.assigned_to ? COURIER_NAMES[note.assigned_to] ?? null : null,
    failure_reason: note.failure_reason ?? "",
    failure_reason_label: note.failure_reason ? FAILURE_REASONS[note.failure_reason as DeliveryFailureReason] ?? "" : "",
    available_actions: me ? actionsFor(me, note) : note.available_actions,
  };
  // Lô bổ sung A #18: mốc giờ cho phiếu đã đi giao / thất bại. Seed không ghi sẵn thì suy ra từ giờ tạo phiếu.
  const started = note.status === "DELIVERING" || note.status === "COMPLETED" || note.status === "FAILED";
  base.delivery_started_at = note.delivery_started_at ?? (started ? plusHours(note.created_at, 2) : null);
  base.failed_at = note.failed_at ?? (note.status === "FAILED" ? plusHours(note.created_at, 4) : null);
  if (asDetail && "lines" in note) {
    const d = base as unknown as DeliveryNoteDetail;
    d.phone = fakePhone(note.id);
    if (lineExtras) d.lines = d.lines.map((l) => ({ ...l, ...lineExtras!(note.id, l) }));
    d.failure_note = (note as unknown as DeliveryNoteDetail).failure_note ?? "";
  }
  if (!me || !hasLimitedCourierScope(me)) return base;
  if (note.status !== "COMPLETED" && note.status !== "CANCELLED") return base;
  const cutoffDay = vnIsoDaysAgo(PII_RECENT_DAYS, 0).slice(0, 10);
  const endedDay = (note.completed_at || note.created_at).slice(0, 10);
  if (endedDay >= cutoffDay) return base;
  const hidden: T = { ...base, customer_name: null, address: null, note: null };
  if (asDetail && "recipient_name" in hidden) {
    const d = hidden as unknown as DeliveryNoteDetail;
    d.recipient_name = null;
    d.phone = null;
    d.failure_note = null;
  }
  return hidden;
}

/** Người có phạm vi giao hạn chế chỉ thấy phiếu gán cho mình (BR-PQ-12). */
function inCourierScope(me: MockMe, note: DeliveryNoteItem): boolean {
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

export function mockListDeliveryNotes(req: MockRequest | { url?: string; token?: string | null }): { status: number; body: DeliveryListResponse | { detail: string } } {
  const me = mockRequireUser(req as MockRequest);
  const q = paramsOf(pathOf(req));
  const status = q.get("status") || undefined;
  const completedFrom = q.get("completed_from") || undefined;
  const assignedTo = q.get("assigned_to");
  if (assignedTo && assignedTo !== "me" && me && hasLimitedCourierScope(me) && Number(assignedTo) !== me.id) {
    return { status: 403, body: { detail: "Bạn chỉ xem được phiếu giao của mình." } };
  }
  const base = getMockDeliveryNotes({ status, completed_from: completedFrom });
  let rows = base.results.filter((n) => inCourierScope(me, n));
  if (assignedTo === "me") rows = rows.filter((n) => me && n.assigned_to === me.id);
  else if (assignedTo) rows = rows.filter((n) => n.assigned_to === Number(assignedTo));
  if (completedFrom) rows = rows.filter((n) => n.status !== "COMPLETED" || (n.completed_at ?? "").slice(0, 10) >= completedFrom);
  const results = rows.map((n) => {
    const v = viewFor(me, n);
    // Lô bổ sung A #17: chỉ danh sách `assigned_to=me` có `phone`; chỉ phiếu Đang giao/Giao thất bại, còn trong cửa sổ 7 ngày (như chi tiết).
    if (assignedTo === "me") v.phone = n.status === "DELIVERING" || n.status === "FAILED" ? fakePhone(n.id) : null;
    return v;
  });
  return { status: 200, body: { ...base, count: results.length, results } };
}

export function mockGetDeliveryNoteDetail(req: MockRequest | { url?: string; token?: string | null }): { status: number; body: DeliveryNoteDetail | { detail: string } } {
  const id = noteIdOf(pathOf(req), "") ?? 31;
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  const me = mockRequireUser(req as MockRequest);
  if (!item || !inCourierScope(me, item)) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  }
  return { status: 200, body: viewFor(me, item, true) };
}

// BE `has_long_digit_run`: dãy 9 chữ số trở lên bị chặn kể cả khi có dấu cách, dấu chấm, gạch ngang (dùng chung với FE).

type MockFailure = { status: number; body: { detail: string; code: string } };
function failure(status: number, code: string, detail: string): MockFailure {
  return { status, body: { detail, code } };
}

/** B5: kiểm lý do và ghi chú giao thất bại như `services.validate_failure_input`. */
function validateFailure(reason: unknown, rawNote: unknown): MockFailure | null {
  if (!reason || typeof reason !== "string" || !(reason in FAILURE_REASONS)) {
    return failure(400, "DELIVERY_FAILURE_REASON_REQUIRED", "Chọn lý do giao thất bại.");
  }
  const note = typeof rawNote === "string" ? rawNote.trim() : "";
  if (note.length > 200) return failure(400, "DELIVERY_FAILURE_NOTE_INVALID", "Ghi chú tối đa 200 ký tự.");
  if (reason === "OTHER" && !note) return failure(400, "DELIVERY_FAILURE_NOTE_REQUIRED", "Chọn lý do Khác thì phải ghi chú.");
  if (note && hasLongDigitRun(note)) {
    return failure(400, "DELIVERY_FAILURE_NOTE_PII", "Ghi chú không được chứa số điện thoại hay dãy số dài.");
  }
  return null;
}

const STATUS_LABELS: Record<string, string> = {
  READY: "Chờ lấy hàng",
  DELIVERING: "Đang giao",
  COMPLETED: "Hoàn tất",
  FAILED: "Giao thất bại",
};
const NEXT_FROM: Record<string, string[]> = {
  READY: ["PREPARING"],
  DELIVERING: ["READY", "FAILED"],
  COMPLETED: ["DELIVERING"],
  FAILED: ["DELIVERING"],
};

/**
 * W37 S1: trạng thái đơn sau lần chuyển này, theo luật dùng chung BR-BH-18 (`isDeliveryFinished`). Mọi phiếu cùng đơn được xét.
 * Kho phiếu mock này không nối với kho đơn mock (features/orders/mock): hai kho dùng mã đơn khác nhau, và import chéo làm bản build
 * thật giữ lại seed mock (check-no-mock đỏ).
 */
function orderStatusAfter(item: DeliveryNoteDetail, statuses: string[]): string | null {
  if (!item.order?.code) return null;
  return item.status === "CANCELLED" ? "CANCELLED" : isDeliveryFinished(statuses) ? "COMPLETED" : "PROCESSING";
}

/** `POST /api/delivery/notes/{id}/status/` — đóng gói, nhận hàng đi giao, hoàn tất, báo thất bại (B5). */
export function mockPostDeliveryNoteStatus(req: MockRequest | { url?: string; body?: unknown; token?: string | null }): { status: number; body: unknown } {
  const id = noteIdOf(pathOf(req), "status/") ?? 31;
  const body = bodyOf(req) as { to_status?: string; from_status?: string; failure_reason?: string; failure_note?: string };
  const me = mockRequireUser(req as MockRequest);
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item || !inCourierScope(me, item)) return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  const to = body.to_status;
  // Trạng thái mọi phiếu cùng đơn (đặt trong hàm này, không tách hàm riêng: tách ra thì bản build thật giữ lại seed mock).
  const siblingStatuses = (n: DeliveryNoteDetail) => MOCK_DELIVERY_NOTES.filter((x) => x.order?.code === n.order?.code).map((x) => x.status as string);

  // BR-GH-24: phiếu hoặc đơn đã huỷ → không nhận hàng đi giao, không giao xong, không báo thất bại. 400 kèm `code` (02b §2.3).
  if ((to === "DELIVERING" || to === "COMPLETED" || to === "FAILED") && item.status === "CANCELLED") {
    return { status: 400, body: { detail: "Đơn đã huỷ — mang hàng về kho.", code: "BR-GH-24", current_status: item.status } };
  }

  if (to === "FAILED") {
    if (item.status !== "DELIVERING") {
      return failure(409, "STALE_STATE", `Phiếu đang ở ${item.status_label}, tải lại để xem.`);
    }
    const bad = validateFailure(body.failure_reason, body.failure_note);
    if (bad) return bad;
    item.status = "FAILED";
    item.status_label = STATUS_LABELS.FAILED;
    item.failed_attempts += 1;
    item.failure_reason = body.failure_reason;
    item.failure_note = (body.failure_note ?? "").trim();
    item.failed_at = new Date().toISOString();
    return { status: 200, body: { ...viewFor(me, item), already: false, needs_decision: item.failed_attempts >= 2, order_status: orderStatusAfter(item, siblingStatuses(item)) } };
  }

  if (to === "READY" && (item.status === "PREPARING" || item.status === "READY" || item.status === "CONFIRMING" || item.status === "CANCELLED")) {
    try {
      const res = mockPackDeliveryNote(id, body.from_status);
      return { status: 200, body: { ...viewFor(me, res.note), already: res.already, order_status: orderStatusAfter(res.note, siblingStatuses(res.note)) } };
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Lỗi";
      return { status: 400, body: { detail: msg, code: msg.split(":")[0] } };
    }
  }

  if (to && STATUS_LABELS[to]) {
    if (item.status === to) return { status: 200, body: { ...viewFor(me, item), already: true, order_status: orderStatusAfter(item, siblingStatuses(item)) } };
    if (!(NEXT_FROM[to] ?? []).includes(item.status)) {
      return failure(409, "STALE_STATE", `Phiếu đang ở ${item.status_label}, tải lại để xem.`);
    }
    item.status = to as DeliveryNoteItem["status"];
    item.status_label = STATUS_LABELS[to];
    if (to === "COMPLETED") item.completed_at = new Date().toISOString();
    if (to === "DELIVERING") item.delivery_started_at = new Date().toISOString();
    return { status: 200, body: { ...viewFor(me, item), already: false, order_status: orderStatusAfter(item, siblingStatuses(item)) } };
  }
  return failure(400, "DELIVERY_STATUS_INVALID", "Trạng thái không hợp lệ.");
}

/** `GET /api/delivery/deliverers/` (B6): mảng thường, kèm số phiếu đang giao / chờ lấy; cần quyền giao người. */
export function mockGetDeliverers(req: MockRequest): { status: number; body: Deliverer[] | { detail: string } } {
  const me = mockRequireUser(req);
  if (!me || !hasPerm(me, PERM.assignDelivery)) return { status: 403, body: { detail: "Bạn không có quyền giao phiếu." } };
  return {
    status: 200,
    body: MOCK_DELIVERERS.map((u) => ({
      id: u.id,
      display_name: u.display_name,
      delivering_count: MOCK_DELIVERY_NOTES.filter((n) => n.assigned_to === u.id && n.status === "DELIVERING").length,
      ready_count: MOCK_DELIVERY_NOTES.filter((n) => n.assigned_to === u.id && n.status === "READY").length,
    })),
  };
}

/** Phiếu thử xung đột đã "bị người khác giao trước" chưa (chỉ lần đầu). */
let raceTriggered = false;

/**
 * `POST /api/delivery/notes/{id}/assign/` (B6). Như BE: chỉ CONFIRMING/PREPARING/READY; người được chọn phải thuộc nhóm giao;
 * cùng người → 200 `already`; `expected_assigned_to` lệch người giao hiện tại → 409 `STALE_STATE` (thân chỉ có `assigned_to`).
 * Phiếu 45: lần giao đầu tiên mô phỏng "có người khác vừa giao cho Anh Lâm" → 409, sau khi tải lại thì giao bình thường.
 */
export function mockPostDeliveryAssign(req: MockRequest): { status: number; body: unknown } {
  const me = mockRequireUser(req);
  if (!me || !hasPerm(me, PERM.assignDelivery)) return { status: 403, body: { detail: "Bạn không có quyền giao phiếu." } };
  const id = noteIdOf(pathOf(req), "assign/");
  const item = MOCK_DELIVERY_NOTES.find((n) => n.id === id);
  if (!item) return { status: 404, body: { detail: "Không tìm thấy phiếu giao hàng" } };
  const body = bodyOf(req);
  const to = Number(body.assigned_to);
  if (item.status !== "CONFIRMING" && item.status !== "PREPARING" && item.status !== "READY") {
    return failure(400, "DELIVERY_ASSIGN_STATE", `Phiếu đang ở ${item.status_label}, không đổi người giao được.`);
  }
  if (!MOCK_DELIVERERS.some((u) => u.id === to)) {
    return failure(400, "DELIVERY_ASSIGNEE_INVALID", "Người này không thuộc nhóm Nhân viên giao hoặc đã nghỉ.");
  }
  if (item.id === 45 && !raceTriggered && item.assigned_to === null) {
    raceTriggered = true;
    item.assigned_to = 7;
    return { status: 409, body: { detail: "Phiếu vừa được giao cho người khác, tải lại để xem.", code: "STALE_STATE", assigned_to: 7 } };
  }
  if (item.assigned_to === to) return { status: 200, body: { ...viewFor(me, item), already: true } };
  if ("expected_assigned_to" in body && (body.expected_assigned_to ?? null) !== item.assigned_to) {
    return { status: 409, body: { detail: "Phiếu vừa được giao cho người khác, tải lại để xem.", code: "STALE_STATE", assigned_to: item.assigned_to } };
  }
  item.assigned_to = to;
  return { status: 200, body: { ...viewFor(me, item), already: false } };
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



/**
 * CS-17 `GET /api/delivery/notes/lookup/?code=`. Như BE: 400 sai định dạng (lỗi không lặp lại giá trị đã gửi), 403 khi thiếu
 * `delivery.print_label` hoặc `view_deliverynote`, 404 khi không có phiếu hoặc phiếu chưa từng in lần đó.
 * Phản hồi chỉ có mã phiếu, trạng thái, số lần in; không tên, SĐT, địa chỉ, mã đơn, giá.
 */
export function mockLookupDeliveryTag(req: MockRequest): { status: number; body: TagLookup | { detail: string; code: string } } {
  const me = mockRequireUser(req);
  if (!me || !hasPerm(me, PERM.printLabel) || !hasPerm(me, PERM.viewDeliveryNote)) {
    return { status: 403, body: { detail: "Bạn không có quyền thực hiện thao tác này.", code: "PERMISSION_DENIED" } };
  }
  const code = paramsOf(pathOf(req)).get("code") ?? "";
  const m = /^(GH-[A-Z0-9-]{3,40})\.(\d{1,3})$/.exec(code);
  if (!m) return { status: 400, body: { detail: "Mã tem không đúng định dạng.", code: "INVALID_INPUT" } };
  const printNo = parseInt(m[2], 10);
  const note = MOCK_DELIVERY_NOTES.find((n) => n.code === m[1]);
  const lastPrinted = note ? Math.max(note.label.valid_print_no ?? 0, ...note.label.to_void) : 0;
  if (!note || !inCourierScope(me, note) || !note.label.printed || printNo < 1 || printNo > lastPrinted) {
    return { status: 404, body: { detail: "Không tìm thấy phiếu.", code: "NOT_FOUND" } };
  }
  const valid = note.status === "CANCELLED" ? null : note.label.valid_print_no;
  const warning = note.status === "CANCELLED" ? "BR-GH-07" : printNo !== valid ? "BR-GH-16" : null;
  return { status: 200, body: { note_id: note.id, status: note.status, print_no: printNo, valid_print_no: valid, warning } };
}
