// Từ `reference_link.kind` của sổ nhập xuất → trang chi tiết của chứng từ (nếu trang đã có).
// `ready: false` = trang đích chưa có trong console (do lô khác làm) → mã chứng từ hiện chữ thường, không thành link chết.
// Khi một lô xong trang chi tiết thì đổi `ready` thành true; vitest (referenceRoutes.test.ts) kiểm mọi route `ready` có trang thật.
export type ReferenceRoute = { kind: string; /** Thư mục trang trong app/(console). */ page: string; ready: boolean };

export const REFERENCE_ROUTES: readonly ReferenceRoute[] = [
  { kind: "batch", page: "inventory/detail", ready: true },
  { kind: "order", page: "orders/detail", ready: true }, // Lô 3 đã vào: /orders/detail/?id=
  { kind: "invoice", page: "invoices/detail", ready: false }, // chưa có lô nhận
  { kind: "receipt", page: "purchasing/detail", ready: false }, // phiếu nhập: Lô 10 chưa vào
  { kind: "stocktake", page: "stocktake/detail", ready: false }, // Lô 8
  { kind: "return", page: "returns/detail", ready: false }, // Lô 9
  { kind: "supplier_return", page: "inventory/supplier-returns/detail", ready: false }, // chưa có màn
];

/** Đường dẫn tới chứng từ, hoặc null khi chưa có trang. URL chỉ mang id số. */
export function referenceHref(link: { kind: string; id: number } | null | undefined): string | null {
  if (!link || !Number.isInteger(link.id) || link.id <= 0) return null;
  const route = REFERENCE_ROUTES.find((r) => r.kind === link.kind);
  return route && route.ready ? `/${route.page}/?id=${link.id}` : null;
}
