import { describe, expect, it } from "vitest";
import { budgetView } from "./budgetView";
import { mockStatus } from "./mock";

describe("budgetView (#1)", () => {
  it("không có budget (vai khác Chủ) → không dựng khối", () => {
    expect(budgetView(null)).toBeNull();
    expect(budgetView(undefined)).toBeNull();
  });
  it("hiện đã dùng / hạn mức bằng VNĐ, trạng thái ok không có câu nhắc", () => {
    const v = budgetView({ spent_vnd: 0, limit_vnd: 200000, status: "ok" });
    expect(v?.usage).toBe("Đã dùng 0 đ / 200.000 đ");
    expect(v?.note).toBe("");
    expect(v?.tone).toBe("ok");
  });
  it("warning và blocked có câu nhắc; trạng thái lạ coi như ok", () => {
    expect(budgetView({ spent_vnd: 170000, limit_vnd: 200000, status: "warning" })?.note).toMatch(/Sắp chạm/);
    expect(budgetView({ spent_vnd: 200000, limit_vnd: 200000, status: "blocked" })?.tone).toBe("blocked");
    expect(budgetView({ spent_vnd: 1, limit_vnd: 2, status: "weird" })?.tone).toBe("ok");
  });
  it("dữ liệu hỏng (không phải số) → không hiện", () => {
    expect(budgetView({ spent_vnd: Number.NaN, limit_vnd: 1, status: "ok" })).toBeNull();
  });
});

describe("mock /api/ai/status/ theo vai", () => {
  const tok = (u: string) => `mock-token-${u}-${Date.now() + 60_000}`;
  it("AI tắt: không budget; AI bật: chỉ Chủ nhận budget", () => {
    const get = (u: string) => (mockStatus({ method: "GET", path: "/api/ai/status/", token: tok(u) }).body as { ai_enabled: boolean; budget: unknown });
    expect(get("loc").budget).toBeNull(); // node: không có window → cờ tắt
    const store = new Map<string, string>([["cave_erp_mock_ai", "on"]]);
    (globalThis as unknown as { window: unknown }).window = { localStorage: { getItem: (k: string) => store.get(k) ?? null } };
    try {
      expect(get("loc").budget).not.toBeNull();
      expect(get("ql1").budget).toBeNull();
      store.set("cave_erp_mock_ai_budget", "warning");
      expect((get("loc").budget as { status: string }).status).toBe("warning");
    } finally {
      delete (globalThis as unknown as { window?: unknown }).window;
    }
  });
});
