import { describe, expect, it } from "vitest";
import { moneyBody, moneyIssue, moneyMessage } from "./money";

describe("moneyIssue", () => {
  it("phân loại lý do ô tiền không dùng được", () => {
    expect(moneyIssue("")).toBe("empty");
    expect(moneyIssue("  ")).toBe("empty");
    expect(moneyIssue("-5000")).toBe("negative");
    expect(moneyIssue("−5000")).toBe("negative");
    expect(moneyIssue("99.999.999.999.999")).toBe("too_long");
    expect(moneyIssue("1.000.000.000.000")).toBe("too_long");
    expect(moneyIssue("12ab")).toBe("invalid");
    expect(moneyIssue("1,5")).toBe("invalid");
    expect(moneyIssue("0")).toBeNull();
    expect(moneyIssue("999.999.999.999")).toBeNull();
  });
});

describe("moneyMessage", () => {
  it("giá mua: trống là hợp lệ, âm / quá lớn / bằng 0 báo lỗi", () => {
    const rule = { noun: "Giá mua", allowEmpty: true, positive: true };
    expect(moneyMessage("", rule)).toBeNull();
    expect(moneyMessage("80.000", rule)).toBeNull();
    expect(moneyMessage("-5000", rule)).toBe("Giá mua không được âm. Nhập lại, ví dụ 150.000.");
    expect(moneyMessage("99.999.999.999.999", rule)).toContain("quá lớn");
    expect(moneyMessage("0", rule)).toContain("phải lớn hơn 0");
  });
  it("bắt buộc và lớn hơn 0: trống hoặc 0 đều báo 'Nhập … lớn hơn 0.'", () => {
    expect(moneyMessage("", { noun: "Số tiền", positive: true })).toBe("Nhập số tiền lớn hơn 0.");
    expect(moneyMessage("0", { noun: "Số tiền", positive: true })).toBe("Nhập số tiền lớn hơn 0.");
    expect(moneyMessage("1.650.000", { noun: "Số tiền", positive: true })).toBeNull();
  });
  it("cho phép 0 khi không đòi dương", () => {
    expect(moneyMessage("0")).toBeNull();
    expect(moneyMessage("")).toBe("Nhập số tiền.");
  });
});

describe("moneyBody", () => {
  it("giá trị hợp lệ → số nguyên đồng; giá trị lỗi → ném lỗi, không bao giờ '0'", () => {
    expect(moneyBody("1.650.000")).toBe("1650000");
    expect(moneyBody("0")).toBe("0");
    expect(() => moneyBody("-5000")).toThrow();
    expect(() => moneyBody("99.999.999.999.999")).toThrow();
    expect(() => moneyBody("")).toThrow();
  });
});
