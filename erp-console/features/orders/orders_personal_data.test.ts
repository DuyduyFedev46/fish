import { describe, it, expect } from "vitest";
import { mockOrdersApi } from "./mock";
import type { OrderDetail, OrderListItem } from "./types";

// SR-PII-02 (BR-PQ-12, bất biến 9): NV giao không thấy tên/SĐT/địa chỉ của phiếu đã giao quá 7 ngày.
// Đơn 143 trong mock là đơn của giao1 đã hoàn tất ~10 ngày trước; đơn 104 là đơn giao1 đang soạn.
const OLD_ID = 143;
const RECENT_ID = 104;

function tokenFor(username: string): string {
  return `mock-token-${username}-${Date.now() + 1000}`;
}
function get(username: string, path: string) {
  return mockOrdersApi({ method: "GET", path, token: tokenFor(username) });
}

describe("Orders mock: dữ liệu khách của NV giao theo thời hạn 7 ngày", () => {
  it("giao1 mở đơn đã giao 10 ngày trước -> customer.* = null, mã đơn vẫn có", () => {
    const res = get("giao1", `/api/sales/orders/${OLD_ID}/`);
    expect(res.status).toBe(200);
    const body = res.body as OrderDetail;
    expect(body.code).toBeTruthy();
    expect(body.customer).toEqual({ name: null, phone: null, address: null });
  });

  it("giao1 mở đơn đang giao -> vẫn thấy tên, SĐT, địa chỉ", () => {
    const body = get("giao1", `/api/sales/orders/${RECENT_ID}/`).body as OrderDetail;
    expect(body.customer.name).toBeTruthy();
    expect(body.customer.phone).toBeTruthy();
    expect(body.customer.address).toBeTruthy();
  });

  it("Chủ vẫn thấy đủ dữ liệu khách của đơn cũ", () => {
    const body = get("loc", `/api/sales/orders/${OLD_ID}/`).body as OrderDetail;
    expect(body.customer.name).toBeTruthy();
    expect(body.customer.phone).toBeTruthy();
  });

  it("danh sách của giao1: đơn cũ có customer_name/phone null, đơn mới có giá trị", () => {
    const res = get("giao1", "/api/sales/orders/?page=1");
    const rows = (res.body as { results: OrderListItem[] }).results;
    expect(rows.length).toBeGreaterThan(0);
    const all: OrderListItem[] = [];
    for (let p = 1; p <= 3; p++) {
      const r = get("giao1", `/api/sales/orders/?page=${p}`);
      if (r.status !== 200) break;
      all.push(...(r.body as { results: OrderListItem[] }).results);
    }
    const old = all.find((r) => r.id === OLD_ID);
    const recent = all.find((r) => r.id === RECENT_ID);
    expect(old?.customer_name).toBeNull();
    expect(old?.customer_phone).toBeNull();
    expect(recent?.customer_name).toBeTruthy();
  });

  it("tìm theo SĐT/tên không khớp đơn đã ẩn (chống dò)", () => {
    const phone = (get("loc", `/api/sales/orders/${OLD_ID}/`).body as OrderDetail).customer.phone;
    const res = get("giao1", `/api/sales/orders/?q=${phone}`);
    const rows = (res.body as { results: OrderListItem[] }).results;
    expect(rows.some((r) => r.id === OLD_ID)).toBe(false);
  });

  it("cs2 (cskh + nv_giao): đơn 142 đã giao 11 ngày trước bị ẩn khách; kho1 (nv_kho + nv_giao) vẫn thấy đủ", () => {
    const hidden = get("cs2", "/api/sales/orders/142/").body as OrderDetail;
    expect(hidden.customer).toEqual({ name: null, phone: null, address: null });
    const full = get("kho1", "/api/sales/orders/142/").body as OrderDetail;
    expect(full.customer.name).toBeTruthy();
  });
});
