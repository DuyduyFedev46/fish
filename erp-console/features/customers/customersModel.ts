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

/** Giới hạn độ dài của BE: tên ≤ 200, địa chỉ và ghi chú ≤ 1000. */
export const FIELD_LIMITS: Record<CustomerEditableField, number> = { name: 200, default_address: 1000, note: 1000 };

export const FIELD_LABELS: Record<CustomerEditableField, string> = {
  name: "Tên",
  default_address: "Địa chỉ giao mặc định",
  note: "Ghi chú",
};

/** Lỗi nhập tại chỗ (null = hợp lệ). Tên bắt buộc; ba ô đều có giới hạn độ dài. */
export function validateField(field: CustomerEditableField, value: string): string | null {
  const v = value.trim();
  if (field === "name" && !v) return "Nhập tên khách.";
  if (v.length > FIELD_LIMITS[field]) return `${FIELD_LABELS[field]} tối đa ${FIELD_LIMITS[field]} ký tự. Rút ngắn rồi lưu lại.`;
  return null;
}

/** Gói PATCH chỉ gồm trường thật sự đổi (so với bản đang hiện); rỗng = không có gì để lưu. */
export function changedFields(current: CustomerDetail, draft: Record<CustomerEditableField, string>): CustomerPatch {
  const out: CustomerPatch = {};
  (Object.keys(FIELD_LIMITS) as CustomerEditableField[]).forEach((k) => {
    const next = draft[k].trim();
    if (next !== (current[k] ?? "")) out[k] = next;
  });
  return out;
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
