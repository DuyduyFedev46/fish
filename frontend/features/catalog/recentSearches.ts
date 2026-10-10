/**
 * "Tìm gần đây" (SHOP-2-04 AC3, AC4): chỉ lưu từ khoá ngắn, không lưu chuỗi giống số điện thoại (bất biến 9).
 * File thuần TypeScript, chỉ import lib/text (test bằng `scripts/test-catalog-view.mjs`).
 */
import { foldVietnamese, looksLikePhone } from "@/lib/text";

export const RECENT_MAX = 5;
export const RECENT_TERM_MAX_LENGTH = 40;

/** Từ khoá được phép lưu: không rỗng, không quá 40 ký tự, không giống số điện thoại. */
export function isStorableTerm(term: string): boolean {
  const t = term.trim();
  return t !== "" && t.length <= RECENT_TERM_MAX_LENGTH && !looksLikePhone(t);
}

/** Đọc chuỗi đã lưu: hỏng hay mục không hợp lệ thì bỏ, giữ tối đa 5. */
export function parseRecent(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const v = JSON.parse(raw);
    if (!Array.isArray(v)) return [];
    return v.filter((x): x is string => typeof x === "string" && isStorableTerm(x)).map((x) => x.trim()).slice(0, RECENT_MAX);
  } catch {
    return [];
  }
}

/** Thêm từ khoá lên đầu, bỏ trùng (không phân biệt dấu/hoa thường), giữ tối đa 5. Từ khoá không hợp lệ thì giữ nguyên danh sách. */
export function addRecent(prev: string[], term: string): string[] {
  if (!isStorableTerm(term)) return prev;
  const t = term.trim();
  return [t, ...prev.filter((x) => foldVietnamese(x) !== foldVietnamese(t))].slice(0, RECENT_MAX);
}
