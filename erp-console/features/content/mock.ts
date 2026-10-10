import type { ShopCatalogResponse } from "./shopCatalog";
import {
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ContentCategory,
  ContentCounts,
  ContentEntryDetail,
  ContentEntryListItem,
  ContentImage,
  BodyDoc,
  ContentWarning,
  EntryCreatePayload,
  EntryDiscardPayload,
  EntryPublishPayload,
  EntryPublishResponse,
  EntryUnpublishPayload,
  EntryUnpublishResponse,
  EntryUpdatePayload,
  GoliveStatusResponse,
  ContentEntryVersionDetail,
  ContentEntryVersionListItem,
  EntryRestorePayload,
  EntryReturnPayload,
  EntryReturnResponse,
  EntrySubmitPayload,
  EntrySubmitResponse,
} from "./types";
import { ApiError } from "@/shared/lib/http";

// SR-19: bài chính sách bảo mật (id 1) có 2 phiên bản đã đăng. Đơn mock (features/orders/mock.ts) ghi khách đồng ý
// phiên bản 1; chính sách đã lên phiên bản 2. Nội dung 2 bản KHÁC NHAU để e2e nhận ra mở đúng/sai phiên bản.
// Toàn văn là dữ liệu giả, không phải chính sách thật.
const POLICY_V1_AT = "2026-08-01T03:00:00.000Z";
const POLICY_V2_AT = "2026-09-20T03:00:00.000Z";

const POLICY_V1_BODY: BodyDoc = {
  type: "doc",
  blocks: [
    { type: "heading", level: 2, text: "Thông tin chúng tôi thu thập (bản 1)" },
    { type: "paragraph", children: [{ text: "MẪU-V1: Cá Về chỉ thu họ tên, số điện thoại và địa chỉ để giao hàng." }] },
  ],
};

const POLICY_V2_BODY: BodyDoc = {
  type: "doc",
  blocks: [
    { type: "heading", level: 2, text: "Thông tin chúng tôi thu thập (bản 2)" },
    { type: "paragraph", children: [{ text: "MẪU-V2: Bản mới bổ sung thời hạn lưu trữ và quyền yêu cầu ẩn danh hoá dữ liệu." }] },
  ],
};

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
    id: 1,
    kind: "page",
    status: "published",
    title: "Chính sách bảo mật",
    slug: "chinh-sach-quyen-rieng-tu",
    category: null,
    has_unpublished_changes: false,
    updated_at: POLICY_V2_AT,
    source: "human",
    page_role: "privacy",
  },
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
    1,
    {
      id: 1,
      kind: "page",
      status: "published",
      title: "Chính sách bảo mật",
      slug: "chinh-sach-quyen-rieng-tu",
      slug_locked: true,
      category: null,
      excerpt: "",
      seo_title: "",
      seo_description: "",
      cover_image: null,
      body: JSON.parse(JSON.stringify(POLICY_V2_BODY)),
      images: [],
      has_unpublished_changes: false,
      published_version: 2,
      first_published_at: POLICY_V1_AT,
      last_published_at: POLICY_V2_AT,
      restored_from: null,
      return_reason: "",
      page_role: "privacy",
      required_for_golive: true,
      show_in_footer: true,
      footer_order: 1,
      public_url: "/trang?slug=chinh-sach-quyen-rieng-tu",
      source: "human",
      row_version: 3,
      updated_at: POLICY_V2_AT,
    },
  ],
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

function policyVersion(version: number, at: string, body: BodyDoc): ContentEntryVersionDetail {
  return {
    version,
    published_at: at,
    published_by_name: "Chủ vựa (mẫu)",
    kind: "page",
    title: "Chính sách bảo mật",
    slug: "chinh-sach-quyen-rieng-tu",
    excerpt: "",
    seo_title: "",
    seo_description: "",
    description: "",
    category: null,
    cover_image: null,
    body: JSON.parse(JSON.stringify(body)),
    restored_from: null,
  };
}

