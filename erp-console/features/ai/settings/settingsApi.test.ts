// SR-AIS-01: "AI của tôi" gửi thân object một lớp JSON (PUT my-config và POST kill).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installFakeBackendFetch } from "@/shared/lib/testing/fakeBackendFetch";

const CONFIG_BODY = { ai_enabled: true, version: 3, killed: false, updated_at: null, global_mode: "on", write_levels_allowed: ["OFF", "C"], groups: [] };

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("updateMyConfig, killMyConfig trên BE giả y như thật", () => {
  it("PUT /api/ai/my-config/ nhận object", async () => {
    const { sent } = installFakeBackendFetch(CONFIG_BODY);
    const { updateMyConfig } = await import("./api");
    const updated = await updateMyConfig({ base_version: 2, groups: {}, overrides: { "inventory.batch.list": "OFF" }, limits: {}, acknowledge_responsibility: true });
    expect(updated.version).toBe(3);
    expect(sent[0].parsedBody).toMatchObject({ base_version: 2, overrides: { "inventory.batch.list": "OFF" } });
  });

  it("POST /api/ai/my-config/kill/ nhận object", async () => {
    const { sent } = installFakeBackendFetch({ version: 4, killed: true });
    const { killMyConfig } = await import("./api");
    await killMyConfig(true);
    expect(sent[0].parsedBody).toEqual({ killed: true });
  });
});
