import { describe, it, expect } from "vitest";
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
