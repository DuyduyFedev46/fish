/** Ghép tên class, bỏ giá trị rỗng. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Link nội bộ (route của Shop) đi qua next/link; tel:, mailto:, http(s): là thẻ <a> thường. */
export function isInternalHref(href: string): boolean {
  return href.startsWith("/") && !href.startsWith("//");
}
