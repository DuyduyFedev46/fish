// Hàm thuần của màn Mua hàng (Lô 10): thanh trạng thái phiếu, quyền thao tác, lý do bị chặn, tìm trong danh sách.
// Không React, không gọi API, để vitest kiểm được.
import type { Me } from "@/features/auth/types";
import { ENUMS, enumLabel } from "@/shared/lib/enums";
import { PERM } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { matches } from "@/shared/lib/search";
import type { PathStep } from "@/shared/ui/detail/StatusPath";
import type { ReceiptDetail, ReceiptRow } from "./types";

const PATH_KEYS = ["DRAFT", "SUBMITTED"] as const;

/** Vòng đời phiếu nhập: Nháp → Đã ghi nhận (nhãn lấy từ ENUMS.purchaseReceiptStatus). */
export const RECEIPT_STEPS: PathStep[] = PATH_KEYS.map((key) => ({ key, label: enumLabel(ENUMS.purchaseReceiptStatus, key) }));

/** Phiếu đã huỷ là kết thúc xấu: tô đỏ sau bước Nháp (phiếu huỷ khi còn Nháp thì chưa có bước nào qua). */
export function receiptPathOf(status: string): { current: string; badEnd: { label: string; after: string } | null } {
  if (status === "CANCELLED") return { current: "DRAFT", badEnd: { label: enumLabel(ENUMS.purchaseReceiptStatus, status), after: "DRAFT" } };
  return { current: status, badEnd: null };
}

export type ReceiptAbility = {
  create: boolean;
  /** Ghi nhận phiếu Nháp. */
  submit: boolean;
  /** Có thể có nút Huỷ phiếu (BE còn xét người lập; FE chỉ ẩn nút khi chắc chắn không được). */
  cancel: boolean;
  viewInvoices: boolean;
  addInvoice: boolean;
  /** Xem chi phí phụ, giá mua, thành tiền: chỉ Chủ. */
  viewCost: boolean;
  viewCosts: boolean;
  addCost: boolean;
};

/** Quyền của người xem, suy từ danh sách quyền BE trả (không đoán theo tên nhóm). BE vẫn là lớp chặn thật. */
export function receiptAbility(me: Me): ReceiptAbility {
  const has = (perm: string) => me.permissions.includes(perm);
  const viewCost = me.can_view_cost;
  return {
    create: has(PERM.addPurchaseReceipt),
    submit: has(PERM.changePurchaseReceipt),
    cancel: has(PERM.changePurchaseReceipt),
    viewInvoices: has(PERM.viewPurchaseInvoice),
    addInvoice: has(PERM.addPurchaseInvoice),
    viewCost,
    viewCosts: viewCost && has(PERM.viewPurchaseCost),
    addCost: viewCost && has(PERM.addPurchaseCost),
  };
}

/**
 * Người này có huỷ được phiếu không? BE: người lập phiếu, hoặc có quyền xoá phiếu / thuộc nhóm Chủ hay Quản lý.
 * FE suy từ `created_by` và nhóm để ẩn mục không bao giờ làm được; trường hợp biên vẫn do BE trả lời.
 */
export function canCancelReceipt(me: Me, row: Pick<ReceiptRow, "created_by">): boolean {
  if (!me.permissions.includes(PERM.changePurchaseReceipt)) return false;
  if (row.created_by !== null && row.created_by === me.id) return true;
  if (me.permissions.includes(PERM.deletePurchaseReceipt)) return true;
  return me.groups.some((g) => g === ROLE.owner || g === ROLE.manager);
}

/** Lý do ngắn khi chưa huỷ phiếu được; undefined = làm được. Khớp các luật chặn của BE (BR-MH-07). */
export function cancelBlockReason(row: ReceiptDetail): string | undefined {
  if (row.status === "CANCELLED") return "Phiếu đã huỷ.";
  if (row.invoice) return "Phiếu đã có hoá đơn mua.";
  if (row.costs && row.costs.length > 0) return "Phiếu đã có chi phí mua chia vào lô.";
  const moved = row.lines.find((l) => l.batch_status && l.batch_status !== "DRAFT");
  if (moved) return `Lô ${moved.batch_code ?? ""} đã đổi trạng thái, không còn Nháp.`.replace("  ", " ");
  return undefined;
}

/** Việc tiếp theo của phiếu (phiếu không có next_steps ở guidance, nên suy từ trạng thái). null = không có việc. */
export function nextReceiptStep(row: Pick<ReceiptRow, "status" | "invoice">, ability: Pick<ReceiptAbility, "submit" | "addInvoice">): string | null {
  if (row.status === "DRAFT") return ability.submit ? "Ghi nhận phiếu và nhập lô" : null;
  if (row.status === "SUBMITTED" && !row.invoice) return ability.addInvoice ? "Thêm hoá đơn mua" : null;
  return null;
}

/** Nhãn các việc đã làm của phiếu, suy từ trạng thái. */
export function receiptDoneLabels(row: Pick<ReceiptRow, "status" | "invoice">): string[] {
  const out = ["Lập phiếu"];
  if (row.status === "SUBMITTED") out.push("Ghi nhận phiếu");
  if (row.invoice) out.push("Có hoá đơn mua");
  if (row.status === "CANCELLED") out.push("Huỷ phiếu");
  return out;
}

/** Tìm trong các dòng ĐÃ TẢI (R10 chưa có tham số tìm): mã phiếu, nhà cung cấp, mặt hàng, mã lô; không phân biệt dấu. */
export function filterReceiptRows(rows: ReceiptRow[], q: string): ReceiptRow[] {
  if (!q.trim()) return rows;
  return rows.filter((r) => matches(q, r.code, r.supplier_name, r.items_summary, r.warehouse_name, ...r.batch_codes));
}

/** `?id=` của trang chi tiết: chỉ nhận số nguyên dương; còn lại → null (hiện "Không tìm thấy", không gọi API). */
export function idFromSearch(value: string | null | undefined): number | null {
  if (!value || !/^\d{1,9}$/.test(value)) return null;
  const n = Number(value);
  return n > 0 ? n : null;
}

/** `?receipt=` của form chi phí: như idFromSearch, nhưng rỗng cũng là null (mở form không gắn phiếu). */
export const receiptFromSearch = idFromSearch;

/** Số phiếu và tổng kg của các dòng đang hiện (dòng phiếu đã huỷ vẫn tính vào số phiếu, không tính vào kg). Hàm thuần. */
export function receiptTotals(rows: { total_qty: string; status: string }[]): { count: number; qty: number } {
  const qty = rows.reduce((sum, r) => {
    const n = Number(r.total_qty);
    return r.status === "CANCELLED" || !Number.isFinite(n) ? sum : sum + n;
  }, 0);
  return { count: rows.length, qty };
}
