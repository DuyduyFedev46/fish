// Hàm thuần của màn Kho & lô (Lô 7): thanh trạng thái, quyền thao tác, lý do bị chặn, đọc số kg, tìm trong danh sách.
// Không React, không gọi API, để vitest kiểm được.
import type { Me } from "@/features/auth/types";
import { ENUMS, enumLabel } from "@/shared/lib/enums";
import { kg } from "@/shared/lib/format";
import { PERM } from "@/shared/lib/nav";
import { matches } from "@/shared/lib/search";
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import type { BatchApiRow } from "./types";

const PATH_KEYS = ["DRAFT", "SELLING", "NEAR_EXPIRY", "SOLD_OUT", "CLOSED"] as const;

/** Các bước vòng đời của lô: Nháp → Đang bán → Cận hạn → Hết hàng → Đã chốt (nhãn lấy từ ENUMS.batchStatus). */
export const BATCH_STEPS: PathStep[] = PATH_KEYS.map((key) => ({ key, label: enumLabel(ENUMS.batchStatus, key) }));

/** Quá hạn / Đã huỷ là kết thúc xấu: tô đỏ sau bước Cận hạn; còn lại tô đúng bước hiện tại. */
export function pathOf(status: string): { current: string; badEnd: { label: string; after: string } | null } {
  if (status === "EXPIRED" || status === "CANCELLED") {
    return { current: "NEAR_EXPIRY", badEnd: { label: enumLabel(ENUMS.batchStatus, status), after: "NEAR_EXPIRY" } };
  }
  return { current: status, badEnd: null };
}

export type BatchAbility = {
  publish: boolean;
  close: boolean;
  cancelExpired: boolean;
  returnToSupplier: boolean;
  viewCost: boolean;
  viewProfit: boolean;
  viewLedger: boolean;
  viewOrders: boolean;
};

/** Quyền của người đang xem trên một lô, suy từ danh sách quyền BE trả (không đoán theo tên nhóm). BE vẫn là lớp chặn thật. */
export function batchAbility(me: Me): BatchAbility {
  const has = (perm: string) => me.permissions.includes(perm);
  const owner = has(PERM.cancelExpiredBatch);
  return {
    publish: has(PERM.publishBatch),
    close: has(PERM.closeBatch),
    cancelExpired: owner,
    returnToSupplier: owner,
    viewCost: me.can_view_cost,
    viewProfit: me.can_view_profit || has(PERM.viewProfitReport),
    viewLedger: has(PERM.viewLedger),
    viewOrders: has(PERM.viewSalesOrder),
  };
}

const num = (value: string | number | null | undefined): number => {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
};

export const qtyAvailable = (row: Pick<BatchApiRow, "qty_available">): number => num(row.qty_available);
export const qtyReserved = (row: Pick<BatchApiRow, "qty_reserved">): number => num(row.qty_reserved);

/** Lý do ngắn khi chưa trả nhà cung cấp / huỷ phần tồn được; undefined = làm được. */
export function expiredBlockReason(row: Pick<BatchApiRow, "status" | "qty_available" | "qty_reserved">): string | undefined {
  if (row.status === "CLOSED") return "Lô đã chốt.";
  if (row.status !== "EXPIRED") return "Lô chưa quá hạn.";
  if (qtyAvailable(row) <= 0) return "Lô không còn tồn.";
  if (qtyReserved(row) > 0) return `Còn ${kg(qtyReserved(row))} đang giữ chỗ.`;
  return undefined;
}

/** Bỏ mã nghiệp vụ (BR-LO-04…) khỏi câu lý do của máy chủ trước khi hiện cho người dùng. */
export function stripRuleCodes(text: string): string {
  return text
    .replace(/\(?\bBR-[A-Z]{2,4}-\d{1,3}\b\)?/g, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([.,;:])/g, "$1")
    .trim();
}

/** Lý do chưa chốt lô được; `serverReason` = câu lý do của khối "Tiếp theo" (vd thiếu hoá đơn mua). */
export function closeBlockReason(row: Pick<BatchApiRow, "status" | "qty_available">, serverReason?: string): string | undefined {
  if (row.status === "CLOSED") return "Lô đã chốt.";
  if (row.status === "CANCELLED") return "Lô đã huỷ.";
  if (qtyAvailable(row) > 0) return `Lô còn ${kg(qtyAvailable(row))}.`;
  const text = serverReason ? stripRuleCodes(serverReason) : "";
  return text || undefined;
}

/** Lý do lấy từ `missing` của một bước guidance, bỏ mục "thiếu quyền" (người không có quyền thì không thấy mục). */
export function stepReason(step: { missing: { code: string; text: string }[] } | undefined): string | undefined {
  const miss = step?.missing.find((m) => m.code !== "BR-PQ-12");
  return miss ? stripRuleCodes(miss.text) : undefined;
}

