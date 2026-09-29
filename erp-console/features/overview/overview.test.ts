import { describe, it, expect } from "vitest";
import { mockAttention } from "./mock";

describe("Overview Attention Tests (CS-15)", () => {
  it("CS-15-AC4: mockAttention filters keys based on user permissions", () => {
    // Quản lý / Chủ: all 6 keys
    const qlReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-ql1-9999999999999",
    };
    const qlRes = mockAttention(qlReq as any);
    expect(qlRes.status).toBe(200);
    const qlBody = qlRes.body as Record<string, number>;
    expect(qlBody.cskh_queue_waiting).toBeDefined();
    expect(qlBody.refund_calls_open).toBeDefined();
    expect(qlBody.cskh_escalated).toBeDefined();
    expect(qlBody.cskh_auto_cancel_blocked).toBeDefined();
    expect(qlBody.labels_not_printed).toBeDefined();
    expect(qlBody.labels_to_void).toBeDefined();

    // CSKH: only queue and refund calls
    const csReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-cs1-9999999999999",
    };
    const csRes = mockAttention(csReq as any);
    expect(csRes.status).toBe(200);
    const csBody = csRes.body as Record<string, number>;
    expect(csBody.cskh_queue_waiting).toBeDefined();
    expect(csBody.refund_calls_open).toBeDefined();
    expect(csBody.cskh_escalated).toBeUndefined();
    expect(csBody.labels_not_printed).toBeUndefined();

    // Kho: only labels
    const khoReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-kho1-9999999999999",
    };
    const khoRes = mockAttention(khoReq as any);
    expect(khoRes.status).toBe(200);
    const khoBody = khoRes.body as Record<string, number>;
    expect(khoBody.labels_not_printed).toBeDefined();
    expect(khoBody.labels_to_void).toBeDefined();
    expect(khoBody.cskh_queue_waiting).toBeUndefined();
    expect(khoBody.cskh_escalated).toBeUndefined();

    // Giao: 403
    const giaoReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-giao1-9999999999999",
    };
    const giaoRes = mockAttention(giaoReq as any);
    expect(giaoRes.status).toBe(403);
  });
});
