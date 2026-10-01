// Nhóm lệnh AI và mức nhạy cảm — NƠI DUY NHẤT chứa chuỗi giá trị của chúng ở console (P8b Lô 1).
// Giá trị là khoá BE trả (`group`, `sensitivity` trong /api/ai/commands/); từ Lô 4b là tên tiếng Anh, khớp BE Lô 4a.
// Nơi khác dùng `COMMAND_GROUP.*` / `SENSITIVITY.*` và các kiểu bên dưới.

export const COMMAND_GROUP = {
  purchasing: "purchasing",
  sales: "sales",
  customerService: "customer_service",
} as const;

export type AiCommandGroup = (typeof COMMAND_GROUP)[keyof typeof COMMAND_GROUP];

export const SENSITIVITY = {
  high: "high",
  medium: "medium",
  low: "low",
} as const;

export type AiSensitivity = (typeof SENSITIVITY)[keyof typeof SENSITIVITY];

/** Id lệnh AI "Nhập lô" (BE Lô 4a; id cũ `…nhap_lo` được chuẩn hoá ở ./legacyIds.ts). */
export const RECEIVE_BATCHES_COMMAND_ID = "purchasing.purchasereceipt.receive_batches";

/**
 * Nhãn tiếng Việt của nhóm lệnh, chỉ dùng để tìm kiếm (./commands/search.ts). Khoá nhóm đã đổi sang tiếng Anh nên bộ tìm
 * (BM25 bỏ dấu) mất các từ "thu mua", "ban hang"; nhãn này đưa lại đúng các từ đó vào chỉ mục (recall không giảm, P8b Lô 4b).
 */
export const COMMAND_GROUP_SEARCH_LABEL: Record<AiCommandGroup, string> = {
  [COMMAND_GROUP.purchasing]: "thu mua",
  [COMMAND_GROUP.sales]: "bán hàng",
  [COMMAND_GROUP.customerService]: "cskh",
};
