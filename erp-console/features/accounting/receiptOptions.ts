// Logic thuần của ô chọn phiếu nhập (ReceiptSelect): nối trang kế không trùng dòng, giữ phiếu đang chọn trong danh sách.
import type { ReceiptRow } from "@/features/purchasing/types";
import { dateOnly } from "@/shared/lib/format";

export type ReceiptOption = { value: string; label: string };

/** "PR-97 · Tên nhà cung cấp · 24/09/2026". */
export function receiptOptionLabel(r: Pick<ReceiptRow, "code" | "supplier_name" | "received_date">): string {
  return `${r.code} · ${r.supplier_name} · ${dateOnly(r.received_date)}`;
}

/** Nối trang kế vào các dòng đã có; phiếu đã có (theo id) không thêm lần hai, thứ tự giữ nguyên. */
export function mergeReceiptPage<T extends { id: number }>(existing: T[] | null, next: T[]): T[] {
  const base = existing ?? [];
  const seen = new Set(base.map((r) => r.id));
  return [...base, ...next.filter((r) => !seen.has(r.id))];
}

/**
 * Các lựa chọn của ô: lựa chọn rỗng, rồi các phiếu đã tải. Phiếu đang chọn (`value`) luôn có mặt dù nằm ngoài các trang đã tải
 * hay bị bộ lọc nhà cung cấp loại ra, để ô chọn không bị trống chữ sau khi đổi bộ lọc.
 */
export function receiptOptions(rows: ReceiptRow[] | null, picked: ReceiptRow | null, value: string, emptyLabel: string): ReceiptOption[] {
  const list = (rows ?? []).map((r) => ({ value: String(r.id), label: receiptOptionLabel(r) }));
  if (picked && value && String(picked.id) === value && !list.some((o) => o.value === value)) {
    list.unshift({ value, label: receiptOptionLabel(picked) });
  }
  return [{ value: "", label: emptyLabel }, ...list];
}
