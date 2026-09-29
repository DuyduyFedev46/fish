/**
 * Kiểm tra và chuẩn hoá href an toàn chống XSS (§6.3 02b-tech-design, CMS-13-AC3).
 * Tuyệt đối từ chối javascript:, data:, vbscript: hoặc các giao thức độc hại khác.
 */

const SAFE_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);

export function isSafeHref(href?: string): boolean {
  if (!href) return false;
  const trimmed = href.trim();
  if (!trimmed) return false;

  // Relative path hoặc anchor
  if (trimmed.startsWith("/") || trimmed.startsWith("#")) {
    return true;
  }

  // Parse protocol
  try {
    const parsed = new URL(trimmed, "http://localhost");
    return SAFE_PROTOCOLS.has(parsed.protocol);
  } catch {
    return false;
  }
}

export function isExternalLink(href?: string): boolean {
  if (!href) return false;
  const trimmed = href.trim().toLowerCase();
  return trimmed.startsWith("http://") || trimmed.startsWith("https://");
}
