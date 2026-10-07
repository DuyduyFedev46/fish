// CS-18 — kịch bản gọi soạn sẵn. Hàm thuần để vitest. Không AI.
// Nội dung kịch bản KHÔNG được chứa số điện thoại hay dãy số dài (BR-GH-19: kịch bản là chữ chung, không phải dữ liệu khách).
// FE chặn trước để người soạn sửa ngay; BE vẫn chặn lại (lớp chặn thật).
import { hasLongDigitRun } from "./confirmationUi";
import type { CallScript, CallScriptSituation } from "./types";

export const SCRIPT_MAX = 2000;

/** Bốn tình huống, đúng thứ tự hiện ở màn soạn. */
export const SCRIPT_SITUATIONS: Array<{ value: CallScriptSituation; label: string }> = [
  { value: "FIRST_ORDER", label: "Khách mua lần đầu" },
  { value: "RETURNING", label: "Khách quen" },
  { value: "COMBO", label: "Đơn có combo" },
  { value: "GENERAL", label: "Lời dặn chung" },
];

export const SCRIPT_MESSAGES = {
  empty: "Nhập nội dung kịch bản.",
  tooLong: `Nội dung tối đa ${SCRIPT_MAX} ký tự. Rút ngắn rồi lưu lại.`,
  pii: "Kịch bản không được chứa số điện thoại hay dãy số dài. Xoá số đó rồi lưu lại.",
} as const;

/** Lỗi của nội dung kịch bản (null = hợp lệ). */
export function scriptError(content: string): string | null {
  const t = content.trim();
  if (!t) return SCRIPT_MESSAGES.empty;
  if (t.length > SCRIPT_MAX) return SCRIPT_MESSAGES.tooLong;
  if (hasLongDigitRun(t)) return SCRIPT_MESSAGES.pii;
  return null;
}

/** Ghép danh sách BE với bốn tình huống cố định: tình huống chưa soạn có `script: null`. */
export function slotsOf(scripts: readonly CallScript[]): Array<{ situation: CallScriptSituation; label: string; script: CallScript | null }> {
  return SCRIPT_SITUATIONS.map((s) => ({ situation: s.value, label: s.label, script: scripts.find((x) => x.situation === s.value) ?? null }));
}
