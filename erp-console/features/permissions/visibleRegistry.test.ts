import { describe, expect, it } from "vitest";
import { visibleRegistry } from "./permissionsModel";
import type { RegistryItem } from "./types";

const item = (key: string) => ({ key, label: key, section: "S", owner_only: false, requires: [] }) as unknown as RegistryItem;

describe("W39: ma trận phân quyền", () => {
  it("giao diện AI tắt thì bỏ ai_policy, bật thì giữ", () => {
    const reg = [item("publish_batch"), item("ai_policy")];
    expect(visibleRegistry(reg, false).map((r) => r.key)).toEqual(["publish_batch"]);
    expect(visibleRegistry(reg, true)).toHaveLength(2);
  });
});
