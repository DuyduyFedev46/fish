// Nháp form "Nhập lô" (SR-07, BM-04).
// - Giá mua (rate) là dữ liệu nhạy cảm (bất biến 1) → KHÔNG bao giờ ghi vào storage; nạp lại nháp thì ô giá để trống.
// - Khoá gắn id người dùng (`cave_draft_nhap_lo:<userId>`), lưu ở sessionStorage (mất khi đóng tab), không dùng localStorage.
// - Idempotency key nằm trong nháp của CHÍNH người đó (F5 giữ key để gửi lại sau lỗi mạng không tạo phiếu thứ hai);
//   nháp của người khác / đã đăng xuất / đã gửi thành công thì không bao giờ dùng lại key (form sinh key mới).
// - Đăng xuất gọi clearAllDrafts() của `shared/lib/drafts.ts` (không import vào đây): xoá mọi khoá `cave_draft_nhap_lo*` ở cả sessionStorage và localStorage (khoá cũ dùng chung).

import { RECEIVE_BATCHES_DRAFT_PREFIX } from "@/shared/lib/drafts";
import type { ReceiveBatchesLineInput } from "../types";

/** Khoá cũ (dùng chung mọi người, ở localStorage, có cả giá mua) — chỉ còn để dọn. */
export const LEGACY_DRAFT_KEY = RECEIVE_BATCHES_DRAFT_PREFIX;

export type ReceiveBatchesDraftLine = Omit<ReceiveBatchesLineInput, "rate">;

export type ReceiveBatchesDraft = {
  supplierId: number | "";
  receivedDate: string;
  lines: ReceiveBatchesDraftLine[];
  /** Key chống gửi trùng của lần nhập đang dở — chỉ của người sở hữu nháp. */
  idempotencyKey?: string;
};

export function draftKey(userId: number): string {
  return `${LEGACY_DRAFT_KEY}:${userId}`;
}

function storage(kind: "sessionStorage" | "localStorage"): Storage | null {
  try {
    return typeof window === "undefined" ? null : window[kind];
  } catch {
    return null;
  }
}

/** Chỉ giữ các trường an toàn; cố ý bỏ `rate` (kể cả khi dữ liệu cũ còn) và mọi trường lạ. */
function sanitize(draft: unknown): ReceiveBatchesDraft | null {
  if (!draft || typeof draft !== "object") return null;
  const d = draft as Record<string, unknown>;
  if (!Array.isArray(d.lines)) return null;
  const lines: ReceiveBatchesDraftLine[] = d.lines
    .filter((l): l is Record<string, unknown> => !!l && typeof l === "object")
    .map((l) => ({
      item_code: typeof l.item_code === "string" ? l.item_code : "",
      qty: typeof l.qty === "string" ? l.qty : "",
      shelf_life_days: typeof l.shelf_life_days === "number" ? l.shelf_life_days : null,
    }));
  return {
    supplierId: typeof d.supplierId === "number" ? d.supplierId : "",
    receivedDate: typeof d.receivedDate === "string" ? d.receivedDate : "",
    lines,
    ...(typeof d.idempotencyKey === "string" && d.idempotencyKey ? { idempotencyKey: d.idempotencyKey } : {}),
  };
}

export function saveDraft(userId: number, draft: ReceiveBatchesDraft): void {
  const s = storage("sessionStorage");
  const safe = sanitize(draft);
  if (!s || !safe) return;
  try {
    s.setItem(draftKey(userId), JSON.stringify(safe));
  } catch {
    /* bỏ qua: hết dung lượng / chế độ riêng tư */
  }
}

export function loadDraft(userId: number): ReceiveBatchesDraft | null {
  const raw = storage("sessionStorage")?.getItem(draftKey(userId));
  if (!raw) return null;
  try {
    return sanitize(JSON.parse(raw));
  } catch {
    return null;
  }
}

/**
 * Key cho form vừa mở: có key trong nháp của CHÍNH `userId` → dùng lại; không có → `generate()` (key mới).
 * Nháp của người khác không bao giờ được đọc vì khoá gắn userId; đăng xuất/gửi thành công đã xoá nháp.
 */
export function resolveIdempotencyKey(userId: number | null, generate: () => string): string {
  const saved = userId !== null ? loadDraft(userId)?.idempotencyKey : undefined;
  return saved || generate();
}

/** Xoá nháp của một người (sau khi gửi phiếu thành công). */
export function clearDraft(userId: number): void {
  try {
    storage("sessionStorage")?.removeItem(draftKey(userId));
  } catch {
    /* bỏ qua */
  }
}

/** Xoá khoá cũ ở localStorage (có giá mua, dùng chung mọi người). An toàn để gọi bất cứ lúc nào. */
export function purgeLegacyDraft(): void {
  try {
    storage("localStorage")?.removeItem(LEGACY_DRAFT_KEY);
  } catch {
    /* bỏ qua */
  }
}
