// Mock module orders — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dựng JSON theo contract THỰC TẾ BE L7 (03-dev-notes.md "Lô L7 — S10, S11 (BE)"): mã SO…/INV…/GH-…, `payments[].source`,
// thêm status_label/total_amount/created_at/reserved_until ở chi tiết; và "Lô L7 — bổ sung (BE)": `q` khớp cả tên khách (bỏ dấu),
// `*_label` của giao dịch/phiếu giao/phiếu hoàn, `timeline [{at, kind, label, actor_display}]` tăng dần. Đổi ở BE thì chép lại ở đây.
//
//   GET  /api/sales/orders/?status=A,B&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&q=&page=   (20 dòng/trang)
//   GET  /api/sales/orders/{id}/
//   POST /api/sales/orders/{id}/confirm-payment[/]   {bank_txn_id, amount?}
//
// Luật mock (mô phỏng BE, FE KHÔNG dùng lại các luật này — nút chỉ theo `available_actions`):
//  - Cần sales.view_salesorder (thiếu → 403). Người CHỈ thuộc nv_giao chỉ thấy đơn của phiếu giao gán cho mình; đơn khác → 404 (S5).
//  - `q` khớp một phần mã đơn (không phân biệt hoa thường), SĐT, hoặc tên khách bỏ dấu ("chi hoa" → "Chị Hoa");
//    ngày lọc theo ngày tạo (giờ VN), sai dạng → 400 INVALID_FILTER.
//  - `allocations[].unit_cost` chỉ có KEY khi có inventory.view_costprice (BR-PQ-15).
//  - `needs_attention` = có giao dịch UNDERPAID/ORPHAN hoặc phiếu giao FAILED (giả định 5 của BE).
//  - available_actions (thứ tự cố định): confirm_payment = BOOKED/AUTO_CANCELLED + sales.confirm_payment_manual;
//    cancel = PAID/PROCESSING có hoá đơn + sales.cancel_paid_order; create_refund = có hoá đơn, còn tiền hoàn được + sales.create_refund.
//  - confirm-payment: thiếu quyền → 403 (kiểm TRƯỚC khi tra đơn); thiếu mã / mã > 100 ký tự / amount ≤ 0 → 400 BR-TT-08;
//    mã đã ghi cho ĐƠN KHÁC → 400 BR-TT-03; cùng mã cùng đơn (kể cả webhook ghi trước, vd FT2626700002 của đơn "chuyển thiếu")
//    → kết quả + trạng thái HIỆN TẠI của đơn kèm duplicate:true; đơn không BOOKED/AUTO_CANCELLED → 400 BR-TT-08;
//    AUTO_CANCELLED → ORPHAN (BR-TT-05); BOOKED: MỘT giao dịch ≥ tổng → PAID (PROCESSING, hoá đơn, phiếu giao PREPARING),
//    thiếu → UNDERPAID (đơn vẫn BOOKED; paid_total = MATCHED + UNDERPAID của đơn, BR-TT-04 khớp theo từng giao dịch).
//
// Dữ liệu giữ trong sessionStorage (qua reload trong cùng tab), tự gieo lại sau 25 phút để giờ giữ chỗ còn ý nghĩa.
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.orders("ok" | "fail" | "empty" | "forbidden" | "detailfail") — chế độ (localStorage, qua reload)
//   window.__caveMock.resetOrders()                  — gieo lại dữ liệu
//   window.__caveMock.orderJson(username, id)        — JSON chi tiết đúng như người đó nhận (e2e kiểm key unit_cost)
//
// ---- S12/S13 (lô L8) — theo contract THỰC TẾ BE ở 03-dev-notes.md "Lô L8 — S12, S13 (BE)" ----
//   GET  /api/sales/payments/?resolution_status=OPEN|RESOLVED&match_status=&page=     (20 dòng/trang, mới → cũ)
//   GET  /api/sales/payments/{id}/
//   POST /api/sales/payments/{id}/resolve[/]   {action: ATTACH_TO_ORDER, order_id, note} | {action: CONFIRM_ORDER, note}
//   POST /api/sales/refunds/create[/]          {payment_transaction, amount, reason, request_id}
// Hàng chờ = mọi giao dịch có `resolution_status` (UNDERPAID/ORPHAN/UNMATCHED/OVERPAID lúc ghi). Webhook MATCHED không vào.
// Luật mock (giả định FE, BE chốt thì chép lại):
//  - Cần sales.confirm_payment_manual (thiếu → 403, kiểm TRƯỚC khi tra giao dịch) — Quản lý/NV kho 403 (S12-AC7).
//  - available_actions (khoản OPEN): UNMATCHED → attach_to_order; UNDERPAID + đơn Giữ chỗ + tổng đã trả ĐỦ (giả định 1 BE)
//    → confirm_order; mọi loại còn tiền hoàn được (BR-HT-04) + sales.create_refund → refund. Khoản RESOLVED → [].
//    Tổng đã trả = MATCHED + UNDERPAID, TRỪ giao dịch đang có phiếu hoàn chưa Thất bại (Q9 BE).
//  - ATTACH_TO_ORDER: chỉ UNMATCHED; đơn Tự huỷ → BR-TT-05; đơn khác Giữ chỗ → 400 (tạm); đủ tiền (cộng các khoản đã nhận
//    của đơn) → đơn PROCESSING như S11-AC1, khoản RESOLVED/ATTACHED (khoản thiếu cũ của đơn → CONFIRMED); chưa đủ → khoản
//    thành UNDERPAID của đơn, VẪN OPEN.
//  - CONFIRM_ORDER: chỉ UNDERPAID; đơn Tự huỷ/Huỷ → BR-TT-05; tổng MATCHED+UNDERPAID < tổng đơn → BR-TT-09 (S12-AC4);
//    đủ → PROCESSING, MỌI khoản UNDERPAID của đơn RESOLVED/CONFIRMED (S12-AC3). Đã RESOLVED → 400 (S12-AC6).
//  - refunds/create: thiếu create_refund → 403; gắn payment_transaction mà thiếu confirm_payment_manual → 403 (S13-AC6);
//    gửi cả hai nguồn / thiếu cả hai → BR-HT-01; vượt số còn hoàn (không tính phiếu FAILED) → BR-HT-04; request_id không phải
//    UUID → BR-HT-01; cùng request_id → 200 phiếu cũ + duplicate:true.
//    Phiếu PENDING, khoản vẫn OPEN (S13-AC1). Xác nhận phiếu (S16, chưa có màn) giả lập bằng __caveMock.confirmRefund.
// Công cụ thử:
//   window.__caveMock.payments("ok" | "fail" | "empty" | "forbidden")  — chế độ hàng chờ (localStorage)
//   window.__caveMock.expireOrder(id)                 — đơn tự huỷ "trong lúc chờ" (S12-AC5)
//   window.__caveMock.confirmRefund(refundId, ref)    — giả lập S16: phiếu REFUNDED → khoản RESOLVED/REFUNDED (S13-AC2)
//   window.__caveMock.queueJson(username)             — JSON hàng chờ OPEN đúng như người đó nhận

import type { MockRequest, MockResponse, Paginated } from "@/shared/lib/http";
import { beError } from "@/shared/lib/beErrors.mock";
import { onlyDelivery } from "@/shared/lib/nav";
import { MOCK_UNAUTHORIZED, mockRequireUser, mockUsers, mockPermsOf } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import { vnd } from "@/shared/lib/format";
import type {
  ConfirmPaymentResult,
  CreateRefundResult,
  OrderAllocation,
  OrderDetail,
  OrderListItem,
  OrderPayment,
  OrderRefund,
  OrderStatus,
  OrderTimelineEntry,
  PaymentQueueItem,
  QueueRefund,
  ResolveResult,
} from "./types";

