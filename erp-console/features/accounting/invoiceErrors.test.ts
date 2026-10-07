import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { mockInvoiceCreate } from "./mock";
import { invoiceFieldError } from "./invoiceErrors";

const token = (u: string) => `mock-token-${u}-${Date.now() + 60_000}`;
const post = (body: object, user = "loc") => mockInvoiceCreate({ method: "POST", path: "/api/purchasing/invoices/", body, token: token(user) });
const ok = { supplier: 1, receipt: null, amount: "1000000", invoice_date: "2026-10-01", is_paid: false, paid_at: null };

describe("hoá đơn mua: 5 mã lỗi Lô 17a (mock theo contract)", () => {
  it("hợp lệ → 201", () => {
    expect(post(ok).status).toBe(201);
    expect(post({ ...ok, is_paid: true, paid_at: new Date().toISOString() }).status).toBe(201);
  });
  it("số tiền 0 → AMOUNT_NOT_POSITIVE", () => {
    const r = post({ ...ok, amount: "0" });
    expect(r.status).toBe(400);
    expect(r.body).toMatchObject({ code: "AMOUNT_NOT_POSITIVE", detail: "Số tiền hoá đơn phải lớn hơn 0." });
  });
  it("đã trả mà thiếu giờ trả → PAID_AT_REQUIRED", () => {
    expect(post({ ...ok, is_paid: true, paid_at: null }).body).toMatchObject({ code: "PAID_AT_REQUIRED" });
  });
  it("chưa trả mà có giờ trả → PAID_AT_WHEN_UNPAID", () => {
    expect(post({ ...ok, paid_at: new Date().toISOString() }).body).toMatchObject({ code: "PAID_AT_WHEN_UNPAID" });
  });
  it("giờ trả ở tương lai (quá 5 phút) → PAID_AT_IN_FUTURE; lệch 1 phút thì chịu được", () => {
    expect(post({ ...ok, is_paid: true, paid_at: new Date(Date.now() + 3_600_000).toISOString() }).body).toMatchObject({ code: "PAID_AT_IN_FUTURE" });
    expect(post({ ...ok, is_paid: true, paid_at: new Date(Date.now() + 60_000).toISOString() }).status).toBe(201);
  });
  it("vai không có quyền ghi vẫn 403", () => {
    expect(post(ok, "kho1").status).toBe(403);
  });
});

describe("invoiceFieldError: đặt câu của BE dưới đúng ô", () => {
  const e = (code: string) => new ApiError("Câu của BE.", 400, code);
  it("số tiền, giờ trả, phiếu nhập", () => {
    expect(invoiceFieldError(e("AMOUNT_NOT_POSITIVE"), true)).toEqual({ field: "amount", message: "Câu của BE." });
    expect(invoiceFieldError(e("PAID_AT_REQUIRED"), true)?.field).toBe("paid_at");
    expect(invoiceFieldError(e("PAID_AT_IN_FUTURE"), false)?.field).toBe("paid_at");
    expect(invoiceFieldError(e("INVOICE_SUPPLIER_MISMATCH"), true)?.field).toBe("receipt");
  });
  it("hộp mở từ một phiếu: lỗi khác nhà cung cấp không có ô → null (hiện ở đầu hộp)", () => {
    expect(invoiceFieldError(e("INVOICE_SUPPLIER_MISMATCH"), false)).toBeNull();
  });
  it("mã lạ, 500, lỗi không phải ApiError → null", () => {
    expect(invoiceFieldError(e("SOMETHING_ELSE"), true)).toBeNull();
    expect(invoiceFieldError(new ApiError("x", 500, "AMOUNT_NOT_POSITIVE"), true)).toBeNull();
    expect(invoiceFieldError(new Error("x"), true)).toBeNull();
  });
});