// Mới nhất trước, giống API thật.
let MOCK_VERSIONS_DB = new Map<number, ContentEntryVersionDetail[]>([
  [1, [policyVersion(2, POLICY_V2_AT, POLICY_V2_BODY), policyVersion(1, POLICY_V1_AT, POLICY_V1_BODY)]],
]);


// ---- Dữ liệu mẫu cho các màn Nội dung (ED-35, ED-36): đủ 4 trạng thái, bài AI, trang bắt buộc, bài có thay đổi chưa đăng.
// Toàn chữ giả, không có dữ liệu khách. Ảnh mẫu là hình SVG nhúng sẵn (không gọi mạng).
MOCK_CATEGORIES.push({
  id: 4,
  name: "Câu chuyện vựa",
  slug: "cau-chuyen-vua",
  description: "Chuyện nghề, chuyện cảng cá",
  order: 4,
  is_active: true,
  published_count: 0,
});

function sampleImage(id: number, alt: string): ContentImage {
  const svg = encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="640" height="480" fill="#d7e6f2"/><circle cx="320" cy="240" r="80" fill="#8fb4d1"/></svg>'
  );
  const url = `data:image/svg+xml;utf8,${svg}`;
  return { id, alt, width: 640, height: 480, urls: { sm: url, md: url, lg: url } };
}

function paragraphs(...texts: string[]): BodyDoc {
  return { type: "doc", blocks: texts.map((t) => ({ type: "paragraph" as const, children: [{ text: t }] })) };
}

type SeedInput = {
  id: number;
  kind: "post" | "page";
  status: ContentEntryDetail["status"];
  title: string;
  slug: string;
  category: number | null;
  excerpt?: string;
  body?: BodyDoc;
  source?: "human" | "ai";
  pageRole?: ContentEntryDetail["page_role"];
  coverAlt?: string | null;
  published?: boolean;
  hasChanges?: boolean;
  returnReason?: string;
  minutesAgo: number;
};

function addSeed(x: SeedInput): void {
  const at = new Date(Date.now() - x.minutesAgo * 60000).toISOString();
  const images = x.coverAlt !== undefined && x.coverAlt !== null ? [sampleImage(8000 + x.id, x.coverAlt)] : [];
  const published = !!x.published;
  const detail: ContentEntryDetail = {
    id: x.id,
    kind: x.kind,
    status: x.status,
    title: x.title,
    slug: x.slug,
    slug_locked: published,
    category: x.category,
    excerpt: x.excerpt ?? "",
    seo_title: "",
    seo_description: "",
    cover_image: images.length ? images[0].id : null,
    body: x.body ?? paragraphs("Nội dung mẫu của bài."),
    images,
    has_unpublished_changes: !!x.hasChanges,
    published_version: published ? 1 : null,
    first_published_at: published ? at : null,
    last_published_at: published ? at : null,
    restored_from: null,
    return_reason: x.returnReason ?? "",
    page_role: x.pageRole ?? null,
    required_for_golive: !!x.pageRole,
    show_in_footer: x.kind === "page",
    footer_order: x.kind === "page" ? x.id : 0,
    public_url: published ? (x.kind === "post" ? `/bai-viet?slug=${x.slug}` : `/trang?slug=${x.slug}`) : null,
    source: x.source ?? "human",
    row_version: published ? 2 : 1,
    updated_at: at,
  };
  if (published) {
    (detail as unknown as { _published_snapshot: unknown })._published_snapshot = {
      title: detail.title,
      slug: detail.slug,
      category: detail.category,
      excerpt: detail.excerpt,
      seo_title: "",
      seo_description: "",
      cover_image: detail.cover_image,
      body: JSON.parse(JSON.stringify(detail.body)),
    };
    MOCK_VERSIONS_DB.set(x.id, [
      {
        version: 1,
        published_at: at,
        published_by_name: "Chủ vựa (mẫu)",
        kind: x.kind,
        title: x.title,
        slug: x.slug,
        excerpt: detail.excerpt,
        seo_title: "",
        seo_description: "",
        description: detail.excerpt,
        category: x.category,
        cover_image: detail.cover_image,
        body: JSON.parse(JSON.stringify(detail.body)),
        restored_from: null,
      },
    ]);
  }
  MOCK_ENTRY_DETAILS.set(x.id, detail);
  MOCK_ENTRIES.push({
    id: x.id,
    kind: x.kind,
    status: x.status,
    title: x.title,
    slug: x.slug,
    category: x.category,
    has_unpublished_changes: !!x.hasChanges,
    updated_at: at,
    source: detail.source,
    page_role: detail.page_role,
  });
}