const STORE_KEY = "cave_erp_mock_orders";
const MODE_KEY = "cave_erp_mock_orders_mode";
const QUEUE_MODE_KEY = "cave_erp_mock_payments_mode";
const RESEED_MS = 25 * 60_000;
const TTL_MIN = 30;
const PAGE_SIZE = 20;
const PERM_VIEW = "sales.view_salesorder";
const PERM_CONFIRM = "sales.confirm_payment_manual";
const PERM_CANCEL = "sales.cancel_paid_order";
const PERM_REFUND = "sales.create_refund";
const PERM_COST = "inventory.view_costprice";
const PERM_VIEW_REFUND = "sales.view_refund";
const PERM_CONFIRM_REFUND = "sales.confirm_refund";
const REFUND_MODE_KEY = "cave_erp_mock_refunds_mode";

/** Giao dịch trong kho mock: field nội bộ (người xác nhận tay, xử lý hàng chờ, nội dung CK) — BE chỉ trả một phần. */
type Pay = OrderPayment & {
  actor?: string;
  content?: string;
  /** Có key = giao dịch từng vào hàng chờ (S12). */
  resolution_status?: "OPEN" | "RESOLVED";
  resolution?: "ATTACHED" | "CONFIRMED" | "REFUNDED" | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  resolution_note?: string;
};
/** Phiếu hoàn gắn `payment_transaction` (S13). S16 bổ sung: người lập/lúc lập/xác nhận/lý do thất bại. */
type MockRefund = QueueRefund & {
  txnId: number;
  reason: string;
  request_id: string;
  created_by: string;
  created_at: string;
  confirmed_at: string | null;
  failure_reason: string;
};
/** Phiếu hoàn gắn `sales_invoice` (S15) — sống trong `Order.refunds`; field nội bộ, `detail()` chỉ lộ phần công khai. */
type MockOrderRefund = OrderRefund & {
  reason: string;
  request_id: string;
  created_by: string;
  created_at: string;
  confirmed_at: string | null;
  failure_reason: string;
};

type Line = { item_code: string; item_name: string; qty: number; price: number; discount: number; batches: [string, number, number][] };
type Delivery = { id: number; code: string; status: string; assigned_to: number | null; failed_attempts: number };
type Order = {
  id: number;
  code: string;
  status: OrderStatus;
  customer: { name: string; phone: string; address: string };
  created_at: string;
  reserved_until: string | null;
  lines: Line[];
  invoice: { id: number; code: string; issued_at: string } | null;
  /** `actor` = tên người xác nhận tay (nội bộ mock, không trả ra) — nguồn `actor_display` của timeline. */
  payments: Pay[];
  delivery: Delivery | null;
  refunds: MockOrderRefund[];
  needs_attention: boolean;
  /** S14 (thử BR-LO-05): lô của đơn này giả lập đã CHỐT — cancel trả lỗi "không hoàn kho được". Bật qua devtool. */
  batchClosed?: boolean;
};
type Txn = { orderId: number; result: ConfirmPaymentResult };
type Store = {
  seededAt: number;
  orders: Order[];
  txns: Record<string, Txn>;
  seq: number;
  /** S12: tiền về không khớp đơn nào (chưa gắn). */
  unmatched: Pay[];
  /** S13: phiếu hoàn gắn giao dịch (không hoá đơn). */
  txnRefunds: MockRefund[];
};

const ORDER_LABEL: Record<OrderStatus, string> = {
  BOOKED: "Giữ chỗ",
  PAID: "Đã thanh toán",
  PROCESSING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  CANCELLED: "Đã huỷ",
  AUTO_CANCELLED: "Tự huỷ (quá TTL)",
};

// [mã, tên, giá bán/kg, lô, giá vốn/kg]
const ITEMS: [string, string, number, string, number][] = [
  ["TOM-SU-1", "Tôm sú loại 1", 270000, "TOM-SU-1-260920-AB12C", 180000],
  ["CA-THU-PL", "Cá thu phi lê", 260000, "CA-THU-PL-260914-CT01", 182000],
  ["MUC-LA", "Mực lá câu", 320000, "MUC-LA-260915-MU02", 236500],
  ["CA-BOP", "Cá bớp cắt khúc", 230000, "CA-BOP-260917-CB01", 158000],
  ["GHE-XANH", "Ghẹ xanh", 380000, "GHE-XANH-260918-GX01", 265000],
  ["CA-HONG", "Cá hồng đỏ", 210000, "CA-HONG-260918-CH01", 142500],
  ["CA-NGU", "Cá ngừ đại dương loin", 290000, "CA-NGU-260919-CN01", 205000],
];
// Lô khác cùng mặt hàng — để có đơn phân bổ 2 lô (BR-BH-06).
const OLD_BATCH: Record<string, [string, number]> = {
  "TOM-SU-1": ["TOM-SU-1-260912-ZX09A", 176000],
  "CA-BOP": ["CA-BOP-260910-CB00", 151000],
};

const CUSTOMERS: [string, string, string][] = [
  ["Chị Hoa", "0901234567", "12 Lê Lợi, Vũng Tàu"],
  ["Anh Minh", "0912345678", "45 Trần Phú, Vũng Tàu"],
  ["Cô Lan", "0938765432", "8 Hoàng Hoa Thám, Vũng Tàu"],
  ["Anh Khoa", "0977111222", "102 Nguyễn An Ninh, Vũng Tàu"],
  ["Chị Thảo", "0983456123", "27 Bà Triệu, Vũng Tàu"],
  ["Khách lẻ", "0868554561", "Chung cư Vũng Tàu Centre Point, tháp B, tầng 12, căn hộ 1208, 1 Lê Hồng Phong, Phường 7, TP Vũng Tàu"],
  ["Bác Tư", "0703999888", "3 Thùy Vân, Vũng Tàu"],
  ["Chị Ngọc Ánh", "0945222333", "66 Lý Thường Kiệt, Vũng Tàu"],
];

// Kịch bản trạng thái theo thứ tự đơn MỚI → CŨ (45 đơn). Phần tử: [trạng thái, phút trước, ghi chú kịch bản]
type Plan = [OrderStatus, number, string?];
const PLAN: Plan[] = [
  ["BOOKED", 10, "hoa"], // id 101 — DH mẫu của contract
  ["BOOKED", 27, "soon"], // còn ~3 phút giữ chỗ
  ["AUTO_CANCELLED", 55],
  ["PROCESSING", 80, "giao1"],
  ["PAID", 95],
  ["BOOKED", 18, "under"],
  ["PROCESSING", 150, "giao2"],
  ["PROCESSING", 200, "failed"],
  ["COMPLETED", 260],
  ["CANCELLED", 320, "refund-pending"],
];

