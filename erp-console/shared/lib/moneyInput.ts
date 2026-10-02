// Ô nhập tiền VNĐ dùng chung (Lô 3, QA B4). Tiền VNĐ là số nguyên, nên giá trị thật của ô CHỈ gồm chữ số:
// mỗi lần ô đổi, bỏ mọi ký tự không phải số (kể cả dấu chấm, dấu phẩy, "đ", chữ) rồi nhóm nghìn lại từ chuỗi chữ số đó.
// Nhờ vậy xoá lùi từ "150.000" ra "15.000", không bao giờ ra "150.00" (đọc thành 150 đ).
// Dấu trừ KHÔNG bị bỏ lặng lẽ: "-5" giữ nguyên để người dùng thấy câu báo "không được âm", thay vì biến thành 5 đ.

export type MoneyEdit = {
  value: string;
  caret: number;
  /** Có giá trị khi lần sửa bị TỪ CHỐI (giữ nguyên giá trị cũ của ô): chuỗi dán/gõ có phần lẻ khác 0, không đoán. */
  rejected?: "fraction";
};

/** Câu báo dưới ô khi chuỗi có phần lẻ (nói cách sửa). */
export const MONEY_FRACTION_MESSAGE = "Số tiền là số nguyên đồng, không có phần lẻ. Nhập lại, ví dụ 150.000.";

// Phần lẻ kiểu sao kê: dấu chấm hoặc phẩy rồi 1–2 chữ số ở CUỐI chuỗi, có thể kèm "đ" / "₫" / "VND" ("150.000,00", "150,000.50", "0.5").
const FRACTION_TAIL = /^(.*?)[.,](\d{1,2})\s*(?:đ|₫|vnd)?\s*$/i;

/**
 * Tách phần lẻ ở cuối chuỗi. `none` = không có; `zero` = phần lẻ toàn số 0 (150.000,00 → nhận là 150.000, `text` đã bỏ phần lẻ);
 * `nonzero` = có phần lẻ khác 0 (150.000,50 / 0.5 / 540,5) → không đoán, người dùng phải nhập lại.
 */
export function splitFraction(raw: string): { kind: "none" | "zero" | "nonzero"; text: string } {
  const m = raw.match(FRACTION_TAIL);
  if (!m) return { kind: "none", text: raw };
  return /^0+$/.test(m[2]) ? { kind: "zero", text: m[1] } : { kind: "nonzero", text: raw };
}

const NEGATIVE = /[-−]/;

/** Nhóm nghìn kiểu Việt từ chuỗi chữ số: "1500000" → "1.500.000". */
export function groupThousands(digitString: string): string {
  return digitString.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function onlyDigits(s: string): string {
  return s.replace(/\D+/g, "");
}

/** Vị trí con trỏ ngay sau `count` chữ số trong chuỗi đã nhóm. */
function caretAfterDigits(formatted: string, count: number): number {
  let pos = 0;
  let seen = 0;
  while (pos < formatted.length && seen < count) {
    if (formatted[pos] >= "0" && formatted[pos] <= "9") seen += 1;
    pos += 1;
  }
  return pos;
}

/**
 * Tính giá trị mới và vị trí con trỏ sau một lần sửa ô tiền.
 * - `prev`: giá trị đang hiển thị trước lần sửa; `next`: chuỗi trong ô sau lần sửa; `caret`: `selectionStart` sau lần sửa.
 * - `inputType`: `InputEvent.inputType` ("deleteContentBackward" / "deleteContentForward" / "insertFromPaste"…).
 * Xoá lùi (hoặc xoá tới) đúng một dấu chấm phân nhóm thì xoá chữ số liền kề, để phím xoá không "đứng im".
 */
export function editMoneyInput(prev: string, next: string, caret: number, inputType = ""): MoneyEdit {
  if (NEGATIVE.test(next)) return { value: next, caret };
  // Chỉ xét phần lẻ khi THÊM chữ (gõ, dán). Xoá lùi từ "1.500.000" tạm ra "1.500.00": đó là xoá, không phải phần lẻ.
  if (!/^(delete|history)/.test(inputType)) {
    const frac = splitFraction(next);
    if (frac.kind === "nonzero") return { value: prev, caret: prev.length, rejected: "fraction" };
    if (frac.kind === "zero") {
      const kept = String(onlyDigits(frac.text)).replace(/^0+(?=\d)/, "");
      const value = groupThousands(kept);
      return { value, caret: value.length };
    }
  }
  const at = Math.max(0, Math.min(caret, next.length));
  let before = onlyDigits(next.slice(0, at)).length;
  let digits = onlyDigits(next);

  // Chỉ coi là xoá khi sự kiện không phải chèn/dán: dán "1000000" đè lên "1.000.000" giữ nguyên chữ số, không được mất một số.
  if (!/^insert/.test(inputType) && digits === onlyDigits(prev) && next.length < prev.length) {
    if (inputType === "deleteContentForward") {
      if (before < digits.length) digits = digits.slice(0, before) + digits.slice(before + 1);
    } else if (before > 0) {
      digits = digits.slice(0, before - 1) + digits.slice(before);
      before -= 1;
    }
  }

  const zeros = digits.match(/^0+(?=\d)/)?.[0].length ?? 0;
  if (zeros) {
    digits = digits.slice(zeros);
    before = Math.max(0, before - zeros);
  }

  const value = groupThousands(digits);
  return { value, caret: caretAfterDigits(value, before) };
}

/** Định dạng một chuỗi cho sẵn (giá trị ban đầu từ BE, không có con trỏ): "540000" → "540.000". */
export function formatMoneyInput(raw: string): string {
  return editMoneyInput("", raw, raw.length).value;
}
