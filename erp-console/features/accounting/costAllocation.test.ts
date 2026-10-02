import { describe, expect, it } from "vitest";
import { checkAllocation, splitCost } from "./costAllocation";
import { moneyBody, parseMoney } from "./money";
import type { CostTargetBatch } from "./types";

const lot = (batch: number, qty: string, rate: string): CostTargetBatch => ({ batch, batch_code: `L-${batch}`, item_name: "Cá", qty, rate });

describe("splitCost", () => {
  it("chia theo số kg, tổng đúng từng đồng, dư dồn lô cuối", () => {
    const parts = splitCost(1_000_000, [lot(1, "10", "1000"), lot(2, "10", "1000"), lot(3, "10", "1000")], "BY_QTY");
    expect(parts).toEqual([333_333, 333_333, 333_334]);
    expect(parts.reduce((a, b) => a + b, 0)).toBe(1_000_000);
  });
  it("chia theo giá trị: lô giá cao nhận nhiều hơn", () => {
    const parts = splitCost(1_200_000, [lot(1, "10", "100000"), lot(2, "20", "50000")], "BY_VALUE");
    expect(parts).toEqual([600_000, 600_000]);
    const skew = splitCost(900_000, [lot(1, "10", "30000"), lot(2, "10", "60000")], "BY_VALUE");
    expect(skew).toEqual([300_000, 600_000]);
  });
  it("giá mua bằng 0 ở mọi lô: chia đều, vẫn đủ tổng", () => {
    expect(splitCost(100, [lot(1, "5", "0"), lot(2, "5", "0"), lot(3, "5", "0")], "BY_VALUE")).toEqual([33, 33, 34]);
  });
  it("không lô hoặc tổng không hợp lệ", () => {
    expect(splitCost(100, [], "BY_QTY")).toEqual([]);
    expect(splitCost(0, [lot(1, "5", "1")], "BY_QTY")).toEqual([0]);
    expect(splitCost(Number.NaN, [lot(1, "5", "1")], "BY_QTY")).toEqual([0]);
  });
  it("một lô nhận toàn bộ", () => {
    expect(splitCost(95_000, [lot(1, "12.5", "40000")], "BY_QTY")).toEqual([95_000]);
  });
});

describe("checkAllocation (AC4)", () => {
  it("khớp → ok, không câu báo", () => {
    expect(checkAllocation(1_200_000, [600_000, 600_000])).toEqual({ allocated: 1_200_000, difference: 0, ok: true, message: null });
  });
  it("thiếu 50.000 đ", () => {
    const r = checkAllocation(1_200_000, [600_000, 550_000]);
    expect(r.ok).toBe(false);
    expect(r.difference).toBe(50_000);
    expect(r.message).toBe("Tổng tiền chia phải bằng 1.200.000 đ, còn thiếu 50.000 đ.");
  });
  it("thừa", () => {
    expect(checkAllocation(1_000_000, [600_000, 450_000]).message).toBe("Tổng tiền chia phải bằng 1.000.000 đ, đang thừa 50.000 đ.");
  });
  it("chưa nhập tổng → khoá nhưng không báo đỏ", () => {
    expect(checkAllocation(null, [100]).ok).toBe(false);
    expect(checkAllocation(null, [100]).message).toBeNull();
    expect(checkAllocation(0, [0]).message).toBeNull();
  });
  it("ô trống tính 0", () => {
    expect(checkAllocation(100, [100, null]).ok).toBe(true);
  });
});

describe("parseMoney / moneyBody", () => {
  it("bỏ dấu chấm nhóm, trả số nguyên đồng", () => {
    expect(parseMoney("1.650.000")).toBe(1_650_000);
    expect(parseMoney("81.234")).toBe(81_234);
    expect(moneyBody("1.650.000")).toBe("1650000");
  });
  it("rỗng, chữ, âm, số lẻ → null; moneyBody ném lỗi chứ không đổi thành '0'", () => {
    expect(parseMoney("")).toBeNull();
    expect(parseMoney("abc")).toBeNull();
    expect(parseMoney("-5")).toBeNull();
    expect(parseMoney("1,5")).toBeNull();
    for (const bad of ["", "abc", "-5000", "1,5", "99.999.999.999.999"]) expect(() => moneyBody(bad)).toThrow();
  });
  it("quá 12 chữ số (BE chỉ nhận max_digits 14 với 2 số lẻ) → null", () => {
    expect(parseMoney("999.999.999.999")).toBe(999_999_999_999);
    expect(parseMoney("1.000.000.000.000")).toBeNull();
    expect(parseMoney("12345678901234")).toBeNull();
  });
});

describe("recentMonthOptions", () => {
  it("12 tháng gần nhất, qua đầu năm", async () => {
    const { recentMonthOptions } = await import("./months");
    const opts = recentMonthOptions("2026-02-15", 3);
    expect(opts.map((o) => o.value)).toEqual(["", "2026-02", "2026-01", "2025-12"]);
    expect(opts[3].label).toBe("Tháng 12/2025");
    expect(recentMonthOptions("2026-10-02")).toHaveLength(13);
  });
});