function pad(n: number, w = 2): string {
  return String(n).padStart(w, "0");
}
/** ISO có múi +07:00 như BE (Asia/Ho_Chi_Minh). */
function isoVN(ms: number): string {
  const d = new Date(ms + 7 * 3600_000);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(
    d.getUTCMinutes(),
  )}:${pad(d.getUTCSeconds())}+07:00`;
}
function dayVN(iso: string): string {
  return iso.slice(0, 10);
}
function yymmdd(iso: string): string {
  return iso.slice(2, 4) + iso.slice(5, 7) + iso.slice(8, 10);
}
/** Đuôi mã kiểu BE (hex in hoa), tất định theo số. */
function hex(n: number, w: number): string {
  return ((n * 2654435761) >>> 0).toString(16).toUpperCase().padStart(8, "0").slice(0, w);
}
function money(n: number): string {
  return String(Math.round(n));
}
function kgStr(n: number): string {
  return n.toFixed(3);
}

function lineTotal(l: Line): number {
  return l.qty * l.price - l.discount;
}
function orderTotal(o: Order): number {
  return o.lines.reduce((s, l) => s + lineTotal(l), 0);
}

function makeLines(i: number): Line[] {
  const count = 1 + (i % 3);
  const out: Line[] = [];
  for (let k = 0; k < count; k++) {
    const [code, name, price, batch, cost] = ITEMS[(i * 2 + k * 3) % ITEMS.length];
    if (out.some((l) => l.item_code === code)) continue;
    const qty = [2, 1.5, 0.5, 3, 1, 2.5][(i + k) % 6];
    const old = OLD_BATCH[code];
    const batches: [string, number, number][] =
      old && qty >= 2 ? [[old[0], 0.5, old[1]], [batch, qty - 0.5, cost]] : [[batch, qty, cost]];
    out.push({ item_code: code, item_name: name, qty, price, discount: k === 1 && i % 4 === 0 ? 20000 : 0, batches });
  }
  return out;
}

function seed(): Store {
  const now = Date.now();
  const orders: Order[] = [];
  let payId = 800;
  let invId = 40;
  let delId = 20;
  let refId = 3;
  const txns: Record<string, Txn> = {};
  for (let i = 0; i < 45; i++) {
    const plan: Plan =
      PLAN[i] ||
      (() => {
        // Đơn cũ hơn: rải 1–20 ngày trước, chủ yếu hoàn tất, xen huỷ / tự huỷ.
        const st: OrderStatus = i % 9 === 0 ? "AUTO_CANCELLED" : i % 11 === 0 ? "CANCELLED" : "COMPLETED";
        return [st, 360 + (i - PLAN.length) * 610 + (i % 5) * 37];
      })();
    const [status, minutesAgo, tag] = plan;
    const id = 101 + i;
    const createdMs = now - minutesAgo * 60_000;
    const created = isoVN(createdMs);
    const cust = tag === "hoa" ? CUSTOMERS[0] : CUSTOMERS[1 + (i % (CUSTOMERS.length - 1))];
    const lines: Line[] =
      tag === "hoa"
        ? [{ item_code: "TOM-SU-1", item_name: "Tôm sú loại 1", qty: 2, price: 270000, discount: 0, batches: [["TOM-SU-1-260920-AB12C", 2, 180000]] }]
        : makeLines(i);
    const o: Order = {
      id,
      code: `SO${yymmdd(created)}-${hex(id, 6)}`,
      status,
      customer: { name: cust[0], phone: cust[1], address: cust[2] },
      created_at: created,
      reserved_until: isoVN(createdMs + TTL_MIN * 60_000), // BE giữ mốc này cả sau khi đơn đã trả tiền
      lines,
      invoice: null,
      payments: [],
      delivery: null,
      refunds: [],
      needs_attention: false,
    };
    const total = orderTotal(o);
    if (status === "PAID" || status === "PROCESSING" || status === "COMPLETED" || status === "CANCELLED") {
      const paidAt = isoVN(createdMs + 6 * 60_000);
      const txn = `FT26267${pad(id, 5)}`;
      o.payments.push({ id: ++payId, bank_txn_id: txn, amount: money(total), match_status: "MATCHED", received_at: paidAt, source: "WEBHOOK" });
      txns[txn] = { orderId: id, result: { result: "PAID", duplicate: false, order_status: "PROCESSING" } };
      if (status !== "PAID") {
        o.invoice = { id: ++invId, code: `INV${yymmdd(created)}-${hex(invId * 7, 6)}`, issued_at: isoVN(createdMs + 6 * 60_000 + 20_000) };
      }
    }
    if (status === "PROCESSING" || status === "COMPLETED") {
      const assigned = tag === "giao1" ? 4 : tag === "giao2" ? 7 : tag === "failed" ? 4 : status === "COMPLETED" ? [4, 7, 3][i % 3] : null;
      const dStatus = status === "COMPLETED" ? "COMPLETED" : tag === "giao2" ? "DELIVERING" : tag === "failed" ? "FAILED" : "PREPARING";
      o.delivery = {
        id: ++delId,
        code: `GH-${o.invoice!.code}-${hex(delId * 13, 5)}`,
        status: dStatus,
        assigned_to: assigned,
        failed_attempts: tag === "failed" ? 1 : 0,
      };
      if (tag === "failed") o.needs_attention = true;
    }
    if (status === "CANCELLED") {
      const pending = tag === "refund-pending";
      o.refunds.push({
        id: ++refId,
        amount: money(total),
        status: pending ? "PENDING" : "REFUNDED",
        bank_txn_ref: pending ? "" : `HT26267${pad(refId, 4)}`,
        reason: CANCEL_REASON,
        request_id: `seed-order-refund-${refId}`,
        created_by: "Lộc",
        created_at: isoVN(createdMs + 30 * 60_000),
        confirmed_at: pending ? null : isoVN(createdMs + 90 * 60_000),
        failure_reason: "",
      });
    }
    if (tag === "under") {
      // Khách đã chuyển thiếu một lần (webhook ghi UNDERPAID).
      const txn = "FT2626700002";
      o.payments.push({
        id: ++payId,
        bank_txn_id: txn,
        amount: money(total - 100000),
        match_status: "UNDERPAID",
        received_at: isoVN(createdMs + 4 * 60_000),
        source: "WEBHOOK",
        content: `${o.code} chuyen khoan`,
        resolution_status: "OPEN",
      });
      txns[txn] = {
        orderId: id,
        result: { result: "UNDERPAID", duplicate: false, order_status: "BOOKED", paid_total: money(total - 100000), missing: "100000" },
      };
      o.needs_attention = true;
    }
    // S12 — thêm vài khoản lệch trên đơn CŨ (không đụng đơn 101–110 mà e2e S10/S11 bám).
    if (id === 119 && status === "AUTO_CANCELLED") {
      // Tiền về 12′ sau khi đơn tự huỷ (BR-TT-05) — webhook ghi ORPHAN.
      const txn = "FT2626700019";
      o.payments.push({
        id: ++payId, bank_txn_id: txn, amount: money(total), match_status: "ORPHAN",
        received_at: isoVN(createdMs + (TTL_MIN + 12) * 60_000), source: "WEBHOOK", content: `${o.code} thanh toan`, resolution_status: "OPEN",
      });
      txns[txn] = { orderId: id, result: { result: "ORPHAN", duplicate: false, order_status: "AUTO_CANCELLED" } };
    }
    if (id === 113 && status === "COMPLETED") {
      // P5: khách chuyển lần hai cho đơn đã thanh toán → "chuyển thừa", vào hàng chờ để Chủ hoàn.
      const txn = "FT2626700013";
      o.payments.push({
        id: ++payId, bank_txn_id: txn, amount: "150000", match_status: "OVERPAID",
        received_at: isoVN(createdMs + 40 * 60_000), source: "WEBHOOK", content: `${o.code} ck lan 2`, resolution_status: "OPEN",
      });
      txns[txn] = { orderId: id, result: { result: "OVERPAID", duplicate: false, order_status: "COMPLETED" } };
    }
    if (id === 128 && status === "AUTO_CANCELLED") {
      // Lịch sử: khoản về sau khi đơn tự huỷ, đã hoàn xong (RESOLVED/REFUNDED).
      const txn = "FT2626700028";
      o.payments.push({
        id: 870, bank_txn_id: txn, amount: money(total), match_status: "ORPHAN",
        received_at: isoVN(createdMs + (TTL_MIN + 5) * 60_000), source: "WEBHOOK", content: `${o.code}`,
        resolution_status: "RESOLVED", resolution: "REFUNDED", resolved_by: "Lộc",
        resolved_at: isoVN(createdMs + 26 * 3600_000), resolution_note: "Đã chuyển trả khách",
      });
      txns[txn] = { orderId: id, result: { result: "ORPHAN", duplicate: false, order_status: "AUTO_CANCELLED" } };
    }
    orders.push(o);
  }
  // S12 — tiền về không khớp đơn nào (UNMATCHED). Khoản 1 bằng đúng tổng đơn 101 của Chị Hoa (540.000 ₫) → S12-AC2.
  const unmatched: Pay[] = [
    {
      id: 880, bank_txn_id: "FT2626700091", amount: "540000", match_status: "UNMATCHED",
      received_at: isoVN(now - 6 * 60_000), source: "WEBHOOK", content: "CHI HOA CK TIEN TOM", resolution_status: "OPEN",
    },
    {
      id: 881, bank_txn_id: "FT2626700092", amount: "185000", match_status: "UNMATCHED",
      received_at: isoVN(now - 2 * 86_400_000 - 3 * 3600_000), source: "WEBHOOK", content: "chuyen tien", resolution_status: "OPEN",
    },
  ];
  txns["FT2626700091"] = { orderId: 0, result: { result: "UNMATCHED", duplicate: false, order_status: "" } };
  txns["FT2626700092"] = { orderId: 0, result: { result: "UNMATCHED", duplicate: false, order_status: "" } };
  const txnRefunds: MockRefund[] = [
    {
      id: 30, txnId: 870, amount: "0", status: "REFUNDED", bank_txn_ref: "HT2626700028",
      reason: "Tiền về sau khi đơn tự huỷ", request_id: "seed-30",
      created_by: "Lộc", created_at: isoVN(now - 20 * 3600_000), confirmed_at: isoVN(now - 19 * 3600_000), failure_reason: "",
    },
  ];
  const o128 = orders.find((x) => x.id === 128);
  if (o128) txnRefunds[0].amount = money(orderTotal(o128));
  // S16: một phiếu Thất bại sẵn có để thử "Thử lại" ngay khi mở màn (BR-HT-09).
  txnRefunds.push({
    id: 31, txnId: 881, amount: "80000", status: "FAILED", bank_txn_ref: "",
    reason: "Tiền không khớp đơn nào", request_id: "seed-31",
    created_by: "Lộc", created_at: isoVN(now - 3 * 3600_000), confirmed_at: null, failure_reason: "Sai số tài khoản",
  });
  return { seededAt: now, orders, txns, seq: 60, unmatched, txnRefunds };
}

function ss(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

let memory: Store | null = null;
function load(): Store {
  if (memory && Date.now() - memory.seededAt < RESEED_MS) return memory;
  const raw = ss()?.getItem(STORE_KEY);
  if (raw) {
    try {
      const s = JSON.parse(raw) as Store;
      if (Date.now() - s.seededAt < RESEED_MS && Array.isArray(s.unmatched) && Array.isArray(s.txnRefunds)) {
        memory = s;
        return s;
      }
    } catch {
      /* hỏng → gieo lại */
    }
  }
  memory = seed();
  save(memory);
  return memory;
}
function save(s: Store): void {
  memory = s;
  try {
    ss()?.setItem(STORE_KEY, JSON.stringify(s));
  } catch {
    /* bỏ qua */
  }
}

type Mode = "ok" | "fail" | "empty" | "forbidden" | "detailfail";
function mode(): Mode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return v === "fail" || v === "empty" || v === "forbidden" || v === "detailfail" ? v : "ok";
  } catch {
    return "ok";
  }
}

// ---------- Nhãn BE (TextChoices) + dòng thời gian ----------
const DELIVERY_LABEL: Record<string, string> = {
  PREPARING: "Soạn hàng",
  READY: "Chờ lấy hàng",
  DELIVERING: "Đang giao",
  COMPLETED: "Hoàn tất",
  FAILED: "Giao thất bại",
  CANCELLED: "Đã huỷ theo đơn",
};
const CANCEL_REASON_CODES = new Set(["CUSTOMER_CHANGED_MIND", "DAMAGED_WHEN_PACKING", "GIVE_UP_AFTER_FAILED", "OTHER"]);
const MATCH_LABEL: Record<string, string> = {
  MATCHED: "Khớp — đã xác nhận",
  UNDERPAID: "Thiếu tiền — chờ Chủ",
  ORPHAN: "Đến sau khi đơn đã huỷ — chờ Chủ",
  UNMATCHED: "Không khớp đơn — chờ Chủ",
  OVERPAID: "Chuyển thừa — đơn đã thanh toán, chờ Chủ",
};
const SOURCE_LABEL: Record<string, string> = { WEBHOOK: "Webhook SePay", MANUAL: "Xác nhận tay" };
const REFUND_LABEL: Record<string, string> = { PENDING: "Chờ hoàn", REFUNDED: "Đã hoàn", FAILED: "Thất bại" };
const SYSTEM = "Hệ thống";
const CANCEL_REASON = "Khách đổi ý";

/** Như BE `fold_text`: bỏ dấu, đ→d, không phân biệt hoa thường. */
function fold(v: string): string {
  return v.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
}

function courierName(id: number | null): string {
  if (id == null) return SYSTEM;
  const u = mockUsers().find((x) => x.id === id);
  return u ? u.display_name || u.username : SYSTEM;
}

/** Dựng `timeline` theo đúng cách BE ghép (chứng từ + AuditLog), `at` tăng dần, cùng giờ giữ thứ tự nghiệp vụ. */
function timelineOf(o: Order): OrderTimelineEntry[] {
  const out: OrderTimelineEntry[] = [];
  const at = (iso: string, plusMin: number) => isoVN(new Date(iso).getTime() + plusMin * 60_000);
  out.push({ at: o.created_at, kind: "order_placed", label: `Khách đặt đơn ${o.code} (${vnd(orderTotal(o))})`, actor_display: SYSTEM });
  o.payments.forEach((p) => {
    if (!p.received_at) return;
    out.push({
      at: p.received_at,
      kind: "payment_received",
      label: `Nhận ${vnd(p.amount)} · ${SOURCE_LABEL[p.source || "WEBHOOK"]} · ${MATCH_LABEL[p.match_status]} (mã GD ${p.bank_txn_id})`,
      actor_display: p.source === "MANUAL" ? p.actor || SYSTEM : SYSTEM,
    });
  });
  if (o.invoice) out.push({ at: o.invoice.issued_at, kind: "invoice_issued", label: `Xuất hoá đơn ${o.invoice.code}`, actor_display: SYSTEM });
  const d = o.delivery;
  if (d && o.invoice) {
    const base = o.invoice.issued_at;
    out.push({ at: base, kind: "delivery_created", label: `Tạo phiếu giao ${d.code} (Soạn hàng)`, actor_display: SYSTEM });
    const who = courierName(d.assigned_to);
    const steps: [number, OrderTimelineEntry["kind"], string][] = [];
    if (d.status !== "PREPARING") {
      steps.push([8, "delivery_status", `Phiếu giao ${d.code}: Soạn hàng → Chờ lấy hàng`]);
      steps.push([15, "delivery_status", `Phiếu giao ${d.code}: Chờ lấy hàng → Đang giao`]);
    }
    if (d.status === "FAILED") steps.push([40, "delivery_failed", `Giao thất bại lần ${d.failed_attempts || 1} (${d.code})`]);
    if (d.status === "COMPLETED") steps.push([45, "delivered", `Giao hàng thành công (${d.code})`]);
    steps.forEach(([m, kind, label]) => out.push({ at: at(base, m), kind, label, actor_display: who }));
  }
  if (o.status === "AUTO_CANCELLED" && o.reserved_until) {
    out.push({ at: o.reserved_until, kind: "auto_cancelled", label: "Tự huỷ vì quá hạn giữ chỗ, đã nhả hàng giữ", actor_display: SYSTEM });
  }
  if (o.status === "CANCELLED" && o.invoice) {
    out.push({ at: at(o.invoice.issued_at, 30), kind: "cancelled", label: `Huỷ đơn, hoàn hàng về lô gốc — lý do: ${CANCEL_REASON}`, actor_display: "Lộc" });
  }
  o.refunds.forEach((r, i) => {
    const base = o.invoice ? o.invoice.issued_at : o.created_at;
    out.push({ at: at(base, 32 + i), kind: "refund_created", label: `Tạo phiếu hoàn ${vnd(r.amount)} — ${CANCEL_REASON}`, actor_display: "Lộc" });
    if (r.status === "REFUNDED") {
      out.push({ at: at(base, 90 + i), kind: "refund_confirmed", label: `Đã hoàn ${vnd(r.amount)} (mã GD ${r.bank_txn_ref})`, actor_display: "Lộc" });
    }
  });
  // Sắp tăng dần theo giờ, giữ thứ tự chèn (= thứ tự nghiệp vụ) khi cùng giờ.
  return out.map((e, i) => ({ e, i })).sort((a, b) => a.e.at.localeCompare(b.e.at) || a.i - b.i).map((x) => x.e);
}

// ---------- Quyền + phạm vi ----------
const has = (me: Me, p: string) => me.permissions.includes(p);
function inScope(me: Me, o: Order): boolean {
  if (!onlyDelivery(me)) return true;
  return !!o.delivery && o.delivery.assigned_to === me.id;
}

function actions(me: Me, o: Order): string[] {
  const out: string[] = [];
  if ((o.status === "BOOKED" || o.status === "AUTO_CANCELLED") && has(me, PERM_CONFIRM)) out.push("confirm_payment");
  if ((o.status === "PAID" || o.status === "PROCESSING") && o.invoice && has(me, PERM_CANCEL)) out.push("cancel");
  const refunded = o.refunds.filter((r) => r.status !== "FAILED").reduce((sum, r) => sum + Number(r.amount), 0);
  if (o.invoice && refunded < orderTotal(o) && has(me, PERM_REFUND)) out.push("create_refund");
  return out;
}

function listItem(o: Order): OrderListItem {
  return {
    id: o.id,
    code: o.code,
    status: o.status,
    status_label: ORDER_LABEL[o.status],
    customer_name: o.customer.name,
    customer_phone: o.customer.phone,
    total_amount: money(orderTotal(o)),
    created_at: o.created_at,
    reserved_until: o.reserved_until,
    delivery_status: o.delivery ? o.delivery.status : null,
    // Giả định 5 của BE L7 + S12: chỉ tính khoản lệch CÒN MỞ (khoản đã xử lý không còn cần chú ý).
    needs_attention: o.delivery?.status === "FAILED" || o.payments.some((p) => p.resolution_status === "OPEN"),
  };
}

function detail(me: Me, o: Order): OrderDetail {
  const canCost = has(me, PERM_COST);
  const users = mockUsers();
  const courier = o.delivery?.assigned_to != null ? users.find((u) => u.id === o.delivery!.assigned_to) : undefined;
  const allocations: OrderAllocation[] = [];
  o.lines.forEach((l, idx) =>
    l.batches.forEach(([batch, qty, cost]) => {
      const a: OrderAllocation = { line_no: idx + 1, batch_id: batch, qty_kg: kgStr(qty) };
      if (canCost) a.unit_cost = money(cost); // thiếu quyền → KHÔNG có key (BR-PQ-15)
      allocations.push(a);
    }),
  );
  return {
    id: o.id,
    code: o.code,
    status: o.status,
    status_label: ORDER_LABEL[o.status],
    total_amount: money(orderTotal(o)),
    created_at: o.created_at,
    reserved_until: o.reserved_until,
    customer: { ...o.customer },
    lines: o.lines.map((l, idx) => ({
      no: idx + 1,
      item_code: l.item_code,
      item_name: l.item_name,
      qty_kg: kgStr(l.qty),
      unit_price: money(l.price),
      discount: money(l.discount),
      line_total: money(lineTotal(l)),
    })),
    allocations: o.status === "AUTO_CANCELLED" ? [] : allocations,
    invoice: o.invoice ? { ...o.invoice } : null,
    // Chỉ các key của contract S10 — field nội bộ (người xác nhận tay, hàng chờ S12) không trả ra.
    payments: o.payments.map((p) => ({
      id: p.id,
      bank_txn_id: p.bank_txn_id,
      amount: p.amount,
      match_status: p.match_status,
      match_status_label: MATCH_LABEL[p.match_status],
      received_at: p.received_at,
      source: p.source,
      source_label: p.source ? SOURCE_LABEL[p.source] : undefined,
    })),
    delivery: o.delivery
      ? {
          id: o.delivery.id,
          code: o.delivery.code,
          status: o.delivery.status,
          status_label: DELIVERY_LABEL[o.delivery.status],
          assigned_to: courier ? { id: courier.id, display_name: courier.display_name, phone: courier.phone } : null,
          failed_attempts: o.delivery.failed_attempts,
        }
      : null,
    // Chỉ lộ field công khai (contract S10) — reason/request_id/created_by/created_at/confirmed_at/failure_reason
    // là bookkeeping nội bộ cho S16, không nằm trong OrderRefund.
    refunds: o.refunds.map((r) => ({ id: r.id, amount: r.amount, status: r.status, status_label: REFUND_LABEL[r.status], bank_txn_ref: r.bank_txn_ref })),
    timeline: timelineOf(o),
    available_actions: actions(me, o),
  };
}

// ---------- Handler ----------
function parsePath(path: string): { id: number | null; action: string | null; query: URLSearchParams } {
  const [p, q = ""] = path.split("?");
  const m = /^\/api\/sales\/orders\/(?:(\d+)\/(?:([a-z-]+)\/?)?)?$/.exec(p);
  return { id: m && m[1] ? Number(m[1]) : null, action: m && m[2] ? m[2] : null, query: new URLSearchParams(q) };
}

function listResponse(me: Me, query: URLSearchParams): MockResponse {
  const statuses = (query.get("status") || "").split(",").map((s) => s.trim()).filter(Boolean);
  const from = query.get("date_from") || "";
  const to = query.get("date_to") || "";
  const q = (query.get("q") || "").trim().toLowerCase();
  const page = Math.max(1, Number(query.get("page") || "1") || 1);
  for (const [param, v] of [["date_from", from], ["date_to", to]] as const) {
    if (v && !/^\d{4}-\d{2}-\d{2}$/.test(v)) return beError("INVALID_FILTER", { param });
  }
  const rows = mode() === "empty" ? [] : load().orders;
  const hit = rows
    .filter((o) => inScope(me, o))
    .filter((o) => !statuses.length || statuses.includes(o.status))
    .filter((o) => !from || dayVN(o.created_at) >= from)
    .filter((o) => !to || dayVN(o.created_at) <= to)
    .filter((o) => !q || o.code.toLowerCase().includes(q) || o.customer.phone.includes(q) || fold(o.customer.name).includes(fold(q)))
    .sort((a, b) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : b.id - a.id));
  const pages = Math.max(1, Math.ceil(hit.length / PAGE_SIZE));
  if (page > pages) return { status: 404, body: { detail: "Trang không hợp lệ." } };
  const link = (n: number) => {
    const qs = new URLSearchParams(query);
    qs.set("page", String(n));
    return `http://localhost:8000/api/sales/orders/?${qs.toString()}`;
  };
  const body: Paginated<OrderListItem> = {
    count: hit.length,
    next: page < pages ? link(page + 1) : null,
    previous: page > 1 ? link(page - 1) : null,
    results: hit.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(listItem),
  };
  return { status: 200, body };
}

