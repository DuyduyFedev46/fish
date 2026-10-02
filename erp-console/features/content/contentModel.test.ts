// ED-35, ED-36: logic thuần của module Nội dung + hành vi lỗi của mock (đúng hình dạng lỗi thật của BE).
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import {
  CONTENT_PERM,
  applyLocalDraft,
  blockedDetailsOf,
  canDeleteEntry,
  coverAltMissing,
  deleteBlockedReason,
  discardBlockedReason,
  emptyForm,
  entryNote,
  errorText,
  filterEntries,
  hasPerm,
  historyBlockedReason,
  isCategoryNameTaken,
  localDraftOf,
  missingOf,
  missingSentence,
  parseOrder,
  pathViewOf,
  positiveIntParam,
  primaryActionOf,
  reasonLabelOf,
  suggestionOf,
  unpublishBlockedReason,
  warningLine,
  warningsOf,
  type EntryFacts,
} from "./contentModel";
import { mockCreateCategory, mockCreateEntry, mockPublishEntry, mockUpdateCategory, mockUpdateEntry } from "./mock";
import type { ContentEntryListItem } from "./types";

const facts = (over: Partial<EntryFacts> = {}): EntryFacts => ({
  status: "draft",
  pageRole: null,
  publishedVersion: null,
  firstPublishedAt: null,
  hasUnpublishedChanges: false,
  saved: true,
  ...over,
});

describe("quyền thật của app content", () => {
  it("chỉ dựa vào permissions, không dựa tên nhóm", () => {
    expect(hasPerm({ permissions: [CONTENT_PERM.publish] }, CONTENT_PERM.publish)).toBe(true);
    expect(hasPerm({ permissions: ["content.view_entry"] }, CONTENT_PERM.publish)).toBe(false);
    expect(hasPerm(null, CONTENT_PERM.view)).toBe(false);
  });
});

describe("đọc lỗi BE từ details", () => {
  it("CONTENT_WARNINGS: lấy details.warnings, bỏ loại lạ", () => {
    const err = new ApiError("x", 409, "CONTENT_WARNINGS", { warnings: [{ type: "phone_like", field: "body" }, { type: "lạ" }, null, { type: "item_unavailable", item_code: "CA-1" }] });
    expect(warningsOf(err).map((w) => w.type)).toEqual(["phone_like", "item_unavailable"]);
    expect(warningsOf(new ApiError("x", 409, "STALE_VERSION"))).toEqual([]);
    expect(warningsOf(new Error("x"))).toEqual([]);
  });

  it("BR-ND-03: danh sách trường thiếu và câu tiếng thường", () => {
    const err = new ApiError("x", 400, "BR-ND-03", { missing: ["category", "cover_image_alt", "khác"] });
    expect(missingOf(err)).toEqual(["category", "cover_image_alt", "khác"]);
    const text = missingSentence(missingOf(err), "publish");
    expect(text).toContain("Chuyên mục");
    expect(text).toContain("Mô tả ảnh bìa");
    expect(text).not.toMatch(/BR-|cover_image/);
    expect(missingSentence(["title"], "submit")).toMatch(/gửi duyệt/);
  });

  it("BR-ND-04: gợi ý đường dẫn chỉ nhận dạng an toàn", () => {
    expect(suggestionOf(new ApiError("x", 400, "BR-ND-04", { suggestion: "ca-thu-2" }))).toBe("ca-thu-2");
    expect(suggestionOf(new ApiError("x", 400, "BR-ND-04", { suggestion: "<script>" }))).toBeNull();
    expect(suggestionOf(new ApiError("x", 400, "OTHER", { suggestion: "a" }))).toBeNull();
    expect(isCategoryNameTaken(new ApiError("x", 400, "BR-ND-04"))).toBe(true);
  });

  it("BR-ND-02: bài chặn việc ngừng chuyên mục", () => {
    const err = new ApiError("x", 400, "BR-ND-02", { entries: [{ id: 3, title: "A" }, { id: "x" }], total: 7 });
    expect(blockedDetailsOf(err)).toEqual({ entries: [{ id: 3, title: "A" }], total: 7 });
    expect(blockedDetailsOf(new ApiError("x", 400, "BR-ND-02"))).toEqual({ entries: [], total: 0 });
    expect(blockedDetailsOf(new ApiError("x", 400, "BR-ND-04"))).toBeNull();
  });

  it("errorText bỏ mã luật khỏi câu hiển thị", () => {
    expect(errorText(new ApiError("Bài chưa đủ điều kiện (BR-ND-03).", 400, "BR-ND-03"), "dự phòng")).not.toMatch(/BR-ND/);
    expect(errorText(new Error("lạ"), "dự phòng")).toBe("dự phòng");
  });

  it("nhãn cảnh báo và lý do", () => {
    expect(warningLine({ type: "phone_like" })).toMatch(/điện thoại/);
    expect(warningLine({ type: "item_unavailable", item_code: "CA-1" })).toContain("CA-1");
    expect(reasonLabelOf("wrong_price")).toBe("Giá chưa đúng");
    expect(reasonLabelOf("không_biết")).toBe("không_biết");
  });
});