addSeed({ id: 43, kind: "post", status: "pending_review", title: "Cá thu một nắng chiên giòn", slug: "ca-thu-mot-nang-chien-gion", category: 1, excerpt: "Cá thu phơi một nắng, chiên giòn ăn với cơm nóng.", coverAlt: "Đĩa cá thu một nắng chiên vàng", body: paragraphs("Chọn cá thu tươi, phơi một nắng rồi chiên lửa vừa.", "Ăn kèm rau sống và nước mắm gừng."), minutesAgo: 25 });
addSeed({ id: 44, kind: "post", status: "draft", title: "Gợi ý 5 món từ cá bớp", slug: "goi-y-5-mon-tu-ca-bop", category: 1, source: "ai", body: paragraphs("Cá bớp nấu canh chua, kho tiêu, nướng, chiên và hấp."), minutesAgo: 90 });
addSeed({ id: 45, kind: "page", status: "draft", title: "Đổi trả và hoàn tiền", slug: "doi-tra-va-hoan-tien", category: null, pageRole: "refund", body: paragraphs("Nội dung mẫu: quy định đổi trả hàng tươi sống trong ngày."), minutesAgo: 180 });
addSeed({ id: 46, kind: "post", status: "published", title: "Bảo quản tôm sú trong tủ đông", slug: "bao-quan-tom-su-trong-tu-dong", category: 2, excerpt: "Cách cấp đông tôm sú giữ độ ngọt.", coverAlt: "Tôm sú xếp khay", source: "ai", published: true, hasChanges: true, minutesAgo: 300 });
addSeed({ id: 47, kind: "page", status: "published", title: "Thông tin người bán", slug: "thong-tin-nguoi-ban", category: null, pageRole: "seller_info", published: true, excerpt: "Thông tin giới thiệu vựa.", body: paragraphs("Nội dung mẫu: giới thiệu vựa cá."), minutesAgo: 600 });
addSeed({ id: 48, kind: "post", status: "published", title: "Mực lá nướng muối ớt", slug: "muc-la-nuong-muoi-ot", category: 1, excerpt: "Mực lá nướng muối ớt, chấm muối tiêu chanh.", coverAlt: "Mực lá nướng trên than", published: true, minutesAgo: 900 });
addSeed({ id: 49, kind: "post", status: "unpublished", title: "Cá ngừ đại dương mùa lặn biển", slug: "ca-ngu-dai-duong-mua-lan-bien", category: 2, excerpt: "Cá ngừ đại dương về cảng theo mùa.", coverAlt: "Cá ngừ trên bàn cân", published: true, returnReason: "out_of_season", minutesAgo: 1500 });

function publishedInCategory(id: number): ContentEntryListItem[] {
  return MOCK_ENTRIES.filter((e) => e.category === id && e.status === "published");
}

// ---- Chế độ giả lập lỗi để kiểm các trạng thái màn hình (chỉ có ở bản build mock, check-no-mock gỡ khỏi bản thật) ----
//   window.__caveMock.content("ok" | "fail" | "empty" | "forbidden")  — lưu ở localStorage, giữ qua tải lại; không chứa dữ liệu cá nhân.
//   window.__caveMock.contentBump(id)  — tăng row_version của bài như thể người khác vừa sửa (kiểm xung đột phiên bản).
type ContentMode = "ok" | "fail" | "empty" | "forbidden";
const CONTENT_MODE_KEY = "cave_erp_mock_content_mode";

