import {
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ContentCategory,
  ContentCounts,
  ContentEntryDetail,
  ContentEntryListItem,
  ContentImage,
  ContentWarning,
  EntryCreatePayload,
  EntryDiscardPayload,
  EntryPublishPayload,
  EntryPublishResponse,
  EntryUnpublishPayload,
  EntryUpdatePayload,
  GoliveStatusResponse,
} from "./types";
import { ApiError } from "@/shared/lib/http";

let MOCK_CATEGORIES: ContentCategory[] = [
  {
    id: 1,
    name: "Công thức nấu",
    slug: "cong-thuc-nau",
    description: "Các món ngon từ hải sản tươi",
    order: 1,
    is_active: true,
    published_count: 4,
  },
  {
    id: 2,
    name: "Mẹo nhà bếp",
    slug: "meo-nha-bep",
    description: "Bảo quản, rã đông cá đúng cách",
    order: 2,
    is_active: true,
    published_count: 2,
  },
  {
    id: 3,
    name: "Tin mùa vụ",
    slug: "tin-mua-vu",
    description: "Thông tin hải sản theo mùa cảng cá",
    order: 3,
    is_active: false,
    published_count: 0,
  },
];

let MOCK_ENTRIES: ContentEntryListItem[] = [
  {
    id: 42,
    kind: "post",
    status: "draft",
    title: "Cách rã đông cá thu",
    slug: "cach-ra-dong-ca-thu",
    category: 1,
    has_unpublished_changes: false,
    updated_at: new Date().toISOString(),
    source: "human",
    page_role: null,
  },
];

let MOCK_ENTRY_DETAILS = new Map<number, ContentEntryDetail>([
  [
    42,
    {
      id: 42,
      kind: "post",
      status: "draft",
      title: "Cách rã đông cá thu",
      slug: "cach-ra-dong-ca-thu",
      slug_locked: false,
      category: 1,
      excerpt: "Mẹo rã đông cá thu giữ nguyên vị ngọt tươi",
      seo_title: "",
      seo_description: "",
      cover_image: null,
      body: {
        type: "doc",
        blocks: [
          { type: "heading", level: 2, text: "Hướng dẫn rã đông" },
          {
            type: "paragraph",
            children: [{ text: "Để cá trong ngăn mát tủ lạnh từ 4-6 tiếng trước khi chế biến." }],
          },
        ],
      },
      images: [],
      has_unpublished_changes: false,
      published_version: null,
      first_published_at: null,
      last_published_at: null,
      restored_from: null,
      return_reason: "",
      page_role: null,
      required_for_golive: false,
      show_in_footer: false,
      footer_order: 0,
      public_url: null,
      source: "human",
      row_version: 1,
      updated_at: new Date().toISOString(),
    },
  ],
]);

export function mockListCategories(): ContentCategory[] {
  return [...MOCK_CATEGORIES].sort((a, b) => a.order - b.order || a.id - b.id);
}

export function mockCreateCategory(payload: CategoryCreatePayload): ContentCategory {
  const name = payload.name.trim();
  const slug = name
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[đĐ]/g, "d")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

  const id = Math.max(0, ...MOCK_CATEGORIES.map((c) => c.id)) + 1;
  const newCat: ContentCategory = {
    id,
    name,
    slug: slug || `chuyen-muc-${id}`,
    description: payload.description || "",
    order: payload.order ?? 0,
    is_active: true,
    published_count: 0,
  };
  MOCK_CATEGORIES.push(newCat);
  return newCat;
}

export function mockUpdateCategory(
  id: number,
  payload: CategoryUpdatePayload
): ContentCategory {
  const cat = MOCK_CATEGORIES.find((c) => c.id === id);
  if (!cat) throw new ApiError("Category not found", 404, "NOT_FOUND");

  if (payload.name !== undefined) cat.name = payload.name.trim();
  if (payload.description !== undefined) cat.description = payload.description.trim();
  if (payload.order !== undefined) cat.order = payload.order;
  if (payload.is_active !== undefined) cat.is_active = payload.is_active;

  return { ...cat };
}

export function mockListEntries(params?: {
  status?: string;
  kind?: string;
  category?: number;
  page?: number;
}): { count: number; results: ContentEntryListItem[] } {
  let list = [...MOCK_ENTRIES];
  if (params?.status) {
    list = list.filter((e) => e.status === params.status);
  }
  if (params?.kind) {
    list = list.filter((e) => e.kind === params.kind);
  }
  if (params?.category) {
    list = list.filter((e) => e.category === params.category);
  }
  return {
    count: list.length,
    results: list,
  };
}

