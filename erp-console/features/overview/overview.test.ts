import { describe, it, expect } from "vitest";
import { buildDashboardSummaryMock } from "@/shared/lib/dashboardSummary.mock";
import { filterRecentOrders, readConfirmationCounts } from "./api";
import { mockAttention } from "./mock";
import type { RecentOrder } from "./types";

describe("Overview Attention Tests (CS-15)", () => {
  it("CS-15-AC4: mockAttention filters keys based on user permissions", () => {
    // Quản lý: 6 khoá (không có expired_batches_open — chỉ Chủ có quyền xử lý lô quá hạn)
    const managerReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-ql1-9999999999999",
    };
    const managerRes = mockAttention(managerReq as any);
    expect(managerRes.status).toBe(200);
    const managerBody = managerRes.body as Record<string, number>;
    expect(managerBody.confirmation_queue_waiting).toBeDefined();
    expect(managerBody["cskh_queue_waiting"]).toBeDefined(); // khoá cũ BE còn trả song song tới Lô 5
    expect(managerBody.refund_calls_open).toBeDefined();
    expect(managerBody.confirmation_escalated).toBeDefined();
    expect(managerBody.confirmation_auto_cancel_blocked).toBeDefined();
    expect(managerBody["cskh_escalated"]).toBeDefined();
    expect(managerBody["cskh_auto_cancel_blocked"]).toBeDefined();
    expect(managerBody.labels_not_printed).toBeDefined();
    expect(managerBody.labels_to_void).toBeDefined();
    expect(managerBody.expired_batches_open).toBeUndefined();

    // CSKH: only queue and refund calls
    const csReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-cs1-9999999999999",
    };
    const csRes = mockAttention(csReq as any);
    expect(csRes.status).toBe(200);
    const csBody = csRes.body as Record<string, number>;
    expect(csBody.confirmation_queue_waiting).toBeDefined();
    expect(csBody.refund_calls_open).toBeDefined();
    expect(csBody.confirmation_escalated).toBeUndefined();
    expect(csBody["cskh_escalated"]).toBeUndefined();
    expect(csBody.labels_not_printed).toBeUndefined();
    expect(csBody.expired_batches_open).toBeUndefined();

    // Kho: only labels
    const warehouseReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-kho1-9999999999999",
    };
    const warehouseRes = mockAttention(warehouseReq as any);
    expect(warehouseRes.status).toBe(200);
    const warehouseBody = warehouseRes.body as Record<string, number>;
    expect(warehouseBody.labels_not_printed).toBeDefined();
    expect(warehouseBody.labels_to_void).toBeDefined();
    expect(warehouseBody.confirmation_queue_waiting).toBeUndefined();
    expect(warehouseBody["cskh_queue_waiting"]).toBeUndefined();
    expect(warehouseBody.confirmation_escalated).toBeUndefined();
    expect(warehouseBody["cskh_escalated"]).toBeUndefined();
    expect(warehouseBody.expired_batches_open).toBeUndefined();

    // Giao: 403
    const deliveryReq = {
      method: "GET",
      path: "/api/dashboard/attention/",
      token: "mock-token-giao1-9999999999999",
    };
    const deliveryRes = mockAttention(deliveryReq as any);
    expect(deliveryRes.status).toBe(403);
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

describe("readConfirmationCounts (P8b Lô 3: khoá mới, khoá cũ làm dự phòng)", () => {
  it("payload cũ (chỉ cskh_*) và payload mới (confirmation_*) cho cùng một kết quả", () => {
    const oldPayload = { "cskh_queue_waiting": 3, "cskh_escalated": 2, "cskh_auto_cancel_blocked": 1 };
    const newPayload = { confirmation_queue_waiting: 3, confirmation_escalated: 2, confirmation_auto_cancel_blocked: 1 };
    const expected = { queueWaiting: 3, escalated: 2, autoCancelBlocked: 1 };
    expect(readConfirmationCounts(oldPayload)).toEqual(expected);
    expect(readConfirmationCounts(newPayload)).toEqual(expected);
  });

  it("BE trả cả hai họ khoá: ưu tiên khoá mới, số 0 của khoá mới không bị khoá cũ đè", () => {
    const both = { confirmation_queue_waiting: 0, "cskh_queue_waiting": 9, confirmation_escalated: 4, "cskh_escalated": 4 };
    const r = readConfirmationCounts(both);
    expect(r.queueWaiting).toBe(0);
    expect(r.escalated).toBe(4);
    expect(r.autoCancelBlocked).toBeUndefined();
  });
});
