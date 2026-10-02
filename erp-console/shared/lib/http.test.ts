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

  it("lỗi BE: message hiển thị không có mã luật '(BR-…)', mã vẫn nằm ở ApiError.code (QA Lô 10 N2)", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    const error = await apiFetch("/api/x/", {
      method: "POST",
      body: {},
      mock: () => ({ status: 400, body: { detail: "Phiếu nhập đã bị huỷ (BR-MH-07).", code: "RECEIPT_CANCELLED" } }),
    }).catch((e) => e as { message: string; code?: string });
    expect((error as { message: string }).message).toBe("Phiếu nhập đã bị huỷ.");
    expect((error as { code?: string }).code).toBe("RECEIPT_CANCELLED");
  });

  it("lỗi 400 chỉ có detail và code: details là undefined", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    const error = await apiFetch("/api/x/", { method: "PUT", body: {}, mock: () => ({ status: 400, body: { detail: "x", code: "Y" } }) }).catch((e) => e);
    expect((error as { details?: unknown }).details).toBeUndefined();
  });
});

describe("apiFetch lỗi 409 (xung đột phiên bản, W6f)", () => {
  it("ApiError mang status, code và details có updated_at, updated_by_name", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch, ApiError } = await import("./http");
    const error = await apiFetch("/api/x/", {
      method: "PUT",
      body: {},
      mock: () => ({
        status: 409,
        body: { detail: "Phiếu vừa được người khác cập nhật, tải lại để xem.", code: "STALE_STATE", updated_at: "2026-09-28T03:30:00+00:00", updated_by_name: "Lộc" },
      }),
    }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    const e = error as InstanceType<typeof ApiError>;
    expect(e.status).toBe(409);
    expect(e.code).toBe("STALE_STATE");
    expect(e.message).toBe("Phiếu vừa được người khác cập nhật, tải lại để xem.");
    expect(e.details).toEqual({ updated_at: "2026-09-28T03:30:00+00:00", updated_by_name: "Lộc" });
  });

  it("409 không có detail: dùng câu chung tiếng Việt, details undefined", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    const error = await apiFetch("/api/x/", { method: "PUT", body: {}, mock: () => ({ status: 409, body: {} }) }).catch((e) => e);
    expect((error as Error).message).toMatch(/người khác/);
    expect((error as { details?: unknown }).details).toBeUndefined();
  });

  it("conflictOf đọc được updated_by_name và updated_at từ lỗi 409 thật qua apiFetch", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
    const { apiFetch } = await import("./http");
    const { conflictOf, isConflictError } = await import("../ui/form/useSubmit");
    const error = await apiFetch("/api/x/", {
      method: "PUT",
      body: {},
      mock: () => ({ status: 409, body: { detail: "x", code: "STALE_STATE", updated_at: "2026-09-28T03:30:00+00:00", updated_by_name: "Lộc" } }),
    }).catch((e) => e);
    expect(isConflictError(error)).toBe(true);
    expect(conflictOf(error)).toEqual({ updatedAt: "2026-09-28T03:30:00+00:00", updatedByName: "Lộc" });
  });
});
