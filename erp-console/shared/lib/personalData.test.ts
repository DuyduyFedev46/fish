import { describe, it, expect } from "vitest";
import { MSG } from "./messages";
import { hasLimitedCourierScope, personalText } from "./personalData";
import { ROLE } from "./roles";

// SR-PII-02: BE trả `null` khi dữ liệu khách bị ẩn theo thời hạn; chuỗi rỗng là "chưa có" thật.
describe("personalText", () => {
  it("null -> chữ thống nhất 'Đã ẩn (quá 7 ngày)'", () => {
    expect(personalText(null)).toBe("Đã ẩn (quá 7 ngày)");
  });
  it("chuỗi rỗng -> chữ thay thế cũ, KHÔNG phải 'đã ẩn'", () => {
    expect(personalText("", "Chưa có địa chỉ")).toBe("Chưa có địa chỉ");
    expect(personalText("")).toBe("—");
  });
  it("undefined (BE không trả khoá) coi như rỗng, không phải đã ẩn", () => {
    expect(personalText(undefined, "—")).toBe("—");
  });
  it("có giá trị -> giữ nguyên", () => {
    expect(personalText("Khách Thử A")).toBe("Khách Thử A");
  });
});

// Đảo của BE `has_full_delivery_scope`: có nv_giao mà không có chủ/quản lý/NV kho.
describe("hasLimitedCourierScope", () => {
  const g = (...groups: string[]) => ({ groups });
  it("chỉ nv_giao, hoặc cskh + nv_giao -> phạm vi hạn chế", () => {
    expect(hasLimitedCourierScope(g(ROLE.deliveryStaff))).toBe(true);
    expect(hasLimitedCourierScope(g(ROLE.customerService, ROLE.deliveryStaff))).toBe(true);
  });
  it("kèm chủ / quản lý / NV kho -> đủ phạm vi", () => {
    expect(hasLimitedCourierScope(g(ROLE.warehouseStaff, ROLE.deliveryStaff))).toBe(false);
    expect(hasLimitedCourierScope(g(ROLE.manager, ROLE.deliveryStaff))).toBe(false);
    expect(hasLimitedCourierScope(g(ROLE.owner, ROLE.deliveryStaff))).toBe(false);
  });
  it("không có nv_giao -> không hạn chế", () => {
    expect(hasLimitedCourierScope(g(ROLE.customerService))).toBe(false);
    expect(hasLimitedCourierScope(g())).toBe(false);
  });
});

// §2.7: chữ ô khách theo lý do che (customer_hidden_reason).
describe("personalText theo lý do che", () => {
  it("null + not_permitted → không có quyền xem thông tin khách", () => {
    expect(personalText(null, "—", "not_permitted")).toBe("Đã ẩn (không có quyền xem thông tin khách)");
    expect(personalText(null, "—", "not_permitted")).toBe(MSG.personalDataNotPermitted);
  });
  it("null + expired → quá 7 ngày", () => {
    expect(personalText(null, "—", "expired")).toBe("Đã ẩn (quá 7 ngày)");
  });
  it("null không kèm lý do (phiếu giao, khách, gọi xác nhận) → quá 7 ngày", () => {
    expect(personalText(null)).toBe("Đã ẩn (quá 7 ngày)");
    expect(personalText(null, "—", null)).toBe("Đã ẩn (quá 7 ngày)");
  });
  it("có giá trị hoặc rỗng → lý do không đổi chữ", () => {
    expect(personalText("Khách giả", "—", "not_permitted")).toBe("Khách giả");
    expect(personalText("", "—", "not_permitted")).toBe("—");
    expect(personalText(undefined, "Chưa có", "expired")).toBe("Chưa có");
  });
});
