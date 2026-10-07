import type { DeliveryLine } from "@/features/deliveries/types";

// Kiểu dữ liệu module Hàng hoàn (ED-26) — theo contract BE Lô 9 (R9): backend/apps/inventory/returns/serializers.py.
// Chỉ có số kg, không có tiền hay giá vốn. `note` là chữ tự do (có thể chứa dữ liệu cá nhân): chỉ hiện ở màn này.

/** CANCELLED: phiếu bị huỷ khi còn Chờ duyệt (Duy chốt 02/10, #8); số kg của phiếu huỷ không còn tính vào số đã hoàn. */
export type ReturnStatus = "DRAFT" | "APPROVED" | "CANCELLED";
export type ReturnDecision = "PENDING" | "RESTOCK" | "WRITE_OFF";
/** Hai quyết định duyệt gửi lên BE. */
export type ApproveDecision = "RESTOCK" | "WRITE_OFF";

export type ReturnItem = {
  id: number;
  /** "RT-<id>" */
  code: string;
  delivery_note: number;
  delivery_note_code: string | null;
  order_code: string | null;
  /** Id lô (khoá chính). */
  batch: number;
  batch_code: string;
  item_name: string;
  /** Số kg, chuỗi thập phân. */
  qty: string;
  /** Giờ rời kho = lần phiếu giao chuyển sang Đang giao gần nhất; null nếu không có mốc. */
  left_warehouse_at: string | null;
  returned_at: string | null;
  /** Số phút hàng ở ngoài kho lạnh; null khi thiếu một trong hai mốc. */
  outside_minutes: number | null;
  decision: ReturnDecision;
  decision_label: string;
  status: ReturnStatus;
  status_label: string;
  created_by: number | null;
  created_by_name: string;
  approved_by: number | null;
  approved_by_name: string;
  created_at: string;
  note: string;
  /** Việc người xem được làm trên phiếu (BE #8): tập con của "approve" | "cancel" | "delete". `delete` chỉ khi là Chủ và phiếu Chờ duyệt hoặc Đã huỷ. */
  available_actions?: string[];
};

export type ReturnListParams = { status: string; month: string };

/** Thân POST /api/inventory/returns/. `qty` là chuỗi thập phân dấu chấm. */
export type CreateReturnBody = { delivery_note: number; batch: number; qty: string; note?: string };

/** Số liệu BE kèm theo lỗi RETURN_QTY_EXCEEDS (chuỗi thập phân). */
export type QtyExceedsExtras = { delivered_qty: string; already_returned_qty: string };

/**
 * Dòng hàng của phiếu giao kèm hai khoá BE Lô 9 (GET /api/delivery/notes/<id>/): `batch_pk` = id lô để gửi POST (người giao không có quyền xem lô),
 * `returned_qty` = kg đã hoàn của lô đó trên phiếu này (Chờ duyệt + Đã duyệt; mọi dòng cùng lô mang cùng tổng). Thiếu khoá → coi là chưa biết.
 */
export type ReturnableLine = DeliveryLine & { batch_pk?: number; returned_qty?: string };

/** Một lô trên phiếu giao (gộp các dòng cùng lô) để chọn ở hộp F2m. */
/** `returned` = kg đã hoàn (null khi BE chưa trả `returned_qty`). */
export type BatchChoice = { key: string; label: string; delivered: number; returned: number | null; line: ReturnableLine };
