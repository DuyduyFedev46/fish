import { describe, expect, it } from "vitest";
import { absDecimal, addDecimal, formatDecimal, parseDecimal, ratioOf, roundToDong, signOf, subDecimal } from "./decimal";

describe("decimal (số thập phân dạng chuỗi)", () => {
  it("đọc và ghi lại đúng, bỏ số 0 thừa", () => {
    expect(formatDecimal(parseDecimal("1650000.50")!)).toBe("1650000.5");
    expect(formatDecimal(parseDecimal("-0.25")!)).toBe("-0.25");
    expect(formatDecimal(parseDecimal("7.000")!)).toBe("7");
    expect(parseDecimal("")).toBeNull();
    expect(parseDecimal("abc")).toBeNull();
    expect(parseDecimal("1e5")).toBeNull();
  });

  it("cộng trừ không lệch như số thực", () => {
    expect(addDecimal("0.1", "0.2")).toBe("0.3");
    expect(subDecimal("1000000.10", "0.20")).toBe("999999.9");
    expect(subDecimal("100", "250")).toBe("-150");
    expect(addDecimal("12", "x")).toBeNull();
  });

  it("số lớn vượt 2^53 vẫn chính xác", () => {
    expect(addDecimal("9007199254740993", "1")).toBe("9007199254740994");
  });

  it("làm tròn đồng: .5 lên, dưới .5 xuống, âm đối xứng", () => {
    expect(roundToDong("1650000.50")).toBe("1650001");
    expect(roundToDong("1650000.49")).toBe("1650000");
    expect(roundToDong("2.5")).toBe("3");
    expect(roundToDong("-2.5")).toBe("-3");
    expect(roundToDong("-0.4")).toBe("0");
    expect(roundToDong("540000")).toBe("540000");
    expect(roundToDong("")).toBe("");
  });

  it("dấu và giá trị tuyệt đối", () => {
    expect(signOf("-1")).toBe(-1);
    expect(signOf("0.00")).toBe(0);
    expect(signOf("3")).toBe(1);
    expect(signOf("x")).toBeNull();
    expect(absDecimal("-250000.5")).toBe("250000.5");
  });

  it("tỉ lệ để vẽ thanh nằm trong 0..1", () => {
    expect(ratioOf("50", "200")).toBe(0.25);
    expect(ratioOf("-50", "200")).toBe(0.25);
    expect(ratioOf("500", "200")).toBe(1);
    expect(ratioOf("5", "0")).toBe(0);
  });
});
