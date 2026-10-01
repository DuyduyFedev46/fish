// SR-AIS-01: ghi chính sách AI gửi thân object một lớp JSON; BE thật (DRF) trả 400 nếu nhận chuỗi.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installFakeBackendFetch } from "@/shared/lib/testing/fakeBackendFetch";

const POLICY_BODY = { version: 6, global_mode: "on", env: "staging", production_ready: false, red_zone: [], caps: {}, users: [] };

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("updateAiPolicy trên BE giả y như thật", () => {
  it("PUT /api/ai/policy/ nhận object và trả phiên bản mới (không 400)", async () => {
    const { sent } = installFakeBackendFetch(POLICY_BODY);
    const { updateAiPolicy } = await import("./api");
    const updated = await updateAiPolicy({
      base_version: 5,
      global_mode: "on",
      caps: { "purchasing.purchasereceipt.receive_batches": { kg: "80", daily: 3 } },
      acknowledge_responsibility: true,
    });
    expect(updated.version).toBe(6);
    expect(sent[0].method).toBe("PUT");
    expect(sent[0].parsedBody).toMatchObject({ base_version: 5, acknowledge_responsibility: true });
  });

  it("POST kill của một nhân viên cũng gửi object", async () => {
    const { sent } = installFakeBackendFetch({ version: 2, killed: true, user_id: 9 });
    const { killUserAi } = await import("./api");
    await killUserAi(9, true);
    expect(sent[0].parsedBody).toEqual({ killed: true });
  });
});