function contentMode(): ContentMode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(CONTENT_MODE_KEY);
    return v === "fail" || v === "empty" || v === "forbidden" ? v : "ok";
  } catch {
    return "ok";
  }
}

function assertContentReadable(): void {
  const m = contentMode();
  if (m === "fail") throw new ApiError("Máy chủ gặp lỗi.", 500);
  if (m === "forbidden") throw new ApiError("Bạn không có quyền xem nội dung.", 403, "FORBIDDEN");
}

/** Bản sao độc lập (ảnh, thân bài) để màn đổi state không làm đổi kho mock qua tham chiếu chung. */
function snapshotOf(e: ContentEntryDetail): ContentEntryDetail {
  return { ...e, images: (e.images ?? []).map((i) => ({ ...i })), body: { ...e.body, blocks: [...e.body.blocks] } };
}

function withCount(c: ContentCategory): ContentCategory {
  return { ...c, published_count: publishedInCategory(c.id).length };
}

function assertCategoryNameFree(name: string, exceptId?: number): void {
  const lower = name.trim().toLowerCase();
  if (MOCK_CATEGORIES.some((c) => c.id !== exceptId && c.name.trim().toLowerCase() === lower)) {
    throw new ApiError(`Chuyên mục '${name.trim()}' đã tồn tại (BR-ND-04).`, 400, "BR-ND-04");
  }
}

export function mockListCategories(): ContentCategory[] {
  assertContentReadable();
  if (contentMode() === "empty") return [];
  return MOCK_CATEGORIES.map(withCount).sort((a, b) => a.order - b.order || a.id - b.id);
}

export function mockCreateCategory(payload: CategoryCreatePayload): ContentCategory {
  const name = payload.name.trim();
  if (!name) throw new ApiError("Tên chuyên mục không được để trống.", 400, "BR-ND-04");
  assertCategoryNameFree(name);
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
  return withCount(newCat);
}

export function mockUpdateCategory(
  id: number,
  payload: CategoryUpdatePayload
): ContentCategory {
  const cat = MOCK_CATEGORIES.find((c) => c.id === id);
  if (!cat) throw new ApiError("Category not found", 404, "NOT_FOUND");

  if (payload.name !== undefined) {
    if (!payload.name.trim()) throw new ApiError("Tên chuyên mục không được để trống.", 400, "BR-ND-04");
    assertCategoryNameFree(payload.name, id);
  }
  if (payload.is_active === false && cat.is_active) {
    const live = publishedInCategory(id);
    if (live.length > 0) {
      throw new ApiError(`Chuyên mục còn ${live.length} bài đang đăng, không thể ngừng dùng (BR-ND-02).`, 400, "BR-ND-02", {
        entries: live.slice(0, 5).map((e) => ({ id: e.id, title: e.title })),
        total: live.length,
      });
    }
  }

  if (payload.name !== undefined) cat.name = payload.name.trim();
  if (payload.description !== undefined) cat.description = payload.description.trim();
  if (payload.order !== undefined) cat.order = payload.order;
  if (payload.is_active !== undefined) cat.is_active = payload.is_active;

  return withCount(cat);
}

export function mockListEntries(params?: {
  status?: string;
  kind?: string;
  category?: number;
  page?: number;
}): { count: number; next: string | null; previous: string | null; results: ContentEntryListItem[] } {
  assertContentReadable();
  let list = contentMode() === "empty" ? [] : [...MOCK_ENTRIES];
  if (params?.status) {
    list = list.filter((e) => e.status === params.status);
  }
  if (params?.kind) {
    list = list.filter((e) => e.kind === params.kind);
  }
  if (params?.category) {
    list = list.filter((e) => e.category === params.category);
  }
  list.sort((x, y) => (x.updated_at < y.updated_at ? 1 : x.updated_at > y.updated_at ? -1 : y.id - x.id));
  return {
    count: list.length,
    next: null,
    previous: null,
    results: list.map((e) => ({ ...e })),
  };
}

