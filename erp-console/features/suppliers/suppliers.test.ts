import { describe, it, expect } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { supplierListQuery } from "./api";
import { mockSuppliersApi } from "./mock";
import {
  ACTIVE_OPTIONS,
  EMPTY_DRAFT,
  TYPE_OPTIONS,
  asActiveFilter,
  asTypeFilter,
  changedFields,
  draftOf,
  inputOf,
  isNameTaken,
  nameTakenMessage,
  saveErrorMessage,
  shouldResetSaveErrorOnNameEdit,
  topFormError,
  validateField,
} from "./suppliersModel";
import { parseSupplierId } from "./useSupplierDetail";
import type { Supplier } from "./types";

// Mock theo contract BE Lô 11 (B3): quyền, số liệu chỉ phiếu Đã ghi nhận, khoá tiền chỉ Chủ, tên trùng, 405.
// Token mock "mock-token-<user>-<hết hạn>" (xem features/auth/mock).
const token = (username: string) => `mock-token-${username}-${Date.now() + 60_000}`;
const call = (username: string, method: "GET" | "POST" | "PATCH" | "DELETE" | "PUT", path: string, body?: unknown) => mockSuppliersApi({ method, path, body, token: token(username) });
const BASE = "/api/purchasing/suppliers/";
type Page = { count: number; next: string | null; previous: string | null; results: Supplier[] };
const pageOf = (username: string, path = BASE) => call(username, "GET", path).body as Page;

describe("supplierListQuery", () => {
  it("bỏ tham số rỗng, đúng tên tham số contract, chỉ gửi page từ trang 2", () => {
    expect(supplierListQuery({ q: "  ", type: "", active: "" }, 1)).toBe("");
    expect(supplierListQuery({ q: " lagi ", type: "COMPANY", active: "0" }, 2)).toBe("?q=lagi&supplier_type=COMPANY&is_active=0&page=2");
  });
});

