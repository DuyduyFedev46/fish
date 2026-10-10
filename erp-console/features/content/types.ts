/**
 * Kiểu dữ liệu cho module Nội dung / CMS (doc/features/2026-09-28-cms-viet-bai)
 */

export type ContentKind = "post" | "page";

export type ContentStatus = "draft" | "pending_review" | "published" | "unpublished";

export type ContentPageRole =
  | "privacy"
  | "terms"
  | "refund"
  | "seller_info"
  | "shipping"
  | "payment"
  | "complaints"
  | null;

export interface ContentCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  order: number;
  is_active: boolean;
  published_count: number;
}

export interface ContentEntryListItem {
  id: number;
  kind: ContentKind;
  status: ContentStatus;
  title: string;
  slug: string;
  category: number | null;
  has_unpublished_changes: boolean;
  updated_at: string;
  source: "human" | "ai";
  page_role: ContentPageRole;
}

export interface ContentCounts {
  draft: number;
  pending_review: number;
  published: number;
  unpublished: number;
}

export interface CategoryCreatePayload {
  name: string;
  description?: string;
  order?: number;
}

export interface CategoryUpdatePayload {
  name?: string;
  description?: string;
  order?: number;
  is_active?: boolean;
}

/** Phần `details` của lỗi BR-ND-02 khi ngừng dùng chuyên mục còn bài đang đăng (BE: tối đa 5 bài kèm tổng số). */
export interface DeactivateCategoryBlockedDetails {
  entries: Array<{ id: number; title: string }>;
  total: number;
}

export interface ContentImage {
  id: number;
  alt: string;
  width: number;
  height: number;
  urls: {
    sm: string;
    md: string;
    lg: string;
  };
}

export type InlineNode = {
  text: string;
  marks?: Array<"bold" | "italic">;
  href?: string;
};

export type Block =
  | { type: "heading"; level: 2 | 3; text: string }
  | { type: "paragraph"; children: InlineNode[] }
  | { type: "quote"; children: InlineNode[] }
  | { type: "list"; ordered: boolean; items: InlineNode[][] }
  | { type: "image"; image_id: number; alt?: string; caption?: string }
  | { type: "item_card"; item_code: string };

export interface BodyDoc {
  type: "doc";
  blocks: Block[];
}

export interface ContentEntryDetail {
  id: number;
  kind: ContentKind;
  status: ContentStatus;
  title: string;
  slug: string;
  slug_locked: boolean;
  category: number | null;
  excerpt: string;
  seo_title: string;
  seo_description: string;
  cover_image: number | null;
  body: BodyDoc;
  images: ContentImage[];
  has_unpublished_changes: boolean;
  published_version: number | null;
  first_published_at: string | null;
  last_published_at: string | null;
  restored_from: number | null;
  return_reason: string;
  page_role: ContentPageRole;
  required_for_golive: boolean;
  show_in_footer: boolean;
  footer_order: number;
  public_url: string | null;
  source: "human" | "ai";
  row_version: number;
  updated_at: string;
}

export interface EntryCreatePayload {
  kind?: ContentKind;
  title?: string;
  slug?: string;
  category?: number | null;
  excerpt?: string;
  seo_title?: string;
  seo_description?: string;
  cover_image?: number | null;
  body?: BodyDoc;
  page_role?: ContentPageRole;
  show_in_footer?: boolean;
  footer_order?: number;
}

export interface EntryUpdatePayload {
  row_version: number;
  kind?: ContentKind;
  title?: string;
  slug?: string;
  category?: number | null;
  excerpt?: string;
  seo_title?: string;
  seo_description?: string;
  cover_image?: number | null;
  body?: BodyDoc;
  page_role?: ContentPageRole;
  show_in_footer?: boolean;
  footer_order?: number;
}

/** Trường BE báo thiếu khi đăng/gửi duyệt (400 BR-ND-03, `details.missing`). */
export type MissingField =
  | "title"
  | "slug"
  | "body"
  | "category"
  | "cover_image"
  | "cover_image_alt"
  | "description";

export interface ContentWarning {
  type: "phone_like" | "cost_keyword" | "item_unavailable";
  field?: string;
  snippet?: string;
  item_code?: string;
}

export interface EntryPublishPayload {
  row_version: number;
  checklist_confirmed: boolean;
  acknowledge_warnings?: boolean;
}

export interface EntryPublishResponse {
  id: number;
  slug: string;
  status: ContentStatus;
  version: number;
  public_url: string;
  row_version: number;
}

export type UnpublishReason =
  | "wrong_price"
  | "complaint"
  | "out_of_season"
  | "wrong_content"
  | "other";

export interface EntryUnpublishPayload {
  row_version: number;
  reason: UnpublishReason;
}

/** Máy chủ chỉ trả trạng thái mới và phiên bản dòng, không trả cả bài. */
export interface EntryUnpublishResponse {
  status: ContentStatus;
  row_version: number;
}

export interface EntryDiscardPayload {
  row_version: number;
}

export interface GoliveStatusResponse {
  missing_roles: string[];
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

export type ReturnReason =
  | "missing_info"
  | "wrong_content"
  | "legal_risk"
  | "other";

export interface EntrySubmitPayload {
  row_version: number;
  acknowledge_warnings?: boolean;
}

export interface EntrySubmitResponse {
  status: string;
  row_version: number;
}

export interface EntryReturnPayload {
  row_version: number;
  reason: ReturnReason;
}

export interface EntryReturnResponse {
  status: string;
  row_version: number;
  return_reason?: string;
}

export interface EntryRestorePayload {
  row_version: number;
}

export interface ContentEntryVersionListItem {
  version: number;
  published_at: string;
  published_by_name: string;
  title: string;
  restored_from: number | null;
}

export interface ContentEntryVersionDetail {
  version: number;
  published_at: string;
  published_by_name: string;
  kind: ContentKind;
  title: string;
  slug: string;
  excerpt: string;
  seo_title: string;
  seo_description: string;
  description: string;
  category: number | null;
  cover_image: number | null;
  body: BodyDoc;
  restored_from: number | null;
}



