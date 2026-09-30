import { describe, it, expect } from "vitest";
import { buildDashboardSummaryMock } from "@/shared/lib/dashboardSummary.mock";
import { filterRecentOrders } from "./api";
import { mockAttention } from "./mock";
import type { RecentOrder } from "./types";

describe("Overview Attention Tests (CS-15)", () => {
  it("CS-15-AC4: mockAttention filters keys based on user permissions", () => {
    // Quản lý: 6 khoá (không có expired_batches_open — chỉ Chủ có quyền xử lý lô quá hạn)
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
    expect(qlBody.expired_batches_open).toBeUndefined();

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
    expect(csBody.expired_batches_open).toBeUndefined();

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
    expect(khoBody.expired_batches_open).toBeUndefined();

    // Giao: 403
    const giaoReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-giao1-9999999999999",
    };
    const giaoRes = mockAttention(giaoReq as any);
    expect(giaoRes.status).toBe(403);
  });

  it("SR-15-AC4: Chủ (loc) có expired_batches_open = số lô quá hạn còn tồn; người khác không có", () => {
    const req = { method: "GET", path: "/api/dashboard/attention/", token: "mock-token-loc-9999999999999" };
    const res = mockAttention(req as any);
    expect(res.status).toBe(200);
    expect((res.body as Record<string, number>).expired_batches_open).toBe(3);
  });

  it("SR-15-AC4: người không có quyền nào trong 4 quyền (kể cả xử lý lô quá hạn) vẫn 403", () => {
    const req = { method: "GET", path: "/api/dashboard/attention/", token: "mock-token-giao1-9999999999999" };
    expect(mockAttention(req as any).status).toBe(403);
  });
});

describe("Overview orders (SR-17-AC3)", () => {
  it("filterRecentOrders chỉ lọc theo mã đơn / trạng thái, không theo tên khách", () => {
    const rows = [
      { code: "DH-1", amount: 1, status: "PAID", status_label: "Đã thanh toán", expires_at: null },
      { code: "DH-2", amount: 2, status: "BOOKED", status_label: "Giữ chỗ", expires_at: null },
    ] as RecentOrder[];
    expect(filterRecentOrders(rows, "DH-2").map((o) => o.code)).toEqual(["DH-2"]);
    expect(filterRecentOrders(rows, "giữ chỗ").map((o) => o.code)).toEqual(["DH-2"]);
  });

  it("dữ liệu mock của dashboard không có tên khách / SĐT trong recent_orders", () => {
    const body = buildDashboardSummaryMock({ username: "loc", can_cost: true });
    expect(body.recent_orders.length).toBeGreaterThan(0);
    for (const o of body.recent_orders) {
      expect(Object.keys(o)).not.toContain("customer");
      expect(Object.keys(o)).not.toContain("phone_last4");
    }
    expect(JSON.stringify(body)).not.toMatch(/Chị Mai|Anh Khoa|Nhà hàng|Quán Ốc|Khách lẻ/);
  });
});
