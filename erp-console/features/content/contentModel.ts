// Logic thuần của module Nội dung (ED-35, ED-36): đọc lỗi BE, câu chữ lỗi, quyền, trạng thái, lọc danh sách.
// Không đụng React, mạng hay storage — để vitest kiểm từng ca (contentModel.test.ts).
//
// Hợp đồng lỗi của BE (kiểm trong backend/apps/content): phần "thêm" của BusinessError nằm ở `ApiError.details`
// (CONTENT_WARNINGS → details.warnings, BR-ND-03 → details.missing, BR-ND-04 → details.suggestion,
// BR-ND-02 ngừng chuyên mục → details.entries + details.total), KHÔNG nằm trên chính đối tượng lỗi.

import { ApiError } from "@/shared/lib/http";
import { stripRuleCodes } from "@/shared/lib/ruleCodes";
import { CONTENT_MSG as M, MISSING_LABELS, RETURN_REASONS, UNPUBLISH_REASONS } from "./messages";
import type {
  BodyDoc,
  ContentEntryDetail,
  ContentEntryListItem,
  ContentImage,
  ContentKind,
  ContentPageRole,
  ContentStatus,
  ContentWarning,
  DeactivateCategoryBlockedDetails,
  EntryCreatePayload,
  EntryUpdatePayload,
} from "./types";

/** Quyền thật của app content (không dựa tên nhóm: UI-RULES §8.1). */
export const CONTENT_PERM = {
  view: "content.view_entry",
  add: "content.add_entry",
  change: "content.change_entry",
  delete: "content.delete_entry",
  publish: "content.publish_entry",
  addCategory: "content.add_category",
  changeCategory: "content.change_category",
} as const;

export type PermHolder = { permissions: string[] } | null | undefined;

export function hasPerm(me: PermHolder, perm: string): boolean {
  return !!me?.permissions?.includes(perm);
}

// ---- Đọc lỗi BE ----

function detailsOf(err: unknown): Record<string, unknown> {
  if (err instanceof ApiError && err.details && typeof err.details === "object") return err.details as Record<string, unknown>;
  return {};
}

export function isApiCode(err: unknown, code: string): boolean {
  return err instanceof ApiError && err.code === code;
}

export function isStale(err: unknown): boolean {
  return isApiCode(err, "STALE_VERSION");
}

const WARNING_TYPES = new Set(["phone_like", "cost_keyword", "item_unavailable"]);

/** 409 CONTENT_WARNINGS → danh sách cảnh báo; thiếu/hỏng → mảng rỗng. */
export function warningsOf(err: unknown): ContentWarning[] {
  if (!isApiCode(err, "CONTENT_WARNINGS")) return [];
  const raw = detailsOf(err).warnings;
  if (!Array.isArray(raw)) return [];
  const out: ContentWarning[] = [];
  for (const w of raw) {
    if (!w || typeof w !== "object") continue;
    const r = w as Record<string, unknown>;
    if (typeof r.type !== "string" || !WARNING_TYPES.has(r.type)) continue;
    out.push({
      type: r.type as ContentWarning["type"],
      field: typeof r.field === "string" ? r.field : undefined,
      snippet: typeof r.snippet === "string" ? r.snippet : undefined,
      item_code: typeof r.item_code === "string" ? r.item_code : undefined,
    });
  }
  return out;
}

/** 400 BR-ND-03 → danh sách trường còn thiếu (mã BE). */
export function missingOf(err: unknown): string[] {
  if (!isApiCode(err, "BR-ND-03")) return [];
  const raw = detailsOf(err).missing;
  return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === "string") : [];
}

/** 400 BR-ND-04 (đường dẫn trùng) → đường dẫn BE gợi ý, nếu có. */
export function suggestionOf(err: unknown): string | null {
  if (!isApiCode(err, "BR-ND-04")) return null;
  const s = detailsOf(err).suggestion;
  return typeof s === "string" && /^[a-z0-9-]{1,200}$/.test(s) ? s : null;
}

