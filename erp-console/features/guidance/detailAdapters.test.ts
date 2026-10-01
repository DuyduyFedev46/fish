import { describe, expect, it } from "vitest";
import { nextStepLabel, toTimelineEntries } from "./detailAdapters";
import type { GuidanceNextStep, GuidanceTimelineEntry } from "./types";

const entry = (at: string, label: string, kind: "user" | "ai" | "system" = "user"): GuidanceTimelineEntry => ({
  at,
  kind: "x",
  label,
  doc: "",
  actor: { kind, display: kind === "ai" ? "AI của Lộc" : "Lộc" },
});

describe("toTimelineEntries", () => {
  it("mới nhất trước, cờ AI theo actor.kind, không mang mã BR", () => {
    const rows = toTimelineEntries([entry("2026-09-28T01:00:00Z", "Tạo phiếu"), entry("2026-09-28T03:00:00Z", "Xác nhận", "ai")]);
    expect(rows.map((r) => r.label)).toEqual(["Xác nhận", "Tạo phiếu"]);
    expect(rows[0].byAi).toBe(true);
    expect(rows[1].byAi).toBe(false);
    expect(JSON.stringify(rows)).not.toMatch(/BR-/);
  });
  it("null/undefined → rỗng", () => {
    expect(toTimelineEntries(null)).toEqual([]);
    expect(toTimelineEntries(undefined)).toEqual([]);
  });
});

describe("nextStepLabel", () => {
  const step = (over: Partial<GuidanceNextStep>): GuidanceNextStep => ({
    key: "k", label: "Việc", actor: "user", allowed: true, who: [], missing: [], deadline: null, why: null, command: null, ai: null, ...over,
  });
  it("lấy bước người dùng được phép đầu tiên", () => {
    expect(nextStepLabel({ next_steps: [step({ actor: "system", label: "Tự huỷ" }), step({ allowed: false, label: "A" }), step({ label: "Xác nhận" })] })).toBe("Xác nhận");
  });
  it("không có → null", () => {
    expect(nextStepLabel({ next_steps: [] })).toBeNull();
    expect(nextStepLabel(null)).toBeNull();
  });
});