describe("suppliersModel", () => {
  it("lựa chọn lọc: mục đầu là không lọc, giá trị lạ về không lọc", () => {
    expect(TYPE_OPTIONS[0].value).toBe("");
    expect(ACTIVE_OPTIONS[0].value).toBe("");
    expect(asTypeFilter("COMPANY")).toBe("COMPANY");
    expect(asTypeFilter("x")).toBe("");
    expect(asActiveFilter("0")).toBe("0");
    expect(asActiveFilter("maybe")).toBe("");
  });
  it("tên bắt buộc, giới hạn độ dài theo BE (tên 200, số điện thoại 20)", () => {
    expect(validateField("name", "   ")).toMatch(/Nhập tên/);
    expect(validateField("name", "a".repeat(201))).toMatch(/200/);
    expect(validateField("name", "Vựa A")).toBeNull();
    expect(validateField("phone", "1".repeat(21))).toMatch(/20/);
    expect(validateField("phone", "")).toBeNull();
    expect(validateField("note", "a".repeat(1001))).toMatch(/1000/);
  });
  it("gói tạo mới cắt khoảng trắng; mặc định Cá nhân, đang hợp tác", () => {
    expect(EMPTY_DRAFT).toMatchObject({ supplier_type: "INDIVIDUAL", is_active: true });
    expect(inputOf({ ...EMPTY_DRAFT, name: "  Vựa A  ", phone: " 0901 " })).toMatchObject({ name: "Vựa A", phone: "0901" });
  });
  it("gói PATCH chỉ chứa trường đổi, không bao giờ có trường tính toán", () => {
    const cur = { id: 1, name: "A", supplier_type: "INDIVIDUAL", phone: "", note: "x", is_active: true, receipt_count: 3, last_received_at: null } as Supplier;
    expect(changedFields(cur, draftOf(cur))).toEqual({});
    const out = changedFields(cur, { ...draftOf(cur), name: " B ", supplier_type: "COMPANY" });
    expect(out).toEqual({ name: "B", supplier_type: "COMPANY" });
    expect("receipt_count" in out).toBe(false);
    expect("purchase_total" in out).toBe(false);
  });
  it("nhận ra tên trùng ở CẢ HAI dạng 400 của BE và lấy câu của BE", () => {
    const asField = new ApiError("Đã có nhà cung cấp trùng tên này.", 400, undefined, { name: ["Đã có nhà cung cấp trùng tên này."] });
    const asCode = new ApiError("Đã có nhà cung cấp trùng tên này.", 400, "SUPPLIER_NAME_TAKEN");
    expect(isNameTaken(asField)).toBe(true);
    expect(isNameTaken(asCode)).toBe(true);
    expect(nameTakenMessage(asField)).toBe("Đã có nhà cung cấp trùng tên này.");
    expect(nameTakenMessage(asCode)).toBe("Đã có nhà cung cấp trùng tên này.");
    expect(isNameTaken(new ApiError("x", 400, "INVALID_FILTER"))).toBe(false);
    expect(isNameTaken(new ApiError("x", 500))).toBe(false);
    expect(isNameTaken(new Error("x"))).toBe(false);
  });
  it("câu lỗi lưu: ưu tiên câu theo trường của DRF, rồi tới detail", () => {
    expect(saveErrorMessage(new ApiError("Dữ liệu không hợp lệ.", 400, undefined, { phone: ["Quá dài."] }))).toBe("Quá dài.");
    expect(saveErrorMessage(new ApiError("Máy chủ đang bận.", 500))).toBe("Máy chủ đang bận.");
  });
  it("B1: sau lỗi trùng tên, lỗi chung của lần gửi cũ không được nhảy lên đầu form khi gỡ ghim tên trùng", () => {
    const taken = "Đã có nhà cung cấp trùng tên này.";
    // Ngay sau lần gửi lỗi: tên trùng ghim dưới ô Tên, đầu form không lặp lại.
    const afterFail = { nameServerError: taken, submitNameError: null, submitError: taken };
    expect(topFormError(afterFail)).toBeNull();
    // Người dùng gõ tên khác: phải xoá lỗi của lần gửi (reset) thì mới hết hẳn.
    expect(shouldResetSaveErrorOnNameEdit(afterFail)).toBe(true);
    // Mô phỏng thứ tự cũ (chỉ gỡ ghim, quên reset): lỗi cũ lộ ra ở đầu form. Đây là lỗi QA đã bắt.
    expect(topFormError({ ...afterFail, nameServerError: null })).toBe(taken);
    // Sau reset đúng: không còn lỗi nào để hiện.
    expect(topFormError({ nameServerError: null, submitNameError: null, submitError: null })).toBeNull();
    // Lỗi 400 theo trường name (không qua ghim) cũng bị xoá khi sửa tên.
    expect(shouldResetSaveErrorOnNameEdit({ nameServerError: null, submitNameError: taken, submitError: taken })).toBe(true);
    // Lỗi chung khác (500) vẫn hiện ở đầu form và cũng được xoá khi người dùng bắt đầu sửa lại tên.
    const offline = { nameServerError: null, submitNameError: null, submitError: "Máy chủ đang bận." };
    expect(topFormError(offline)).toBe("Máy chủ đang bận.");
    expect(shouldResetSaveErrorOnNameEdit(offline)).toBe(true);
    // Chưa có lỗi nào thì không cần reset.
    expect(shouldResetSaveErrorOnNameEdit({ nameServerError: null, submitNameError: null, submitError: null })).toBe(false);
  });
  it("?id= chỉ nhận số nguyên dương", () => {
    expect(parseSupplierId("?id=12")).toBe(12);
    expect(parseSupplierId("?id=0")).toBeNull();
    expect(parseSupplierId("?id=abc")).toBeNull();
    expect(parseSupplierId("")).toBeNull();
  });
});

describe("mock nhà cung cấp: quyền", () => {
  it("Chủ, Quản lý, NV kho xem được; NV giao và CSKH 403; chưa đăng nhập 401", () => {
    for (const u of ["loc", "ql1", "kho1"]) expect(call(u, "GET", BASE).status).toBe(200);
    for (const u of ["giao1", "cs2"]) expect(call(u, "GET", BASE).status).toBe(403);
    expect(mockSuppliersApi({ method: "GET", path: BASE, token: null }).status).toBe(401);
  });
  it("tạo / sửa: Chủ và Quản lý được, NV kho 403", () => {
    expect(call("kho1", "POST", BASE, { name: "Vựa Kho Thử" }).status).toBe(403);
    expect(call("kho1", "PATCH", `${BASE}1/`, { note: "x" }).status).toBe(403);
    expect(call("ql1", "POST", BASE, { name: "Vựa Quản Lý Thử" }).status).toBe(201);
  });
  it("không có DELETE / PUT", () => {
    expect(call("loc", "DELETE", `${BASE}1/`).status).toBe(405);
    expect(call("loc", "PUT", `${BASE}1/`, { name: "Z" }).status).toBe(405);
  });
});

