// Lô 17b NEW-1: tìm đơn theo SĐT/tên chỉ qua POST /api/sales/orders/search/ (từ khoá không vào URL, bất biến 9); GET ?q= chỉ khớp mã đơn.
import { describe, expect, it } from "vitest";
import { orderListQuery, orderSearchBody } from "./api";
import { mockOrdersApi } from "./mock";
import type { OrderListItem, OrderListParams } from "./types";

const tok = (u: string) => `mock-token-${u}-${Date.now() + 60_000}`;
const get = (path: string, user = "loc") => mockOrdersApi({ method: "GET", path, token: tok(user) });
const post = (body: unknown, user = "loc") => mockOrdersApi({ method: "POST", path: "/api/sales/orders/search/", body, token: tok(user) });
type Page = { count: number; next: string | null; results: OrderListItem[] };

const base: OrderListParams = { status: "", date_from: "", date_to: "", q: "" };

describe("orderListQuery / orderSearchBody", () => {
  it("URL không bao giờ có q (kể cả khi người dùng gõ SĐT)", () => {
    expect(orderListQuery({ ...base, q: "0912345678", status: "PAID" }, 1)).toBe("?status=PAID");
    expect(orderListQuery({ ...base, q: "SO2610" }, 2)).toBe("?page=2");
  });
  it("thân POST: q, status là mảng chuỗi, page chỉ khi > 1, bỏ khoá rỗng", () => {
    expect(orderSearchBody({ ...base, q: " An " }, 1)).toEqual({ q: "An" });
    expect(orderSearchBody({ ...base, q: "x", status: "BOOKED,PAID", date_from: "2026-10-01", customer: "7" }, 3)).toEqual({
      q: "x",
      status: ["BOOKED", "PAID"],
      date_from: "2026-10-01",
      customer: "7",
      page: 3,
    });
  });
});

describe("mock POST search/", () => {
  it("tìm theo SĐT và theo tên bỏ dấu ra đơn; cùng dạng phân trang với GET", () => {
    const all = get("/api/sales/orders/").body as Page;
    const sample = all.results[0];
    const detail = mockOrdersApi({ method: "GET", path: `/api/sales/orders/${sample.id}/`, token: tok("loc") }).body as { customer: { phone: string; name: string } };
    const byPhone = post({ q: detail.customer.phone.slice(-6) }).body as Page;
    expect(byPhone.results.some((o) => o.id === sample.id)).toBe(true);
    expect(Object.keys(byPhone).sort()).toEqual(Object.keys(all).sort());
    const byName = post({ q: detail.customer.name.toLowerCase() }).body as Page;
    expect(byName.count).toBeGreaterThan(0);
  });
  it("GET ?q=<SĐT> không còn khớp SĐT (400 SEARCH_USE_POST); chuỗi mã vẫn chạy", () => {
    const r = get("/api/sales/orders/?q=0912345678");
    expect(r.status).toBe(400);
    expect(r.body).toMatchObject({ code: "SEARCH_USE_POST" });
    expect(JSON.stringify(r.body)).not.toContain("0912345678");
    expect(get("/api/sales/orders/?q=An%20Binh").status).toBe(400);
    expect(get("/api/sales/orders/?q=Nguy%E1%BB%85n").status).toBe(400);
    const code = (get("/api/sales/orders/").body as Page).results[0].code;
    const hit = get(`/api/sales/orders/?q=${code}`).body as Page;
    expect(hit.results.map((o) => o.code)).toContain(code);
  });
  it("status chuỗi hoặc mảng chuỗi đều được, số thì 400; q không phải chuỗi thì 400; page vượt thì 404", () => {
    expect(post({ q: "", status: "PAID" }).status).toBe(200);
    expect(post({ status: ["PAID", "BOOKED"] }).status).toBe(200);
    expect(post({ status: [1] }).status).toBe(400);
    expect(post({ q: 12 }).status).toBe(400);
    expect(post({ page: 999 }).status).toBe(404);
  });
  it("`next` không chứa từ khoá", () => {
    const r = post({ q: "SO" }).body as Page;
    if (r.next) expect(r.next).not.toContain("q=");
  });
  it("chưa đăng nhập 401", () => {
    expect(mockOrdersApi({ method: "POST", path: "/api/sales/orders/search/", body: {}, token: null }).status).toBe(401);
  });
});
