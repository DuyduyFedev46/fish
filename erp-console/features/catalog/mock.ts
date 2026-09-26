// Mock module catalog — chạy khi NEXT_PUBLIC_USE_MOCK=1. Contract A2 (02-stories.md, hồ sơ
// 2026-09-26-anh-mat-hang). BE thật chưa xong nên FE dựng theo đúng bảng lỗi/response của story.
//
// Ảnh mẫu sinh BẰNG CODE lúc chạy (SVG data URI) — KHÔNG commit tệp ảnh nào vào repo (quy ước
// 2026-09-25, BR-DM-16). Danh sách seed có đủ 3 trạng thái theo yêu cầu contract: có ảnh (data URI),
// chưa có ảnh (null), ảnh lỗi (data URI hỏng, giải mã lỗi ngay — không phụ thuộc mạng) để thử khung
// mặc định (ItemThumb tự chuyển khi <img> báo onError).
//
// Cách thử lỗi khi tải ảnh (đặt TÊN TỆP khi chọn file, không phân biệt hoa/thường):
//   - tên chứa "loi-luu-tru"  -> 503 BR-DM-16 (kho ảnh lỗi, A2-AC11)
//   - tên chứa "mat-mang"     -> mô phỏng rớt mạng giữa chừng (A2-AC12): trả status 0, không có body
// Cách thử 409 (A2-AC13, "ghi đè"): gõ đúng chữ TEST_CONFLICT vào ô "Mô tả ảnh (alt text)".
// Định dạng/dung lượng/độ phân giải được KIỂM THẬT trên tệp đã chọn (đọc byte đầu để biết JPEG/PNG/
// WebP thật hay chỉ đổi đuôi, và đọc kích thước ảnh thật) — không chỉ dựa vào phần mở rộng tên tệp.

import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { beError } from "@/shared/lib/beErrors.mock";
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import type { CatalogItem, CatalogItemImage, ImageWarning, UploadImageResponse } from "./types";

const MAX_BYTES = 10 * 1024 * 1024; // ITEM_IMAGE_MAX_BYTES mặc định (02-stories.md)
const MIN_SIDE_WARN = 600; // ITEM_IMAGE_MIN_SIDE_WARN mặc định
const STORAGE_KEY = "cave_erp_mock_catalog_items";

/** btoa() chỉ nhận Latin-1 — chữ có dấu tiếng Việt (vd "Ghẹ") cần mã hoá UTF-8 trước. */
function toBase64Utf8(text: string): string {
  if (typeof TextEncoder !== "undefined" && typeof window !== "undefined") {
    const bytes = new TextEncoder().encode(text);
    let binary = "";
    bytes.forEach((b) => (binary += String.fromCharCode(b)));
    return window.btoa(binary);
  }
  return Buffer.from(text, "utf-8").toString("base64");
}

function svgDataUri(bg: string, label: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240"><rect width="240" height="240" fill="${bg}"/><text x="120" y="128" font-size="26" text-anchor="middle" fill="#fff" font-family="sans-serif" font-weight="600">${label}</text></svg>`;
  return `data:image/svg+xml;base64,${toBase64Utf8(svg)}`;
}

function urlsOf(src: string): { thumb: string; card: string; detail: string } {
  return { thumb: src, card: src, detail: src };
}

/** Data URI hỏng (không phải ảnh thật, giải mã lỗi ngay, không cần mạng) — để thử khung mặc định khi
 * ảnh lỗi (thay vì gọi ra một host GCS giả, vốn tuỳ máy có mạng hay không mới báo lỗi kịp). */
const BROKEN_URLS = urlsOf("data:image/webp;base64,AAAAAAAAAAAAAAAAAAAAAAAA");

