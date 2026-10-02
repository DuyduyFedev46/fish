// Bỏ mã luật nghiệp vụ (BR-MH-07, BR-PQ-10…) khỏi câu lỗi BE trước khi hiện lên màn hình (UI-RULES §1: người dùng không đọc mã luật).
// Mã vẫn nằm ở `ApiError.code` cho log và logic; chỉ phần chữ hiển thị (`message`) bị lọc. Hàm thuần.

const RULE_CODE = "(?:BR|DW|V|E|P)-[A-Z0-9]+(?:-[A-Z0-9]+)*";
// "(BR-MH-07)", "(BR-MH-07, BR-PQ-10)": ngoặc chỉ chứa mã luật.
const PAREN_CODES = new RegExp(`\\s*[(（]\\s*${RULE_CODE}(?:\\s*[,;/]\\s*${RULE_CODE})*\\s*[)）]`, "g");
// Mã trần nằm giữa câu: "… theo BR-MH-07 …".
const BARE_BR_CODE = /\s*\bBR-[A-Z]+(?:-\d+)?\b/g;

/** "Phiếu nhập đã bị huỷ (BR-MH-07)." → "Phiếu nhập đã bị huỷ." Câu không có mã luật giữ nguyên. */
export function stripRuleCodes(message: string): string {
  if (!/\b(?:BR|DW|V|E|P)-[A-Z0-9]/.test(message)) return message;
  return message
    .replace(PAREN_CODES, "")
    .replace(BARE_BR_CODE, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([.,;:!?])/g, "$1")
    .trim();
}
