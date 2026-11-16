/**
 * Luật kiểm form nhận hàng (SHOP-3-03, 02a mục 6.3). File thuần TypeScript, không import gì, để
 * `scripts/test-order-state.mjs` kiểm được. Luật SĐT dùng chung với máy chủ: sau khi bỏ khoảng trắng và đổi +84 thành 0,
 * phải đúng 10 chữ số bắt đầu bằng 0.
 */

export const NAME_MAX = 100;
/** Số nhà, tên đường, hẻm, tầng (02b §2.2). Dòng đầy đủ do máy chủ ghép nên không còn ADDRESS_MAX. */
export const STREET_MAX = 200;

export const MESSAGES = {
  name: "Nhập họ tên người nhận",
  phone: "Số điện thoại cần 10 chữ số, bắt đầu bằng 0",
  province: "Chọn tỉnh/thành phố",
  district: "Chọn quận/huyện",
  ward: "Chọn phường/xã",
  street: "Nhập số nhà, tên đường (tối đa 200 ký tự)",
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

/** Số nhà: khác rỗng sau khi gộp khoảng trắng, tối đa STREET_MAX (cùng luật máy chủ). */
export function validStreet(value: string): boolean {
  const v = value.split(/\s+/).filter(Boolean).join(" ");
  return v.length > 0 && v.length <= STREET_MAX;
}

export type AddressScheme = "current" | "legacy";

/** Phần chọn của địa chỉ. Mã rỗng = chưa chọn. `districtCode` chỉ dùng ở kiểu `legacy`. */
export type AddressSelection = {
  scheme: AddressScheme;
  provinceCode: string;
  districtCode: string;
  wardCode: string;
};

export const INITIAL_SELECTION: AddressSelection = { scheme: "current", provinceCode: "", districtCode: "", wardCode: "" };

/** Đổi kiểu: xoá tỉnh, huyện, xã (02b §6). */
export function selectScheme(sel: AddressSelection, scheme: AddressScheme): AddressSelection {
  return scheme === sel.scheme ? sel : { scheme, provinceCode: "", districtCode: "", wardCode: "" };
}
/** Đổi tỉnh: xoá huyện, xã. */
export function selectProvince(sel: AddressSelection, code: string): AddressSelection {
  return code === sel.provinceCode ? sel : { ...sel, provinceCode: code, districtCode: "", wardCode: "" };
}
/** Đổi huyện: xoá xã. */
export function selectDistrict(sel: AddressSelection, code: string): AddressSelection {
  return code === sel.districtCode ? sel : { ...sel, districtCode: code, wardCode: "" };
}
export function selectWard(sel: AddressSelection, code: string): AddressSelection {
  return { ...sel, wardCode: code };
}

/** Lọc danh sách theo chữ gõ, không dấu, không phân biệt hoa thường (`fold` = `foldVietnamese` ở lib/text.ts). */
export function filterUnits<T extends { name: string }>(items: T[], query: string, fold: (s: string) => string): T[] {
  const q = fold(query).trim();
  if (!q) return items;
  return items.filter((u) => fold(u.name).includes(q));
}

export type FormField = "name" | "phone" | "province" | "district" | "ward" | "street" | "consent";
export type FormErrors = Partial<Record<FormField, string>>;

/** Kiểm cả form. `consentRequired` false (site-info không bắt đồng ý) thì bỏ qua ô đồng ý. Huyện chỉ bắt buộc ở kiểu cũ. */
export function validateForm(
  values: { name: string; phone: string; scheme: AddressScheme; provinceCode: string; districtCode: string; wardCode: string; street: string; consent: boolean },
  consentRequired: boolean
): FormErrors {
  const errors: FormErrors = {};
  if (!validName(values.name)) errors.name = MESSAGES.name;
  if (!validPhone(values.phone)) errors.phone = MESSAGES.phone;
  if (!values.provinceCode) errors.province = MESSAGES.province;
  if (values.scheme === "legacy" && !values.districtCode) errors.district = MESSAGES.district;
  if (!values.wardCode) errors.ward = MESSAGES.ward;
  if (!validStreet(values.street)) errors.street = MESSAGES.street;
  if (consentRequired && !values.consent) errors.consent = MESSAGES.consent;
  return errors;
}

/** Id ô trên form theo thứ tự hiển thị, để khối "Còn N chỗ cần sửa" liệt kê đúng thứ tự. */
export const FIELD_ORDER: { field: FormField; id: string; label: string }[] = [
  { field: "name", id: "f-name", label: "Họ và tên" },
  { field: "phone", id: "f-phone", label: "Số điện thoại" },
  { field: "province", id: "f-addr-province", label: "Tỉnh/thành phố" },
  { field: "district", id: "f-addr-district", label: "Quận/huyện" },
  { field: "ward", id: "f-addr-ward", label: "Phường/xã" },
  { field: "street", id: "f-addr", label: "Số nhà, tên đường" },
  { field: "consent", id: "f-consent", label: "Đồng ý xử lý dữ liệu" },
];

/** Danh sách lỗi cho FormErrorSummary, theo thứ tự ô trên form. */
export function errorSummary(errors: FormErrors): { fieldId: string; label: string }[] {
  return FIELD_ORDER.filter((f) => errors[f.field]).map((f) => ({ fieldId: f.id, label: f.label }));
}

/** Lỗi máy chủ (`fields`, 02b §2.2) → ô trên form. `scheme` và `delivery_address` rơi về ô tỉnh. */
export function mapServerFields(f: Record<string, string>): FormErrors {
  const next: FormErrors = {};
  if (f.name) next.name = MESSAGES.name;
  if (f.phone) next.phone = MESSAGES.phone;
  if (f.scheme || f.province_code || f.delivery_address) next.province = MESSAGES.province;
  if (f.district_code) next.district = MESSAGES.district;
  if (f.ward_code) next.ward = MESSAGES.ward;
  if (f.street) next.street = MESSAGES.street;
  if (f.consent) next.consent = MESSAGES.consent;
  return next;
}
