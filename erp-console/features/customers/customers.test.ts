import { describe, it, expect } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { customerSearchBody } from "./api";
import { DEFAULT_ORDERING, ORDERING_OPTIONS, asOrdering, changedFields, isValidPhone, normalizePhone, phoneSaveError, saveErrorMessage, validateField } from "./customersModel";
import { mockCustomerTimelineApi, mockCustomersApi } from "./mock";
import { parseCustomerId } from "./useCustomerDetail";
import type { CustomerDetail, CustomerListItem } from "./types";

// Mock theo contract BE Lô 6 (B2): quyền, tìm kiếm, sắp xếp, PATCH. Token mock "mock-token-<user>-<hết hạn>" (xem features/auth/mock).
const token = (username: string) => `mock-token-${username}-${Date.now() + 60_000}`;
const call = (username: string, method: "GET" | "PATCH" | "POST", path: string, body?: unknown) => mockCustomersApi({ method, path, body, token: token(username) });
const BASE = "/api/sales/customer-directory/";
type Page = { count: number; next: string | null; previous: string | null; results: CustomerListItem[] };

describe("customerSearchBody (#11: từ khoá nằm trong thân POST, không vào URL)", () => {
  it("luôn gửi ordering, cắt khoảng trắng q, chỉ gửi page từ trang 2", () => {
    expect(customerSearchBody({ q: "  ", ordering: "-last_order_at" }, 1)).toEqual({ q: "", ordering: "-last_order_at" });
    expect(customerSearchBody({ q: " 0900 ", ordering: "name" }, 2)).toEqual({ q: "0900", ordering: "name", page: 2 });
  });
});

describe("customersModel", () => {
  it("lựa chọn sắp xếp: mặc định đứng đầu, giá trị lạ về mặc định", () => {
    expect(ORDERING_OPTIONS[0].value).toBe(DEFAULT_ORDERING);
    expect(asOrdering("-total_spent")).toBe("-total_spent");
    expect(asOrdering("phone")).toBe(DEFAULT_ORDERING);
  });
  it("tên bắt buộc và giới hạn độ dài theo BE", () => {
    expect(validateField("name", "   ")).toMatch(/Nhập tên/);
    expect(validateField("name", "a".repeat(201))).toMatch(/200/);
    expect(validateField("note", "a".repeat(1001))).toMatch(/1000/);
    expect(validateField("note", "")).toBeNull();
  });
  it("gói PATCH chỉ chứa trường đổi; số điện thoại so sánh sau khi chuẩn hoá", () => {
    const cur = { name: "A", phone: "+84900000111", default_address: "", note: "x" } as CustomerDetail;
    const same = { name: "A", phone: "0900000111", default_address: "", note: "x" };
    expect(changedFields(cur, same)).toEqual({});
    expect(changedFields(cur, { ...same, name: " B " })).toEqual({ name: "B" });
    expect(changedFields(cur, { ...same, phone: "0900 000 222" })).toEqual({ phone: "0900000222" });
  });
  it("số điện thoại: chuẩn hoá giống BE, bắt buộc, đúng dạng 0 + 9-10 số", () => {
    expect(normalizePhone("+84 900.000-111")).toBe("0900000111");
    expect(normalizePhone("84900000111")).toBe("0900000111");
    expect(isValidPhone("0900000111")).toBe(true);
    expect(isValidPhone("090000011")).toBe(false);
    expect(isValidPhone("abc")).toBe(false);
    expect(validateField("phone", "  ")).toMatch(/Nhập số điện thoại/);
    expect(validateField("phone", "12345")).toMatch(/10 hoặc 11 số/);
    expect(validateField("phone", "0900000111")).toBeNull();
  });
  it("lỗi số điện thoại của BE (trùng / sai dạng) đi vào ô, lỗi khác thì không", () => {
    expect(phoneSaveError(new ApiError("Số điện thoại này đã thuộc về một khách hàng khác.", 400, "CUSTOMER_PHONE_TAKEN"))).toMatch(/khách hàng khác/);
    expect(phoneSaveError(new ApiError("Số điện thoại không hợp lệ.", 400, "INVALID_PHONE"))).toMatch(/không hợp lệ/);
    expect(phoneSaveError(new ApiError("Không có thông tin nào để cập nhật.", 400, "INPUT_EMPTY"))).toBeNull();
    expect(phoneSaveError(new Error("x"))).toBeNull();
  });
  it("câu lỗi lưu: ưu tiên câu theo trường của DRF, rồi tới detail", () => {
    expect(saveErrorMessage(new ApiError("Dữ liệu không hợp lệ.", 400, undefined, { note: ["Quá dài."] }))).toBe("Quá dài.");
    expect(saveErrorMessage(new ApiError("Không có thông tin nào để cập nhật.", 400, "INPUT_EMPTY"))).toBe("Không có thông tin nào để cập nhật.");
  });
  it("?id= chỉ nhận số nguyên dương", () => {
    expect(parseCustomerId("?id=12")).toBe(12);
    expect(parseCustomerId("?id=0")).toBeNull();
    expect(parseCustomerId("?id=abc")).toBeNull();
    expect(parseCustomerId("")).toBeNull();
  });
});

