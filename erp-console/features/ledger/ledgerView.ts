// Hàm thuần của Sổ nhập xuất (Lô 7, ED-29). Không React, không gọi API.
import { kg } from "@/shared/lib/format";
import { matches } from "@/shared/lib/search";
import type { LedgerEntry } from "./types";

/** "+14,2 kg" khi nhập, "-3,5 kg" khi xuất (dấu rõ ràng để đọc nhanh cột Thay đổi). */
export function signedKg(value: string | number | null | undefined): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n > 0 ? `+${kg(n)}` : kg(n);
}

/** Dòng do hệ thống tự ghi (bán hàng, chuyển trạng thái) không có người làm → "Hệ thống". */
export function actorOf(row: Pick<LedgerEntry, "created_by_name">): string {
  return row.created_by_name?.trim() || "Hệ thống";
}

/** Tìm trong các dòng ĐÃ TẢI: mã lô, mặt hàng, chứng từ, loại, kho, người làm; không phân biệt dấu. */
export function filterLedgerRows(rows: LedgerEntry[], q: string): LedgerEntry[] {
  if (!q.trim()) return rows;
  return rows.filter((r) => matches(q, r.batch_code, r.item_name, r.reference_display, r.type_label, r.warehouse_name, r.created_by_name));
}

/** `?batch=` của Sổ nhập xuất (link từ chi tiết lô): chỉ nhận số nguyên dương, còn lại → "". */
export function batchFromSearch(search: string): string {
  const v = new URLSearchParams(search).get("batch") || "";
  return /^\d{1,9}$/.test(v) && Number(v) > 0 ? v : "";
}

/** Khoảng ngày sai thứ tự (từ > đến) thì không gọi API, báo lỗi tại chỗ. */
export function badDateRange(from: string, to: string): boolean {
  return !!from && !!to && from > to;
}
