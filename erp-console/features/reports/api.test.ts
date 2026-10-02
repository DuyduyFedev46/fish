import { describe, expect, it } from "vitest";
import { toDecimalString } from "./decimal";
import { normalizeBatchRow, normalizePeriodReport } from "./api";
import { batchDetail, periodIsEmpty, profitBreakdown } from "./reportView";

// Payload đúng shape BE thật: DRF đổi Decimal thành float nên tiền và kg là JSON number (TL12-FE-H1).
const WIRE_PERIOD = {
  year: 2026,
  month: 9,
  revenue: 1650000.5,
  cogs: 1000000,
  credit_notes: 0,
  cogs_reversed: 0,
  refunds: 0,
  profit: -250000,
  invoice_count: 3,
  refund_count: 0,
};

const WIRE_BATCH = {
  batch_id: "LO-0926-A",
  provisional: true,
  qty_received: 120,
  qty_sold: 74.5,
  landed_unit_cost: 98500.25,
  revenue: 8940000,
  reversed_qty: 0,
  reversed_revenue: 0,
  purchase_cost: 11400000,
  allocated_cost: 420000,
  shrinkage_qty: 2,
  shrinkage_cost: 197000,
  damage_qty: 0,
  damage_cost: 0,
  expired_qty: 0,
  expired_cost: 0,
  supplier_return_qty: 0,
  supplier_refund_amount: 0,
  total_cost: 11820000,
  profit: -2880000,
  item_name: "Cá thu nguyên con",
  status: "SELLING",
  status_label: "Đang bán",
};

describe("toDecimalString", () => {
  it("chuỗi giữ nguyên, số đổi sang chuỗi thập phân", () => {
    expect(toDecimalString("1650000.00")).toBe("1650000.00");
    expect(toDecimalString(1650000.5)).toBe("1650000.5");
    expect(toDecimalString(0)).toBe("0");
    expect(toDecimalString(-250000)).toBe("-250000");
  });
  it("dạng mũ đổi sang dạng thường để parseDecimal đọc được", () => {
    expect(toDecimalString(1e-7)).toBe("0.000000");
    expect(toDecimalString(1.5e21)).toBe("1500000000000000000000");
    expect(toDecimalString(-1e21)).toBe("-1000000000000000000000");
  });
  it("không đoán: null/undefined giữ nguyên, số vô hạn thành chuỗi rỗng", () => {
    expect(toDecimalString(null)).toBeNull();
    expect(toDecimalString(undefined)).toBeUndefined();
    expect(toDecimalString(Number.NaN)).toBe("");
  });
});

describe("normalizePeriodReport (payload dạng số như BE thật)", () => {
  const period = normalizePeriodReport(WIRE_PERIOD);
  it("mọi field tiền thành chuỗi, field đếm giữ số", () => {
    expect(period.revenue).toBe("1650000.5");
    expect(period.cogs).toBe("1000000");
    expect(period.profit).toBe("-250000");
    expect(typeof period.cogs_reversed).toBe("string");
    expect(period.invoice_count).toBe(3);
  });
  it("đi qua profitBreakdown mà mọi dòng amount là chuỗi và cộng ra đúng profit", () => {
    const rows = profitBreakdown(period);
    expect(rows.every((r) => typeof r.amount === "string")).toBe(true);
    expect(rows.find((r) => r.key === "profit")?.amount).toBe("-250000");
    expect(rows.find((r) => r.key === "cogs_reversed")?.amount).toBe("0");
    expect(() => rows.forEach((r) => r.amount.startsWith("-"))).not.toThrow();
  });
  it("periodIsEmpty đúng với số", () => {
    expect(periodIsEmpty(period)).toBe(false);
    const empty = normalizePeriodReport({ ...WIRE_PERIOD, revenue: 0, cogs: 0, profit: 0, invoice_count: 0 });
    expect(periodIsEmpty(empty)).toBe(true);
  });
  it("payload chuỗi (mock cũ) vẫn qua được", () => {
    expect(normalizePeriodReport({ ...WIRE_PERIOD, revenue: "5.00" }).revenue).toBe("5.00");
  });
});

describe("normalizeBatchRow (payload dạng số như BE thật)", () => {
  const row = { ...normalizeBatchRow(WIRE_BATCH), id: 1 };
  it("tiền và kg thành chuỗi, field chữ giữ nguyên", () => {
    expect(row.qty_sold).toBe("74.5");
    expect(row.landed_unit_cost).toBe("98500.25");
    expect(row.profit).toBe("-2880000");
    expect(row.batch_id).toBe("LO-0926-A");
    expect(row.item_name).toBe("Cá thu nguyên con");
    expect(row.provisional).toBe(true);
  });
  it("batchDetail dùng được và không ném lỗi", () => {
    const detail = batchDetail(row, (v) => `${v} kg`);
    expect(detail.composition.find((l) => l.key === "profit")?.value).toBe("−2.880.000 đ");
    expect(detail.composition.find((l) => l.key === "received")?.value).toBe("120 kg");
  });
});
