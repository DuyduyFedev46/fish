// Kiểu dữ liệu module Khách hàng (ED-14). Chép đúng contract BE Lô 6 (B2), 03-dev-notes.md "Lô 6 — BE (B2)".
// Tiền là chuỗi thập phân của BE ("2140000.00"): FE chỉ đưa qua `vnd()` để hiện "2.140.000 đ", không tự cộng trừ.
// Khoá đếm đơn huỷ là `cancelled_count` (02b thắng story), không phải `cancelled_order_count`.

/** Một dòng danh bạ: GET /api/sales/customer-directory/ (20 dòng/trang). */
export type CustomerListItem = {
  id: number;
  name: string;
  phone: string;
  order_count: number;
  /** Tổng trên đơn không huỷ, đã trừ phiếu hoàn REFUNDED. */
  total_spent: string;
  cancelled_count: number;
  /** ISO; null = chưa có đơn nào. */
  last_order_at: string | null;
  note: string;
};

export type CustomerOrderRow = {
  id: number;
  code: string;
  status: string;
  status_label: string;
  total_amount: string;
  created_at: string;
};

/** Phiếu hoàn của khách: KHÔNG có lý do (BE không trả). */
export type CustomerRefundRow = {
  id: number;
  order_code: string;
  status: string;
  status_label: string;
  amount: string;
  created_at: string;
};

/** GET /api/sales/customer-directory/{id}/ và thân 200 của PATCH. */
export type CustomerDetail = CustomerListItem & {
  default_address: string;
  created_at: string;
  first_order_at: string | null;
  /** 50 đơn mới nhất. */
  orders: CustomerOrderRow[];
  /** 50 phiếu hoàn mới nhất. */
  refunds: CustomerRefundRow[];
};

/** Bốn trường sửa được; số điện thoại sửa được từ 02/10 (Lô bổ sung A #5), BE chuẩn hoá và chặn trùng khách khác. */
export type CustomerEditableField = "name" | "phone" | "default_address" | "note";
export type CustomerPatch = Partial<Record<CustomerEditableField, string>>;

/** Giá trị `ordering` BE cho phép; thêm "-" phía trước để giảm dần. */
export type CustomerOrdering =
  | "-last_order_at"
  | "last_order_at"
  | "-order_count"
  | "-total_spent"
  | "name"
  | "-name"
  | "-created_at";

export type CustomerListParams = {
  /** Từ khoá tìm: chỉ nằm trong state màn hình, không bao giờ vào URL hay storage (quyết định #11). */
  q: string;
  ordering: CustomerOrdering;
};
