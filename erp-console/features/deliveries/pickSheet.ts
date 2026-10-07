// CS-16 — phiếu soạn nội bộ (khổ 100x150 mm). Hàm thuần để vitest.
// Phiếu chỉ có mã phiếu, dòng hàng, kg, mã lô, hạn dùng. API chi tiết trả cả tên, SĐT, địa chỉ, người nhận hộ: `toPickSheet`
// chép đúng bốn trường của dòng hàng + mã phiếu + tổng kg, phần còn lại bị bỏ ngay, không vào state hay DOM (bất biến 9, BR-GH-17).
import { PERM } from "@/shared/lib/nav";
import type { DeliveryNoteDetail, DeliveryStatus, PickSheetData } from "./types";

/** Quyền mở phiếu soạn: người in tem hoặc người đóng gói. NV giao có thể đọc chi tiết phiếu của mình nhưng không có hai quyền này. */
export function canOpenPickSheet(permissions: readonly string[]): boolean {
  return permissions.includes(PERM.printLabel) || permissions.includes(PERM.packDeliveryNote);
}

export function toPickSheet(detail: Pick<DeliveryNoteDetail, "code" | "status" | "total_kg" | "lines">): PickSheetData {
  return {
    note_code: detail.code,
    status: detail.status,
    total_kg: detail.total_kg,
    lines: (detail.lines ?? []).map((l) => ({ item_name: l.item_name, batch_id: l.batch_id, expiry_date: l.expiry_date, qty_kg: l.qty_kg })),
  };
}

/** Trạng thái phiếu không nên in phiếu soạn: câu giải thích + mức độ. null = in được (đang Soạn hàng). */
export function pickSheetBlock(status: DeliveryStatus): { kind: "warn" | "error"; text: string } | null {
  if (status === "PREPARING") return null;
  if (status === "CANCELLED") return { kind: "error", text: "Đơn đã huỷ, không soạn, xé tem." };
  if (status === "CONFIRMING") return { kind: "warn", text: "Phiếu chưa xác nhận với khách nên chưa soạn hàng." };
  return { kind: "warn", text: "Phiếu đã qua bước soạn hàng, không cần in phiếu soạn." };
}

export const PICK_SHEET_HREF = (noteId: number) => `/print/pick-sheet/?note=${noteId}`;