/** Dòng phần thừa `<mã GD>-THUA` (BE `split_overpaid`): cùng nguồn, cùng giờ, OVERPAID, vào hàng chờ. */
function splitOverpaid(store: Store, from: Pay, extra: number): Pay {
  const code = `${from.bank_txn_id.slice(0, 95)}-THUA`;
  const extraPay: Pay = {
    id: ++store.seq + 900,
    bank_txn_id: code,
    amount: money(extra),
    match_status: "OVERPAID",
    received_at: from.received_at,
    source: from.source,
    actor: from.actor,
    resolution_status: "OPEN",
  };
  return extraPay;
}

/** Đủ tiền → hoá đơn + phiếu giao PREPARING + đơn PROCESSING (lõi chung `_record_payment` của BE, S11-AC1). */
function markPaid(store: Store, o: Order): void {
  const created = isoVN(Date.now());
  o.status = "PROCESSING";
  o.invoice = { id: ++store.seq, code: `INV${yymmdd(created)}-${hex(store.seq * 7, 6)}`, issued_at: created };
  o.delivery = { id: ++store.seq, code: `GH-${o.invoice.code}-${hex(store.seq * 13, 5)}`, status: "PREPARING", assigned_to: null, failed_attempts: 0 };
}

function confirm(me: Me, o: Order, body: unknown): MockResponse {
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  const txn = typeof b.bank_txn_id === "string" ? b.bank_txn_id.trim() : "";
  if (!txn) return beError("TT_TXN_REQUIRED");
  if (txn.length > 100) return beError("TT_TXN_TOO_LONG");
  const store = load();
  const prev = store.txns[txn];
  if (prev && prev.orderId !== o.id) return beError("TT_TXN_OTHER");
  if (prev) return { status: 200, body: { ...prev.result, order_status: o.status, duplicate: true } }; // BR-TT-03
  const total = orderTotal(o);
  const rawAmount = b.amount === undefined || b.amount === null || b.amount === "" ? String(total) : String(b.amount);
  // B13: làm tròn 2 lẻ như cột `amount` (14 chữ số, 2 lẻ) — ≤ 0 sau làm tròn (0.004) hoặc vượt 12 chữ số phần nguyên → 400,
  // KHÔNG ghi giao dịch 0 ₫, KHÔNG 500. BE đang sửa song song, câu "quá lớn" chưa chốt → mock dùng chung câu TT_AMOUNT_INVALID.
  const amount = Math.round(Number(rawAmount) * 100) / 100;
  if (!Number.isFinite(amount) || amount <= 0 || amount >= 1e12) return beError("TT_AMOUNT_INVALID");
  if (amount < 1) return beError("TT_AMOUNT_MIN"); // L8 bổ sung tiền: tối thiểu 1đ
  if (o.status !== "BOOKED" && o.status !== "AUTO_CANCELLED") return beError("TT_WRONG_STATUS");

  const now = Date.now();
  const payment: Pay = {
    id: ++store.seq + 900,
    bank_txn_id: txn,
    amount: money(amount),
    match_status: "MATCHED",
    received_at: isoVN(now),
    source: "MANUAL",
    actor: me.display_name || me.username,
  };
  let result: ConfirmPaymentResult;
  if (o.status === "AUTO_CANCELLED") {
    payment.match_status = "ORPHAN";
    payment.resolution_status = "OPEN"; // vào hàng chờ S12
    o.needs_attention = true;
    result = { result: "ORPHAN", duplicate: false, order_status: "AUTO_CANCELLED" };
  } else if (amount >= total) {
    markPaid(store, o);
    result = { result: "PAID", duplicate: false, order_status: "PROCESSING", invoice_id: o.invoice!.id, delivery_note_code: o.delivery!.code };
    if (amount > total) {
      // L8 bổ sung tiền (BR-TT-10 mở rộng): dòng khớp mang đúng tổng đơn, phần thừa tách thành `<mã>-THUA` OVERPAID/OPEN.
      payment.amount = money(total);
      o.payments.push(splitOverpaid(store, payment, amount - total));
      result.overpaid_amount = money(amount - total);
    }
  } else {
    payment.match_status = "UNDERPAID";
    payment.resolution_status = "OPEN"; // vào hàng chờ S12
    o.needs_attention = true;
    const paid =
      o.payments.filter((p) => p.match_status === "MATCHED" || p.match_status === "UNDERPAID").reduce((sum, p) => sum + Number(p.amount), 0) +
      amount;
    result = { result: "UNDERPAID", duplicate: false, order_status: "BOOKED", paid_total: money(paid), missing: money(Math.max(0, total - paid)) };
  }
  o.payments.push(payment);
  store.txns[txn] = { orderId: o.id, result };
  save(store);
  return { status: 200, body: result };
}

