import { describe, expect, it } from "vitest";
import { parseAmount } from "../../features/orders/amount";
import { MONEY_FRACTION_MESSAGE, editMoneyInput, formatMoneyInput, groupThousands, splitFraction } from "./moneyInput";

/** Mô phỏng người dùng gõ từng ký tự ở cuối ô. */
function typeAll(text: string, start = ""): { value: string; caret: number } {
  let state = { value: start, caret: start.length };
  for (const ch of text) {
    const next = state.value.slice(0, state.caret) + ch + state.value.slice(state.caret);
    state = editMoneyInput(state.value, next, state.caret + 1, "insertText");
  }
  return state;
}

/** Xoá lùi một ký tự trước con trỏ (như phím Backspace) rồi để hàm tính lại. */
function backspace(value: string, caret: number) {
  const next = value.slice(0, caret - 1) + value.slice(caret);
  return editMoneyInput(value, next, caret - 1, "deleteContentBackward");
}

function del(value: string, caret: number) {
  const next = value.slice(0, caret) + value.slice(caret + 1);
  return editMoneyInput(value, next, caret, "deleteContentForward");
}

/** Số thật mà ô sẽ gửi đi. */
const sent = (v: string) => parseAmount(v).value;

describe("groupThousands / formatMoneyInput", () => {
  it("nhóm nghìn kiểu Việt", () => {
    expect(groupThousands("1500000")).toBe("1.500.000");
    expect(groupThousands("999")).toBe("999");
    expect(formatMoneyInput("540000")).toBe("540.000");
    expect(formatMoneyInput("")).toBe("");
  });
});

describe("editMoneyInput: gõ", () => {
  it("gõ 150000 → 150.000, đọc ra 150000", () => {
    const r = typeAll("150000");
    expect(r.value).toBe("150.000");
    expect(r.caret).toBe(7);
    expect(sent(r.value)).toBe("150000");
  });
  it("gõ thêm chữ số làm xuất hiện dấu chấm mới thì con trỏ đi theo", () => {
    expect(editMoneyInput("999", "9999", 4, "insertText")).toEqual({ value: "9.999", caret: 5 });
  });
  it("chèn giữa ô: con trỏ ở sau chữ số vừa chèn", () => {
    expect(editMoneyInput("1.500.000", "19.500.000", 2, "insertText")).toEqual({ value: "19.500.000", caret: 2 });
  });
  it("gõ chữ bị bỏ, giá trị và con trỏ giữ nguyên", () => {
    expect(editMoneyInput("150.000", "150.000a", 8, "insertText")).toEqual({ value: "150.000", caret: 7 });
    expect(editMoneyInput("150.000", "15a0.000", 3, "insertText")).toEqual({ value: "150.000", caret: 2 });
    expect(typeAll("abc").value).toBe("");
  });
  it("bỏ số 0 đứng đầu nhưng giữ một số 0 đơn", () => {
    expect(typeAll("0").value).toBe("0");
    expect(typeAll("05").value).toBe("5");
    expect(typeAll("0005000").value).toBe("5.000");
  });
});

describe("editMoneyInput: Backspace (lỗi B4)", () => {
  it("150.000 + Backspace → 15.000 (không phải 150.00 → 150 đ)", () => {
    const r = backspace("150.000", 7);
    expect(r).toEqual({ value: "15.000", caret: 6 });
    expect(sent(r.value)).toBe("15000");
  });
  it("1.500.000 + Backspace → 150.000 (không phải 1.500 đ)", () => {
    const r = backspace("1.500.000", 9);
    expect(r.value).toBe("150.000");
    expect(sent(r.value)).toBe("150000");
  });
  it("gõ 12345 rồi xoá lùi 2 lần → 123", () => {
    let r = typeAll("12345");
    r = backspace(r.value, r.caret);
    r = backspace(r.value, r.caret);
    expect(r.value).toBe("123");
    expect(sent(r.value)).toBe("123");
  });
  it("xoá lùi qua dấu chấm thì xoá chữ số liền trước, con trỏ không đứng im", () => {
    // "150.000" con trỏ ở sau dấu chấm (4), Backspace xoá dấu chấm → xoá thêm chữ số 0 đứng trước
    expect(backspace("150.000", 4)).toEqual({ value: "15.000", caret: 2 });
  });
  it("xoá lùi giữa ô giữ con trỏ đúng chỗ", () => {
    // "1.234.567", con trỏ sau số 3 (vị trí 4), xoá số 3 → 124.567
    expect(backspace("1.234.567", 4)).toEqual({ value: "124.567", caret: 2 });
  });
  it("xoá lùi hết từng số đến rỗng", () => {
    let r = { value: "12", caret: 2 };
    r = backspace(r.value, r.caret);
    expect(r.value).toBe("1");
    r = backspace(r.value, r.caret);
    expect(r).toEqual({ value: "", caret: 0 });
  });
});

describe("editMoneyInput: Delete (xoá tới)", () => {
  it("Delete ngay trước chữ số xoá chữ số đó", () => {
    expect(del("150.000", 0)).toEqual({ value: "50.000", caret: 0 });
  });
  it("Delete ngay trước dấu chấm xoá chữ số liền sau dấu chấm", () => {
    // "150.000", con trỏ ở vị trí 3 (trước dấu chấm), Delete → xoá chữ số 0 đầu của nhóm sau
    const r = del("150.000", 3);
    expect(r.value).toBe("15.000");
    expect(r.caret).toBe(4);
    expect(sent(r.value)).toBe("15000");
  });
  it("Delete ở cuối ô không làm gì", () => {
    expect(del("150.000", 7)).toEqual({ value: "150.000", caret: 7 });
  });
});

