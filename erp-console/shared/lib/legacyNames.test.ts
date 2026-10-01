// P8b Lô 3: lớp chuẩn hoá tên ở biên API. Payload BE cũ (tên Group/home/id lệnh/nhóm AI/mức nhạy cảm cũ) và payload BE Lô 4
// (tên tiếng Anh) phải cho cùng một kết quả: cùng menu, cùng trang đầu, cùng màn chính sách AI và cấu hình AI.
// Dữ liệu giả. Tên cũ/mới nằm trong CHUỖI (bảng cũ ở roles.ts, legacyIds.ts), file test chỉ xét định danh.
import { describe, expect, it } from "vitest";
import { normalizeMe } from "@/features/auth/api";
import type { Me } from "@/features/auth/types";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID, SENSITIVITY } from "@/features/ai/commandGroups";
import {
  findByCommand,
  isSameCommand,
  normalizeAiGroup,
  normalizeAiPolicy,
  normalizeCommandId,
  normalizeDescriptor,
  normalizeIndexResponse,
  normalizeMyConfig,
  normalizeSensitivity,
} from "@/features/ai/legacyIds";
import type { AiCommandDescriptor, AiCommandsIndexResponse, AiPolicy, MyConfig } from "@/features/ai/types";
import { HOME_CONFIRMATION_QUEUE, ROLE, normalizeHome, normalizeRole, normalizeRoles } from "./roles";
import { PERM, homePath, visibleNav } from "./nav";

const OLD_TO_NEW_ROLES: Array<[string, string]> = [
  ["chu", "owner"],
  ["quan_ly", "manager"],
  ["nv_kho", "warehouse_staff"],
  ["nv_giao", "delivery_staff"],
  ["cskh", "customer_service"],
];

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

describe("normalizeRole / normalizeRoles / normalizeHome", () => {
  it("tên Group cũ và mới cùng ra giá trị nội bộ của ROLE", () => {
    for (const [oldName, newName] of OLD_TO_NEW_ROLES) {
      expect(normalizeRole(oldName)).toBe(normalizeRole(newName));
    }
    expect(normalizeRole("owner")).toBe(ROLE.owner);
    expect(normalizeRole("customer_service")).toBe(ROLE.customerService);
    expect(normalizeRole("warehouse_staff")).toBe(ROLE.warehouseStaff);
  });

  it("tên lạ giữ nguyên; danh sách lẫn cũ/mới được gộp, bỏ trùng, giữ thứ tự", () => {
    expect(normalizeRole("group_la")).toBe("group_la");
    expect(normalizeRoles(["owner", "chu", "customer_service", "x"])).toEqual([ROLE.owner, ROLE.customerService, "x"]);
  });

  it("me.home cũ và mới cùng ra HOME_CONFIRMATION_QUEUE; giá trị khác giữ nguyên", () => {
    expect(normalizeHome("cskh-queue")).toBe(HOME_CONFIRMATION_QUEUE);
    expect(normalizeHome("confirmation-queue")).toBe(HOME_CONFIRMATION_QUEUE);
    expect(normalizeHome("dashboard")).toBe("dashboard");
    expect(normalizeHome("my-deliveries")).toBe("my-deliveries");
    expect(normalizeHome("no-role")).toBe("no-role");
  });
});