/** 400 BR-ND-02 khi ngừng dùng chuyên mục còn bài đang đăng. */
export function blockedDetailsOf(err: unknown): DeactivateCategoryBlockedDetails | null {
  if (!isApiCode(err, "BR-ND-02")) return null;
  const d = detailsOf(err);
  const entries: DeactivateCategoryBlockedDetails["entries"] = [];
  if (Array.isArray(d.entries)) {
    for (const e of d.entries) {
      if (e && typeof e === "object" && typeof (e as { id?: unknown }).id === "number") {
        const r = e as { id: number; title?: unknown };
        entries.push({ id: r.id, title: typeof r.title === "string" ? r.title : "" });
      }
    }
  }
  const total = typeof d.total === "number" ? d.total : entries.length;
  return { entries, total };
}

/** Tên chuyên mục trùng: BE trả 400 BR-ND-04 với câu "Chuyên mục '…' đã tồn tại". */
export function isCategoryNameTaken(err: unknown): boolean {
  return isApiCode(err, "BR-ND-04");
}

/** Câu lỗi để hiện: bỏ mã luật; lỗi lạ (không phải ApiError) → `fallback`. */
export function errorText(err: unknown, fallback: string): string {
  if (err instanceof ApiError && err.message) return stripRuleCodes(err.message);
  return fallback;
}

export function missingLabels(missing: string[]): string[] {
  return missing.map((m) => MISSING_LABELS[m] ?? m);
}

/** Câu "Chưa đăng được. Còn thiếu: …". */
export function missingSentence(missing: string[], action: "publish" | "submit"): string {
  const labels = missingLabels(missing);
  return action === "publish" ? M.publishMissing(labels) : M.submitMissing(labels);
}

/** Một dòng cảnh báo cho hộp "Có chỗ cần xem lại". */
export function warningLine(w: ContentWarning): string {
  if (w.type === "phone_like") return M.warnPhone;
  if (w.type === "cost_keyword") return M.warnCost;
  return M.warnItem(w.item_code ?? "");
}

// ---- Form soạn bài ----

export type EntryForm = {
  kind: ContentKind;
  title: string;
  slug: string;
  category: number | null;
  excerpt: string;
  seoTitle: string;
  seoDescription: string;
  coverImageId: number | null;
  body: BodyDoc;
  pageRole: ContentPageRole;
  showInFooter: boolean;
  footerOrder: number;
};

export const EMPTY_BODY: BodyDoc = { type: "doc", blocks: [] };

export function emptyForm(kind: ContentKind): EntryForm {
  return {
    kind,
    title: "",
    slug: "",
    category: null,
    excerpt: "",
    seoTitle: "",
    seoDescription: "",
    coverImageId: null,
    body: EMPTY_BODY,
    pageRole: null,
    showInFooter: false,
    footerOrder: 0,
  };
}

export function formOf(d: ContentEntryDetail): EntryForm {
  return {
    kind: d.kind,
    title: d.title || "",
    slug: d.slug || "",
    category: d.category,
    excerpt: d.excerpt || "",
    seoTitle: d.seo_title || "",
    seoDescription: d.seo_description || "",
    coverImageId: d.cover_image,
    body: d.body || EMPTY_BODY,
    pageRole: d.page_role || null,
    showInFooter: Boolean(d.show_in_footer),
    footerOrder: d.footer_order || 0,
  };
}

function pageFields(f: EntryForm): Pick<EntryCreatePayload, "page_role" | "show_in_footer" | "footer_order"> | Record<string, never> {
  return f.kind === "page" ? { page_role: f.pageRole || null, show_in_footer: f.showInFooter, footer_order: f.footerOrder } : {};
}

export function createPayloadOf(f: EntryForm): EntryCreatePayload {
  return {
    kind: f.kind,
    title: f.title.trim(),
    slug: f.slug.trim(),
    category: f.kind === "post" ? f.category : null,
    excerpt: f.excerpt.trim(),
    seo_title: f.seoTitle.trim(),
    seo_description: f.seoDescription.trim(),
    cover_image: f.coverImageId,
    body: f.body,
    ...pageFields(f),
  };
}

export function updatePayloadOf(f: EntryForm, rowVersion: number): EntryUpdatePayload {
  return { row_version: rowVersion, ...createPayloadOf(f) };
}