describe("editMoneyInput: dán", () => {
  it("dán 150.000 vào ô trống → 150.000", () => {
    expect(editMoneyInput("", "150.000", 7, "insertFromPaste")).toEqual({ value: "150.000", caret: 7 });
  });
  it("dán 1,500,000 → 1.500.000", () => {
    const r = editMoneyInput("", "1,500,000", 9, "insertFromPaste");
    expect(r.value).toBe("1.500.000");
    expect(sent(r.value)).toBe("1500000");
  });
  it("dán '1,190,000 đ' / '540.000 VND' bỏ phần chữ", () => {
    expect(editMoneyInput("", "1,190,000 đ", 11, "insertFromPaste").value).toBe("1.190.000");
    expect(editMoneyInput("", "540.000 VND", 11, "insertFromPaste").value).toBe("540.000");
  });
  it("dán đè lên một đoạn: con trỏ sau đoạn dán", () => {
    // đang "1.000", bôi đen "000" (vị trí 2..5) rồi dán "250" → "1.250" caret 5
    expect(editMoneyInput("1.000", "1.250", 5, "insertFromPaste")).toEqual({ value: "1.250", caret: 5 });
  });
});

describe("editMoneyInput: biên", () => {
  it("xoá hết (chọn tất cả + Delete) → rỗng", () => {
    expect(editMoneyInput("150.000", "", 0, "deleteContentBackward")).toEqual({ value: "", caret: 0 });
  });
  it("số rất lớn vẫn nhóm đúng, không mất chữ số, và bị báo quá lớn khi đọc", () => {
    const big = "123456789012345678901234567890";
    const r = editMoneyInput("", big, big.length, "insertFromPaste");
    expect(r.value.replace(/\./g, "")).toBe(big);
    expect(r.value.startsWith("123.456.789")).toBe(true);
    expect(parseAmount(r.value).problem).toBe("tooBig");
  });
  it("đúng 12 chữ số là hợp lệ, 13 chữ số quá lớn", () => {
    expect(sent("999.999.999.999")).toBe("999999999999");
    expect(parseAmount("1.000.000.000.000").problem).toBe("tooBig");
  });
  it("dấu trừ không bị bỏ lặng lẽ: giữ nguyên để báo 'không được âm'", () => {
    expect(editMoneyInput("", "-5", 2, "insertText")).toEqual({ value: "-5", caret: 2 });
    expect(parseAmount("-5").problem).toBe("negative");
  });
  it("mọi giá trị ô sinh ra đều đọc lại đúng số chữ số đã gõ (không bao giờ ra phần lẻ)", () => {
    for (const n of ["1", "12", "123", "1234", "12345", "123456", "1234567", "100", "1000", "100000", "1000000"]) {
      const r = typeAll(n);
      expect(sent(r.value)).toBe(n);
      expect(r.value).toMatch(/^\d{1,3}(\.\d{3})*$/);
    }
  });
});

describe("phần lẻ kiểu sao kê: không đoán (02/10)", () => {
  const paste = (prev: string, text: string) => editMoneyInput(prev, text, text.length, "insertFromPaste");

  it("150.000,00 và 150,000.00 (phần lẻ toàn số 0) nhận là 150.000", () => {
    for (const t of ["150.000,00", "150,000.00", "150.000,0", "150.000,00 đ"]) {
      const r = paste("", t);
      expect(r.rejected, t).toBeUndefined();
      expect(r.value, t).toBe("150.000");
      expect(sent(r.value), t).toBe("150000");
    }
  });
  it("150.000,50 và 150,000.50 bị từ chối, giữ nguyên giá trị cũ", () => {
    for (const t of ["150.000,50", "150,000.50", "150.000,5"]) {
      expect(paste("20.000", t)).toEqual({ value: "20.000", caret: 6, rejected: "fraction" });
    }
  });
  it("0.5 và 540,5 bị từ chối (không thành 5 đ / 5.405 đ)", () => {
    expect(paste("", "0.5")).toEqual({ value: "", caret: 0, rejected: "fraction" });
    expect(paste("100.000", "540,5")).toEqual({ value: "100.000", caret: 7, rejected: "fraction" });
  });
  it("1.500.000 đ vẫn là 1.500.000 (nhóm cuối 3 chữ số không phải phần lẻ)", () => {
    const r = paste("", "1.500.000 đ");
    expect(r.rejected).toBeUndefined();
    expect(r.value).toBe("1.500.000");
  });
  it("dán 0.00 thành 0 (báo 'phải lớn hơn 0' ở bước đọc), không bị từ chối", () => {
    expect(paste("", "0.00").value).toBe("0");
  });
  it("Backspace tạm ra dạng '1.500.00' là xoá, không phải phần lẻ: vẫn ra 150.000", () => {
    const r = editMoneyInput("1.500.000", "1.500.00", 8, "deleteContentBackward");
    expect(r.rejected).toBeUndefined();
    expect(r.value).toBe("150.000");
  });
  it("dấu trừ vẫn giữ nguyên", () => {
    expect(paste("", "-150.000,50")).toEqual({ value: "-150.000,50", caret: 11 });
  });
  it("lời nhắn nói cách sửa, có ví dụ", () => {
    expect(MONEY_FRACTION_MESSAGE).toBe("Số tiền là số nguyên đồng, không có phần lẻ. Nhập lại, ví dụ 150.000.");
  });
  it("splitFraction", () => {
    expect(splitFraction("150.000,00").kind).toBe("zero");
    expect(splitFraction("150.000").kind).toBe("none");
    expect(splitFraction("0.5").kind).toBe("nonzero");
    expect(splitFraction("1.000.000 ₫").kind).toBe("none");
  });
});
