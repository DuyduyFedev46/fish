/**
 * Xử lý chữ cho tìm kiếm (SHOP-2-04). File thuần TypeScript, không import gì
 * (test bằng `scripts/test-catalog-view.mjs`).
 */

/**
 * Bỏ dấu tiếng Việt và hạ chữ thường: "Mực Ống" -> "muc ong", "Đông" -> "dong".
 * Chuẩn hoá về dạng gộp trước, rồi xử lý từng ký tự, nên độ dài chuỗi kết quả bằng độ dài chuỗi gộp
 * (dùng để tô đậm đúng phần khớp trong chuỗi gốc).
 */
export function foldVietnamese(input: string): string {
  const composed = input.normalize("NFC");
  let out = "";
  for (const ch of composed) {
    if (ch === "đ" || ch === "Đ") {
      out += "d";
      continue;
    }
    const base = ch.normalize("NFD").replace(/[̀-ͯ]/g, "");
    out += (base || ch).toLowerCase();
  }
  return out;
}

/** Chuỗi đã gộp (NFC), cùng dạng mà `foldVietnamese` dùng để đếm vị trí. */
export function composeVietnamese(input: string): string {
  return input.normalize("NFC");
}

/** Chuỗi trông như số điện thoại hay mã nhạy cảm: có từ 9 chữ số trở lên (bất biến 9). */
export function looksLikePhone(input: string): boolean {
  return (input.match(/\d/g) ?? []).length >= 9;
}