/** Bản nháp giữ trên máy: chỉ chữ do người viết soạn, không có dữ liệu khách. */
export type LocalDraft = Partial<{
  title: string;
  slug: string;
  category: number | null;
  excerpt: string;
  seo_title: string;
  seo_description: string;
  cover_image: number | null;
  body: BodyDoc;
  /** row_version của bài lúc người viết bắt đầu sửa; để biết bản trên máy có cũ hơn bản máy chủ không. */
  base_version: number;
}>;

export function localDraftOf(f: EntryForm, baseVersion?: number): LocalDraft {
  return {
    ...(baseVersion !== undefined ? { base_version: baseVersion } : {}),
    title: f.title,
    slug: f.slug,
    excerpt: f.excerpt,
    seo_title: f.seoTitle,
    seo_description: f.seoDescription,
    category: f.category,
    cover_image: f.coverImageId,
    body: f.body,
  };
}

/** Bản nháp trên máy có khác bản máy chủ không (so phần chữ, bỏ qua row_version). */
export function draftDiffers(server: EntryForm, d: LocalDraft): boolean {
  const a = localDraftOf(server);
  const b = localDraftOf(applyLocalDraft(server, d));
  return JSON.stringify(a) !== JSON.stringify(b);
}

/**
 * Bản nháp còn "mới" so với máy chủ khi dựng trên đúng phiên bản máy chủ đang giữ.
 * Thiếu base_version (nháp cũ) hoặc khác phiên bản = máy chủ đã đổi sau đó, không tự khôi phục.
 */
export function draftIsCurrent(d: LocalDraft, serverRowVersion: number): boolean {
  return d.base_version !== undefined && d.base_version === serverRowVersion;
}

export function applyLocalDraft(f: EntryForm, d: LocalDraft): EntryForm {
  return {
    ...f,
    title: d.title ?? f.title,
    slug: d.slug ?? f.slug,
    category: d.category !== undefined ? d.category : f.category,
    excerpt: d.excerpt ?? f.excerpt,
    seoTitle: d.seo_title ?? f.seoTitle,
    seoDescription: d.seo_description ?? f.seoDescription,
    coverImageId: d.cover_image !== undefined ? d.cover_image : f.coverImageId,
    body: d.body ?? f.body,
  };
}

// ---- Ảnh bìa ----

export function coverImageOf(images: ContentImage[], coverImageId: number | null): ContentImage | null {
  if (coverImageId === null) return null;
  return images.find((i) => i.id === coverImageId) ?? null;
}

/** Ảnh bìa đã chọn nhưng chưa có mô tả (BR-ND-03: cover_image_alt). */
export function coverAltMissing(images: ContentImage[], coverImageId: number | null): boolean {
  const cover = coverImageOf(images, coverImageId);
  return cover !== null && !cover.alt.trim();
}

// ---- Quyền theo trạng thái ----

export type EntryFacts = {
  status: ContentStatus;
  pageRole: ContentPageRole;
  publishedVersion: number | null;
  firstPublishedAt: string | null;
  hasUnpublishedChanges: boolean;
  saved: boolean;
};

/** Xoá chỉ cho nháp chưa từng đăng (BE: BR-ND-02). */
export function canDeleteEntry(f: EntryFacts): boolean {
  return f.saved && f.publishedVersion === null && f.firstPublishedAt === null;
}

export function deleteBlockedReason(f: EntryFacts): string | undefined {
  if (!f.saved) return M.blockedUnsaved;
  return canDeleteEntry(f) ? undefined : M.blockedHasPublished;
}

export function unpublishBlockedReason(f: EntryFacts): string | undefined {
  if (f.status !== "published") return M.blockedNotPublished;
  if (f.pageRole) return M.blockedGolivePage;
  return undefined;
}

export function discardBlockedReason(f: EntryFacts): string | undefined {
  if (f.status !== "published") return M.blockedNotPublished;
  return f.hasUnpublishedChanges ? undefined : M.blockedNoChanges;
}

export function historyBlockedReason(f: EntryFacts): string | undefined {
  if (!f.saved) return M.blockedUnsaved;
  return f.firstPublishedAt === null && f.status !== "published" && f.status !== "unpublished" ? M.blockedNeverPublished : undefined;
}