describe("mock danh bạ khách: quyền", () => {
  it("Chủ và Quản lý xem được; NV kho, NV giao, CSKH 403", () => {
    expect(call("loc", "GET", BASE).status).toBe(200);
    expect(call("ql1", "GET", BASE).status).toBe(200);
    for (const u of ["kho1", "giao1", "cs2"]) expect(call(u, "GET", BASE).status).toBe(403);
  });
  it("chưa đăng nhập → 401", () => {
    expect(mockCustomersApi({ method: "GET", path: BASE, token: null }).status).toBe(401);
  });
  it("PATCH của người chỉ có quyền xem → 403 trước khi tra bản ghi", () => {
    expect(call("kho1", "PATCH", `${BASE}999999/`, { note: "x" }).status).toBe(403);
  });
});

describe("mock danh bạ khách: danh sách", () => {
  const list = (q: string) => call("loc", "GET", `${BASE}${q}`);
  it("20 dòng/trang, có trang 2, mặc định đơn gần nhất mới trước, khách chưa mua cuối", () => {
    const p1 = list("").body as Page;
    expect(p1.results).toHaveLength(20);
    expect(p1.next).not.toBeNull();
    const p2 = list("?page=2").body as Page;
    expect(p2.results.length).toBe(p1.count - 20);
    const all = [...p1.results, ...p2.results];
    const times = all.filter((c) => c.last_order_at).map((c) => Date.parse(c.last_order_at as string));
    expect([...times].sort((a, b) => b - a)).toEqual(times);
    expect(all[all.length - 1].last_order_at).toBeNull();
  });
  it("khoá ordering lạ quay về mặc định; -total_spent giảm dần", () => {
    const def = (list("").body as Page).results.map((c) => c.id);
    expect((list("?ordering=phone").body as Page).results.map((c) => c.id)).toEqual(def);
    const spent = (list("?ordering=-total_spent").body as Page).results.map((c) => Number(c.total_spent));
    expect([...spent].sort((a, b) => b - a)).toEqual(spent);
  });
  it("q khớp tên bỏ dấu; SĐT cần ≥ 4 chữ số (qua POST search/, Lô 17b-BE)", () => {
    const search = (q: string) => call("loc", "POST", `${BASE}search/`, { q }).body as Page;
    expect(search("khach thu a").results.some((c) => c.name === "Khách Thử A")).toBe(true);
    const phone = (list("").body as Page).results[0].phone;
    expect(search(phone.slice(-4)).results.some((c) => c.phone === phone)).toBe(true);
    expect(search("090").count).toBe(0); // 3 chữ số: không dò danh bạ
  });
  it("GET có q không rỗng → 400 SEARCH_USE_POST, câu lỗi không lặp lại q; q rỗng vẫn liệt kê", () => {
    const r = list("?q=0912345678");
    expect(r.status).toBe(400);
    expect(r.body).toMatchObject({ code: "SEARCH_USE_POST", detail: "Tìm khách dùng ô tìm trên màn Khách hàng." });
    expect(JSON.stringify(r.body)).not.toContain("0912345678");
    expect(list("?q=").status).toBe(200);
  });
  it("khoá của một dòng đúng contract (cancelled_count, không có default_address)", () => {
    const row = (list("").body as Page).results[0];
    expect(Object.keys(row).sort()).toEqual(["cancelled_count", "id", "last_order_at", "name", "note", "order_count", "phone", "total_spent"]);
  });
});