/** Thiếu quyền theo guidance (BR-PQ-12) → ẩn hẳn mục, không hiện mục bị khoá. */
export function stepLacksPermission(step: { missing: { code: string }[] } | undefined): boolean {
  return !!step?.missing.some((m) => m.code === "BR-PQ-12");
}

/** Tìm trong các dòng ĐÃ TẢI (R5 chưa có tham số tìm): mã lô, mặt hàng, nhà cung cấp, kho; không phân biệt dấu. */
export function filterBatchRows(rows: BatchApiRow[], q: string): BatchApiRow[] {
  if (!q.trim()) return rows;
  return rows.filter((r) => matches(q, r.batch_id, r.item_name, r.item_code, r.supplier_name, r.warehouse_name));
}

/** `?status=` hợp lệ (có trong ENUMS.batchStatus) hoặc "". */
export function statusFromSearch(search: string): string {
  const v = new URLSearchParams(search).get("status") || "";
  return Object.prototype.hasOwnProperty.call(ENUMS.batchStatus, v) ? v : "";
}

/** `?id=` của trang chi tiết: chỉ nhận số nguyên dương; còn lại → null (hiện "Không tìm thấy", không gọi API). */
export function idFromSearch(value: string | null | undefined): number | null {
  if (!value || !/^\d{1,9}$/.test(value)) return null;
  const n = Number(value);
  return n > 0 ? n : null;
}

/** "3,5" / "3.5" → 3.5; chữ hay quá 3 số lẻ → null. */
export function parseKgInput(text: string): number | null {
  const t = text.trim().replace(",", ".");
  if (!/^\d+(\.\d{1,3})?$/.test(t)) return null;
  return Number(t);
}

/** Số kg đưa lại vào ô nhập ("18.5" → "18,5"). */
export function kgToInput(n: number): string {
  return String(n).replace(".", ",");
}

/** UUID v4 cho `request_id`: sinh MỘT LẦN khi mở form F1g, gửi lại cùng mã thì máy chủ trả bản ghi cũ. */
export function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** Ghi chú trả hàng không được có dãy từ 8 chữ số liền nhau (tránh lộ số điện thoại). */
export const NOTE_HAS_LONG_DIGITS = /\d{8,}/;

/** Nhãn ngắn của việc đã làm trên lô (cho "Đã làm" của thanh trạng thái); loại việc lạ → bỏ qua. */
const DONE_LABEL: Record<string, string> = {
  batch_created: "Nhập lô",
  published: "Mở bán",
  stocktake: "Kiểm kê",
  write_off: "Huỷ phần tồn",
  supplier_return: "Trả nhà cung cấp",
  restock: "Hàng hoàn tái nhập",
  expired: "Quá hạn",
  closed: "Chốt lô",
};

export function doneLabels(timeline: { kind: string; at: string }[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const e of [...timeline].sort((a, b) => Date.parse(a.at) - Date.parse(b.at))) {
    const label = DONE_LABEL[e.kind];
    if (label && !seen.has(label)) {
      seen.add(label);
      out.push(label);
    }
  }
  return out;
}

/**
 * Lỗi do SỐ LIỆU trên màn đã cũ (trạng thái hay tồn đổi) thì mời "Tải lại tồn"; lỗi do người dùng nhập sai thì không.
 * BE dùng chung mã BR-MH-08 cho cả "vượt tồn" (cũ thật) lẫn mã yêu cầu trùng, tiền hoàn, ghi chú (nhập sai), nên với
 * mã đó chỉ coi là cũ khi câu báo là vượt tồn. BR-LO-07 "Số kg xác nhận không hợp lệ" là lỗi dữ liệu gửi, không phải cũ.
 */
export function isLotStateError(code: string | undefined): boolean {
  return code === "BR-MH-05" || code === "BR-LO-03" || code === "BR-LO-04" || code === "BR-LO-05" || code === "BR-KK-05";
}

export function isStaleLotError(code: string | undefined, message: string): boolean {
  // Trạng thái lô đã đổi ở nơi khác (BE services.py): Mở bán (BR-MH-05: không còn Nháp), Huỷ phần tồn (BR-LO-03: không
  // còn Quá hạn), Trả nhà cung cấp / Huỷ (BR-LO-05: đã chốt), Chốt lô (BR-LO-04: còn tồn/giữ chỗ/đơn mở/phiếu hoàn/chưa có
  // hoá đơn mua; BR-KK-05: chưa kiểm kê duyệt). Gửi lại không đổi được kết quả, chỉ tải lại mới thấy trạng thái thật.
  if (isLotStateError(code)) return true;
  if (code === "BR-LO-07") return !/không hợp lệ/i.test(message);
  if (code === "BR-MH-08") return /vượt tồn/i.test(message);
  return false;
}
