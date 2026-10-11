import { ApiError } from "@/lib/types";
import { fetchPublicEntry } from "@/features/content/api";
import type { PublicEntryDetail } from "@/features/content/types";
import { HOME_BANNER_SLUG, HOME_COMMITMENTS_SLUG } from "@/features/content/slugs";

/**
 * Nạp hai trang CMS cố định của trang chủ (SHOP-5-03; 02b §3.7.2), dùng chung cho HomeScreen và dải chữ đầu trang
 * của ShopFrame, để một lần mở web chỉ tốn một request cho mỗi trang.
 *
 * Kết quả: trang (đã đăng) · `null` khi 404/410 (chưa có hoặc đã gỡ -> ẩn khối) · ném lỗi khi lỗi mạng/máy chủ.
 * Chỉ giữ cache khi có câu trả lời chắc chắn (trang hoặc 404/410); lỗi mạng thì bỏ cache để lần sau thử lại
 * (bài học review lô 3+4, L3).
 */
const cache = new Map<string, Promise<PublicEntryDetail | null>>();

function isGone(err: unknown): boolean {
  return err instanceof ApiError && (err.status === 404 || err.status === 410);
}

export function loadHomeEntry(slug: string): Promise<PublicEntryDetail | null> {
  const hit = cache.get(slug);
  if (hit) return hit;
  const promise = fetchPublicEntry(slug).catch((err: unknown) => {
    if (isGone(err)) return null;
    if (cache.get(slug) === promise) cache.delete(slug);
    throw err;
  });
  cache.set(slug, promise);
  return promise;
}

export const loadHomeBanner = () => loadHomeEntry(HOME_BANNER_SLUG);
export const loadHomeCommitments = () => loadHomeEntry(HOME_COMMITMENTS_SLUG);
