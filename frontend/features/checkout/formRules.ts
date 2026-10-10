/**
 * Luật kiểm form nhận hàng (SHOP-3-03, 02a mục 6.3). File thuần TypeScript, không import gì, để
 * `scripts/test-order-state.mjs` kiểm được. Luật SĐT dùng chung với máy chủ: sau khi bỏ khoảng trắng và đổi +84 thành 0,
 * phải đúng 10 chữ số bắt đầu bằng 0.
 */

export const NAME_MAX = 100;
export const ADDRESS_MAX = 500;

export const MESSAGES = {
  name: "Nhập họ tên người nhận",
  phone: "Số điện thoại cần 10 chữ số, bắt đầu bằng 0",
  address: "Nhập địa chỉ giao hàng hoặc chọn trên bản đồ",
  consent: "Đánh dấu đồng ý ở trên để đặt hàng.",
} as const;

/** "+84 900 000 001" | "0900.000.001" -> "0900000001". Ký tự lạ giữ nguyên để kiểm sau không lọt. */
export function normalizeVnPhone(raw: string): string {
  const compact = raw.replace(/[\s.\-()]/g, "");
  if (compact.startsWith("+84")) return `0${compact.slice(3)}`;
  if (/^84\d{9}$/.test(compact)) return `0${compact.slice(2)}`;
  return compact;
}

export function validName(value: string): boolean {
  const v = value.trim();
  return v.length > 0 && v.length <= NAME_MAX;
}

export function validPhone(value: string): boolean {
  return /^0\d{9}$/.test(normalizeVnPhone(value));
}

export function validAddress(value: string): boolean {
  const v = value.trim();
  return v.length > 0 && v.length <= ADDRESS_MAX;
}

export type FormField = "name" | "phone" | "address" | "consent";
export type FormErrors = Partial<Record<FormField, string>>;

/** Kiểm cả form. `consentRequired` false (site-info không bắt đồng ý) thì bỏ qua ô đồng ý. */
export function validateForm(
  values: { name: string; phone: string; address: string; consent: boolean },
  consentRequired: boolean
): FormErrors {
  const errors: FormErrors = {};
  if (!validName(values.name)) errors.name = MESSAGES.name;
  if (!validPhone(values.phone)) errors.phone = MESSAGES.phone;
  if (!validAddress(values.address)) errors.address = MESSAGES.address;
  if (consentRequired && !values.consent) errors.consent = MESSAGES.consent;
  return errors;
}

/** Id ô trên form theo thứ tự hiển thị, để khối "Còn N chỗ cần sửa" liệt kê đúng thứ tự. */
export const FIELD_ORDER: { field: FormField; id: string; label: string }[] = [
  { field: "name", id: "f-name", label: "Họ và tên" },
  { field: "phone", id: "f-phone", label: "Số điện thoại" },
  { field: "address", id: "f-addr", label: "Địa chỉ giao hàng" },
  { field: "consent", id: "f-consent", label: "Đồng ý xử lý dữ liệu" },
];

/** Danh sách lỗi cho FormErrorSummary, theo thứ tự ô trên form. */
export function errorSummary(errors: FormErrors): { fieldId: string; label: string }[] {
  return FIELD_ORDER.filter((f) => errors[f.field]).map((f) => ({ fieldId: f.id, label: f.label }));
}