/** Nút chính ở header: quyền thật + trạng thái. null = không có nút chính. */
export type PrimaryAction = "publish" | "publish_changes" | "submit" | null;

export function primaryActionOf(status: ContentStatus, hasUnpublishedChanges: boolean, canPublish: boolean, canChange: boolean): PrimaryAction {
  if (canPublish) {
    if (status === "published") return hasUnpublishedChanges ? "publish_changes" : null;
    return "publish";
  }
  if (canChange && status === "draft") return "submit";
  return null;
}

// ---- StatusPath ----

export const STATUS_STEPS = [
  { key: "draft", label: M.stepDraft },
  { key: "pending_review", label: M.stepPending },
  { key: "published", label: M.stepPublished },
] as const;

export type PathView = {
  current: string;
  badEnd: { label: string; after: string } | null;
  next: string | null;
  done: string[];
};

export function pathViewOf(status: ContentStatus, canPublish: boolean, firstPublishedAt: string | null, savedOnce: boolean): PathView {
  const done: string[] = [];
  if (savedOnce) done.push(M.doneSaved);
  if (status === "pending_review") done.push(M.doneSubmitted);
  if (firstPublishedAt !== null || status === "published" || status === "unpublished") done.push(M.donePublished);
  if (status === "unpublished") {
    return { current: "published", badEnd: { label: "Đã gỡ", after: "published" }, next: null, done };
  }
  let next: string | null = null;
  if (status === "draft") next = canPublish ? M.stepNextDraftPublisher : M.stepNextDraftAuthor;
  else if (status === "pending_review") next = canPublish ? M.stepNextPending : null;
  return { current: status, badEnd: null, next, done };
}

// ---- Danh sách ----

/** Lọc tại chỗ theo tiêu đề hoặc đường dẫn (BE chưa có tìm kiếm). Không ghi từ khoá đi đâu. */
export function filterEntries(rows: ContentEntryListItem[], query: string): ContentEntryListItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((r) => r.title.toLowerCase().includes(q) || r.slug.toLowerCase().includes(q));
}

/** Cột "Ghi chú": suy từ dữ liệu có sẵn của danh sách. Rỗng = hiện "—". */
export function entryNote(row: ContentEntryListItem, aiOn: boolean): string {
  if (row.has_unpublished_changes) return M.noteUnpublished;
  if (aiOn && row.source === "ai" && row.status === "draft") return M.noteAiDraft;
  if (row.page_role && row.status !== "published") return M.noteGolive;
  return "";
}

export function categoryNameOf(map: Map<number, string>, id: number | null): string {
  if (id === null) return "";
  return map.get(id) ?? "";
}

export const STATUS_TAB_KEYS = ["all", "draft", "pending_review", "published", "unpublished"] as const;
export type StatusTab = (typeof STATUS_TAB_KEYS)[number];

export function statusOfTab(tab: StatusTab): string {
  return tab === "all" ? "" : tab;
}

export function kindFilterOf(v: string): "" | ContentKind {
  return v === "post" || v === "page" ? v : "";
}

export function categoryFilterOf(v: string): number {
  return /^\d{1,9}$/.test(v) ? Number(v) : 0;
}

/** Thứ tự chuyên mục: số nguyên không âm; trống = 0. null = không hợp lệ. */
export function parseOrder(raw: string): number | null {
  const t = raw.trim();
  if (t === "") return 0;
  return /^\d{1,6}$/.test(t) ? Number(t) : null;
}

/** BE lưu lý do trả về / gỡ bài dưới dạng khoá; đổi sang nhãn người đọc. Khoá lạ → để nguyên chữ BE gửi. */
export function reasonLabelOf(key: string): string {
  const all: ReadonlyArray<{ value: string; label: string }> = [...RETURN_REASONS, ...UNPUBLISH_REASONS];
  return all.find((r) => r.value === key)?.label ?? key;
}

/** Mở bài theo `?id=` hoặc `?version=`: chỉ nhận số nguyên dương thuần. */
export function positiveIntParam(raw: string | null): number | null {
  return raw && /^\d{1,9}$/.test(raw) && Number(raw) > 0 ? Number(raw) : null;
}
