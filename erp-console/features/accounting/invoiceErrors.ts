// Lỗi nghiệp vụ của POST/PATCH /api/purchasing/invoices/ (contract Lô 17a A5): BE trả `{detail, code}` (không khoá theo ô), nên FE đặt câu
// của BE dưới đúng ô theo mã (UI-RULES §6.6: lỗi nằm dưới ô gây lỗi). Hàm thuần để kiểm bằng vitest.

import { ApiError } from "@/shared/lib/http";

export type InvoiceField = "amount" | "receipt" | "supplier" | "paid_at";

export type InvoiceFieldError = { field: InvoiceField; message: string };

const CODE_FIELD: Record<string, "amount" | "receipt" | "paid_at"> = {
  AMOUNT_NOT_POSITIVE: "amount",
  INVOICE_SUPPLIER_MISMATCH: "receipt",
  PAID_AT_REQUIRED: "paid_at",
  PAID_AT_IN_FUTURE: "paid_at",
  // PAID_AT_WHEN_UNPAID: form luôn gửi paid_at = null khi chưa trả nên không gắn ô; hiện ở đầu hộp nếu BE vẫn trả.
};

/**
 * Lỗi 400 có mã thuộc 5 mã mới → ô cần hiện câu. `hasReceiptSelect=false` (hộp mở từ một phiếu, nhà cung cấp và phiếu cố định)
 * thì lỗi "khác nhà cung cấp" không có ô để gắn, trả null để hộp hiện alert đầu hộp. Mã khác, lỗi mạng → null.
 */
export function invoiceFieldError(err: unknown, hasReceiptSelect: boolean): InvoiceFieldError | null {
  if (!(err instanceof ApiError) || err.status !== 400 || !err.code) return null;
  const field = CODE_FIELD[err.code];
  if (!field) return null;
  if (field === "receipt" && !hasReceiptSelect) return null;
  return { field, message: err.message };
}
