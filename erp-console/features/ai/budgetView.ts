// Hiển thị hạn mức chi phí AI (Lô bổ sung A #1). Hàm thuần: BE chỉ trả `budget` cho Chủ (quyền ai.manage_ai_policy),
// vai khác nhận null → màn không dựng khối này. FE không tự tính trạng thái, chỉ dịch `status` của BE ra câu.

import { vnd } from "@/shared/lib/format";
import type { AiBudget } from "./types";

export type BudgetView = {
  /** "Đã dùng 0 đ / 200.000 đ". */
  usage: string;
  /** Câu trạng thái; rỗng khi bình thường (không nhắc gì khi chưa cần). */
  note: string;
  /** "ok" không đổi màu; "warning" / "blocked" để màn tô cảnh báo. */
  tone: "ok" | "warning" | "blocked";
};

const NOTES = {
  warning: "Sắp chạm hạn mức tháng này.",
  blocked: "Đã hết hạn mức tháng này, trợ lý trên mây tạm dừng.",
} as const;

/** `null` khi BE không trả budget (vai không phải Chủ) hoặc dữ liệu hỏng → không hiện khối. */
export function budgetView(budget: AiBudget | null | undefined): BudgetView | null {
  if (!budget || !Number.isFinite(budget.spent_vnd) || !Number.isFinite(budget.limit_vnd)) return null;
  const tone = budget.status === "warning" || budget.status === "blocked" ? budget.status : "ok";
  return {
    usage: `Đã dùng ${vnd(budget.spent_vnd)} / ${vnd(budget.limit_vnd)}`,
    note: tone === "ok" ? "" : NOTES[tone],
    tone,
  };
}
