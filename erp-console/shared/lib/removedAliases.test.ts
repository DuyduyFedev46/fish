// P8b Lô 5: alias tên cũ đã gỡ. BE chỉ trả tên tiếng Anh; FE không còn map tên cũ -> mới.
// Tên cũ nằm trong CHUỖI (dữ liệu giả cho ca "không còn được hiểu"), file test chỉ xét định danh.
import { describe, expect, it } from "vitest";
import type { Me } from "@/features/auth/types";
import { buildCapsForSave } from "@/features/ai/policy/caps";
import { RECEIVE_BATCHES_COMMAND_ID } from "@/features/ai/commandGroups";
import * as rolesModule from "./roles";
import { HOME_CONFIRMATION_QUEUE, ROLE } from "./roles";
import { PERM, homePath, visibleNav } from "./nav";

function makeMe(groups: string[], home: string, permissions: string[]): Me {
  return {
    id: 1,
    username: "demo",
    display_name: "Demo",
    phone: "0900000000",
    groups,
    permissions,
    can_view_cost: false,
    can_view_profit: false,
    home: home as Me["home"],
    group_labels: groups.map((code) => ({ code, label: "Nhãn" })),
  };
}

describe("lớp chuẩn hoá tên cũ đã bị gỡ khỏi roles.ts", () => {
  it("không còn export normalize* hay bảng tên cũ", () => {
    const exported = Object.keys(rolesModule).sort();
    expect(exported).toEqual(["HOME_CONFIRMATION_QUEUE", "ROLE"]);
  });
});

describe("tên mới đi thẳng vào menu và trang đầu", () => {
  const allPerms = Object.values(PERM);

  it("vai customer_service với home confirmation-queue: vào /confirmation/, menu có mục confirmation", () => {
    const me = makeMe([ROLE.customerService], HOME_CONFIRMATION_QUEUE, [PERM.confirmWithCustomer]);
    expect(homePath(me)).toBe("/confirmation/");
    expect(visibleNav(me).some((n) => n.key === "confirmation" && n.href === "/confirmation/")).toBe(true);
  });

  it("mỗi vai tên mới có ít nhất một mục menu khi đủ quyền", () => {
    for (const role of Object.values(ROLE)) {
      expect(visibleNav(makeMe([role], "dashboard", allPerms)).length).toBeGreaterThan(0);
    }
  });
});

describe("buildCapsForSave: khoá mới thắng (techlead 03b mục 3b)", () => {
  it("giá trị phụ lấy từ khoá mới, không từ khoá khác", () => {
    const out = buildCapsForSave(
      { [RECEIVE_BATCHES_COMMAND_ID]: { kg: "200", max_level: "B" }, "purchasing.purchasereceipt.nhap_lo": { kg: "9", max_level: "A" } },
      { kg: "300", vnd: null, daily: 10 }
    );
    expect(out[RECEIVE_BATCHES_COMMAND_ID]).toEqual({ kg: "300", vnd: null, daily: 10, max_level: "B" });
  });
});
