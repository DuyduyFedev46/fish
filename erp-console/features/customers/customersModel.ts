// Phần thuần của màn Khách hàng (không React, không gọi API): lựa chọn sắp xếp, kiểm tra ô sửa, gói PATCH chỉ gồm trường đổi.
// Không giữ tên/SĐT/địa chỉ ở đâu ngoài tham số hàm (không log, không storage).

import { ApiError } from "@/shared/lib/http";
import type { CustomerDetail, CustomerEditableField, CustomerOrdering, CustomerPatch } from "./types";

/** Lựa chọn sắp xếp của danh sách; mặc định đứng đầu (đơn gần nhất mới trước, khách chưa mua cuối). */
export const ORDERING_OPTIONS: { value: CustomerOrdering; label: string }[] = [
  { value: "-last_order_at", label: "Đơn gần nhất mới trước" },
  { value: "last_order_at", label: "Đơn gần nhất cũ trước" },
  { value: "-total_spent", label: "Tổng đã mua nhiều nhất" },
  { value: "-order_count", label: "Nhiều đơn nhất" },
  { value: "name", label: "Tên từ A đến Z" },
  { value: "-created_at", label: "Khách mới nhất" },
];

export const DEFAULT_ORDERING: CustomerOrdering = "-last_order_at";

const ORDERING_VALUES = new Set<string>(ORDERING_OPTIONS.map((o) => o.value));

/** Giá trị lạ (vd gõ tay vào select) quay về mặc định. */
export function asOrdering(value: string): CustomerOrdering {
  return ORDERING_VALUES.has(value) ? (value as CustomerOrdering) : DEFAULT_ORDERING;
}

/** Giới hạn độ dài của BE: tên ≤ 200, số điện thoại ≤ 40, địa chỉ và ghi chú ≤ 1000. */
export const FIELD_LIMITS: Record<CustomerEditableField, number> = { name: 200, phone: 40, default_address: 1000, note: 1000 };

export const FIELD_LABELS: Record<CustomerEditableField, string> = {
  name: "Tên",
  phone: "Số điện thoại",
  default_address: "Địa chỉ giao mặc định",
  note: "Ghi chú",
};

/** Chuẩn hoá số điện thoại giống BE (`normalize_phone`): bỏ ký tự không phải số, +84 / 84 đổi thành 0. */
export function normalizePhone(raw: string): string {
  const kept = raw.replace(/[^\d+]/g, "");
  let digits = kept;
  if (kept.startsWith("+84")) digits = `0${kept.slice(3)}`;
  else if (kept.startsWith("84") && kept.length >= 11) digits = `0${kept.slice(2)}`;
  return digits.replace(/\D/g, "");
}

/** Số điện thoại hợp lệ: sau khi chuẩn hoá phải là 0 + 9 hoặc 10 chữ số (BE: INVALID_PHONE nếu sai). */
export function isValidPhone(raw: string): boolean {
  return /^0\d{9,10}$/.test(normalizePhone(raw));
}

/** Lỗi nhập tại chỗ (null = hợp lệ). Tên và số điện thoại bắt buộc; các ô đều có giới hạn độ dài. */
export function validateField(field: CustomerEditableField, value: string): string | null {
  const v = value.trim();
  if (field === "name" && !v) return "Nhập tên khách.";
  if (field === "phone") {
    if (!v) return "Nhập số điện thoại.";
    if (v.length > FIELD_LIMITS.phone) return `${FIELD_LABELS.phone} tối đa ${FIELD_LIMITS.phone} ký tự. Rút ngắn rồi lưu lại.`;
    if (!isValidPhone(v)) return "Số điện thoại gồm 10 hoặc 11 số, bắt đầu bằng 0 (hoặc +84).";
    return null;
  }
  if (v.length > FIELD_LIMITS[field]) return `${FIELD_LABELS[field]} tối đa ${FIELD_LIMITS[field]} ký tự. Rút ngắn rồi lưu lại.`;
  return null;
}

/** Gói PATCH chỉ gồm trường thật sự đổi (so với bản đang hiện); rỗng = không có gì để lưu. */
export function changedFields(current: CustomerDetail, draft: Record<CustomerEditableField, string>): CustomerPatch {
  const out: CustomerPatch = {};
  (Object.keys(FIELD_LIMITS) as CustomerEditableField[]).forEach((k) => {
    const next = k === "phone" ? normalizePhone(draft[k]) : draft[k].trim();
    const before = k === "phone" ? normalizePhone(current[k] ?? "") : (current[k] ?? "");
    if (next !== before) out[k] = next;
  });
  return out;
}

/** Mã lỗi BE gắn vào ô số điện thoại (dòng đỏ dưới ô), không phải alert đầu form. */
export const PHONE_ERROR_CODES = ["CUSTOMER_PHONE_TAKEN", "INVALID_PHONE"] as const;

/** Lỗi của riêng số điện thoại khi lưu (BE: trùng khách khác / sai dạng); null nếu lỗi khác. Câu của BE không chứa số. */
export function phoneSaveError(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "CUSTOMER_PHONE_TAKEN") return err.message || "Số điện thoại này đã thuộc về một khách hàng khác.";
  if (err.code === "INVALID_PHONE") return err.message || "Số điện thoại không hợp lệ.";
  return null;
}

/**
 * Câu lỗi khi lưu (PATCH): 400 theo trường của DRF `{field:[...]}` → câu đầu tiên của BE; còn lại dùng `message` của ApiError
 * (BE trả `detail`: INPUT_NOT_ALLOWED, INPUT_EMPTY…). Mất mạng / 5xx đã có câu chuẩn trong ApiError.
 */
export function saveErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 400 && err.details && typeof err.details === "object") {
    for (const v of Object.values(err.details as Record<string, unknown>)) {
      const first = Array.isArray(v) ? v[0] : v;
      if (typeof first === "string" && first.trim()) return first;
    }
  }
  return err instanceof Error && err.message ? err.message : "Chưa lưu được. Kiểm tra mạng rồi bấm lại.";
}
