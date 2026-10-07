// Đọc lỗi của PUT lưu nhóm (PV-09, PV-10). Logic chỉ dựa vào `status` và `code`, không dựa vào câu `detail`.

import { ApiError } from "@/shared/lib/http";
import type { ScopePreview } from "./types";

/** 409 GROUP_CHANGED: người khác vừa đổi nhóm (Q-8). Mọi 409 của PUT này đều là xung đột phiên bản. */
export function isGroupChanged(err: unknown): boolean {
  return err instanceof ApiError && err.status === 409;
}

/** 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED: trả `impact` (cùng dạng bản xem trước) để mở hộp cảnh báo. Không có `impact` hợp lệ → null. */
export function wideningImpactOf(err: unknown): ScopePreview | null {
  if (!(err instanceof ApiError) || err.status !== 400 || err.code !== "CUSTOMER_DATA_WIDENING_UNCONFIRMED") return null;
  const details = err.details && typeof err.details === "object" ? (err.details as { impact?: unknown }) : null;
  const impact = details?.impact;
  if (!impact || typeof impact !== "object") return null;
  const i = impact as Partial<ScopePreview>;
  return {
    widens_customer_data: true,
    widened: Array.isArray(i.widened) ? i.widened : [],
    affected_members: Array.isArray(i.affected_members) ? i.affected_members : [],
    affected_count: typeof i.affected_count === "number" ? i.affected_count : 0,
    message: typeof i.message === "string" ? i.message : "",
    already_wider_elsewhere: Array.isArray(i.already_wider_elsewhere) ? i.already_wider_elsewhere : [],
    narrowed: Array.isArray(i.narrowed) ? i.narrowed : [],
  };
}