export function mockGetEntryCounts(): ContentCounts {
  assertContentReadable();
  if (contentMode() === "empty") return { draft: 0, pending_review: 0, published: 0, unpublished: 0 };
  return {
    draft: MOCK_ENTRIES.filter((e) => e.status === "draft").length,
    pending_review: MOCK_ENTRIES.filter((e) => e.status === "pending_review").length,
    published: MOCK_ENTRIES.filter((e) => e.status === "published").length,
    unpublished: MOCK_ENTRIES.filter((e) => e.status === "unpublished").length,
  };
}

export function mockGetEntry(id: number): ContentEntryDetail {
  assertContentReadable();
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");
  return snapshotOf(entry);
}

function assertSlugFree(slug: string, exceptId?: number): void {
  const taken = Array.from(MOCK_ENTRY_DETAILS.values()).some((e) => e.id !== exceptId && e.slug === slug);
  if (!taken) return;
  let n = 2;
  while (Array.from(MOCK_ENTRY_DETAILS.values()).some((e) => e.slug === `${slug}-${n}`)) n += 1;
  throw new ApiError("Đường dẫn bài viết đã tồn tại (BR-ND-04).", 400, "BR-ND-04", { suggestion: `${slug}-${n}` });
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
  assertSlugFree(slug);

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

  return snapshotOf(detail);
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
    if (newSlug !== entry.slug) assertSlugFree(newSlug, id);
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

  return snapshotOf(entry);
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
    const cat = MOCK_CATEGORIES.find((c) => c.id === entry.category);
    if (!cat || !cat.is_active) missing.push("category");
    if (!entry.cover_image) missing.push("cover_image");
    else if (!entry.images.find((i) => i.id === entry.cover_image)?.alt.trim()) missing.push("cover_image_alt");
  }
  if (!entry.excerpt?.trim() && !entry.seo_description?.trim()) missing.push("description");
  if (missing.length > 0) {
    throw new ApiError("Bài viết chưa đủ điều kiện xuất bản (BR-ND-03).", 400, "BR-ND-03", { missing });
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
  const lowerBody = bodyText.toLowerCase();
  const warnings: ContentWarning[] = [];
  if (bodyText.includes("0912") || lowerBody.includes("giá mua") || lowerBody.includes("giá vốn")) {
    if (bodyText.includes("0912")) {
      warnings.push({
        type: "phone_like",
        field: "body",
        snippet: "…vui lòng gọi 09xx xxx 678 để…",
      });
    }
    if (lowerBody.includes("giá mua") || lowerBody.includes("giá vốn")) {
      warnings.push({
        type: "cost_keyword",
        field: "body",
        snippet: "…giá mua tại cảng…",
      });
    }
  }

  if (warnings.length > 0 && payload.acknowledge_warnings !== true) {
    throw new ApiError("Phát hiện cảnh báo trước khi xuất bản (CONTENT_WARNINGS).", 409, "CONTENT_WARNINGS", { warnings });
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

  const vDetail: ContentEntryVersionDetail = {
    version: nextVer,
    published_at: now,
    published_by_name: "Quản trị viên",
    kind: entry.kind,
    title: entry.title,
    slug: entry.slug,
    excerpt: entry.excerpt,
    seo_title: entry.seo_title,
    seo_description: entry.seo_description,
    description: entry.seo_description || entry.excerpt,
    category: entry.category,
    cover_image: entry.cover_image,
    body: JSON.parse(JSON.stringify(entry.body)),
    restored_from: entry.restored_from,
  };
  const currentVersions = MOCK_VERSIONS_DB.get(id) || [];
  MOCK_VERSIONS_DB.set(id, [vDetail, ...currentVersions.filter((v) => v.version !== nextVer)]);


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
): EntryUnpublishResponse {
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

  // Giống máy chủ thật: chỉ trả trạng thái mới và phiên bản dòng.
  return { status: entry.status, row_version: entry.row_version };
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

  return snapshotOf(entry);
}

export function mockGetGoliveStatus(): GoliveStatusResponse {
  const publishedRoles = new Set(
    MOCK_ENTRIES.filter((e) => e.status === "published" && e.page_role).map((e) => e.page_role as string)
  );
  const requiredRoles = ["privacy", "terms", "refund", "seller_info"];
  const missing = requiredRoles.filter((r) => !publishedRoles.has(r));
  return { missing_roles: missing };
}

// Đúng hình dạng 02b Shop §3.1 `{groups, items}`: giá là chuỗi, chỉ mức tồn, không số kg tồn (review lô 1, H1).
export function mockFetchShopCatalog(): ShopCatalogResponse {
  const fish = { slug: "ca", name: "Cá" };
  const shrimp = { slug: "tom", name: "Tôm" };
  const squid = { slug: "muc", name: "Mực" };
  return {
    groups: [
      { ...fish, item_count: 2 },
      { ...shrimp, item_count: 1 },
      { ...squid, item_count: 1 },
    ],
    items: [
      { item_code: "CA-THU-1KG", name: "Cá thu Phan Thiết 1kg", item_type: "SIMPLE", unit: "kg", price: "250000", stock_level: "in", group: fish },
      { item_code: "CA-BOP-1KG", name: "Cá bớp cắt khoanh 1kg", item_type: "SIMPLE", unit: "kg", price: "280000", stock_level: "low", group: fish },
      { item_code: "TOM-SU-1KG", name: "Tôm sú Cà Mau 1kg", item_type: "SIMPLE", unit: "kg", price: "320000", stock_level: "in", group: shrimp },
      { item_code: "MUC-ONG-1KG", name: "Mực ống Phan Thiết 1kg", item_type: "SIMPLE", unit: "kg", price: "220000", stock_level: "out", group: squid },
    ],
  };
}

export function mockSubmitEntry(
  id: number,
  payload: EntrySubmitPayload
): EntrySubmitResponse {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.status !== "draft") {
    throw new ApiError(
      "Chỉ có thể gửi duyệt bài viết đang ở trạng thái bản nháp (BR-ND-01).",
      400,
      "BR-ND-01"
    );
  }

  if (entry.row_version !== payload.row_version) {
    throw new ApiError(
      "Dữ liệu đã bị thay đổi bởi người khác (STALE_VERSION).",
      409,
      "STALE_VERSION"
    );
  }

  entry.status = "pending_review";
  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.status = "pending_review";
    listItem.updated_at = entry.updated_at;
  }

  return { status: "pending_review", row_version: entry.row_version };
}

