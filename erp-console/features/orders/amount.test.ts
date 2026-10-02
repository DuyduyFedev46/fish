import { describe, expect, it } from "vitest";
import { digits, formatAmountInput, parseAmount } from "./amount";

describe("parseAmount (F2a/F2c chặn tại ô)", () => {
  it("đọc dấu nghìn kiểu Việt", () => {
    expect(parseAmount("540.000")).toEqual({ value: "540000", problem: null });
    expect(parseAmount("540,000")).toEqual({ value: "540000", problem: null });
  });
  it("âm, 0, chữ, rỗng, quá 12 chữ số", () => {
    expect(parseAmount("-5").problem).toBe("negative");
    expect(parseAmount("0").problem).toBe("zero");
    expect(parseAmount("abc").problem).toBe("notNumber");
    expect(parseAmount("").problem).toBe("missing");
    expect(parseAmount("1234567890123").problem).toBe("tooBig");
  });
  it("digits chỉ giữ chữ số", () => {
    expect(digits("540.000 ")).toBe("540000");
  });
});

describe("formatAmountInput (giá trị ban đầu của ô tiền)", () => {
  it("nhóm nghìn kiểu Việt", () => {
    expect(formatAmountInput("540000")).toBe("540.000");
    expect(formatAmountInput("1500000")).toBe("1.500.000");
    expect(formatAmountInput("999")).toBe("999");
    expect(formatAmountInput("")).toBe("");
  });
  it("kết quả vẫn đọc được thành đúng số", () => {
    expect(parseAmount(formatAmountInput("1500000")).value).toBe("1500000");
  });
  it("giữ dấu trừ để báo lỗi âm", () => {
    expect(formatAmountInput("-5")).toBe("-5");
  });
});

describe("parseAmount chỉ đọc chữ số, phần lẻ không đoán", () => {
  it("phần lẻ toàn số 0 thì bỏ", () => {
    expect(parseAmount("150.000,00").value).toBe("150000");
    expect(parseAmount("150,000.00").value).toBe("150000");
    expect(parseAmount("1.500.000 đ").value).toBe("1500000");
  });
  it("phần lẻ khác 0 báo lỗi, không đoán", () => {
    expect(parseAmount("150.000,50").problem).toBe("fraction");
    expect(parseAmount("150,000.50").problem).toBe("fraction");
    expect(parseAmount("0.5").problem).toBe("fraction");
    expect(parseAmount("540,5").problem).toBe("fraction");
  });
  it("số 0 và rỗng", () => {
    expect(parseAmount("0").problem).toBe("zero");
    expect(parseAmount("0.00").problem).toBe("zero");
    expect(parseAmount(".").problem).toBe("missing");
  });
});