describe("mock nhà cung cấp: khoá tiền và số liệu", () => {
  it("tổng tiền mua CHỈ Chủ có key; Quản lý và NV kho không có key (không phải null)", () => {
    expect("purchase_total" in pageOf("loc").results[0]).toBe(true);
    for (const u of ["ql1", "kho1"]) {
      for (const row of pageOf(u).results) expect("purchase_total" in row).toBe(false);
    }
    expect("purchase_total" in (call("ql1", "GET", `${BASE}1/`).body as Supplier)).toBe(false);
  });
  it("số phiếu / lần nhập / tổng tiền chỉ tính phiếu Đã ghi nhận; nhà cung cấp chưa có phiếu → 0 / null / 0.00", () => {
    const rows = pageOf("loc").results;
    const withDraft = rows.find((r) => r.name === "Đầu mối Cảng cá Phan Thiết");
    expect(withDraft).toMatchObject({ receipt_count: 4, purchase_total: "37451000.00" });
    const none = rows.find((r) => r.name === "Vựa Phước Hải");
    expect(none).toMatchObject({ receipt_count: 0, last_received_at: null, purchase_total: "0.00" });
  });
  it("bảng phiếu nhập: tiền mua chỉ Chủ có key; thiếu quyền xem phiếu → 403", () => {
    const owner = call("loc", "GET", "/api/purchasing/receipts/?supplier=1").body as { results: { purchase_amount?: string }[] };
    expect(owner.results.every((r) => r.purchase_amount !== undefined)).toBe(true);
    const manager = call("ql1", "GET", "/api/purchasing/receipts/?supplier=1").body as { results: { purchase_amount?: string }[] };
    expect(manager.results.every((r) => !("purchase_amount" in r))).toBe(true);
    expect(call("giao1", "GET", "/api/purchasing/receipts/?supplier=1").status).toBe(403);
  });
});

describe("mock nhà cung cấp: lọc, tạo, sửa", () => {
  it("lọc theo loại và trạng thái; lọc sai → 400 INVALID_FILTER", () => {
    expect(pageOf("loc", `${BASE}?supplier_type=COMPANY`).results.every((r) => r.supplier_type === "COMPANY")).toBe(true);
    expect(pageOf("loc", `${BASE}?is_active=0`).results.every((r) => !r.is_active)).toBe(true);
    const bad = call("loc", "GET", `${BASE}?is_active=maybe`);
    expect(bad.status).toBe(400);
    expect((bad.body as { code: string }).code).toBe("INVALID_FILTER");
  });
  it("tên trùng (không phân biệt hoa thường) → 400 {name:[…]}", () => {
    const res = call("loc", "POST", BASE, { name: "vựa cá lagi (anh ba)" });
    expect(res.status).toBe(400);
    expect((res.body as { name: string[] }).name[0]).toMatch(/trùng tên/);
  });
  it("tên rỗng và số điện thoại quá 20 ký tự → 400 theo trường", () => {
    expect(call("loc", "POST", BASE, { name: "  " }).status).toBe(400);
    const res = call("loc", "POST", BASE, { name: "Vựa Số Dài", phone: "1".repeat(21) });
    expect((res.body as { phone?: string[] }).phone).toBeTruthy();
  });
  it("Ngừng hợp tác rồi bật lại là PATCH is_active; sửa chính mình không bị coi là trùng", () => {
    expect((call("loc", "PATCH", `${BASE}5/`, { is_active: false }).body as Supplier).is_active).toBe(false);
    expect((call("loc", "PATCH", `${BASE}5/`, { is_active: true }).body as Supplier).is_active).toBe(true);
    expect(call("loc", "PATCH", `${BASE}5/`, { name: "Công ty Hải sản Nam Bộ" }).status).toBe(200);
  });
  it("không có nhà cung cấp → 404", () => {
    expect(call("loc", "GET", `${BASE}9999/`).status).toBe(404);
  });
});