export function mockReturnEntry(
  id: number,
  payload: EntryReturnPayload
): EntryReturnResponse {
  const entry = MOCK_ENTRY_DETAILS.get(id);
  if (!entry) throw new ApiError("Không tìm thấy bài viết.", 404, "NOT_FOUND");

  if (entry.status !== "pending_review") {
    throw new ApiError(
      "Chỉ có thể trả về bài viết đang chờ duyệt (BR-ND-01).",
      400,
      "BR-ND-01"
    );
  }

  const validReasons = ["missing_info", "wrong_content", "legal_risk", "other"];
  if (!payload.reason || !validReasons.includes(payload.reason)) {
    throw new ApiError("Lý do trả về không hợp lệ (BR-ND-15).", 400, "BR-ND-15");
  }

  if (entry.row_version !== payload.row_version) {
    throw new ApiError(
      "Dữ liệu đã bị thay đổi bởi người khác (STALE_VERSION).",
      409,
      "STALE_VERSION"
    );
  }

  entry.status = "draft";
  entry.return_reason = payload.reason;
  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.status = "draft";
    listItem.updated_at = entry.updated_at;
  }

  return { status: "draft", row_version: entry.row_version, return_reason: entry.return_reason };
}

export function mockFetchEntryVersions(id: number): ContentEntryVersionListItem[] {
  const list = MOCK_VERSIONS_DB.get(id) || [];
  return list.map((v) => ({
    version: v.version,
    published_at: v.published_at,
    published_by_name: v.published_by_name,
    title: v.title,
    restored_from: v.restored_from,
  }));
}