export function mockGetEntryCounts(): ContentCounts {
  return {
    draft: MOCK_ENTRIES.filter((e) => e.status === "draft").length,
    pending_review: MOCK_ENTRIES.filter((e) => e.status === "pending_review").length,
    published: MOCK_ENTRIES.filter((e) => e.status === "published").length,
    unpublished: MOCK_ENTRIES.filter((e) => e.status === "unpublished").length,
  };
}

export function mockGetEntry(id: number): ContentEntryDetail {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");
  return { ...entry, body: { ...entry.body, blocks: [...entry.body.blocks] } };
}

export function mockCreateEntry(payload: EntryCreatePayload): ContentEntryDetail {
  const id = Math.max(0, ...Array.from(MOCK_ENTRY_DETAILS.keys())) + 1;
  const rawTitle = (payload.title || "").trim();
  let slug = (payload.slug || "").trim();
  if (!slug && rawTitle) {
    slug = rawTitle
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[đĐ]/g, "d")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
  }
  if (!slug) slug = `bai-${id}`;

  // Kiểm tra trùng slug
  for (const item of Array.from(MOCK_ENTRY_DETAILS.values())) {
    if (item.slug === slug) {
      throw new ApiError("Đường dẫn bài viết đã tồn tại (BR-ND-04).", 400, "BR-ND-04");
    }
  }

  const detail: ContentEntryDetail = {
    id,
    kind: payload.kind || "post",
    status: "draft",
    title: rawTitle,
    slug,
    slug_locked: false,
    category: payload.category ?? null,
    excerpt: payload.excerpt || "",
    seo_title: payload.seo_title || "",
    seo_description: payload.seo_description || "",
    cover_image: payload.cover_image ?? null,
    body: payload.body || { type: "doc", blocks: [] },
    images: [],
    has_unpublished_changes: false,
    published_version: null,
    first_published_at: null,
    last_published_at: null,
    restored_from: null,
    return_reason: "",
    page_role: null,
    required_for_golive: false,
    show_in_footer: false,
    footer_order: 0,
    public_url: null,
    source: "human",
    row_version: 1,
    updated_at: new Date().toISOString(),
  };

  MOCK_ENTRY_DETAILS.set(id, detail);
  MOCK_ENTRIES.unshift({
    id,
    kind: detail.kind,
    status: detail.status,
    title: detail.title,
    slug: detail.slug,
    category: detail.category,
    has_unpublished_changes: false,
    updated_at: detail.updated_at,
    source: "human",
    page_role: null,
  });

  return detail;
}

export function mockUpdateEntry(id: number, payload: EntryUpdatePayload): ContentEntryDetail {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (payload.row_version !== undefined && payload.row_version !== entry.row_version) {
    throw new ApiError("Bài viết đã được chỉnh sửa bởi người khác (STALE_VERSION).", 409, "STALE_VERSION");
  }

  if (payload.title !== undefined) entry.title = payload.title.trim();
  if (payload.slug !== undefined) {
    const newSlug = payload.slug.trim();
    if (entry.slug_locked && newSlug !== entry.slug) {
      throw new ApiError("Không thể đổi đường dẫn bài đã đăng (BR-ND-04).", 400, "BR-ND-04");
    }
    entry.slug = newSlug;
  }
  if (payload.category !== undefined) entry.category = payload.category;
  if (payload.excerpt !== undefined) entry.excerpt = payload.excerpt;
  if (payload.seo_title !== undefined) entry.seo_title = payload.seo_title;
  if (payload.seo_description !== undefined) entry.seo_description = payload.seo_description;
  if (payload.cover_image !== undefined) entry.cover_image = payload.cover_image;
  if (payload.body !== undefined) entry.body = payload.body;
  if (payload.page_role !== undefined) entry.page_role = payload.page_role;
  if (payload.show_in_footer !== undefined) entry.show_in_footer = payload.show_in_footer;
  if (payload.footer_order !== undefined) entry.footer_order = payload.footer_order;

  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  // Cập nhật list item
  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.title = entry.title;
    listItem.slug = entry.slug;
    listItem.category = entry.category;
    listItem.updated_at = entry.updated_at;
  }

  if (entry.published_version) {
    entry.has_unpublished_changes = true;
    if (listItem) {
      listItem.has_unpublished_changes = true;
    }
  }

  return { ...entry };
}

