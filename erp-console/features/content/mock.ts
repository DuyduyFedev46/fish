import {
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ContentCategory,
  ContentCounts,
  ContentEntryListItem,
} from "./types";

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

let MOCK_ENTRIES: ContentEntryListItem[] = [];

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
  if (!cat) throw new Error("Category not found");

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