export function mockOrdersApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!has(me, PERM_VIEW) || mode() === "forbidden") return beError("DRF_FORBIDDEN");
  const { id, action, query } = parsePath(req.path);
  // S11: thiếu sales.confirm_payment_manual → 403 TRƯỚC khi tra đơn (BE L7).
  if (action === "confirm-payment" && req.method === "POST" && !has(me, PERM_CONFIRM)) return beError("DRF_FORBIDDEN");
  if (id === null) {
    if (req.method !== "GET") return beError("METHOD_NOT_ALLOWED", { method: req.method });
    if (mode() === "fail") return { status: 500, body: null };
    return listResponse(me, query);
  }
  const store = load();
  const o = store.orders.find((x) => x.id === id);
  if (!o || !inScope(me, o)) return beError("NOT_FOUND"); // BR-PQ-12: không tiết lộ có tồn tại
  if (!action) {
    if (req.method !== "GET") return beError("METHOD_NOT_ALLOWED", { method: req.method });
    if (mode() === "detailfail") return { status: 500, body: null };
    return { status: 200, body: detail(me, o) };
  }
  if (action === "confirm-payment") {
    if (req.method !== "POST") return beError("METHOD_NOT_ALLOWED", { method: req.method });
    return confirm(me, o, req.body);
  }
  return beError("NOT_FOUND");
}

