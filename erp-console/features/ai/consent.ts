// Đồng ý của người dùng trước khi trợ lý tải model về máy (S08-AC1, C.2).
// CHỈ lưu cờ boolean — KHÔNG ghi bất kỳ dữ liệu cá nhân nào (bất biến 9).

const KEY = "cave_erp_ai_consent";

export function hasAiConsent(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function setAiConsent(v: boolean): void {
  if (typeof window === "undefined") return;
  try {
    if (v) window.localStorage.setItem(KEY, "1");
    else window.localStorage.removeItem(KEY);
  } catch {
    // hết dung lượng / chặn storage → coi như chưa đồng ý, vẫn nhập tay được
  }
}
