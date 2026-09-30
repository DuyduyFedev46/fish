// "Giữ nháp" cho form (S7-AC6, UC-01 E2).
// - Nháp lưu localStorage kèm id chủ nháp.
// - Token hết hạn (401) → nháp GIỮ nguyên; đăng nhập lại cùng người → form mở lại đủ nội dung.
// - Người khác đăng nhập trên cùng máy → purgeForeignDrafts() xoá sạch nháp của người trước.
// - Đăng xuất chủ động → clearAllDrafts() (S46-AC1) — gồm cả nháp Nhập lô (SR-07).

const PREFIX = "cave_erp_draft:";

/**
 * Tiền tố khoá nháp form "Nhập lô" (SR-07): khoá mới `cave_draft_nhap_lo:<userId>` ở sessionStorage,
 * khoá cũ `cave_draft_nhap_lo` (dùng chung, có giá mua) ở localStorage. Đăng xuất phải xoá tất cả.
 * Khai ở đây (shared) để `auth` dọn được mà không import vào ruột `purchasing`.
 */
export const RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_nhap_lo";

type Stored<T> = { owner: number; savedAt: string; data: T };

function ls(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function draftKeys(): string[] {
  const s = ls();
  if (!s) return [];
  const keys: string[] = [];
  for (let i = 0; i < s.length; i++) {
    const k = s.key(i);
    if (k && k.startsWith(PREFIX)) keys.push(k);
  }
  return keys;
}

export function loadDraft<T>(formKey: string, owner: number): T | null {
  const raw = ls()?.getItem(PREFIX + formKey);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Stored<T>;
    return parsed.owner === owner ? parsed.data : null;
  } catch {
    return null;
  }
}

export function saveDraft<T>(formKey: string, owner: number, data: T): void {
  const s = ls();
  if (!s) return;
  const payload: Stored<T> = { owner, savedAt: new Date().toISOString(), data };
  try {
    s.setItem(PREFIX + formKey, JSON.stringify(payload));
  } catch {
    /* bỏ qua */
  }
}

export function clearDraft(formKey: string): void {
  ls()?.removeItem(PREFIX + formKey);
}

/** Xoá mọi nháp không thuộc `owner`. Gọi ngay sau khi biết người vừa đăng nhập là ai. */
export function purgeForeignDrafts(owner: number): void {
  const s = ls();
  if (!s) return;
  for (const k of draftKeys()) {
    try {
      const parsed = JSON.parse(s.getItem(k) || "null") as Stored<unknown> | null;
      if (!parsed || parsed.owner !== owner) s.removeItem(k);
    } catch {
      s.removeItem(k);
    }
  }
}

function removeByPrefix(s: Storage | null, prefix: string): void {
  if (!s) return;
  try {
    const keys: string[] = [];
    for (let i = 0; i < s.length; i++) {
      const k = s.key(i);
      if (k && k.startsWith(prefix)) keys.push(k);
    }
    for (const k of keys) s.removeItem(k);
  } catch {
    /* bỏ qua */
  }
}

function ss(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

/** Đăng xuất: xoá mọi nháp ERP (localStorage) và mọi nháp Nhập lô của mọi người (session + khoá cũ ở local). */
export function clearAllDrafts(): void {
  removeByPrefix(ls(), PREFIX);
  removeByPrefix(ls(), RECEIVE_BATCHES_DRAFT_PREFIX);
  removeByPrefix(ss(), RECEIVE_BATCHES_DRAFT_PREFIX);
}
