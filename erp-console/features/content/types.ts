/**
 * Kiểu dữ liệu cho module Nội dung / CMS (doc/features/2026-09-28-cms-viet-bai)
 */

export type ContentKind = "post" | "page";

export type ContentStatus = "draft" | "pending_review" | "published" | "unpublished";

export type ContentPageRole = "privacy" | "terms" | "refund" | "seller_info" | null;

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

export interface DeactivateCategoryBlockedError {
  detail: string;
  code: string;
  entries: Array<{ id: number; title: string }>;
  total: number;
}