export function mockDeleteEntry(id: number): void {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");
  if (entry.published_version !== null || entry.first_published_at !== null) {
    throw new ApiError("Không thể xoá bài viết đã từng đăng (BR-ND-02).", 400, "BR-ND-02");
  }
  MOCK_ENTRY_DETAILS.delete(id);
  MOCK_ENTRIES = MOCK_ENTRIES.filter((e) => e.id !== id);
}

export function mockUploadEntryImage(entryId: number, file: File, alt?: string): ContentImage {
  const entry = MOCK_ENTRY_DETAILS.get(entryId);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.images.length >= 20) {
    throw new ApiError("Bài viết đã đạt giới hạn 20 ảnh (BR-ND-07).", 400, "BR-ND-07");
  }

  const imgId = Math.floor(Math.random() * 9000) + 1000;
  const image: ContentImage = {
    id: imgId,
    alt: alt || entry.title || "Ảnh bài viết",
    width: 1600,
    height: 1200,
    urls: {
      sm: `https://storage.googleapis.com/test-bucket/content/${entryId}/${imgId}/sm.webp`,
      md: `https://storage.googleapis.com/test-bucket/content/${entryId}/${imgId}/md.webp`,
      lg: `https://storage.googleapis.com/test-bucket/content/${entryId}/${imgId}/lg.webp`,
    },
  };
  entry.images.push(image);
  return image;
}

export function mockUpdateImageAlt(imageId: number, alt: string): ContentImage {
  for (const entry of Array.from(MOCK_ENTRY_DETAILS.values())) {
    const img = entry.images.find((i) => i.id === imageId);
    if (img) {
      img.alt = alt.trim().slice(0, 200);
      return { ...img };
    }
  }
  return {
    id: imageId,
    alt: alt.trim().slice(0, 200),
    width: 1600,
    height: 1200,
    urls: { sm: "", md: "", lg: "" },
  };
}

export function mockPublishEntry(
  id: number,
  payload: EntryPublishPayload
): EntryPublishResponse {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.row_version !== payload.row_version) {
    throw new ApiError(
      "Dữ liệu đã bị thay đổi bởi người khác (STALE_VERSION).",
      409,
      "STALE_VERSION"
    );
  }

  // BR-ND-03: Kiểm tra các trường bắt buộc
  const missing: string[] = [];
  if (!entry.title?.trim()) missing.push("title");
  if (!entry.body?.blocks?.length) missing.push("body");
  if (entry.kind === "post") {
    if (!entry.category) missing.push("category");
    if (!entry.excerpt?.trim()) missing.push("excerpt");
    if (!entry.cover_image) missing.push("cover_image");
  }
  if (missing.length > 0) {
    const err = new ApiError("Bài viết chưa đủ điều kiện xuất bản (BR-ND-03).", 400, "BR-ND-03");
    (err as any).missing = missing;
    throw err;
  }

  if (payload.checklist_confirmed !== true) {
    throw new ApiError(
      "Chưa xác nhận danh sách tự kiểm trước khi đăng (BR-ND-13).",
      400,
      "BR-ND-13"
    );
  }

  // Quét cảnh báo đơn giản cho mock: nếu bài chứa SĐT hoặc từ giá vốn
  const bodyText = JSON.stringify(entry.body);
  const warnings: ContentWarning[] = [];
  if (bodyText.includes("0912") || bodyText.includes("giá mua") || bodyText.includes("giá vốn")) {
    if (bodyText.includes("0912")) {
      warnings.push({
        type: "phone_like",
        field: "body",
        snippet: "…vui lòng gọi 09xx xxx 678 để…",
      });
    }
    if (bodyText.includes("giá mua") || bodyText.includes("giá vốn")) {
      warnings.push({
        type: "cost_keyword",
        field: "body",
        snippet: "…giá mua tại cảng…",
      });
    }
  }

  if (warnings.length > 0 && payload.acknowledge_warnings !== true) {
    const err = new ApiError(
      "Phát hiện cảnh báo trước khi xuất bản (CONTENT_WARNINGS).",
      409,
      "CONTENT_WARNINGS"
    );
    (err as any).warnings = warnings;
    throw err;
  }

  const now = new Date().toISOString();
  const nextVer = (entry.published_version || 0) + 1;
  entry.status = "published";
  entry.published_version = nextVer;
  if (!entry.first_published_at) entry.first_published_at = now;
  entry.last_published_at = now;
  entry.slug_locked = true;
  entry.has_unpublished_changes = false;
  entry.row_version += 1;
  entry.updated_at = now;

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.status = "published";
    listItem.has_unpublished_changes = false;
    listItem.updated_at = now;
  }

  const publicUrl = entry.kind === "post" ? `/bai-viet?slug=${entry.slug}` : `/trang?slug=${entry.slug}`;
  entry.public_url = publicUrl;

  (entry as any)._published_snapshot = {
    title: entry.title,
    slug: entry.slug,
    category: entry.category,
    excerpt: entry.excerpt,
    seo_title: entry.seo_title,
    seo_description: entry.seo_description,
    cover_image: entry.cover_image,
    body: JSON.parse(JSON.stringify(entry.body)),
  };

  return {
    id: entry.id,
    slug: entry.slug,
    status: entry.status,
    version: nextVer,
    public_url: publicUrl,
    row_version: entry.row_version,
  };
}

