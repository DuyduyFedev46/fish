// Token ERP hết hạn (BE trả 401): xoá token ở máy, gọi handler đúng một lần, không vòng lặp (đợt rà soát bảo mật, M-3).
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function fakeWindow(initial: Record<string, string>) {
  const data = { ...initial };
  const localStorage = {
    getItem: (k: string) => (k in data ? data[k] : null),
    setItem: (k: string, v: string) => void (data[k] = v),
    removeItem: (k: string) => void delete data[k],
  };
  vi.stubGlobal("window", { localStorage });
  return data;
}

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("401 do token hết hạn", () => {
  it("xoá token, gọi handler đúng một lần dù còn nhiều request 401 sau đó", async () => {
    const data = fakeWindow({ cave_erp_token: "abc" });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ detail: "Token đã hết hạn." }), { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, ApiError, setUnauthorizedHandler } = await import("./http");
    const { setToken } = await import("./token");
    const handler = vi.fn(() => setToken(null)); // y như AuthProvider: endSession() xoá token
    setUnauthorizedHandler(handler);

    const first = await apiFetch("/api/x/").catch((e) => e);
    expect(first).toBeInstanceOf(ApiError);
    expect((first as InstanceType<typeof ApiError>).status).toBe(401);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(data.cave_erp_token).toBeUndefined();

    // Không còn token: 401 tiếp theo (vd trang đăng nhập) không kích hoạt lại việc chuyển trang.
    await apiFetch("/api/y/").catch(() => undefined);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it("câu thông báo hết phiên là câu tiếng Việt chuẩn", async () => {
    const { MSG } = await import("./messages");
    expect(MSG.sessionExpired).toContain("Phiên đăng nhập đã hết hạn, anh/chị đăng nhập lại");
  });
});
