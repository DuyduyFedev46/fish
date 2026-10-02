import { describe, expect, it } from "vitest";
import { QTY_MESSAGE, buildReceiveLines, firstErrorKey, normalizeQty, qtyMessage, rateMessage, validateReceiveForm } from "./receiveValidation";

const line = (patch: Partial<{ item_code: string; qty: string; rate: string; shelf_life_days: number | null }> = {}) => ({ item_code: "CA-THU", qty: "10", rate: "80.000", shelf_life_days: null, ...patch });

describe("qtyMessage (ED-20-AC3)", () => {
  it("0, âm, trống, chữ đều báo 'Nhập số kg lớn hơn 0.'", () => {
    for (const bad of ["", "0", "0,0", "-3", "abc", "1e3", "12abc", " "]) expect(qtyMessage(bad)).toBe(QTY_MESSAGE);
  });
  it("hợp lệ: số nguyên, dấu phẩy hoặc chấm, tối đa 3 số lẻ", () => {
    for (const ok of ["1", "12,5", "12.5", "0,001", "999999999"]) expect(qtyMessage(ok)).toBeNull();
  });
  it("quá lớn hoặc quá 3 số lẻ thì báo, không cắt lặng lẽ", () => {
    expect(qtyMessage("1000000000")).toContain("quá lớn");
    expect(qtyMessage("1,2345")).toContain("3 chữ số lẻ");
  });
  it("normalizeQty: sai dạng → null", () => {
    expect(normalizeQty("12,5")).toBe("12.5");
    expect(normalizeQty("-1")).toBeNull();
  });
});

describe("rateMessage (QA Lô 10 B5)", () => {
  it("Lô bổ sung A #22: bắt buộc và lớn hơn 0; trống, bằng 0, âm, quá lớn báo lỗi", () => {
    expect(rateMessage("")).toBe("Nhập giá mua lớn hơn 0.");
    expect(rateMessage("   ")).toBe("Nhập giá mua lớn hơn 0.");
    expect(rateMessage("80.000")).toBeNull();
    expect(rateMessage("-5000")).toContain("không được âm");
    expect(rateMessage("99.999.999.999.999")).toContain("quá lớn");
    expect(rateMessage("0")).toBe("Nhập giá mua lớn hơn 0.");
  });
  it("giới hạn 10 chữ số (QA Lô 10 N1): 9.999.999.999 được, 10.000.000.000 và 999.999.999.999 báo lỗi, không gửi", () => {
    expect(rateMessage("9.999.999.999")).toBeNull();
    expect(rateMessage("10.000.000.000")).toBe("Giá mua quá lớn, tối đa 10 chữ số (9.999.999.999).");
    expect(rateMessage("999.999.999.999")).toContain("tối đa 10 chữ số");
    expect(buildReceiveLines([line({ rate: "9.999.999.999" })])[0].rate).toBe("9999999999");
    expect(() => buildReceiveLines([line({ rate: "10.000.000.000" })])).toThrow();
    expect(validateReceiveForm({ supplierId: 1, lines: [line({ rate: "999.999.999.999" })] })).toHaveProperty("rate-0");
  });
});

describe("validateReceiveForm", () => {
  it("giá mua trống hoặc 0 → lỗi đúng ô rate của dòng đó", () => {
    const errors = validateReceiveForm({ supplierId: 1, lines: [line(), line({ rate: "" }), line({ rate: "0" })] });
    expect(Object.keys(errors).sort()).toEqual(["rate-1", "rate-2"]);
  });
  it("hợp lệ → rỗng", () => {
    expect(validateReceiveForm({ supplierId: 1, lines: [line(), line({ rate: "80.000" })] })).toEqual({});
  });
  it("lỗi nằm đúng khoá của ô, các dòng khác không bị đụng", () => {
    const errors = validateReceiveForm({ supplierId: "", lines: [line(), line({ item_code: "", qty: "0", rate: "-5000" })] });
    expect(Object.keys(errors).sort()).toEqual(["item-1", "qty-1", "rate-1", "supplier"]);
    expect(errors["qty-1"]).toBe(QTY_MESSAGE);
  });
  it("firstErrorKey theo thứ tự trên màn hình", () => {
    expect(firstErrorKey({ "qty-1": "x", "rate-0": "y" }, 2)).toBe("rate-0");
    expect(firstErrorKey({ supplier: "x", "qty-0": "y" }, 1)).toBe("supplier");
    expect(firstErrorKey({}, 3)).toBeNull();
  });
});

describe("buildReceiveLines", () => {
  it("giá đúng số nguyên đồng, không còn gửi '0.00'", () => {
    const [a, b] = buildReceiveLines([line({ qty: "12,5" }), line({ rate: "80.000", shelf_life_days: 3 })]);
    expect(a).toEqual({ item_code: "CA-THU", qty: "12.5", rate: "80000", shelf_life_days: null });
    expect(b.rate).toBe("80000");
    expect(b.shelf_life_days).toBe(3);
  });
  it("giá âm / quá lớn / số kg lỗi: ném lỗi, không bao giờ gửi '0'", () => {
    expect(() => buildReceiveLines([line({ rate: "" })])).toThrow();
    expect(() => buildReceiveLines([line({ rate: "-5000" })])).toThrow();
    expect(() => buildReceiveLines([line({ rate: "99.999.999.999.999" })])).toThrow();
    expect(() => buildReceiveLines([line({ qty: "0" })])).toThrow();
  });
});