describe("hành động theo quyền và trạng thái", () => {
  it("người đăng: nháp/chờ duyệt -> Đăng; đã đăng chỉ có nút khi có thay đổi", () => {
    expect(primaryActionOf("draft", false, true, true)).toBe("publish");
    expect(primaryActionOf("pending_review", false, true, true)).toBe("publish");
    expect(primaryActionOf("published", false, true, true)).toBeNull();
    expect(primaryActionOf("published", true, true, true)).toBe("publish_changes");
    expect(primaryActionOf("unpublished", false, true, true)).toBe("publish");
  });
  it("người chỉ soạn: chỉ Gửi duyệt khi đang nháp", () => {
    expect(primaryActionOf("draft", false, false, true)).toBe("submit");
    expect(primaryActionOf("pending_review", false, false, true)).toBeNull();
    expect(primaryActionOf("draft", false, false, false)).toBeNull();
  });
  it("chặn xoá, gỡ, huỷ thay đổi, lịch sử đúng lý do", () => {
    expect(canDeleteEntry(facts())).toBe(true);
    expect(deleteBlockedReason(facts({ firstPublishedAt: "2026-01-01T00:00:00Z" }))).toMatch(/đã từng đăng/);
    expect(deleteBlockedReason(facts({ saved: false }))).toMatch(/chưa lưu/);
    expect(unpublishBlockedReason(facts())).toMatch(/chưa đăng/);
    expect(unpublishBlockedReason(facts({ status: "published", pageRole: "privacy" }))).toMatch(/bắt buộc/);
    expect(unpublishBlockedReason(facts({ status: "published" }))).toBeUndefined();
    expect(discardBlockedReason(facts({ status: "published" }))).toMatch(/Không có thay đổi/);
    expect(discardBlockedReason(facts({ status: "published", hasUnpublishedChanges: true }))).toBeUndefined();
    expect(historyBlockedReason(facts())).toMatch(/chưa đăng lần nào/);
    expect(historyBlockedReason(facts({ status: "unpublished", firstPublishedAt: "2026-01-01T00:00:00Z" }))).toBeUndefined();
  });
  it("đường đi trạng thái", () => {
    expect(pathViewOf("draft", true, null, false).next).toBe("Đăng bài");
    expect(pathViewOf("draft", false, null, true).next).toBe("Gửi duyệt");
    expect(pathViewOf("unpublished", true, "2026-01-01T00:00:00Z", true).badEnd).toEqual({ label: "Đã gỡ", after: "published" });
    expect(pathViewOf("published", true, "2026-01-01T00:00:00Z", true).done).toContain("Đăng bài");
  });
});

describe("danh sách", () => {
  const row = (over: Partial<ContentEntryListItem>): ContentEntryListItem => ({
    id: 1,
    kind: "post",
    status: "draft",
    title: "Cách ra đồng cá thu",
    slug: "ca-thu",
    category: null,
    has_unpublished_changes: false,
    updated_at: "2026-01-01T00:00:00Z",
    source: "human",
    page_role: null,
    ...over,
  });
  it("lọc tại chỗ theo tiêu đề hoặc đường dẫn, không phân biệt hoa thường", () => {
    const rows = [row({ id: 1 }), row({ id: 2, title: "Tôm sú", slug: "tom-su" })];
    expect(filterEntries(rows, "  CÁ THU ").map((r) => r.id)).toEqual([1]);
    expect(filterEntries(rows, "tom-su").map((r) => r.id)).toEqual([2]);
    expect(filterEntries(rows, "")).toHaveLength(2);
  });
  it("tiêu đề lạ (giống mã HTML) vẫn là chữ thường để React tự thoát", () => {
    expect(filterEntries([row({ title: "<img src=x onerror=alert(1)>" })], "onerror")).toHaveLength(1);
  });
  it("ghi chú suy từ dữ liệu có sẵn", () => {
    expect(entryNote(row({ has_unpublished_changes: true, status: "published" }))).toMatch(/thay đổi chưa đăng/);
    expect(entryNote(row({ source: "ai" }))).toMatch(/AI/);
    expect(entryNote(row({ page_role: "privacy" }))).toMatch(/bắt buộc/);
    expect(entryNote(row({}))).toBe("");
  });
  it("tham số số nguyên dương", () => {
    expect(positiveIntParam("12")).toBe(12);
    expect(positiveIntParam("0")).toBeNull();
    expect(positiveIntParam("-1")).toBeNull();
    expect(positiveIntParam("1e3")).toBeNull();
    expect(positiveIntParam(null)).toBeNull();
    expect(parseOrder("")).toBe(0);
    expect(parseOrder("5")).toBe(5);
    expect(parseOrder("-1")).toBeNull();
    expect(parseOrder("1.5")).toBeNull();
  });
});

