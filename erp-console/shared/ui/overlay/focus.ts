// Việc dùng chung của hộp thoại / menu nổi: tìm phần tử bấm được và giữ Tab trong một vùng.
// Tách khỏi Modal.tsx để kiểm bằng vitest (không cần DOM thật).

export const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function focusablesIn(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.offsetParent !== null && !el.closest("[hidden]"),
  );
}

/**
 * Phần tử cần focus khi bấm Tab / Shift+Tab trong vùng giữ focus, hoặc null nếu để trình duyệt tự đi.
 * `items` = các phần tử bấm được theo thứ tự; `active` = phần tử đang focus; `root` = chính vùng giữ focus.
 */
export function trapTarget<T>(items: T[], active: T | null, root: T, shift: boolean, rootContains: (el: T | null) => boolean): T | null {
  if (items.length === 0) return root;
  const first = items[0];
  const last = items[items.length - 1];
  if (!rootContains(active)) return first;
  if (shift && (active === first || active === root)) return last;
  if (!shift && active === last) return first;
  return null;
}
