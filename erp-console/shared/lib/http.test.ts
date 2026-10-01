// Lớp http: thân yêu cầu đi ra đúng MỘT lớp JSON, và mock bắt được lỗi mã hoá hai lần như backend thật (SR-AIS-01, AC2 và AC3).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { installFakeBackendFetch } from "./testing/fakeBackendFetch";

beforeEach(() => {
  vi.resetModules();
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("apiFetch chế độ thật", () => {
  it("object đi ra là chuỗi JSON một lớp (parse ra object)", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    const { sent } = installFakeBackendFetch({ ok: true });
    const { apiFetch } = await import("./http");
    await apiFetch("/api/x/", { method: "PUT", body: { base_version: 1 } });
    expect(sent[0].parsedBody).toEqual({ base_version: 1 });
  });
});

describe("apiFetch chế độ mock", () => {
  it("handler mock nhận thân đã đi qua JSON như trên dây (bỏ khoá undefined)", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    let seen: unknown;
    await apiFetch("/api/x/", {
      method: "PUT",
      body: { a: 1, b: undefined },
      mock: (req) => {
        seen = req.body;
        return { status: 200, body: {} };
      },
    });
    expect(seen).toEqual({ a: 1 });
    expect(Object.keys(seen as object)).toEqual(["a"]);
  });

  it("thân bị mã hoá hai lần (chuỗi) bị mock trả 400 như BE thật, handler không chạy", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch, ApiError } = await import("./http");
    const handler = vi.fn(() => ({ status: 200, body: {} }));
    const error = await apiFetch("/api/x/", { method: "PUT", body: JSON.stringify({ a: 1 }), mock: handler }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as InstanceType<typeof ApiError>).status).toBe(400);
    expect(handler).not.toHaveBeenCalled();
  });

  it("lỗi 400: ApiError.details là phần thân ngoài detail và code (BE trải details ra ngang hàng)", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch, ApiError } = await import("./http");
    const error = await apiFetch("/api/x/", {
      method: "PUT",
      body: {},
      mock: () => ({ status: 400, body: { errors: { "a.b.c": "vượt trần" }, detail: "vượt trần", code: "BR-AI-19" } }),
    }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as InstanceType<typeof ApiError>).code).toBe("BR-AI-19");
    expect((error as InstanceType<typeof ApiError>).details).toEqual({ errors: { "a.b.c": "vượt trần" } });
  });

  it("lỗi 400 chỉ có detail và code: details là undefined", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    const error = await apiFetch("/api/x/", { method: "PUT", body: {}, mock: () => ({ status: 400, body: { detail: "x", code: "Y" } }) }).catch((e) => e);
    expect((error as { details?: unknown }).details).toBeUndefined();
  });
});
