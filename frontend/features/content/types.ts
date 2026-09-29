/**
 * Kiểu dữ liệu nội dung công khai cho Shop Cá Về (CMS-13, CMS-14).
 * Bất biến 1 & 9: Tuyệt đối không chứa ID nội bộ, giá vốn hay thông tin cá nhân.
 */

export interface PublicImageUrls {
  sm: string;
  md: string;
  lg: string;
}

export interface PublicImage {
  alt: string;
  width: number;
  height: number;
  urls: PublicImageUrls;
}

export interface PublicCategory {
  slug: string;
  name: string;
  description: string;
}

export type InlineNode = {
  text: string;
  marks?: Array<"bold" | "italic">;
  href?: string;
};

export type PublicBlock =
  | { type: "heading"; level: 2 | 3; text: string }
  | { type: "paragraph"; children: InlineNode[] }
  | { type: "quote"; children: InlineNode[] }
  | { type: "list"; ordered: boolean; items: InlineNode[][] }
  | {
      type: "image";
      alt: string;
      caption?: string;
      width: number;
      height: number;
      urls: PublicImageUrls;
    }
  | { type: "item_card"; item_code: string };

export interface PublicBodyDoc {
  type: "doc";
  blocks: PublicBlock[];
}

export interface PublicEntryDetail {
  kind: "post" | "page";
  slug: string;
  title: string;
  seo_title: string;
  description: string;
  excerpt: string;
  category: { slug: string; name: string } | null;
  cover_image: PublicImage | null;
  body: PublicBodyDoc;
  published_at: string;
  updated_at: string;
  version: number;
  effective_from: string;
  author: string; // Luôn là "Cá Về"
}

export interface PublicEntryListItem {
  slug: string;
  title: string;
  excerpt: string;
  category: { slug: string; name: string } | null;
  cover_image: PublicImage | null;
  published_at: string;
}

export interface PublicEntryListResponse {
  results: PublicEntryListItem[];
  count?: number;
  total?: number;
  next?: string | null;
  previous?: string | null;
  page?: number;
  total_pages?: number;
}

export interface FooterLink {
  title: string;
  slug: string;
}

export interface PageByRoleResponse {
  slug: string;
  title: string;
  version: number;
  version_id: number;
  effective_from: string;
}