function seed(): CatalogItem[] {
  return [
    {
      id: 1,
      code: "CA-THU",
      name: "Cá thu cắt khúc",
      item_group: 3, group_name: "Cá",
      item_type: "SIMPLE",
      is_active: true,
      image: {
        id: "img_seed_cathu",
        alt: "Cá thu cắt khúc",
        is_illustration: false,
        urls: urlsOf(svgDataUri("#1F66D1", "Cá thu")),
        uploaded_at: "2026-09-20T08:10:00+07:00",
      },
    },
    { id: 2, code: "CA-BASA", name: "Cá basa phi lê", item_group: 3, group_name: "Cá", item_type: "SIMPLE", is_active: true, image: null },
    {
      id: 3,
      code: "TOM-SU",
      name: "Tôm sú tươi",
      item_group: 5, group_name: "Tôm",
      item_type: "SIMPLE",
      is_active: true,
      image: {
        id: "img_seed_tomsu",
        alt: "",
        is_illustration: true,
        urls: BROKEN_URLS,
        uploaded_at: "2026-09-18T09:00:00+07:00",
      },
    },
    { id: 4, code: "MUC-ONG", name: "Mực ống", item_group: 6, group_name: "Mực", item_type: "SIMPLE", is_active: true, image: null },
    {
      id: 5,
      code: "GHEO-BIEN",
      name: "Ghẹ biển",
      item_group: 7, group_name: "Cua ghẹ",
      item_type: "SIMPLE",
      is_active: false,
      image: {
        id: "img_seed_gheo",
        alt: "Ghẹ biển",
        is_illustration: false,
        urls: urlsOf(svgDataUri("#157F3D", "Ghẹ")),
        uploaded_at: "2026-09-10T07:30:00+07:00",
      },
    },
    {
      id: 6,
      code: "COMBO-LAU",
      name: "Combo lẩu hải sản",
      item_group: 9, group_name: "Combo",
      item_type: "BUNDLE",
      is_active: true,
      image: null,
    },
  ];
}

function ls(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function items(): CatalogItem[] {
  const raw = ls()?.getItem(STORAGE_KEY);
  if (raw) {
    try {
      return JSON.parse(raw) as CatalogItem[];
    } catch {
      /* hỏng → seed */
    }
  }
  return seed();
}

function saveItems(list: CatalogItem[]): void {
  try {
    ls()?.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    /* localStorage không khả dụng — mock vẫn chạy trong phiên hiện tại */
  }
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    resetCatalog: () => {
      window.localStorage.removeItem(STORAGE_KEY);
      return "Đã về danh sách mặt hàng seed.";
    },
  };
}

// PAGE_SIZE thấp CỐ Ý (không phải 50 như BE thật) để "Tải thêm" luyện được ngay cả với seed nhỏ —
// mock CHỈ cần đúng HÌNH DẠNG phân trang ({count,next,previous,results}), không cần khớp số/trang thật.
const PAGE_SIZE = 4;

// ---- GET /api/catalog/items/?has_image=true|false&page=N ----
// QA REJECTED lô 1 (B1, 04-qa-report.md): mock từng trả MẢNG TRẦN, che giấu việc `listItems` thật
// (`DEFAULT_PAGINATION_CLASS` toàn cục của BE) trả {count,next,previous,results}. Từ nay mock phải
// trả ĐÚNG hình dạng phân trang, để lệch kiểu dữ liệu như B1 không lọt qua lần kiểm mock nữa.
export function mockListItems(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes(PERM.viewItem)) return beError("DRF_FORBIDDEN");
  const url = new URL(req.path, "http://mock.local");
  const hasImage = url.searchParams.get("has_image");
  const page = Math.max(1, Number(url.searchParams.get("page") || "1") || 1);
  let hit = items();
  if (hasImage === "true") hit = hit.filter((i) => i.image !== null);
  if (hasImage === "false") hit = hit.filter((i) => i.image === null);
  const pages = Math.max(1, Math.ceil(hit.length / PAGE_SIZE));
  const link = (n: number) => {
    const qs = new URLSearchParams(url.searchParams);
    qs.set("page", String(n));
    return `http://localhost:8000/api/catalog/items/?${qs.toString()}`;
  };
  return {
    status: 200,
    body: {
      count: hit.length,
      next: page < pages ? link(page + 1) : null,
      previous: page > 1 ? link(page - 1) : null,
      results: hit.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    },
  };
}