// ---------- S12: hàng chờ thanh toán lệch · S13: phiếu hoàn cho khoản không có hoá đơn ----------
const QUEUE_RESOLUTION_LABEL: Record<string, string> = {
  ATTACHED: "Đã gắn vào đơn",
  CONFIRMED: "Đã xác nhận đơn",
  REFUNDED: "Đã hoàn tiền",
};

type QMode = "ok" | "fail" | "empty" | "forbidden";
function queueMode(): QMode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(QUEUE_MODE_KEY);
    return v === "fail" || v === "empty" || v === "forbidden" ? v : "ok";
  } catch {
    return "ok";
  }
}

/** "300000" → "300.000đ" (cách BE viết tiền trong câu lỗi, contract S12/S13). */
function vndD(n: number): string {
  return `${Math.round(n).toLocaleString("vi-VN")}đ`;
}

/** Mọi giao dịch từng vào hàng chờ, kèm đơn (null = chưa gắn đơn). */
function queueEntries(store: Store): { p: Pay; o: Order | null }[] {
  const out: { p: Pay; o: Order | null }[] = [];
  store.orders.forEach((o) => o.payments.forEach((p) => p.resolution_status && out.push({ p, o })));
  store.unmatched.forEach((p) => out.push({ p, o: null }));
  return out;
}
function findEntry(store: Store, id: number): { p: Pay; o: Order | null } | null {
  return queueEntries(store).find((e) => e.p.id === id) || null;
}
/** Tổng đã trả của đơn (BE `order_paid_total`): MATCHED + UNDERPAID, trừ giao dịch đang có phiếu hoàn chưa Thất bại. */
function paidOf(o: Order, store: Store = load()): number {
  return o.payments
    .filter((p) => p.match_status === "MATCHED" || p.match_status === "UNDERPAID")
    .filter((p) => !store.txnRefunds.some((r) => r.txnId === p.id && r.status !== "FAILED"))
    .reduce((sum, p) => sum + Number(p.amount), 0);
}
function refundsOf(store: Store, txnId: number): MockRefund[] {
  return store.txnRefunds.filter((r) => r.txnId === txnId);
}
function refundableOf(store: Store, p: Pay): number {
  const used = refundsOf(store, p.id)
    .filter((r) => r.status !== "FAILED")
    .reduce((sum, r) => sum + Number(r.amount), 0);
  return Math.max(0, Number(p.amount) - used);
}

function queueActions(me: Me, store: Store, p: Pay, o: Order | null): string[] {
  if (p.resolution_status !== "OPEN" || !has(me, PERM_CONFIRM)) return [];
  const out: string[] = [];
  if (!o && p.match_status === "UNMATCHED") out.push("attach_to_order");
  if (o && p.match_status === "UNDERPAID" && o.status === "BOOKED" && paidOf(o, store) >= orderTotal(o)) out.push("confirm_order");
  if (has(me, PERM_REFUND) && refundableOf(store, p) > 0) out.push("refund");
  return out;
}

