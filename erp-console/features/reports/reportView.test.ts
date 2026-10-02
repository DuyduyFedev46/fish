import { describe, expect, it } from "vitest";
import { addDecimal, subDecimal } from "./decimal";
import { batchDetail, monthLabel, parseMonthKey, periodIsEmpty, previousMonthKey, profitBreakdown, profitTone, reportMonthOptions, signedVnd } from "./reportView";
import type { BatchReportRow, PeriodReport } from "./types";

const period = (over: Partial<PeriodReport> = {}): PeriodReport => ({
  year: 2026,
  month: 9,
  revenue: "17600000.00",
  cogs: "11750000.00",
  credit_notes: "850000.00",
  cogs_reversed: "560000.00",
  refunds: "250000.00",
  profit: "5600000.00",
  invoice_count: 14,
  refund_count: 1,
  ...over,
});

describe("signedVnd / profitTone", () => {
  it("lỗ hiện dấu trừ thật, lãi và 0 như bình thường", () => {
    expect(signedVnd("-1250000.00")).toBe("−1.250.000 đ");
    expect(signedVnd("5600000.00")).toBe("5.600.000 đ");
    expect(signedVnd("0.00")).toBe("0 đ");
    expect(signedVnd(undefined)).toBe("—");
  });
  it("tông màu theo dấu", () => {
    expect(profitTone("-1")).toBe("neg");
    expect(profitTone("1")).toBe("pos");
    expect(profitTone("0.00")).toBe("zero");
    expect(profitTone("x")).toBe("none");
  });
});

describe("periodIsEmpty (ED-32-AC2)", () => {
  const zero = period({ revenue: "0.00", cogs: "0.00", credit_notes: "0.00", cogs_reversed: "0.00", refunds: "0.00", profit: "0.00", invoice_count: 0, refund_count: 0 });
  it("kỳ toàn số 0 là trống", () => expect(periodIsEmpty(zero)).toBe(true));
  it("có hoá đơn, hoàn tiền hay bất kỳ số tiền nào thì không trống", () => {
    expect(periodIsEmpty({ ...zero, invoice_count: 1 })).toBe(false);
    expect(periodIsEmpty({ ...zero, refund_count: 1 })).toBe(false);
    expect(periodIsEmpty({ ...zero, refunds: "100.00" })).toBe(false);
  });
});

describe("profitBreakdown", () => {
  it("dựng lại số gộp và các dòng cộng ra đúng lãi/lỗ của BE", () => {
    const p = period();
    const rows = profitBreakdown(p);
    const by = Object.fromEntries(rows.map((r) => [r.key, r.amount]));
    expect(by.revenue).toBe("18450000");
    expect(by.credit_notes).toBe("-850000");
    expect(by.cogs).toBe("-12310000");
    expect(by.cogs_reversed).toBe("560000.00");
    expect(by.refunds).toBe("-250000");
    let sum = "0";
    for (const r of rows.filter((x) => x.kind !== "total")) sum = addDecimal(sum, r.amount) ?? sum;
    expect(sum).toBe("5600000");
    expect(subDecimal(sum, p.profit)).toBe("0");
  });
  it("thanh dài nhất là dòng lớn nhất, mọi tỉ lệ trong 0..1", () => {
    const rows = profitBreakdown(period());
    expect(rows.find((r) => r.key === "revenue")?.share).toBe(1);
    for (const r of rows) {
      expect(r.share).toBeGreaterThanOrEqual(0);
      expect(r.share).toBeLessThanOrEqual(1);
    }
  });
});

describe("tháng", () => {
  it("tháng liền trước qua năm", () => {
    expect(previousMonthKey("2026-01")).toBe("2025-12");
    expect(previousMonthKey("2026-09")).toBe("2026-08");
  });
  it("12 tháng gần nhất, mới nhất trước, không có 'Mọi tháng'", () => {
    const o = reportMonthOptions("2026-02-15");
    expect(o).toHaveLength(12);
    expect(o[0]).toEqual({ value: "2026-02", label: "Tháng 2/2026" });
    expect(o[2]).toEqual({ value: "2025-12", label: "Tháng 12/2025" });
    expect(o.some((x) => x.value === "")).toBe(false);
  });
  it("đọc và ghi nhãn", () => {
    expect(parseMonthKey("2026-09")).toEqual({ year: 2026, month: 9 });
    expect(monthLabel("2026-09")).toBe("Tháng 9/2026");
  });
});

describe("batchDetail", () => {
  const row = {
    id: 1, batch_id: "LO-1", provisional: true, item_name: "Cá", status: "SELLING", status_label: "Đang bán",
    qty_received: "120", qty_sold: "74.5", landed_unit_cost: "98500.00", revenue: "8940000.00", reversed_qty: "0", reversed_revenue: "0.00",
    purchase_cost: "11400000.00", allocated_cost: "420000.00", shrinkage_qty: "2", shrinkage_cost: "197000.00", damage_qty: "0", damage_cost: "0.00",
    expired_qty: "0", expired_cost: "0.00", supplier_return_qty: "0", supplier_refund_amount: "0.00", total_cost: "11820000.00", profit: "-2880000.00",
  } as BatchReportRow;
  const kgText = (v: string) => `${v} kg`;
  it("hao hụt, hàng hỏng, quá hạn nằm ở nhóm tham khảo, không lẫn vào cấu thành", () => {
    const d = batchDetail(row, kgText);
    expect(d.composition.map((l) => l.key)).not.toContain("shrinkage");
    expect(d.reference.map((l) => l.key)).toEqual(["shrinkage", "damage", "expired", "supplier_return"]);
  });
  it("lô lỗ ghi dấu trừ; dòng đơn huỷ chỉ hiện khi có", () => {
    const d = batchDetail(row, kgText);
    expect(d.composition.find((l) => l.key === "profit")?.value).toBe("−2.880.000 đ");
    expect(d.composition.some((l) => l.key === "reversed")).toBe(false);
    expect(batchDetail({ ...row, reversed_revenue: "650000.00", reversed_qty: "2" }, kgText).composition.some((l) => l.key === "reversed")).toBe(true);
  });
});
