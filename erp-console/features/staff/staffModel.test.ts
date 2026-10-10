import { describe, expect, it } from "vitest";
import { STAFF_MSG as M } from "./messages";
import {
  activityLabel,
  asTab,
  blockedReason,
  can,
  countByTab,
  deliveringBlock,
  groupsDiff,
  namesOf,
  ownerChange,
  parseStaffId,
  rowsOfTab,
  whoOf,
} from "./staffModel";
import type { StaffMember } from "./types";

const member = (over: Partial<StaffMember> = {}): StaffMember => ({
  id: 3,
  username: "kho1",
  display_name: "Anh Tâm",
  phone: "0900000000",
  groups: ["warehouse_staff"],
  is_active: true,
  last_login: null,
  available_actions: ["edit", "set_groups", "reset_password", "deactivate"],
  ...over,
});

describe("tab và đếm", () => {
  const rows = [member({ id: 1 }), member({ id: 2, is_active: false }), member({ id: 3 })];
  it("đếm theo tab", () => {
    expect(countByTab(rows)).toEqual({ active: 2, inactive: 1, all: 3 });
  });
  it("lọc theo tab", () => {
    expect(rowsOfTab(rows, "active").map((r) => r.id)).toEqual([1, 3]);
    expect(rowsOfTab(rows, "inactive").map((r) => r.id)).toEqual([2]);
    expect(rowsOfTab(rows, "all")).toHaveLength(3);
  });
  it("khoá tab lạ về đang làm", () => {
    expect(asTab("inactive")).toBe("inactive");
    expect(asTab("all")).toBe("all");
    expect(asTab("zzz")).toBe("active");
  });
});

describe("parseStaffId", () => {
  it("nhận số nguyên dương", () => {
    expect(parseStaffId("?id=12")).toBe(12);
  });
  it("từ chối thiếu, 0, âm, chữ, quá dài", () => {
    expect(parseStaffId("")).toBeNull();
    expect(parseStaffId("?id=0")).toBeNull();
    expect(parseStaffId("?id=-3")).toBeNull();
    expect(parseStaffId("?id=abc")).toBeNull();
    expect(parseStaffId("?id=1234567890123")).toBeNull();
    expect(parseStaffId("?id=1;drop")).toBeNull();
  });
});

describe("nhãn người và nhóm", () => {
  it("whoOf thêm tên đăng nhập khi khác tên hiển thị", () => {
    expect(whoOf({ display_name: "Anh Tâm", username: "kho1" })).toBe("Anh Tâm (kho1)");
    expect(whoOf({ display_name: "kho1", username: "kho1" })).toBe("kho1");
    expect(whoOf({ display_name: "", username: "kho1" })).toBe("kho1");
  });
  it("namesOf dịch mã nhóm", () => {
    expect(namesOf(["owner", "delivery_staff"])).toContain(", ");
  });
});

describe("so sánh nhóm", () => {
  it("groupsDiff", () => {
    expect(groupsDiff(["manager"], ["manager", "warehouse_staff"])).toEqual({ added: ["warehouse_staff"], removed: [] });
    expect(groupsDiff(["manager", "owner"], ["manager"])).toEqual({ added: [], removed: ["owner"] });
  });
  it("ownerChange chỉ báo khi thêm/bỏ nhóm Chủ", () => {
    expect(ownerChange({ added: ["owner"], removed: [] })).toBe("grant");
    expect(ownerChange({ added: [], removed: ["owner"] })).toBe("revoke");
    expect(ownerChange({ added: ["manager"], removed: ["warehouse_staff"] })).toBeNull();
  });
});

describe("thao tác theo available_actions", () => {
  it("can chỉ đọc danh sách BE trả", () => {
    expect(can(member(), "reset_password")).toBe(true);
    expect(can(member({ available_actions: [] }), "edit")).toBe(false);
  });
  it("blockedReason chọn câu theo hoàn cảnh", () => {
    const owner = member({ groups: ["owner"], id: 1, available_actions: ["edit", "set_groups"] });
    expect(blockedReason("reset_password", owner, 1)).toBe(M.selfBlockedReset);
    expect(blockedReason("deactivate", owner, 1)).toBe(M.selfBlockedDeactivate);
    expect(blockedReason("deactivate", owner, 2)).toBe(M.lastOwnerBlocked);
    expect(blockedReason("deactivate", member({ available_actions: [] }), 2)).toBe(M.noRightBlocked);
    expect(blockedReason("reactivate", member(), 2)).toBe(M.noRightBlocked);
  });
});

describe("activityLabel", () => {
  it("ưu tiên ghi chú, rồi động từ đã dịch, rồi chuỗi BE", () => {
    expect(activityLabel({ action: "update", note: "Sửa số điện thoại" })).toBe("Sửa số điện thoại");
    expect(activityLabel({ action: "deactivate", note: null })).toBe("Cho nghỉ");
    expect(activityLabel({ action: "weird", note: " " })).toBe("weird");
  });
});

describe("deliveringBlock (ED-38-AC3 / BR-GH-08)", () => {
  const note = (code: string) => ({ code });
  it("không có phiếu hoặc chưa tải được thì không chặn, để BE quyết", () => {
    expect(deliveringBlock(null)).toBeNull();
    expect(deliveringBlock([])).toBeNull();
  });
  it("nêu số phiếu kèm mã phiếu", () => {
    const text = deliveringBlock([note("GH-0001"), note("GH-0002")]);
    expect(text).toBe(M.deactivateDelivering(2, "GH-0001, GH-0002", -3));
    expect(text).toContain("2 phiếu Đang giao");
    expect(text).toContain("GH-0001, GH-0002");
    expect(text).not.toContain("nữa");
  });
  it("Lô 17b G7: tổng lấy theo count của API, không phải độ dài trang đầu", () => {
    const firstPage = Array.from({ length: 20 }, (_, i) => note(`GH-${i + 1}`));
    const text = deliveringBlock(firstPage, 23) as string;
    expect(text).toContain("23 phiếu Đang giao");
    expect(text).toContain("và 18 phiếu nữa");
    expect(deliveringBlock([], 0)).toBeNull();
  });
  it("nhiều phiếu thì cắt bớt mã, vẫn đúng tổng", () => {
    const many = Array.from({ length: 8 }, (_, i) => note(`GH-${i + 1}`));
    const text = deliveringBlock(many) as string;
    expect(text).toContain("8 phiếu Đang giao");
    expect(text).toContain("GH-5");
    expect(text).not.toContain("GH-6");
    expect(text).toContain("và 3 phiếu nữa");
  });
});
