// API hoá đơn mua (R11) và chi phí phụ (R12). Lô 10 chỉ thêm đủ để màn Mua hàng chạy; Lô 12 mở rộng cho "Hoá đơn mua & chi phí".
// Điều kiện mock viết thẳng tại chỗ dùng để bản build thật loại bỏ dữ liệu mẫu (check-no-mock).
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockCostCreate, mockCostList, mockInvoiceCreate, mockInvoiceList, mockSalesInvoiceList } from "./mock";
import type {
  SalesInvoiceListParams,
  SalesInvoicePage,
  PurchaseCostInput,
  PurchaseCostListParams,
  PurchaseCostRow,
  PurchaseInvoiceInput,
  PurchaseInvoiceListParams,
  PurchaseInvoiceRow,
} from "./types";

function query(entries: Record<string, string | undefined>, page = 1): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(entries)) if (v) q.set(k, v);
  if (page > 1) q.set("page", String(page));
  const text = q.toString();
  return text ? `?${text}` : "";
}

/** GET /api/purchasing/invoices/ (R11): 20 dòng/trang. Cần view_purchaseinvoice (Chủ, Quản lý), vai khác nhận 403. */
export function fetchPurchaseInvoices(params: PurchaseInvoiceListParams, page: number, signal?: AbortSignal): Promise<Paginated<PurchaseInvoiceRow>> {
  return apiFetch<Paginated<PurchaseInvoiceRow>>(`/api/purchasing/invoices/${query({ is_paid: params.is_paid, supplier: params.supplier, month: params.month }, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockInvoiceList : undefined,
  });
}

/** POST /api/purchasing/invoices/ (F1c). Cần add_purchaseinvoice (chỉ Chủ). */
export function createPurchaseInvoice(input: PurchaseInvoiceInput): Promise<PurchaseInvoiceRow> {
  return apiFetch<PurchaseInvoiceRow>("/api/purchasing/invoices/", {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockInvoiceCreate : undefined,
  });
}

/** GET /api/purchasing/costs/ (R12): chỉ Chủ (view_purchasecost và view_costprice), 20 dòng/trang. */
export function fetchPurchaseCosts(params: PurchaseCostListParams, page: number, signal?: AbortSignal): Promise<Paginated<PurchaseCostRow>> {
  return apiFetch<Paginated<PurchaseCostRow>>(`/api/purchasing/costs/${query({ cost_type: params.cost_type, month: params.month }, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCostList : undefined,
  });
}

/**
 * GET /api/sales/invoices/ (R13): 20 dòng/trang kèm `totals` của toàn bộ kết quả đã lọc (bỏ hoá đơn Đã huỷ).
 * Cần sales.view_salesinvoice (Chủ, Quản lý, Nhân viên kho). `cogs`/`gross_profit` chỉ có khi có view_costprice;
 * `customer_name` null khi thiếu sales.view_customer_list. Có tên khách nên BE trả no-store.
 */
export function fetchSalesInvoices(params: SalesInvoiceListParams, page: number, signal?: AbortSignal): Promise<SalesInvoicePage> {
  return apiFetch<SalesInvoicePage>(`/api/sales/invoices/${query({ q: params.q.trim(), status: params.status, date_from: params.date_from, date_to: params.date_to }, page)}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockSalesInvoiceList : undefined,
  });
}

/** POST /api/purchasing/costs/ (F1d). Chỉ Chủ. Tổng `allocations[].amount` phải bằng `amount`, không thì BE trả 400. */
export function createPurchaseCost(input: PurchaseCostInput): Promise<PurchaseCostRow> {
  return apiFetch<PurchaseCostRow>("/api/purchasing/costs/", {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCostCreate : undefined,
  });
}
