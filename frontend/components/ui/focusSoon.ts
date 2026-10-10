/**
 * Đặt tiêu điểm vào phần tử, thử lại một lần sau khi hộp thoại đang đóng xong.
 * Khi <dialog> modal còn mở, phần còn lại của trang bị khoá nên focus() lần đầu không ăn.
 */
export function focusSoon(el: HTMLElement | null | undefined): void {
  if (!el) return;
  el.focus();
  if (document.activeElement === el) return;
  window.setTimeout(() => {
    if (el.isConnected) el.focus();
  }, 220);
}
