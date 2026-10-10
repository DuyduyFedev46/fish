// Phần thuần của màn Nhà cung cấp (không React, không gọi API): lựa chọn lọc, kiểm tra ô nhập, gói PATCH chỉ gồm trường đổi,
// câu lỗi lưu. Không giữ số điện thoại ở đâu ngoài tham số hàm (không log, không storage, không URL).

import { ENUMS } from "@/shared/lib/enums";
import { ApiError } from "@/shared/lib/http";
import { SUPPLIERS_MSG as M } from "./messages";
import type { Supplier, SupplierInput, SupplierPatch, SupplierType } from "./types";

export const TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: M.typeAll },
  ...Object.entries(ENUMS.supplierType).map(([value, v]) => ({ value, label: v.label })),
];

export const ACTIVE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: M.activeAll },
  { value: "1", label: M.activeYes },
  { value: "0", label: M.activeNo },
];

const TYPE_VALUES = new Set(["", "INDIVIDUAL", "COMPANY"]);
const ACTIVE_VALUES = new Set(["", "1", "0"]);

/** Giá trị lạ (gõ tay vào select) quay về "không lọc". */
export const asTypeFilter = (v: string): string => (TYPE_VALUES.has(v) ? v : "");
export const asActiveFilter = (v: string): string => (ACTIVE_VALUES.has(v) ? v : "");

/** Giới hạn độ dài của BE: tên ≤ 200, số điện thoại ≤ 20; ghi chú không giới hạn ở BE, FE giữ ≤ 1000 cho gọn. */
export const FIELD_LIMITS = { name: 200, phone: 20, note: 1000 } as const;

export type EditableTextField = keyof typeof FIELD_LIMITS;

export function validateField(field: EditableTextField, value: string): string | null {
  const v = value.trim();
  if (field === "name" && !v) return M.nameRequired;
  if (field === "name" && v.length > FIELD_LIMITS.name) return M.nameTooLong;
  if (field === "phone" && v.length > FIELD_LIMITS.phone) return M.phoneTooLong;
  if (field === "note" && v.length > FIELD_LIMITS.note) return M.noteTooLong;
  return null;
}

export type Draft = { name: string; supplier_type: SupplierType; phone: string; note: string; is_active: boolean };

export const EMPTY_DRAFT: Draft = { name: "", supplier_type: "INDIVIDUAL", phone: "", note: "", is_active: true };

export function draftOf(s: Supplier): Draft {
  return { name: s.name ?? "", supplier_type: s.supplier_type, phone: s.phone ?? "", note: s.note ?? "", is_active: s.is_active };
}

/** Gói tạo mới (đã cắt khoảng trắng đầu cuối). */
export function inputOf(d: Draft): SupplierInput {
  return { name: d.name.trim(), supplier_type: d.supplier_type, phone: d.phone.trim(), note: d.note.trim(), is_active: d.is_active };
}

/** Gói PATCH chỉ gồm trường thật sự đổi so với bản đang hiện; rỗng = không có gì để lưu. */
export function changedFields(current: Supplier, draft: Draft): SupplierPatch {
  const next = inputOf(draft);
  const out: SupplierPatch = {};
  if (next.name !== (current.name ?? "")) out.name = next.name;
  if (next.supplier_type !== current.supplier_type) out.supplier_type = next.supplier_type;
  if (next.phone !== (current.phone ?? "")) out.phone = next.phone;
  if (next.note !== (current.note ?? "")) out.note = next.note;
  if (next.is_active !== current.is_active) out.is_active = next.is_active;
  return out;
}

/** BE báo tên trùng theo hai dạng: 400 `{name:[...]}` hoặc `{detail, code:"SUPPLIER_NAME_TAKEN"}` (hai người lưu cùng lúc). */
export function isNameTaken(err: unknown): boolean {
  if (!(err instanceof ApiError) || err.status !== 400) return false;
  if (err.code === "SUPPLIER_NAME_TAKEN") return true;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : null;
  return !!d && Array.isArray(d.name) && d.name.length > 0;
}

/** Câu hiện dưới ô Tên khi tên trùng: nguyên văn BE nếu có, không thì câu chuẩn. */
export function nameTakenMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : null;
    const first = d && Array.isArray(d.name) ? d.name[0] : undefined;
    if (typeof first === "string" && first.trim()) return first;
    if (err.message && err.code === "SUPPLIER_NAME_TAKEN") return err.message;
  }
  return M.nameTaken;
}

/**
 * Câu lỗi khi lưu: 400 theo trường của DRF `{field:[...]}` → câu đầu tiên của BE; còn lại dùng `message` của ApiError
 * (BE trả `detail`). Mất mạng / 5xx đã có câu chuẩn trong ApiError.
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

/** Các lỗi lưu đang hiện trong hộp Thêm/Sửa, để quyết định chỗ hiện và khi nào xoá. */
export type SaveErrorState = {
  /** Lỗi tên trùng đã ghim dưới ô Tên (từ lần gửi trước). */
  nameServerError: string | null;
  /** `fieldErrors.name` của lần gửi trước (BE trả 400 theo trường). */
  submitNameError?: string | null;
  /** `error` chung của lần gửi trước. */
  submitError: string | null;
};

/** Lỗi chung ở ĐẦU form: bỏ khi lỗi đó chính là lỗi tên (đã nằm dưới ô Tên, không lặp lại). */
export function topFormError(state: SaveErrorState): string | null {
  if (!state.submitError) return null;
  return state.nameServerError || state.submitNameError ? null : state.submitError;
}

/**
 * Người dùng sửa ô Tên khi lỗi lưu của lần gửi trước còn nằm đó: phải xoá cả lỗi chung của lần gửi đó,
 * nếu không khi ghim tên trùng được gỡ, câu lỗi cũ sẽ nhảy lên đầu form (và nút vẫn là "Thử lại").
 */
export function shouldResetSaveErrorOnNameEdit(state: SaveErrorState): boolean {
  return !!(state.nameServerError || state.submitNameError || state.submitError);
}
