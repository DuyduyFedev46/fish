// CS-17 — mã trên tem giao hàng: "GH-<mã phiếu>.<lần in>", ví dụ GH-HD-0001-AB12C.1 (khớp regex của BE).
// Kiểm ở máy khách TRƯỚC khi gọi API: chuỗi gõ nhầm (số điện thoại, tên khách) không bao giờ lên đường dẫn của request
// nên không lọt vào access log (QA L1, bất biến 9). Hàm thuần, không đụng log, URL, localStorage.
import type { TagLookup } from "./types";

/** Cùng regex với BE `lookup`: ^GH-[A-Z0-9-]{3,40}\.\d{1,3}$. */
export const TAG_CODE_RE = /^GH-[A-Z0-9-]{3,40}\.\d{1,3}$/;

export const TAG_MESSAGES = {
  empty: "Nhập hoặc quét mã trên tem.",
  /** Không lặp lại chuỗi người dùng đã gõ (có thể là số điện thoại). */
  invalid: "Mã tem không đúng. Mã trên tem bắt đầu bằng GH- và kết thúc bằng dấu chấm kèm số, ví dụ GH-HD-0001-AB12C.1.",
  notFound: "Không tìm thấy phiếu. Kiểm tra lại mã trên tem rồi tra lại.",
  forbidden: "Bạn không có quyền tra mã tem.",
  failed: "Chưa tra được mã tem. Kiểm tra mạng rồi bấm Tra mã lại.",
  camera: "Không mở được camera. Gõ mã trên tem vào ô bên trên.",
} as const;

export type TagCheck = { ok: true; code: string } | { ok: false; message: string };

/** Máy quét USB gõ như bàn phím và có thể kèm khoảng trắng hay xuống dòng: bỏ rồi đổi sang chữ hoa. */
export function normalizeTagCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

export function checkTagCode(raw: string): TagCheck {
  const code = normalizeTagCode(raw);
  if (!code) return { ok: false, message: TAG_MESSAGES.empty };
  if (!TAG_CODE_RE.test(code)) return { ok: false, message: TAG_MESSAGES.invalid };
  return { ok: true, code };
}

/** Cảnh báo của kết quả tra: vàng = tem cũ, đỏ = đơn đã huỷ. null = tem còn hiệu lực. */
export function tagWarning(res: Pick<TagLookup, "warning" | "valid_print_no">): { kind: "warn" | "error"; text: string } | null {
  if (res.warning === "BR-GH-07") return { kind: "error", text: "Đơn đã huỷ, không soạn, xé tem." };
  if (res.warning === "BR-GH-16") {
    return {
      kind: "warn",
      text: res.valid_print_no ? `Tem này không còn hiệu lực, dùng tem lần ${res.valid_print_no}.` : "Tem này không còn hiệu lực. In tem mới rồi xé tem cũ.",
    };
  }
  return null;
}