describe("mock danh bạ khách: chi tiết và PATCH", () => {
  it("chi tiết có đơn, phiếu hoàn (không có lý do), tổng đã mua không tính đơn huỷ", () => {
    const d = call("loc", "GET", `${BASE}1/`).body as CustomerDetail;
    expect(d.orders.length).toBeGreaterThan(0);
    expect(d.orders.length).toBeLessThanOrEqual(50);
    expect(Object.keys(d.refunds[0] ?? { id: 1, order_code: 1, status: 1, status_label: 1, amount: 1, created_at: 1 }).sort()).toEqual(["amount", "created_at", "id", "order_code", "status", "status_label"]);
    const live = d.orders.filter((o) => !/CANCELLED/.test(o.status)).reduce((s, o) => s + Number(o.total_amount), 0);
    expect(Number(d.total_spent)).toBe(live);
    expect(d.cancelled_count).toBe(d.orders.filter((o) => o.status === "CANCELLED" || o.status === "AUTO_CANCELLED").length);
  });
  it("id không tồn tại → 404", () => {
    expect(call("loc", "GET", `${BASE}999999/`).status).toBe(404);
  });
  it("PATCH: một phần, trả thân chi tiết; thân rỗng/khoá lạ/không phải chuỗi/quá dài → 400", () => {
    const ok = call("loc", "PATCH", `${BASE}5/`, { note: "Ghi chú kiểm thử" });
    expect(ok.status).toBe(200);
    expect((ok.body as CustomerDetail).note).toBe("Ghi chú kiểm thử");
    const blocked = call("loc", "PATCH", `${BASE}5/`, { id: 99 });
    expect(blocked.status).toBe(400);
    expect((blocked.body as { code: string }).code).toBe("INPUT_NOT_ALLOWED");
    expect((call("loc", "PATCH", `${BASE}5/`, {}).body as { code: string }).code).toBe("INPUT_EMPTY");
    expect(call("loc", "PATCH", `${BASE}5/`, { name: 12 }).status).toBe(400);
    expect(call("loc", "PATCH", `${BASE}5/`, { name: "a".repeat(201) }).status).toBe(400);
  });
  it("PATCH phone: chuẩn hoá +84, sai dạng INVALID_PHONE, trùng khách khác CUSTOMER_PHONE_TAKEN (không lặp lại số)", () => {
    const ok = call("loc", "PATCH", `${BASE}6/`, { phone: "+84 900 000 777" });
    expect(ok.status).toBe(200);
    expect((ok.body as CustomerDetail).phone).toBe("0900000777");
    const bad = call("loc", "PATCH", `${BASE}6/`, { phone: "12345" });
    expect(bad.status).toBe(400);
    expect((bad.body as { code: string }).code).toBe("INVALID_PHONE");
    const taken = call("loc", "PATCH", `${BASE}7/`, { phone: "0900000777" });
    expect(taken.status).toBe(400);
    expect((taken.body as { code: string; detail: string }).code).toBe("CUSTOMER_PHONE_TAKEN");
    expect(JSON.stringify(taken.body)).not.toMatch(/\d{9}/);
    expect(call("loc", "PATCH", `${BASE}6/`, { phone: "0900000777" }).status).toBe(200); // giữ nguyên số của chính mình: không báo trùng
  });
  it("POST search: cùng shape với danh sách, tìm theo q trong thân, page trong thân; quyền như GET", () => {
    const search = (user: string, body: unknown) => call(user, "POST", `${BASE}search/`, body);
    const all = search("loc", { q: "", ordering: "-last_order_at" }).body as Page;
    expect(all.results).toHaveLength(20);
    const p2 = search("loc", { q: "", ordering: "-last_order_at", page: 2 }).body as Page;
    expect(p2.results.length).toBe(all.count - 20);
    expect((search("loc", { q: "khach thu a" }).body as Page).results.some((c) => c.name === "Khách Thử A")).toBe(true);
    expect((search("loc", { q: "090" }).body as Page).count).toBe(0);
    expect(search("loc", { q: "", page: 0 }).status).toBe(400);
    for (const u of ["kho1", "giao1", "cs2"]) expect(search(u, { q: "" }).status).toBe(403);
    expect(mockCustomersApi({ method: "POST", path: `${BASE}search/`, body: {}, token: null }).status).toBe(401);
    expect(call("loc", "POST", `${BASE}5/`, {}).status).toBe(405);
  });
  it("timeline khách: nhãn không chứa số điện thoại; ngoài quyền 403", () => {
    const t = mockCustomerTimelineApi({ method: "GET", path: "/api/guidance/customer/1/", token: token("loc") });
    expect(t.status).toBe(200);
    expect(JSON.stringify(t.body)).not.toMatch(/0900000\d{3}/);
    expect(mockCustomerTimelineApi({ method: "GET", path: "/api/guidance/customer/1/", token: token("kho1") }).status).toBe(403);
  });
});
