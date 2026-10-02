// Đọc ô tiền VNĐ (Field type="money" giữ chuỗi chữ số nhóm nghìn "1.650.000") thành số nguyên đồng. Hàm thuần.
// Nguyên tắc (QA Lô 10 B5): tiền không đoán. Giá trị lỗi (âm, quá lớn, có chữ) phải được BÁO cho người dùng và KHÔNG gửi,
// không bao giờ bị đổi lặng lẽ thành "0". Gọi `moneyIssue`/`moneyMessage` để kiểm trước khi gửi, rồi mới `moneyBody`.
import { vnd } from "@/shared/lib/format";

/** BE lưu tiền DecimalField(max_digits=14, decimal_places=2) nên phần nguyên tối đa 12 chữ số (999.999.999.999 đ). */
export const MONEY_MAX_DIGITS = 12;

/** Giá mua/kg của phiếu nhập: tối đa 10 chữ số phần nguyên, khớp cột giá vốn lô (Batch.landed_unit_cost, max_digits=14, 4 số lẻ); BE trả 400 nếu vượt (QA Lô 10 N1). */
export const RATE_MAX_DIGITS = 10;

const digitsPattern = (maxDigits: number) => new RegExp(`^\\d{1,${maxDigits}}$`);

/** Đơn vị tiền trong ô nhập (lấy từ vnd() để không viết tay hậu tố tiền). */
export const CURRENCY_UNIT = vnd(0).replace(/^[\d.,\s]+/, "");

/** "1.650.000" → 1650000; rỗng, chữ, âm hay quá 12 chữ số → null. Không bao giờ làm tròn. */
export function parseMoney(text: string, maxDigits: number = MONEY_MAX_DIGITS): number | null {
  const digits = text.replace(/\./g, "");
  return digitsPattern(maxDigits).test(digits) ? Number(digits) : null;
}

export type MoneyIssue = "empty" | "negative" | "too_long" | "invalid";

/** Lý do một ô tiền không dùng được; `null` = hợp lệ (kể cả số 0). */
export function moneyIssue(text: string, maxDigits: number = MONEY_MAX_DIGITS): MoneyIssue | null {
  const raw = text.trim();
  if (raw === "") return "empty";
  if (/[-−]/.test(raw)) return "negative";
  const digits = raw.replace(/\./g, "");
  if (!/^\d+$/.test(digits)) return "invalid";
  if (!digitsPattern(maxDigits).test(digits)) return "too_long";
  return null;
}

export type MoneyRule = {
  /** Danh từ trong câu báo, ví dụ "Giá mua". Mặc định "Số tiền". */
  noun?: string;
  /** Để trống là hợp lệ (trả null). Mặc định: bắt buộc nhập. */
  allowEmpty?: boolean;
  /** Phải lớn hơn 0 (kể cả khi gõ "0"). Mặc định: cho phép 0. */
  positive?: boolean;
  /** Số chữ số phần nguyên tối đa. Mặc định MONEY_MAX_DIGITS (12). */
  maxDigits?: number;
};

/** Số lớn nhất ghi bằng chữ số có dấu chấm nghìn: 10 chữ số → "9.999.999.999". */
function maxMoneyText(maxDigits: number): string {
  return "9".repeat(maxDigits).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** Câu báo tiếng Việt dưới ô (nói cách sửa), hoặc `null` khi hợp lệ. */
export function moneyMessage(text: string, rule: MoneyRule = {}): string | null {
  const noun = rule.noun ?? "Số tiền";
  const maxDigits = rule.maxDigits ?? MONEY_MAX_DIGITS;
  const issue = moneyIssue(text, maxDigits);
  if (issue === "empty") {
    if (rule.allowEmpty) return null;
    return rule.positive ? `Nhập ${noun.toLowerCase()} lớn hơn 0.` : `Nhập ${noun.toLowerCase()}.`;
  }
  if (issue === "negative") return `${noun} không được âm. Nhập lại, ví dụ 150.000.`;
  if (issue === "too_long") return `${noun} quá lớn, tối đa ${maxDigits} chữ số (${maxMoneyText(maxDigits)}).`;
  if (issue === "invalid") return `${noun} chỉ gồm chữ số. Nhập lại, ví dụ 150.000.`;
  if (rule.positive && parseMoney(text, maxDigits) === 0) {
    return rule.allowEmpty ? `${noun} phải lớn hơn 0, hoặc để trống nếu chưa có.` : `Nhập ${noun.toLowerCase()} lớn hơn 0.`;
  }
  return null;
}

/**
 * Chuỗi tiền gửi BE: đúng số nguyên đồng, không số lẻ ("1650000").
 * NÉM LỖI khi ô trống hoặc không hợp lệ: không có đường nào đổi giá trị lỗi thành "0".
 * Người gọi phải kiểm bằng `moneyMessage` trước (và tự quyết ô trống nghĩa là gì).
 */
export function moneyBody(text: string, maxDigits: number = MONEY_MAX_DIGITS): string {
  const n = parseMoney(text, maxDigits);
  if (n === null) throw new Error(`Số tiền không hợp lệ, không gửi: ${moneyIssue(text, maxDigits) ?? "invalid"}`);
  return String(n);
}
