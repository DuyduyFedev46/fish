// Mục lục cho trang chính sách và bài Góc bếp (SHOP-5-04 AC1, COMPONENTS #36 PolicyNav mục 7).
// Mỗi tiêu đề cấp 2 trong thân bài CMS có một `id` ổn định sinh từ chữ; mục lục và thân bài dùng chung hàm này
// nên link neo luôn khớp. File thuần TypeScript, không import gì ngoài kiểu.

import type { PublicBlock } from "./types";

/** "1. Điều kiện đổi" -> "dieu-kien-doi". Bỏ số thứ tự đầu dòng, bỏ dấu, chỉ giữ a-z 0-9 và gạch nối. */
export function slugifyHeading(text: string): string {
  const folded = text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[đĐ]/g, "d")
    .toLowerCase();
  const base = folded
    .replace(/^\s*\d+[.)]\s*/, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return base || "muc";
}

export interface TocEntry {
  id: string;
  label: string;
}

/**
 * Gán `id` cho các khối tiêu đề cấp 2 theo thứ tự xuất hiện; trùng chữ thì thêm hậu tố "-2", "-3".
 * Trả về map chỉ số khối -> id và danh sách mục lục.
 */
export function headingAnchors(blocks: PublicBlock[]): { idByIndex: Map<number, string>; toc: TocEntry[] } {
  const idByIndex = new Map<number, string>();
  const toc: TocEntry[] = [];
  const used = new Map<string, number>();
  blocks.forEach((block, index) => {
    if (block.type !== "heading" || block.level !== 2) return;
    const base = `muc-${slugifyHeading(block.text)}`;
    const count = (used.get(base) ?? 0) + 1;
    used.set(base, count);
    const id = count === 1 ? base : `${base}-${count}`;
    idByIndex.set(index, id);
    toc.push({ id, label: block.text.replace(/^\s*\d+[.)]\s*/, "") });
  });
  return { idByIndex, toc };
}
