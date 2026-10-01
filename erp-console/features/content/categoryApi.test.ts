// SR-AIS-01 (AC2): tạo/sửa chuyên mục CMS gửi object một lớp JSON.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installFakeBackendFetch } from "@/shared/lib/testing/fakeBackendFetch";

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("chuyên mục CMS trên BE giả y như thật", () => {
  it("POST tạo chuyên mục nhận object", async () => {
    const { sent } = installFakeBackendFetch({ id: 1, name: "Mẹo" });
    const { createCategory } = await import("./api");
    await createCategory({ name: "Mẹo", description: "x", order: 1 });
    expect(sent[0].parsedBody).toEqual({ name: "Mẹo", description: "x", order: 1 });
  });

  it("PATCH sửa chuyên mục nhận object", async () => {
    const { sent } = installFakeBackendFetch({ id: 1, name: "Mẹo" });
    const { updateCategory } = await import("./api");
    await updateCategory(1, { is_active: false });
    expect(sent[0].parsedBody).toEqual({ is_active: false });
  });
});