// ---- Kiểm nội dung tệp: đọc byte đầu để biết JPEG/PNG/WebP THẬT (bắt được .txt đổi đuôi .jpg) ----
async function sniffImageFormat(file: File): Promise<boolean> {
  try {
    const head = new Uint8Array(await file.slice(0, 16).arrayBuffer());
    if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return true; // JPEG
    if (head[0] === 0x89 && head[1] === 0x50 && head[2] === 0x4e && head[3] === 0x47) return true; // PNG
    if (
      head[0] === 0x52 && head[1] === 0x49 && head[2] === 0x46 && head[3] === 0x46 &&
      head[8] === 0x57 && head[9] === 0x45 && head[10] === 0x42 && head[11] === 0x50
    ) return true; // WebP (RIFF....WEBP)
    return false;
  } catch {
    return false;
  }
}

/** Kích thước thật của ảnh đã chọn — best effort, không chặn luồng nếu trình duyệt không hỗ trợ. */
async function readImageSize(file: File): Promise<{ width: number; height: number } | null> {
  try {
    if (typeof createImageBitmap === "function") {
      const bmp = await createImageBitmap(file);
      const size = { width: bmp.width, height: bmp.height };
      bmp.close?.();
      return size;
    }
  } catch {
    /* không đọc được (định dạng lạ) — bỏ qua cảnh báo kích thước */
  }
  return null;
}

function genImageId(): string {
  return `img_${Math.random().toString(36).slice(2, 10)}`;
}

// ---- POST /api/catalog/items/{id}/image/ ----
export async function mockUploadImage(req: MockRequest): Promise<MockResponse> {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes(PERM.changeItemImage)) return beError("CATALOG_IMAGE_FORBIDDEN");

  const m = /\/api\/catalog\/items\/(\d+)\/image\/?/.exec(req.path);
  const itemId = m ? Number(m[1]) : NaN;
  const list = items();
  const item = list.find((i) => i.id === itemId);
  if (!item) return beError("CATALOG_ITEM_NOT_FOUND");

  const fd = req.body;
  if (!(fd instanceof FormData)) return beError("CATALOG_IMAGE_MISSING_FILE");
  const file = fd.get("file");
  if (!(file instanceof File) || file.size === 0) return beError("CATALOG_IMAGE_MISSING_FILE");

  const altText = String(fd.get("alt_text") ?? "");
  const isIllustration = fd.get("is_illustration") === "true";
  const expectedImageId = String(fd.get("expected_image_id") ?? "");

  // Mã thử lỗi qua tên tệp (xem ghi chú đầu file).
  const lowerName = file.name.toLowerCase();
  if (lowerName.includes("loi-luu-tru")) return beError("CATALOG_IMAGE_STORAGE_ERROR");
  if (lowerName.includes("mat-mang")) return { status: 0, body: null };

  if (altText.length > 125) return beError("CATALOG_IMAGE_ALT_TOO_LONG");
  if (file.size > MAX_BYTES) return beError("CATALOG_IMAGE_TOO_LARGE");
  if (!(await sniffImageFormat(file))) return beError("CATALOG_IMAGE_BAD_FORMAT");

  // A2-AC13: xung đột ghi đè — mã thử qua alt text (không mô phỏng 2 phiên trình duyệt thật được).
  const currentImageId = item.image?.id ?? "";
  if (altText.trim() === "TEST_CONFLICT" || expectedImageId !== currentImageId) {
    return beError("CATALOG_IMAGE_CONFLICT");
  }

  const warnings: ImageWarning[] = [];
  const size = await readImageSize(file);
  if (size && Math.min(size.width, size.height) < MIN_SIDE_WARN) {
    warnings.push({ code: "LOW_RESOLUTION", message: "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ." });
  }

  // Xem trước ngay bằng blob URL của tệp thật vừa chọn (chỉ sống trong phiên trình duyệt — đủ cho mock).
  const objectUrl = URL.createObjectURL(file);
  const wasEmpty = !item.image;
  const image = {
    id: genImageId(),
    alt: altText.trim() || item.name,
    is_illustration: isIllustration,
    urls: urlsOf(objectUrl),
    uploaded_at: new Date().toISOString(),
  };
  item.image = image;
  saveItems(list);

  const body: UploadImageResponse = {
    item_id: item.id,
    item_code: item.code,
    image: { ...image, uploaded_by: me.display_name || me.username },
    warnings,
  };
  return { status: wasEmpty ? 201 : 200, body };
}
