// SHOP-5-02 (BR-ND-20): màn Nội dung ERP hiện 3 vai trò trang bắt buộc mới.
import { describe, expect, it } from "vitest";
import { mockGetGoliveStatus } from "./mock";
import { PAGE_ROLE_OPTIONS, REQUIRED_PAGE_ROLES, pageRoleLabel } from "./pageRoles";

describe("SHOP-5-02 vai trò trang bắt buộc", () => {
  it("có đủ 7 vai trò, đúng thứ tự backend", () => {
    expect(REQUIRED_PAGE_ROLES).toEqual(["privacy", "terms", "refund", "seller_info", "shipping", "payment", "complaints"]);
  });

  it("nhãn tiếng Việt cho vai trò mới, vai trò lạ thì trả nguyên mã", () => {
    expect(pageRoleLabel("shipping")).toBe("Chính sách giao hàng");
    expect(pageRoleLabel("payment")).toBe("Chính sách thanh toán");
    expect(pageRoleLabel("complaints")).toBe("Cơ chế giải quyết khiếu nại");
    expect(pageRoleLabel("privacy")).toBe("Chính sách bảo mật");
    expect(pageRoleLabel("unknown_role")).toBe("unknown_role");
  });

  it("ô chọn vai trò có lựa chọn trống + 7 vai trò", () => {
    expect(PAGE_ROLE_OPTIONS[0].value).toBe("");
    expect(PAGE_ROLE_OPTIONS.slice(1).map((o) => o.value)).toEqual(REQUIRED_PAGE_ROLES);
  });

  it("mock golive-status chỉ báo vai trò trong danh sách và có báo vai trò mới chưa đăng", () => {
    const missing = mockGetGoliveStatus().missing_roles;
    for (const r of missing) expect(REQUIRED_PAGE_ROLES).toContain(r);
    expect(missing).toEqual(expect.arrayContaining(["shipping", "payment", "complaints"]));
  });
});
