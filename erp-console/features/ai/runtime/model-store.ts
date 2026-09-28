// Cache model GGUF trong IndexedDB (K6) — key = URL (immutable theo version, không ghi đè).
// Chỉ lưu Blob model (KHÔNG lưu bất kỳ dữ liệu cá nhân nào — bất biến 9).
// IndexedDB không dùng được (ẩn danh, đầy, bị chặn) → trả null/false, màn vẫn nhập tay được.

const DB_NAME = "cave_erp_ai";
const STORE = "models";
const DB_VERSION = 1;

export type CachedModel = {
  /** Key (keyPath) — URL GGUF tải về. */
  url: string;
  bytes: number;
  fetchedAt: number;
  etag: string | null;
  blob: Blob;
};

function openDb(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      if (typeof indexedDB === "undefined") return resolve(null);
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: "url" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

/** Đọc bản model đã cache theo URL; không có / hỏng → null (hỏi lại — S08-AC4). */
export async function getCachedModel(url: string): Promise<CachedModel | null> {
  const db = await openDb();
  if (!db) return null;
  try {
    return await new Promise<CachedModel | null>((resolve) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(url);
      req.onsuccess = () => {
        const rec = req.result as CachedModel | undefined;
        resolve(rec && rec.blob instanceof Blob && rec.bytes > 0 ? rec : null);
      };
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  } finally {
    db.close();
  }
}

/** Lưu bản model mới (xoá bản cũ cùng URL trước — URL đổi theo version nên không ghi đè nhầm). */
export async function putCachedModel(rec: CachedModel): Promise<boolean> {
  const db = await openDb();
  if (!db) return false;
  try {
    return await new Promise<boolean>((resolve) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(rec);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
      tx.onabort = () => resolve(false);
    });
  } catch {
    return false;
  } finally {
    db.close();
  }
}

/** Xoá bản cache (model đổi version / bản hỏng). */
export async function removeCachedModel(url: string): Promise<boolean> {
  const db = await openDb();
  if (!db) return false;
  try {
    return await new Promise<boolean>((resolve) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(url);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
      tx.onabort = () => resolve(false);
    });
  } catch {
    return false;
  } finally {
    db.close();
  }
}