function queueItem(me: Me, store: Store, p: Pay, o: Order | null): PaymentQueueItem {
  // Đúng key BE L8: KHÔNG có `content`, `refunds`, `order.customer_name` (FE đề xuất thêm, xem 03-dev-notes.md).
  return {
    id: p.id,
    bank_txn_id: p.bank_txn_id,
    amount: p.amount,
    received_at: p.received_at,
    match_status: p.match_status,
    match_status_label: MATCH_LABEL[p.match_status],
    source: p.source,
    source_label: p.source ? SOURCE_LABEL[p.source] : undefined,
    order: o
      ? {
          id: o.id,
          code: o.code,
          status: o.status,
          status_label: ORDER_LABEL[o.status],
          total_amount: money(orderTotal(o)),
          paid_total: money(paidOf(o, store)),
        }
      : null,
    resolution_status: p.resolution_status || "OPEN",
    resolution: p.resolution ?? "",
    resolution_label: p.resolution ? QUEUE_RESOLUTION_LABEL[p.resolution] : "",
    resolved_by: p.resolved_by ?? null,
    resolved_at: p.resolved_at ?? null,
    resolution_note: p.resolution_note || "",
    refundable_amount: money(refundableOf(store, p)),
    available_actions: queueActions(me, store, p, o),
  };
}

function queueList(me: Me, query: URLSearchParams): MockResponse {
  const status = query.get("resolution_status") || "";
  const type = (query.get("match_status") || "").split(",").filter(Boolean);
  const page = Math.max(1, Number(query.get("page") || "1") || 1);
  const store = load();
  const hit = (queueMode() === "empty" ? [] : queueEntries(store))
    .filter(({ p }) => !status || p.resolution_status === status)
    .filter(({ p }) => !type.length || type.includes(p.match_status))
    .sort((a, b) => ((a.p.received_at || "") < (b.p.received_at || "") ? 1 : (a.p.received_at || "") > (b.p.received_at || "") ? -1 : b.p.id - a.p.id));
  const pages = Math.max(1, Math.ceil(hit.length / PAGE_SIZE));
  if (page > pages) return { status: 404, body: { detail: "Trang không hợp lệ." } };
  const link = (n: number) => {
    const qs = new URLSearchParams(query);
    qs.set("page", String(n));
    return `http://localhost:8000/api/sales/payments/?${qs.toString()}`;
  };
  const body: Paginated<PaymentQueueItem> = {
    count: hit.length,
    next: page < pages ? link(page + 1) : null,
    previous: page > 1 ? link(page - 1) : null,
    results: hit.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(({ p, o }) => queueItem(me, store, p, o)),
  };
  return { status: 200, body };
}

function closeEntry(me: Me, p: Pay, resolution: "ATTACHED" | "CONFIRMED" | "REFUNDED", note: string): void {
  p.resolution_status = "RESOLVED";
  p.resolution = resolution;
  p.resolved_by = me.display_name || me.username;
  p.resolved_at = isoVN(Date.now());
  p.resolution_note = note;
}

function resolve(me: Me, id: number, body: unknown): MockResponse {
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  const note = typeof b.note === "string" ? b.note.trim() : "";
  const store = load();
  const e = findEntry(store, id);
  if (!e) return beError("NOT_FOUND");
  const { p } = e;
  if (b.action !== "ATTACH_TO_ORDER" && b.action !== "CONFIRM_ORDER") return beError("TT_ACTION_INVALID");
  if (p.resolution_status === "RESOLVED") return beError("TT_ALREADY_RESOLVED"); // S12-AC6
  const cancelled = (o: Order) =>
    o.status === "AUTO_CANCELLED" ? beError("TT_ORDER_CANCELLED") : o.status === "CANCELLED" ? beError("TT_ORDER_CANCELLED_MANUAL") : null;
  const closeUnder = (o: Order): number[] => {
    const ids: number[] = [];
    o.payments
      .filter((x) => x.match_status === "UNDERPAID" && x.resolution_status === "OPEN")
      .forEach((x) => {
        closeEntry(me, x, "CONFIRMED", note);
        ids.push(x.id);
      });
    return ids;
  };
  if (b.action === "ATTACH_TO_ORDER") {
    if (e.o || p.match_status !== "UNMATCHED") return beError("TT_ATTACH_ONLY_UNMATCHED");
    const orderId = Number(b.order_id);
    if (!Number.isInteger(orderId) || orderId <= 0) return beError("TT_ORDER_REQUIRED");
    const o = store.orders.find((x) => x.id === orderId);
    if (!o) return beError("TT_ORDER_NOT_FOUND");
    const c = cancelled(o);
    if (c) return c; // S12-AC5
    if (o.status !== "BOOKED") return beError("TT_ORDER_NOT_BOOKED");
    const before = paidOf(o, store);
    store.unmatched = store.unmatched.filter((x) => x.id !== p.id);
    o.payments.push(p);
    // BE giả định 2: đánh giá lại match_status — một mình khoản này đủ thì MATCHED, không thì UNDERPAID.
    p.match_status = Number(p.amount) >= orderTotal(o) ? "MATCHED" : "UNDERPAID";
    store.txns[p.bank_txn_id] = { orderId: o.id, result: { result: p.match_status, duplicate: false, order_status: o.status } };
    if (before + Number(p.amount) >= orderTotal(o)) {
      const ids = closeUnder(o).filter((x) => x !== p.id);
      closeEntry(me, p, "ATTACHED", note);
      markPaid(store, o);
      let overpaid: string | undefined;
      if (Number(p.amount) > orderTotal(o)) {
        // BE giả định 1 (bổ sung tiền): một mình khoản gắn > tổng đơn → tách phần thừa như lần đầu.
        const extra = Number(p.amount) - orderTotal(o);
        p.amount = money(orderTotal(o));
        o.payments.push(splitOverpaid(store, p, extra));
        overpaid = money(extra);
      }
      save(store);
      return {
        status: 200,
        body: {
          payment_id: p.id, resolution_status: "RESOLVED", resolution: "ATTACHED", order_status: o.status,
          invoice_id: o.invoice!.id, delivery_note_code: o.delivery!.code, resolved_payment_ids: [...ids, p.id].sort((a, c2) => a - c2),
          ...(overpaid ? { overpaid_amount: overpaid } : {}),
        } satisfies ResolveResult,
      };
    }
    save(store);
    return { status: 200, body: { payment_id: p.id, resolution_status: "OPEN", resolution: "", order_status: o.status, resolved_payment_ids: [] } satisfies ResolveResult };
  }
  // CONFIRM_ORDER
  const o = e.o;
  if (!o) return beError("TT_CONFIRM_NO_ORDER");
  if (p.match_status !== "UNDERPAID") return beError("TT_CONFIRM_ONLY_UNDERPAID");
  const c = cancelled(o);
  if (c) return c; // S12-AC5
  if (o.status !== "BOOKED") return beError("TT_ORDER_NOT_BOOKED");
  if (refundsOf(store, p.id).some((r) => r.status !== "FAILED")) return beError("TT_CONFIRM_HAS_REFUND");
  const paid = paidOf(o, store);
  const total = orderTotal(o);
  if (paid < total) return beError("TT_NOT_ENOUGH", { paid: vndD(paid), total: vndD(total) }); // S12-AC4
  const ids = closeUnder(o);
  markPaid(store, o);
  save(store);
  return {
    status: 200,
    body: {
      payment_id: p.id, resolution_status: "RESOLVED", resolution: "CONFIRMED", order_status: o.status,
      invoice_id: o.invoice!.id, delivery_note_code: o.delivery!.code, resolved_payment_ids: ids.sort((a, c2) => a - c2),
    } satisfies ResolveResult,
  };
}

