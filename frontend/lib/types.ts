// Kiểu dữ liệu khớp Shop API (công khai) — xem doc/BUILD-PLAN.md, mục "Shop API (công khai)".

export type ItemType = "SIMPLE" | "BUNDLE";

export type CatalogItem = {
  item_code: string;
  name: string;
  group: string;
  item_type: ItemType;
  unit: "Kg";
  price: number;
  sellable_qty: number;
};

export type BundleComponent = {
  item_code: string;
  name: string;
  qty_per_bundle: number;
};

export type CatalogItemDetail = CatalogItem & {
  bundle_components?: BundleComponent[];
};

export type CreateOrderItemInput = {
  item_code: string;
  qty: number;
};

export type CreateOrderPayload = {
  customer: {
    phone: string;
    name: string;
  };
  delivery_address: string;
  phone: string;
  items: CreateOrderItemInput[];
};

export type VietQr = {
  payload: string;
  amount: number;
  content: string;
};

export type CreateOrderResponse = {
  order_code: string;
  total_amount: number;
  vietqr: VietQr;
  booked_expires_at: string; // ISO datetime
};

export type OrderLineStatus = {
  item_code: string;
  name: string;
  qty: number;
  price?: number;
  line_total?: number;
};

export type OrderStatus = {
  order_code: string;
  status: string;
  status_label: string;
  lines: OrderLineStatus[];
  delivery?: {
    status: string;
  };
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
