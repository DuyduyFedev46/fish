import { describe, expect, it } from "vitest";
import { escalatableStep, whoText } from "./escalation";
import type { GuidanceNextStep } from "./types";

const step = (over: Partial<GuidanceNextStep>): GuidanceNextStep => ({
  key: "confirm_payment",
  label: "Xác nhận đã nhận tiền",
  actor: "user",
  allowed: false,
  who: ["Chủ"],
  missing: [],
  deadline: null,
  why: null,
  command: null,
  ai: null,
  ...over,
});

describe("escalatableStep (Lô bổ sung A #19)", () => {
  it("chọn bước đầu tiên mình chưa tự làm được", () => {
    const a = step({ key: "a", allowed: true });
    const b = step({ key: "b" });
    expect(escalatableStep({ next_steps: [a, b] })?.key).toBe("b");
  });
  it("bỏ qua bước hệ thống và bước đã được phép; không có thì null", () => {
    expect(escalatableStep({ next_steps: [step({ actor: "system" }), step({ allowed: true })] })).toBeNull();
    expect(escalatableStep({ next_steps: [] })).toBeNull();
    expect(escalatableStep(null)).toBeNull();
  });
});

describe("whoText", () => {
  it("nối người nhận bằng 'hoặc', thiếu thì nói chung", () => {
    expect(whoText({ who: ["Chủ", "Quản lý"] })).toBe("Chủ hoặc Quản lý");
    expect(whoText({ who: [] })).toBe("người có thẩm quyền");
  });
});