export function mockPaymentsApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  // S12-AC7: Quản lý / NV kho (không có confirm_payment_manual) → 403 cả xem lẫn xử lý; kiểm TRƯỚC khi tra giao dịch.
  if (!has(me, PERM_CONFIRM) || queueMode() === "forbidden") return beError("DRF_FORBIDDEN");
  const [path, q = ""] = req.path.split("?");
  if (path === "/api/sales/payments/") {
    if (req.method !== "GET") return beError("METHOD_NOT_ALLOWED", { method: req.method });
    if (queueMode() === "fail") return { status: 500, body: null };
    return queueList(me, new URLSearchParams(q));
  }
  const one = /^\/api\/sales\/payments\/(\d+)\/$/.exec(path);
  if (one) {
    if (req.method !== "GET") return beError("METHOD_NOT_ALLOWED", { method: req.method });
    const store = load();
    const e = findEntry(store, Number(one[1]));
    return e ? { status: 200, body: queueItem(me, store, e.p, e.o) } : beError("NOT_FOUND");
  }
  const m = /^\/api\/sales\/payments\/(\d+)\/resolve\/?$/.exec(path);
  if (!m) return beError("NOT_FOUND");
  if (req.method !== "POST") return beError("METHOD_NOT_ALLOWED", { method: req.method });
  return resolve(me, Number(m[1]), req.body);
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function createTxnRefund(me: Me, body: unknown): MockResponse {
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  const given = (v: unknown) => v !== undefined && v !== null && v !== "";
  const hasInvoice = given(b.sales_invoice);
  const hasTxn = given(b.payment_transaction);
  // S13-AC6: gắn payment_transaction mà thiếu confirm_payment_manual → 403, kiểm TRƯỚC dữ liệu.
  if (hasTxn && !has(me, PERM_CONFIRM)) return beError("DRF_FORBIDDEN");
  if (hasInvoice && hasTxn) return beError("HT_ONE_SOURCE"); // S13-AC4
  if (!hasInvoice && !hasTxn) return beError("HT_NO_SOURCE");
  if (!hasTxn) return beError("NOT_FOUND"); // phiếu hoàn theo hoá đơn (S15) chưa mock ở đây
  const store = load();
  const requestId = typeof b.request_id === "string" ? b.request_id : "";
  if (requestId && !UUID_RE.test(requestId)) return beError("HT_REQUEST_ID_INVALID");
  const e = findEntry(store, Number(b.payment_transaction));
  const inQueue = e && e.p.resolution_status;
  const anyTxn = store.orders.some((o) => o.payments.some((x) => x.id === Number(b.payment_transaction)));
  if (!e) return beError(anyTxn ? "HT_TXN_MATCHED" : "HT_TXN_NOT_FOUND");
  if (!inQueue) return beError("HT_TXN_MATCHED");
  const shape = (r: MockRefund) => ({
    id: r.id, sales_invoice: null, payment_transaction: r.txnId, amount: r.amount, is_partial: false, method: "MANUAL_TRANSFER",
    status: r.status, status_label: REFUND_LABEL[r.status], bank_txn_ref: r.bank_txn_ref || "", reason: r.reason,
    created_by: me.id, confirmed_by: null, created_at: isoVN(Date.now()), confirmed_at: null, request_id: r.request_id || null,
  });
  const prev = requestId ? store.txnRefunds.find((x) => x.request_id === requestId) : undefined;
  if (prev) {
    if (prev.txnId !== e.p.id) return beError("HT_REQUEST_ID_USED");
    return { status: 200, body: { ...shape(prev), duplicate: true } }; // cùng request_id → không tạo phiếu thứ hai
  }
  if (e.p.resolution_status === "RESOLVED") return beError("HT_TXN_RESOLVED");
  const amount = Math.round(Number(b.amount) * 100) / 100;
  if (b.amount === null || b.amount === "" || !Number.isFinite(amount) || amount <= 0) return beError("HT_AMOUNT_INVALID");
  if (amount < 1) return beError("HT_AMOUNT_MIN"); // L8 bổ sung tiền: tối thiểu 1đ
  const max = refundableOf(store, e.p);
  if (amount > max) return beError("HT_OVER_REFUNDABLE", { max: vndD(max) }); // S13-AC3
  const r: MockRefund = {
    id: ++store.seq + 100,
    txnId: e.p.id,
    amount: money(amount),
    status: "PENDING",
    bank_txn_ref: "",
    reason: typeof b.reason === "string" ? b.reason : "",
    request_id: requestId,
  };
  store.txnRefunds.push(r);
  save(store);
  return { status: 201, body: shape(r) };
}

export function mockRefundsApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!/^\/api\/sales\/refunds\/create\/?$/.test(req.path)) return beError("NOT_FOUND");
  if (req.method !== "POST") return beError("METHOD_NOT_ALLOWED", { method: req.method });
  if (!has(me, PERM_REFUND)) return beError("DRF_FORBIDDEN");
  return createTxnRefund(me, req.body);
}

function meOf(username: string): Me | null {
  const u = mockUsers().find((x) => x.username === username);
  if (!u) return null;
  return { id: u.id, username: u.username, display_name: u.display_name, groups: u.groups, permissions: mockPermsOf(u) } as unknown as Me;
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    orders: (m: Mode) => {
      window.localStorage.setItem(MODE_KEY, m);
      return `Chế độ mock đơn: ${m}`;
    },
    resetOrders: () => {
      memory = null;
      window.sessionStorage.removeItem(STORE_KEY);
      return "Đã gieo lại đơn mock.";
    },
    orderJson: (username: string, id: number) => {
      const u = mockUsers().find((x) => x.username === username);
      const o = load().orders.find((x) => x.id === id);
      if (!u || !o) return null;
      const perms = mockPermsOf(u);
      const me = { id: u.id, groups: u.groups, permissions: perms } as unknown as Me;
      return detail(me, o);
    },
    payments: (m: QMode) => {
      window.localStorage.setItem(QUEUE_MODE_KEY, m);
      return `Chế độ mock hàng chờ: ${m}`;
    },
    /** S12-AC5: đơn tự huỷ "trong lúc Chủ đang xem" (danh sách cũ vẫn còn nút). */
    expireOrder: (id: number) => {
      const store = load();
      const o = store.orders.find((x) => x.id === id);
      if (!o) return null;
      o.status = "AUTO_CANCELLED";
      save(store);
      return o.status;
    },
    /** Giả lập S16 (chưa có màn): Chủ xác nhận phiếu hoàn đã chuyển → khoản lệch RESOLVED/REFUNDED (S13-AC2). */
    confirmRefund: (refundId: number, ref: string) => {
      const store = load();
      const r = store.txnRefunds.find((x) => x.id === refundId);
      if (!r) return null;
      r.status = "REFUNDED";
      r.bank_txn_ref = ref;
      const e = findEntry(store, r.txnId);
      if (e && e.p.resolution_status === "OPEN") {
        e.p.resolution_status = "RESOLVED";
        e.p.resolution = "REFUNDED";
        e.p.resolved_by = "Lộc";
        e.p.resolved_at = isoVN(Date.now());
        e.p.resolution_note = `Mã GD hoàn ${ref}`;
      }
      save(store);
      return r.status;
    },
    /** E2E: gọi thẳng luật resolve như gọi API (kiểm lớp chặn "BE": S12-AC4/AC6). */
    resolveJson: (username: string, id: number, body: unknown) => {
      const me = meOf(username);
      if (!me) return null;
      if (!me.permissions.includes(PERM_CONFIRM)) return { status: 403 };
      return resolve(me, id, body);
    },
    /** Phiếu hoàn đã lập cho một giao dịch (để e2e lấy id giả lập S16). */
    txnRefundsOf: (txnId: number) => refundsOf(load(), txnId).map((r) => ({ ...r })),
    queueJson: (username: string, status = "OPEN") => {
      const me = meOf(username);
      if (!me) return null;
      return queueList(me, new URLSearchParams({ resolution_status: status })).body;
    },
    refundJson: (username: string, body: unknown) => {
      const me = meOf(username);
      if (!me) return null;
      if (!me.permissions.includes(PERM_REFUND)) return { status: 403 };
      return createTxnRefund(me, body);
    },
    /** E2E: gọi thẳng luật confirm-payment của mock như gọi API (bỏ qua ô FE) — kiểm lớp chặn phía "BE" (B13). */
    confirmJson: (username: string, id: number, body: unknown) => {
      const u = mockUsers().find((x) => x.username === username);
      const o = load().orders.find((x) => x.id === id);
      if (!u || !o) return null;
      const me = { id: u.id, username: u.username, display_name: u.username, groups: u.groups, permissions: mockPermsOf(u) } as unknown as Me;
      return confirm(me, o, body);
    },
  };
}
