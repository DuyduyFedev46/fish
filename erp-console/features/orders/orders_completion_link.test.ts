import { beforeAll, describe, expect, it, vi } from "vitest";
import { mockOrdersApi, mockOrdersOverviewSlice } from "./mock";
import { mockPostDeliveryNoteStatus } from "@/features/deliveries/mock";
import { publishOrderCancelled } from "@/shared/lib/orderLink.mock";
import type { OrderDetail, OrderListItem } from "./types";

// W37 S6-AC1, S6-AC8, S7-AC5: bộ đơn mẫu "completion" và việc mock Giao hàng làm mock Đơn đổi theo (kho nối orderLink.mock).
const tok = (u: string) => `mock-token-${u}-${Date.now() + 1000}`;
const list = (status: string) =>
  (mockOrdersApi({ method: "GET", path: `/api/sales/orders/?status=${status}`, token: tok("loc") }).body as { results: OrderListItem[] }).results;
const detail = (id: number) => mockOrdersApi({ method: "GET", path: `/api/sales/orders/${id}/`, token: tok("loc") }).body as OrderDetail;
const completeNote = (id: number) =>
  mockPostDeliveryNoteStatus({ url: `/api/delivery/notes/${id}/status/`, body: { to_status: "COMPLETED", from_status: "DELIVERING" }, token: tok("loc") });

beforeAll(() => {
  const store = new Map<string, string>();
  const area = (init: Record<string, string>) => {
    Object.entries(init).forEach(([k, v]) => store.set(`${k}`, v));
    return { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v), removeItem: (k: string) => void store.delete(k) };
  };
  vi.stubGlobal("window", { localStorage: area({ cave_erp_mock_orders_dataset: "completion" }), sessionStorage: area({}) });
});

describe("bộ mẫu S6-AC1", () => {
  it("1 giữ chỗ · 2 đang xử lý · 3 hoàn tất · 1 huỷ; không có Đã thanh toán", () => {
    expect(list("BOOKED")).toHaveLength(1);
    expect(list("PROCESSING")).toHaveLength(2);
    expect(list("COMPLETED")).toHaveLength(3);
    expect(list("CANCELLED")).toHaveLength(1);
    expect(list("PAID")).toHaveLength(0);
    expect(list("BOOKED,PAID,PROCESSING")).toHaveLength(3);
  });

  it("trạng thái đơn suy từ phiếu (BR-BH-18): phiếu Đang giao và Giao thất bại đều là Đang xử lý", () => {
    const proc = list("PROCESSING").map((o) => o.delivery_status).sort();
    expect(proc).toEqual(["DELIVERING", "FAILED"]);
    expect(list("COMPLETED").every((o) => o.delivery_status === "COMPLETED")).toBe(true);
  });

  it("S7-AC5: đơn Hoàn tất có refund_summary Đã hoàn 200.000 + Chờ hoàn 100.000, vẫn Hoàn tất, còn hoàn được", () => {
    const o = list("COMPLETED").find((x) => detail(x.id).refunds.length === 2)!;
    const d = detail(o.id);
    expect(d.status).toBe("COMPLETED");
    expect(d.refund_summary).toEqual({ refunded_amount: "200000", pending_amount: "100000" });
    expect(d.available_actions).toContain("create_refund");
    expect(d.available_actions).not.toContain("cancel");
  });
});

describe("nối mock Giao hàng và mock Đơn (S6-AC8)", () => {
  it("Tổng quan mock khớp bộ lọc: 3 đơn chưa xong", () => {
    expect(mockOrdersOverviewSlice()?.pending).toBe(3);
  });

  it("giao xong phiếu của đơn đang xử lý → đơn tự Hoàn tất, bộ lọc và Tổng quan đổi theo, doanh thu không liên quan", () => {
    const target = list("PROCESSING").find((o) => o.delivery_status === "FAILED")!; // đơn 103 ↔ phiếu 33
    expect(target.id).toBe(103);
    const res = completeNote(33);
    expect((res.body as { order_status: string }).order_status).toBe("COMPLETED");
    expect(detail(103).status).toBe("COMPLETED");
    expect(detail(103).delivery?.status).toBe("COMPLETED");
    expect(list("BOOKED,PAID,PROCESSING")).toHaveLength(2);
    expect(list("COMPLETED")).toHaveLength(4);
    expect(mockOrdersOverviewSlice()?.pending).toBe(2);
  });

  it("đơn đã huỷ ở mock Đơn: phiếu cũ chưa huỷ vẫn bị chặn BR-GH-24 (Low #3 của review L1)", () => {
    publishOrderCancelled(108);
    const res = mockPostDeliveryNoteStatus({ url: "/api/delivery/notes/38/status/", body: { to_status: "COMPLETED", from_status: "DELIVERING" }, token: tok("loc") });
    expect(res.status).toBe(400);
    expect(res.body).toMatchObject({ code: "BR-GH-24", current_status: "CANCELLED" });
  });
});
