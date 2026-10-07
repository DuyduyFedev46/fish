// Luật ô tìm mã chứng từ của Nhật ký (ED-41-AC2, contract Lô 17a A3). Giống BE: 2–40 ký tự `[0-9A-Za-z#._-]`, không có dãy từ 9 chữ số
// (chặn gõ nhầm SĐT: tìm theo số điện thoại không thuộc nhật ký). Kiểm ở máy để khỏi gửi chuỗi chắc chắn bị 400; BE vẫn là lớp chặn thật.
// Hàm thuần, không đụng React hay mạng.

export const AUDIT_Q_MIN = 2;
export const AUDIT_Q_MAX = 40;

export type AuditQueryCheck = { ok: true; q: string } | { ok: false; q: ""; message: string | null };

/** `message: null` = chưa đủ ký tự để tìm (không báo lỗi, chỉ chưa gửi). */
export function checkAuditQuery(raw: string): AuditQueryCheck {
  const q = raw.trim();
  if (!q) return { ok: false, q: "", message: null };
  if (/\d{9,}/.test(q)) return { ok: false, q: "", message: "Chỉ tìm theo mã chứng từ." };
  if (q.length > AUDIT_Q_MAX) return { ok: false, q: "", message: `Mã tìm tối đa ${AUDIT_Q_MAX} ký tự.` };
  if (!/^[0-9A-Za-z#._-]+$/.test(q)) return { ok: false, q: "", message: "Mã chứng từ chỉ gồm chữ không dấu, số và các ký tự # . _ -" };
  if (q.length < AUDIT_Q_MIN) return { ok: false, q: "", message: null };
  return { ok: true, q };
}

/** Khoảng ngày đảo ngược (từ sau đến) thì BE trả 400; FE báo trước và không gửi. */
export function auditRangeError(from: string, to: string): string | null {
  return from && to && from > to ? "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc." : null;
}
