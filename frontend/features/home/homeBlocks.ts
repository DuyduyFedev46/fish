/**
 * Đọc khối trang chủ từ CMS (SHOP-5-03; 02b §3.7.2). Hàm thuần: chỉ đổi JSON thân bài sang dữ liệu trình bày,
 * không gọi API (nạp ở `homeContent.ts`). Khối sai dạng thì bỏ qua khối đó, không ném lỗi.
 *
 * - `home-banner`: mỗi slide = heading cấp 2 (tiêu đề) + paragraph (câu phụ) + tuỳ chọn paragraph chỉ chứa một link
 *   nội bộ (nút) + tuỳ chọn image (ảnh nền). Tối đa 3 slide. `excerpt` = dải chữ đầu trang (rỗng thì ẩn).
 * - `home-commitments`: một khối list; mỗi mục = phần đậm (tiêu đề) + phần thường (mô tả). Tối đa 4 mục.
 *   Điện thoại hiện tiêu đề 3 mục đầu, máy tính hiện 2 mục đầu kèm mô tả (02a §7.3).
 */
import type { InlineNode, PublicBlock } from "@/features/content/types";

export const MAX_BANNER_SLIDES = 3;
export const MAX_COMMITMENTS = 4;
export const MOBILE_COMMITMENTS = 3;
export const DESKTOP_COMMITMENTS = 2;

export interface BannerSlide {
  title: string;
  subtitle: string;
  button: { label: string; href: string } | null;
  image: { src: string; alt: string } | null;
}

export type CommitmentIcon = "snowflake" | "truck" | "qr" | "check";

export interface Commitment {
  title: string;
  detail: string;
  icon: CommitmentIcon;
}

type BodyLike = { blocks?: unknown } | null | undefined;

function blocksOf(body: BodyLike): PublicBlock[] {
  const blocks = body && Array.isArray(body.blocks) ? body.blocks : [];
  return blocks.filter((b): b is PublicBlock => !!b && typeof b === "object" && typeof (b as PublicBlock).type === "string");
}

function nodesOf(value: unknown): InlineNode[] {
  if (!Array.isArray(value)) return [];
  return value.filter((n): n is InlineNode => !!n && typeof n === "object" && typeof (n as InlineNode).text === "string");
}

function textOf(nodes: InlineNode[]): string {
  return nodes
    .map((n) => n.text)
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

/** Link nội bộ của Shop: bắt đầu bằng "/" một lần, không "//", không ký tự điều khiển hay khoảng trắng. */
export function isInternalHref(href: unknown): href is string {
  if (typeof href !== "string" || href.length === 0 || href.length > 300) return false;
  if (!href.startsWith("/") || href.startsWith("//") || href.includes("\\")) return false;
  return !/[\s\u0000-\u001f]/.test(href);
}

/** Đoạn chỉ gồm một link nội bộ (chữ ngoài link chỉ là khoảng trắng) -> nút; còn lại -> null. */
function buttonOf(nodes: InlineNode[]): { label: string; href: string } | null {
  const links = nodes.filter((n) => n.href);
  if (links.length !== 1) return null;
  const outside = nodes.filter((n) => !n.href).map((n) => n.text).join("").trim();
  const label = links[0].text.replace(/\s+/g, " ").trim();
  if (outside || !label || !isInternalHref(links[0].href)) return null;
  return { label, href: links[0].href as string };
}

/** Thân bài `home-banner` -> danh sách slide (tối đa 3). Slide thiếu tiêu đề bị bỏ. */
export function parseBanner(body: BodyLike): BannerSlide[] {
  const slides: BannerSlide[] = [];
  let current: BannerSlide | null = null;
  const flush = () => {
    if (current && current.title) slides.push(current);
    current = null;
  };
  for (const block of blocksOf(body)) {
    if (block.type === "heading") {
      flush();
      const title = typeof block.text === "string" ? block.text.replace(/\s+/g, " ").trim() : "";
      current = title && block.level === 2 ? { title, subtitle: "", button: null, image: null } : null;
      continue;
    }
    if (!current) continue;
    if (block.type === "paragraph") {
      const nodes = nodesOf(block.children);
      const button = buttonOf(nodes);
      if (button) {
        if (!current.button) current.button = button;
      } else if (!current.subtitle && !nodes.some((n) => n.href)) {
        current.subtitle = textOf(nodes);
      }
    } else if (block.type === "image" && !current.image) {
      const src = block.urls?.lg || block.urls?.md || block.urls?.sm;
      if (typeof src === "string" && /^https?:\/\//.test(src)) {
        current.image = { src, alt: typeof block.alt === "string" ? block.alt : "" };
      }
    }
  }
  flush();
  return slides.slice(0, MAX_BANNER_SLIDES);
}

/** Dải chữ đầu trang: `excerpt` của `home-banner`, gọn khoảng trắng. Rỗng -> "" (ẩn). */
export function stripTextOf(excerpt: unknown): string {
  return typeof excerpt === "string" ? excerpt.replace(/\s+/g, " ").trim() : "";
}

function fold(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

/** Icon theo chữ tiêu đề: đông -> bông tuyết, giao -> xe, QR/chuyển khoản/thanh toán -> mã QR, còn lại -> dấu tích. */
export function commitmentIcon(title: string): CommitmentIcon {
  const t = fold(title);
  if (/\bdong\b/.test(t)) return "snowflake";
  if (/\bgiao\b/.test(t)) return "truck";
  if (/\bqr\b|chuyen khoan|thanh toan/.test(t)) return "qr";
  return "check";
}

/** Thân bài `home-commitments` -> mục cam kết (tối đa 4). Lấy khối list đầu tiên; mục không có phần đậm bị bỏ. */
export function parseCommitments(body: BodyLike): Commitment[] {
  const list = blocksOf(body).find((b) => b.type === "list");
  if (!list || list.type !== "list" || !Array.isArray(list.items)) return [];
  const out: Commitment[] = [];
  for (const raw of list.items) {
    const nodes = nodesOf(raw);
    const title = textOf(nodes.filter((n) => n.marks?.includes("bold")));
    if (!title) continue;
    const detail = textOf(nodes.filter((n) => !n.marks?.includes("bold"))).replace(/^[\s:·.\-–—]+/, "");
    out.push({ title, detail, icon: commitmentIcon(title) });
    if (out.length >= MAX_COMMITMENTS) break;
  }
  return out;
}

/** Dải chữ dự phòng khi CMS chưa có `home-banner` (06-marketing K2). Số kg tối thiểu lấy từ site-info (review lô 1, L7). */
export function fallbackStripText(minQtyKg: unknown): string {
  const raw = typeof minQtyKg === "string" || typeof minQtyKg === "number" ? String(minQtyKg).trim() : "";
  if (!/^\d+(\.\d+)?$/.test(raw)) return "";
  const kg = String(Number(raw)).replace(".", ",");
  return `Hải sản cấp đông theo lô · mua từ ${kg} kg · giao tận nhà`;
}