export function mockGetEntryVersion(
  id: number,
  versionNo: number
): ContentEntryVersionDetail {
  const list = MOCK_VERSIONS_DB.get(id) || [];
  const ver = list.find((v) => v.version === versionNo);
  if (!ver) throw new ApiError("Không tìm thấy phiên bản yêu cầu.", 404, "NOT_FOUND");
  return { ...ver };
}

export function mockRestoreEntryVersion(
  id: number,
  versionNo: number,
  payload: EntryRestorePayload
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

  const ver = mockGetEntryVersion(id, versionNo);
  entry.title = ver.title;
  entry.slug = ver.slug;
  entry.excerpt = ver.excerpt;
  entry.seo_title = ver.seo_title;
  entry.seo_description = ver.seo_description;
  entry.category = ver.category;
  entry.cover_image = ver.cover_image;
  entry.body = JSON.parse(JSON.stringify(ver.body));
  entry.restored_from = versionNo;
  entry.has_unpublished_changes = true;
  entry.row_version += 1;
  entry.updated_at = new Date().toISOString();

  const listItem = MOCK_ENTRIES.find((e) => e.id === id);
  if (listItem) {
    listItem.title = entry.title;
    listItem.slug = entry.slug;
    listItem.category = entry.category;
    listItem.has_unpublished_changes = true;
    listItem.updated_at = entry.updated_at;
  }

  return snapshotOf(entry);
}

/** Giả lập người khác vừa sửa tiêu đề bài (đổi chữ + tăng row_version), để kiểm bản nháp cũ trên máy. */
export function mockOtherEdit(id: number, title: string): number | null {
  const e = MOCK_ENTRY_DETAILS.get(id);
  if (!e) return null;
  e.title = title;
  e.row_version += 1;
  e.updated_at = new Date().toISOString();
  const listItem = MOCK_ENTRIES.find((x) => x.id === id);
  if (listItem) listItem.title = title;
  return e.row_version;
}

/**
 * Đặt thân bài về dạng "chưa chuẩn hoá" như máy chủ thật có thể trả: chữ liền kề bị tách thành nhiều đoạn,
 * đoạn trống, ghi chú định dạng rỗng. Tiptap gộp lại khi nạp, nhưng mở bài không được tính là người dùng đã sửa.
 */
export function mockUseRawBody(id: number): boolean {
  const e = MOCK_ENTRY_DETAILS.get(id);
  if (!e) return false;
  e.body = {
    type: "doc",
    blocks: [
      { type: "heading", level: 3, text: "Cách chọn cá" },
      { type: "paragraph", children: [{ text: "Chọn cá " }, { text: "thu tươi", marks: [] }, { text: " có mắt trong." }] },
      { type: "paragraph", children: [] },
      { type: "quote", children: [{ text: "Tươi ngon " }, { text: "là nhờ giữ lạnh.", marks: [] }] },
    ],
  };
  return true;
}


if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    content: (m: ContentMode) => {
      window.localStorage.setItem(CONTENT_MODE_KEY, m);
      return `Chế độ mock nội dung: ${m}`;
    },
    contentBump: (id: number) => {
      const e = MOCK_ENTRY_DETAILS.get(id);
      if (e) e.row_version += 1;
      return e ? e.row_version : null;
    },
    contentOtherEdit: (id: number, title: string) => mockOtherEdit(id, title),
    contentRawBody: (id: number) => mockUseRawBody(id),
  };
}
