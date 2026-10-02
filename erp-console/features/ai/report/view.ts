// Phần THUẦN của "Báo cáo AI cuối ngày" (ED-42 / W4d): cộng số, đổi ngày, nhãn chứng từ.

import { dateKeyInVietnam } from "@/shared/lib/format";
import type { AiDailyReport, AiDailyReportUserStat } from "../types";

export type ReportTotals = { A: number; B: number; C_confirmed: number; C_expired: number; undone: number; escalated: number };

export function totalsOf(rows: readonly AiDailyReportUserStat[]): ReportTotals {
  return rows.reduce<ReportTotals>(
    (acc, u) => ({
      A: acc.A + u.A,
      B: acc.B + u.B,
      C_confirmed: acc.C_confirmed + u.C_confirmed,
      C_expired: acc.C_expired + u.C_expired,
      undone: acc.undone + u.undone,
      escalated: acc.escalated + u.escalated,
    }),
    { A: 0, B: 0, C_confirmed: 0, C_expired: 0, undone: 0, escalated: 0 },
  );
}

/**
 * Tổng việc AI trong ngày = số dòng của nhật ký (BE trả đủ mọi việc trong ngày, không phân trang).
 * KHÔNG cộng sáu cột: việc mức B bị hoàn tác nằm ở cả cột B lẫn cột "Đã hoàn tác" nên cộng cột sẽ đếm đôi.
 */
export function dayTotal(report: Pick<AiDailyReport, "items">): number {
  return report.items.length;
}

/** Dời ngày "YYYY-MM-DD" theo số ngày (tính trên lịch, không phụ thuộc múi giờ máy). Sai định dạng → trả nguyên. */
export function shiftDay(dateKey: string, delta: number): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateKey);
  if (!m) return dateKey;
  // Lấy 12:00 UTC (19:00 giờ VN) để đổi ngược sang ngày VN không bao giờ lệch ngày.
  return dateKeyInVietnam(new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]) + delta, 12)));
}

/** Được xem ngày sau? Không được vượt quá hôm nay (chưa có báo cáo của tương lai). */
export function canGoNext(dateKey: string, today: string): boolean {
  return dateKey < today;
}

/** Ngày hợp lệ để hỏi BE: đúng dạng và không ở tương lai. */
export function clampDay(dateKey: string, today: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey)) return today;
  return dateKey > today ? today : dateKey;
}

const TARGET_LABEL: Record<string, string> = {
  purchasereceipt: "Phiếu nhập",
  batch: "Lô",
  salesorder: "Đơn bán",
  refund: "Phiếu hoàn",
  returntostock: "Phiếu hoàn về kho",
  stockreconciliation: "Phiếu kiểm kê",
  product: "Mặt hàng",
  customer: "Khách hàng",
};

/** Loại chứng từ AI đụng tới, bằng tiếng Việt; loại lạ thì nói chung là "Chứng từ" (không lộ tên kỹ thuật). */
export function targetTypeLabel(type: string): string {
  return TARGET_LABEL[type.toLowerCase()] ?? "Chứng từ";
}
