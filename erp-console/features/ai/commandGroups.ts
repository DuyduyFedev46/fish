// Nhóm lệnh AI và mức nhạy cảm — NƠI DUY NHẤT chứa chuỗi giá trị của chúng ở console (P8b Lô 1).
// Giá trị là khoá BE đang trả (`group`, `sensitivity` trong /api/ai/commands/); BE đổi sang tên Anh ở Lô 4
// thì chỉ sửa file này. Nơi khác dùng `COMMAND_GROUP.*` / `SENSITIVITY.*` và các kiểu bên dưới.

export const COMMAND_GROUP = {
  purchasing: "thu_mua",
  sales: "ban_hang",
  customerService: "cskh",
} as const;

export type AiCommandGroup = (typeof COMMAND_GROUP)[keyof typeof COMMAND_GROUP];

export const SENSITIVITY = {
  high: "cao",
  medium: "trung_binh",
  low: "thap",
} as const;

export type AiSensitivity = (typeof SENSITIVITY)[keyof typeof SENSITIVITY];
