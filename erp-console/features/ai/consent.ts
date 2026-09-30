// Đồng ý của người dùng trước khi trợ lý tải model về máy (S08-AC1, C.2).
// CHỈ lưu cờ boolean — KHÔNG ghi bất kỳ dữ liệu cá nhân nào (bất biến 9).

const KEY = "cave_erp_ai_consent";

// Người nghe thay đổi cờ đồng ý trong CÙNG tab (SR-20: nút "Tóm tắt" ở màn nghiệp vụ, chạy model local, cần biết ngay khi người dùng vừa bấm đồng ý; "Để AI làm" không xét đồng ý — F6-2).
const listeners = new Set<() => void>();

export function subscribeAiConsent(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

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
  listeners.forEach((cb) => cb());
}
