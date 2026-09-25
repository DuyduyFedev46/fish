// Tìm kiếm phía máy (như bản HTML cũ: chuỗi con, không phân biệt hoa thường), thêm: bỏ dấu tiếng Việt
// để gõ "ca thu" vẫn ra "Cá thu". Mọi kết quả bản cũ khớp thì bản mới cũng khớp.

export function fold(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .trim();
}

/** q rỗng → luôn khớp. */
export function matches(q: string, ...fields: (string | number | null | undefined)[]): boolean {
  const needle = fold(q);
  if (!needle) return true;
  return fold(fields.filter((f) => f !== null && f !== undefined).join(" ")).includes(needle);
}
