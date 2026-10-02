import { describe, expect, it } from "vitest";
import { stripRuleCodes } from "./ruleCodes";

describe("stripRuleCodes", () => {
  it("bỏ mã luật trong ngoặc ở cuối câu (QA Lô 10 N2)", () => {
    expect(stripRuleCodes("Phiếu nhập đã bị huỷ (BR-MH-07)")).toBe("Phiếu nhập đã bị huỷ");
    expect(stripRuleCodes("Phiếu nhập đã bị huỷ (BR-MH-07).")).toBe("Phiếu nhập đã bị huỷ.");
    expect(stripRuleCodes("Không thể huỷ phiếu nhập đã gắn hoá đơn mua. (BR-MH-07)")).toBe("Không thể huỷ phiếu nhập đã gắn hoá đơn mua.");
  });
  it("bỏ nhiều mã trong một cặp ngoặc", () => {
    expect(stripRuleCodes("Chứng từ không được xoá (BR-MH-07, BR-PQ-10).")).toBe("Chứng từ không được xoá.");
  });
  it("bỏ mã trần giữa câu và dọn khoảng trắng", () => {
    expect(stripRuleCodes("Lô đã bị huỷ BR-LO-03 nên không nhận thêm.")).toBe("Lô đã bị huỷ nên không nhận thêm.");
  });
  it("câu không có mã giữ nguyên, kể cả chữ có gạch nối và ngoặc thường", () => {
    for (const s of ["Giá mua quá lớn, tối đa 10 chữ số (9.999.999.999).", "Lô L0921-CT02 hết hạn.", "Chọn mặt hàng (bắt buộc)."]) expect(stripRuleCodes(s)).toBe(s);
  });
  it("không đụng ngoặc có chữ khác ngoài mã", () => {
    expect(stripRuleCodes("Xem hướng dẫn (mục BR-MH-07 ở tài liệu).")).toBe("Xem hướng dẫn (mục ở tài liệu).");
  });
});
