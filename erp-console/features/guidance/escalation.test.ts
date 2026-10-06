import { describe, expect, it } from "vitest";
import { escalatableStep, whoText } from "./escalation";
import type { GuidanceNextStep } from "./types";

const ON = { ai_features_enabled: true };

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
    expect(escalatableStep({ next_steps: [a, b] }, ON)?.key).toBe("b");
  });
  it("bỏ qua bước hệ thống và bước đã được phép; không có thì null", () => {
    expect(escalatableStep({ next_steps: [step({ actor: "system" }), step({ allowed: true })] }, ON)).toBeNull();
    expect(escalatableStep({ next_steps: [] }, ON)).toBeNull();
    expect(escalatableStep(null, ON)).toBeNull();
  });
});

describe("escalatableStep khi BE báo AI tắt (W39)", () => {
  it("cờ build bật nhưng BE tắt hoặc chưa tải me thì không có mục 'Nhờ người xử lý'", () => {
    const data = { next_steps: [step({ key: "b" })] };
    expect(escalatableStep(data, { ai_features_enabled: false })).toBeNull();
    expect(escalatableStep(data, null)).toBeNull();
  });
});

describe("whoText", () => {
  it("nối người nhận bằng 'hoặc', thiếu thì nói chung", () => {
    expect(whoText({ who: ["Chủ", "Quản lý"] })).toBe("Chủ hoặc Quản lý");
    expect(whoText({ who: [] })).toBe("người có thẩm quyền");
  });
});