export function mockUnpublishEntry(
  id: number,
  payload: EntryUnpublishPayload
): ContentEntryDetail {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.row_version !== payload.row_version) {
    throw new ApiError(
      "Dữ liệu đã bị thay đổi bởi người khác (STALE_VERSION).",
      409,
      "STALE_VERSION"
    );
  }

  if (entry.status !== "published") {
    throw new ApiError(
      "Chỉ có thể gỡ bài viết đang ở trạng thái đã đăng (BR-ND-01).",
      400,
      "BR-ND-01"
    );
  }

  if (entry.page_role) {
    throw new ApiError(
      "Trang giữ vai trò go-live không được gỡ trực tiếp (BR-ND-16).",
      400,
      "BR-ND-16"
    );
  }

  const validReasons = ["wrong_price", "complaint", "out_of_season", "wrong_content", "other"];
  if (!payload.reason || !validReasons.includes(payload.reason)) {
    throw new ApiError("Lý do gỡ bài không hợp lệ (BR-ND-15).", 400, "BR-ND-15");
  }

  entry.status = "unpublished";
  entry.return_reason = payload.reason;
  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.status = "unpublished";
    listItem.updated_at = entry.updated_at;
  }

  return { ...entry };
}

export function mockDiscardChanges(
  id: number,
  payload: EntryDiscardPayload
): ContentEntryDetail {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.row_version !== payload.row_version) {
    throw new ApiError(
      "Dữ liệu đã bị thay đổi bởi người khác (STALE_VERSION).",
      409,
      "STALE_VERSION"
    );
  }

  if (!entry.published_version) {
    throw new ApiError(
      "Bài viết chưa từng xuất bản, không có phiên bản để huỷ thay đổi (BR-ND-01).",
      400,
      "BR-ND-01"
    );
  }

  if ((entry as any)._published_snapshot) {
    const snap = (entry as any)._published_snapshot;
    entry.title = snap.title;
    entry.slug = snap.slug;
    entry.category = snap.category;
    entry.excerpt = snap.excerpt;
    entry.seo_title = snap.seo_title;
    entry.seo_description = snap.seo_description;
    entry.cover_image = snap.cover_image;
    entry.body = JSON.parse(JSON.stringify(snap.body));
  }

  entry.has_unpublished_changes = false;
  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.title = entry.title;
    listItem.slug = entry.slug;
    listItem.category = entry.category;
    listItem.has_unpublished_changes = false;
    listItem.updated_at = entry.updated_at;
  }

  return { ...entry };
}

export function mockGetGoliveStatus(): GoliveStatusResponse {
  const publishedRoles = new Set(
    MOCK_ENTRIES.filter((e) => e.status === "published" && e.page_role).map((e) => e.page_role as string)
  );
  const requiredRoles = ["privacy", "terms", "refund", "seller_info"];
  const missing = requiredRoles.filter((r) => !publishedRoles.has(r));
  return { missing_roles: missing };
}

export function mockFetchShopCatalog() {
  return [
    { item_code: "CA-THU-1KG", name: "Cá thu Phan Thiết 1kg", price: 250000, sellable_qty: 10 },
    { item_code: "CA-BOP-1KG", name: "Cá bớp cắt khoanh 1kg", price: 280000, sellable_qty: 5 },
    { item_code: "TOM-SU-1KG", name: "Tôm sú Cà Mau 1kg", price: 320000, sellable_qty: 8 },
    { item_code: "MUC-ONG-1KG", name: "Mực ống Phan Thiết 1kg", price: 220000, sellable_qty: 12 },
  ];
}