describe("bản nháp trên máy và ảnh bìa", () => {
  it("áp bản nháp lên form, giữ trường khác", () => {
    const base = { ...emptyForm("post"), title: "Máy chủ", excerpt: "Tóm tắt" };
    const next = applyLocalDraft(base, { title: "Đang gõ", category: 2 });
    expect(next.title).toBe("Đang gõ");
    expect(next.excerpt).toBe("Tóm tắt");
    expect(next.category).toBe(2);
    expect(Object.keys(localDraftOf(base)).sort()).toEqual(["body", "category", "cover_image", "excerpt", "seo_description", "seo_title", "slug", "title"]);
  });
  it("ảnh bìa thiếu mô tả", () => {
    const img = { id: 5, alt: "  ", width: 1, height: 1, urls: { sm: "", md: "", lg: "" } } as never;
    expect(coverAltMissing([img], 5)).toBe(true);
    expect(coverAltMissing([img], null)).toBe(false);
    expect(coverAltMissing([], 5)).toBe(false);
  });
});

describe("mock giống BE thật", () => {
  it("tên chuyên mục trùng -> BR-ND-04 (không phân biệt hoa thường)", () => {
    const name = `Mẹo vặt thử ${Date.now()}`;
    mockCreateCategory({ name });
    try {
      mockCreateCategory({ name: `  ${name.toUpperCase()} ` });
      expect.unreachable();
    } catch (err) {
      expect(isCategoryNameTaken(err)).toBe(true);
    }
  });

  it("ngừng chuyên mục còn bài đang đăng -> BR-ND-02 kèm details.entries và total", () => {
    // Chuyên mục 1 của dữ liệu mẫu có bài đã đăng.
    try {
      mockUpdateCategory(1, { is_active: false });
      expect.unreachable();
    } catch (err) {
      const d = blockedDetailsOf(err);
      expect(d).not.toBeNull();
      expect(d!.total).toBeGreaterThan(0);
      expect(d!.entries.length).toBeLessThanOrEqual(5);
    }
  });

  it("đăng bài thiếu trường -> BR-ND-03 kèm details.missing", () => {
    const e = mockCreateEntry({ kind: "post", title: "Bài thử thiếu", body: { type: "doc", blocks: [{ type: "paragraph", children: [{ text: "x" }] }] } });
    try {
      mockPublishEntry(e.id, { row_version: e.row_version, checklist_confirmed: true });
      expect.unreachable();
    } catch (err) {
      const missing = missingOf(err);
      expect(missing).toContain("category");
      expect(missing).toContain("cover_image");
      expect(missing).toContain("description");
    }
  });

  it("đường dẫn trùng -> BR-ND-04 kèm gợi ý", () => {
    const a = mockCreateEntry({ kind: "post", title: "Bài trùng đường dẫn", slug: "bai-trung-duong-dan-1" });
    const b = mockCreateEntry({ kind: "post", title: "Bài khác", slug: "bai-khac-1" });
    try {
      mockUpdateEntry(b.id, { row_version: b.row_version, slug: a.slug });
      expect.unreachable();
    } catch (err) {
      expect(isCategoryNameTaken(err)).toBe(true);
    }
  });

  it("row_version cũ -> STALE_VERSION", () => {
    const e = mockCreateEntry({ kind: "post", title: "Bài xung đột" });
    const first = e.row_version; // mock trả đúng đối tượng đang giữ, nên lấy số trước khi sửa
    mockUpdateEntry(e.id, { row_version: first, title: "Sửa lần 1" });
    try {
      mockUpdateEntry(e.id, { row_version: first, title: "Sửa lần 2" });
      expect.unreachable();
    } catch (err) {
      expect((err as ApiError).code).toBe("STALE_VERSION");
    }
  });
});