describe("normalizeMe: payload cũ và payload Lô 4 cho cùng menu và trang đầu", () => {
  const allPerms = Object.values(PERM);
  for (const [oldName, newName] of OLD_TO_NEW_ROLES) {
    it(`vai ${newName}: cùng menu, cùng trang đầu`, () => {
      const oldHome = oldName === "cskh" ? "cskh-queue" : oldName === "nv_giao" ? "my-deliveries" : "dashboard";
      const newHome = oldName === "cskh" ? "confirmation-queue" : oldHome;
      const fromOld = normalizeMe(makeMe([oldName], oldHome, allPerms));
      const fromNew = normalizeMe(makeMe([newName], newHome, allPerms));
      expect(fromNew.groups).toEqual(fromOld.groups);
      expect(fromNew.home).toBe(fromOld.home);
      expect(fromNew.group_labels).toEqual(fromOld.group_labels);
      expect(visibleNav(fromNew).map((n) => n.key)).toEqual(visibleNav(fromOld).map((n) => n.key));
      expect(homePath(fromNew)).toBe(homePath(fromOld));
    });
  }

  it("cskh (home hàng đợi xác nhận): vào /confirmation/, menu có mục confirmation", () => {
    for (const home of ["cskh-queue", "confirmation-queue"]) {
      const me = normalizeMe(makeMe([home === "cskh-queue" ? "cskh" : "customer_service"], home, [PERM.confirmWithCustomer]));
      expect(me.home).toBe(HOME_CONFIRMATION_QUEUE);
      expect(homePath(me)).toBe("/confirmation/");
      expect(visibleNav(me).some((n) => n.key === "confirmation" && n.href === "/confirmation/")).toBe(true);
    }
  });

  it("không đổi dữ liệu đầu vào (trả bản sao)", () => {
    const raw = makeMe(["owner"], "dashboard", []);
    normalizeMe(raw);
    expect(raw.groups).toEqual(["owner"]);
  });
});

describe("normalizeCommandId / normalizeAiGroup / normalizeSensitivity / findByCommand", () => {
  it("id lệnh Nhập lô cũ và mới cùng ra id nội bộ; id khác giữ nguyên", () => {
    expect(normalizeCommandId("purchasing.purchasereceipt.nhap_lo")).toBe(RECEIVE_BATCHES_COMMAND_ID);
    expect(normalizeCommandId("purchasing.purchasereceipt.receive_batches")).toBe(RECEIVE_BATCHES_COMMAND_ID);
    expect(normalizeCommandId("inventory.batch.list")).toBe("inventory.batch.list");
    expect(isSameCommand("purchasing.purchasereceipt.nhap_lo", "purchasing.purchasereceipt.receive_batches")).toBe(true);
    expect(isSameCommand("inventory.batch.list", RECEIVE_BATCHES_COMMAND_ID)).toBe(false);
  });

  it("nhóm lệnh cũ và mới cùng ra COMMAND_GROUP", () => {
    expect(normalizeAiGroup("thu_mua")).toBe(COMMAND_GROUP.purchasing);
    expect(normalizeAiGroup("purchasing")).toBe(COMMAND_GROUP.purchasing);
    expect(normalizeAiGroup("ban_hang")).toBe(COMMAND_GROUP.sales);
    expect(normalizeAiGroup("sales")).toBe(COMMAND_GROUP.sales);
    expect(normalizeAiGroup("cskh")).toBe(COMMAND_GROUP.customerService);
    expect(normalizeAiGroup("customer_service")).toBe(COMMAND_GROUP.customerService);
    expect(normalizeAiGroup("nhom_la")).toBe("nhom_la");
  });

  it("mức nhạy cảm cũ và mới cùng ra SENSITIVITY", () => {
    expect(normalizeSensitivity("cao")).toBe(SENSITIVITY.high);
    expect(normalizeSensitivity("high")).toBe(SENSITIVITY.high);
    expect(normalizeSensitivity("trung_binh")).toBe(SENSITIVITY.medium);
    expect(normalizeSensitivity("medium")).toBe(SENSITIVITY.medium);
    expect(normalizeSensitivity("thap")).toBe(SENSITIVITY.low);
    expect(normalizeSensitivity("low")).toBe(SENSITIVITY.low);
  });

  it("findByCommand tìm mục khoá cũ hay mới và trả đúng khoá thật để ghi ngược", () => {
    const oldTable = { "purchasing.purchasereceipt.nhap_lo": { kg: "200" } };
    const newTable = { "purchasing.purchasereceipt.receive_batches": { kg: "200" } };
    expect(findByCommand(oldTable, RECEIVE_BATCHES_COMMAND_ID)).toEqual({
      key: "purchasing.purchasereceipt.nhap_lo",
      value: { kg: "200" },
    });
    expect(findByCommand(newTable, RECEIVE_BATCHES_COMMAND_ID)).toEqual({
      key: "purchasing.purchasereceipt.receive_batches",
      value: { kg: "200" },
    });
    expect(findByCommand(newTable, "purchasing.purchasereceipt.nhap_lo")?.value).toEqual({ kg: "200" });
    expect(findByCommand({}, RECEIVE_BATCHES_COMMAND_ID)).toBeUndefined();
    expect(findByCommand(null, RECEIVE_BATCHES_COMMAND_ID)).toBeUndefined();
  });
});

