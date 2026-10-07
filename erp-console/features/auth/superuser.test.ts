// Duy 08/10 câu 1 + câu 13: superuser không nhóm vào ERP như Chủ; nhãn vai "Nhân viên gọi xác nhận".
import { describe, expect, it } from "vitest";
import { GROUP_LABEL, SUPERUSER_LABEL } from "@/shared/lib/groups";
import { canView, homePath, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import { roleText } from "./components/ConsoleGate";
import type { Me } from "./types";

const superuser: Viewer = {
  groups: [],
  permissions: Object.values(PERM),
  can_view_profit: true,
  home: "dashboard",
  is_superuser: true,
};

describe("superuser không nhóm", () => {
  it("vào Tổng quan, thấy menu theo quyền, không có Việc giao của tôi", () => {
    expect(homePath(superuser as Me)).toBe("/overview/");
    expect(canView(superuser, "overview")).toBe(true);
    const keys = visibleNav(superuser).map((n) => n.key);
    expect(keys.length).toBeGreaterThan(5);
    expect(keys).not.toContain("my-deliveries");
  });

  it("nhãn vai là Quản trị hệ thống khi không có nhóm", () => {
    expect(roleText({ ...superuser, groups: [], group_labels: [] } as unknown as Me)).toBe(SUPERUSER_LABEL);
  });

  it("người không nhóm, không superuser (home no-role) vẫn không có menu", () => {
    expect(visibleNav({ ...superuser, is_superuser: false, home: "no-role" })).toEqual([]);
  });
});

describe("nhãn vai customer_service", () => {
  it("là Nhân viên gọi xác nhận, không còn CSKH", () => {
    expect(GROUP_LABEL["customer_service"]).toBe("Nhân viên gọi xác nhận");
  });
});
