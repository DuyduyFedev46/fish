import { describe, expect, it } from "vitest";
import { isAiFlagOn, publishAiEnabled, releaseAiEnabled } from "./gate-state";

describe("cờ AI bật không dính theo trang (L2)", () => {
  it("chủ riêng nhả cờ khi rời trang", () => {
    const page = Symbol("page");
    publishAiEnabled(true, page);
    expect(isAiFlagOn()).toBe(true);
    releaseAiEnabled(page);
    expect(isAiFlagOn()).toBe(false);
  });

  it("cổng trợ lý dùng chủ chung: trang riêng nhả không làm mất cờ của cổng chung", () => {
    publishAiEnabled(true); // chủ chung
    const page = Symbol("page");
    publishAiEnabled(true, page);
    releaseAiEnabled(page);
    expect(isAiFlagOn()).toBe(true);
    publishAiEnabled(false);
    expect(isAiFlagOn()).toBe(false);
  });

  it("một chủ báo tắt thì cờ tắt nếu không còn chủ nào bật", () => {
    const a = Symbol("a");
    publishAiEnabled(true, a);
    publishAiEnabled(false, a);
    expect(isAiFlagOn()).toBe(false);
    releaseAiEnabled(a);
  });
});