describe("chuẩn hoá payload AI: payload cũ và payload Lô 4 cho cùng kết quả hiển thị", () => {
  const policyBase = {
    version: 3,
    global_mode: "on",
    red_zone: [],
    caps: {},
  };

  function policyWith(groups: string[], capKey: string): AiPolicy {
    return {
      ...policyBase,
      caps: { [capKey]: { kg: "200", vnd: "30000000", daily: 20 } },
      users: [{ user_id: 1, display_name: "A", groups, killed: false, config_version: 1, counts: { A: 1, B: 0, C: 2, OFF: 0 } }],
    } as unknown as AiPolicy;
  }

  it("chính sách AI: users[].groups cùng giá trị; trần Nhập lô đọc được dù khoá cũ hay mới", () => {
    const fromOld = normalizeAiPolicy(policyWith(["chu", "nv_kho"], "purchasing.purchasereceipt.nhap_lo"));
    const fromNew = normalizeAiPolicy(policyWith(["owner", "warehouse_staff"], "purchasing.purchasereceipt.receive_batches"));
    expect(fromNew.users[0].groups).toEqual(fromOld.users[0].groups);
    expect(findByCommand(fromNew.caps, RECEIVE_BATCHES_COMMAND_ID)?.value).toEqual(
      findByCommand(fromOld.caps, RECEIVE_BATCHES_COMMAND_ID)?.value
    );
    // Khoá caps giữ nguyên như BE trả để PUT ghi ngược đúng khoá.
    expect(Object.keys(fromNew.caps)).toEqual(["purchasing.purchasereceipt.receive_batches"]);
    expect(Object.keys(fromOld.caps)).toEqual(["purchasing.purchasereceipt.nhap_lo"]);
  });

  function configWith(group: string, commandId: string): MyConfig {
    return {
      ai_enabled: true,
      version: 1,
      killed: false,
      updated_at: "2026-10-01T00:00:00+07:00",
      global_mode: "on",
      write_levels_allowed: ["OFF", "C"],
      groups: [
        {
          group,
          label: "Nhóm",
          read_level: "A",
          write_level: "C",
          commands: [{ id: commandId, title: "Nhập lô", kind: "write", level: "C", source: "default", choices: ["OFF", "C"], max_level: "C", locked_reason: null, red_zone: false, limits: null }],
        },
      ],
    } as unknown as MyConfig;
  }

  it("cấu hình AI của tôi: nhóm cùng giá trị; id lệnh giữ nguyên để gửi ngược overrides đúng khoá", () => {
    const fromOld = normalizeMyConfig(configWith("thu_mua", "purchasing.purchasereceipt.nhap_lo"));
    const fromNew = normalizeMyConfig(configWith("purchasing", "purchasing.purchasereceipt.receive_batches"));
    expect(fromNew.groups[0].group).toBe(fromOld.groups[0].group);
    expect(fromOld.groups[0].commands[0].id).toBe("purchasing.purchasereceipt.nhap_lo");
    expect(fromNew.groups[0].commands[0].id).toBe("purchasing.purchasereceipt.receive_batches");
  });

  it("chỉ mục lệnh và mô tả lệnh: nhóm và mức nhạy cảm cùng giá trị", () => {
    const item = (group: string) => ({ id: "x.y", title: "T", group, kind: "read", level: "A", screens: [], keywords: [] });
    const idx = (group: string) => ({ index_version: "1", config_version: 1, commands: [item(group)] }) as unknown as AiCommandsIndexResponse;
    expect(normalizeIndexResponse(idx("purchasing")).commands[0].group).toBe(normalizeIndexResponse(idx("thu_mua")).commands[0].group);
    const desc = (sensitivity: string) => ({ id: "x.y", sensitivity }) as unknown as AiCommandDescriptor;
    expect(normalizeDescriptor(desc("high")).sensitivity).toBe(normalizeDescriptor(desc("cao")).sensitivity);
  });
});
