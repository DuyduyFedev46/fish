import { describe, expect, it } from "vitest";
import { filterPayments } from "./components/PaymentQueueScreen";
import { monthBreakdown } from "./components/RefundQueueScreen";
import { ORDERS_MSG } from "./messages";
import type { PaymentQueueItem, RefundQueueItem } from "./types";

const pay = (id: number, txn: string, code?: string) =>
  ({ id, bank_txn_id: txn, order: code ? { code } : null }) as unknown as PaymentQueueItem;
const refund = (amount: string, status: string) => ({ amount, status }) as unknown as RefundQueueItem;

describe("filterPayments", () => {
  const rows = [pay(1, "FT100", "SO261001-AAAAAA"), pay(2, "FT200"), pay(3, "ZZ300", "SO261001-BBBBBB")];
  it("tìm theo mã giao dịch hoặc mã đơn, không phân biệt hoa thường", () => {
    expect(filterPayments(rows, "ft2").map((r) => r.id)).toEqual([2]);
    expect(filterPayments(rows, "so261001-bbb").map((r) => r.id)).toEqual([3]);
  });
  it("rỗng thì giữ nguyên", () => {
    expect(filterPayments(rows, "  ")).toBe(rows);
  });
});

describe("monthBreakdown (ED-12, TL-M2)", () => {
  it("cộng riêng từng trạng thái, bỏ phiếu Thất bại", () => {
    expect(monthBreakdown([refund("380000", "REFUNDED"), refund("100000", "PENDING"), refund("50000", "FAILED"), refund("20000", "PENDING")])).toEqual({
      parts: [
        { status: "PENDING", count: 2, total: "120000" },
        { status: "REFUNDED", count: 1, total: "380000" },
      ],
      failedCount: 1,
    });
  });
  it("không có phiếu", () => {
    expect(monthBreakdown([])).toEqual({ parts: [], failedCount: 0 });
  });
});

describe("câu tổng theo tháng nói rõ đang cộng gì", () => {
  it("chỉ Chờ hoàn: nêu trạng thái và ghi chú không tính phiếu lỗi", () => {
    const text = ORDERS_MSG.refundsMonthSummary("Tháng 10/2026", [{ status: "PENDING", count: 3, total: "1200000" }], 0);
    expect(text).toBe("Tháng 10/2026: 3 phiếu Chờ hoàn, tổng tiền 1.200.000 đ (không tính phiếu Thất bại)");
  });
  it("hai trạng thái: tách từng số, đếm phiếu Thất bại bị bỏ", () => {
    const text = ORDERS_MSG.refundsMonthSummary(
      "Tháng 10/2026",
      [
        { status: "PENDING", count: 1, total: "100000" },
        { status: "REFUNDED", count: 2, total: "380000" },
      ],
      2
    );
    expect(text).toBe("Tháng 10/2026: 1 phiếu Chờ hoàn, tổng tiền 100.000 đ · 2 phiếu Đã hoàn, tổng tiền 380.000 đ (không tính 2 phiếu Thất bại)");
  });
  it("không có phiếu nào", () => {
    expect(ORDERS_MSG.refundsMonthSummary("Tháng 10/2026", [], 0)).toContain("không có phiếu Chờ hoàn hay Đã hoàn");
  });
});
