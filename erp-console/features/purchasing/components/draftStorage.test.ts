// SR-07 (BM-04): nháp "Nhập lô" không giữ giá mua; gắn theo người dùng; nằm ở sessionStorage; đăng xuất xoá sạch.
// Dữ liệu giả. Môi trường vitest là node nên dựng window + storage giả có length/key để quét khoá.
import { beforeEach, describe, expect, it } from "vitest";
import {
  clearDraft,
  draftKey,
  legacyDraftKey,
  loadDraft,
  migrateLegacyDraft,
  purgeLegacyDraft,
  resolveIdempotencyKey,
  saveDraft,
  LEGACY_DRAFT_KEY,
} from "./draftStorage";
import { clearAllDrafts, LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX, RECEIVE_BATCHES_DRAFT_PREFIX } from "@/shared/lib/drafts";

function makeStorage() {
  let store: Record<string, string> = {};
  return {
    get length() {
      return Object.keys(store).length;
    },
    key: (i: number) => Object.keys(store)[i] ?? null,
    getItem: (k: string) => (k in store ? store[k] : null),
    setItem: (k: string, v: string) => {
      store[k] = String(v);
    },
    removeItem: (k: string) => {
      delete store[k];
    },
    clear: () => {
      store = {};
    },
    dump: () => JSON.stringify(store),
  };
}

let local: ReturnType<typeof makeStorage>;
let session: ReturnType<typeof makeStorage>;

const draftWithRate = {
  supplierId: 3,
  receivedDate: "2026-09-30",
  lines: [{ item_code: "CA-THU", qty: "50", rate: "81234", shelf_life_days: 3 }],
};

beforeEach(() => {
  local = makeStorage();
  session = makeStorage();
  (globalThis as unknown as { window: unknown }).window = { localStorage: local, sessionStorage: session };
});

describe("SR-07 draftStorage", () => {
  it("SR-07-AC1: lưu nháp có rate → đọc lại KHÔNG có rate, các trường khác còn nguyên", () => {
    saveDraft(7, draftWithRate);
    const back = loadDraft(7);
    expect(back).not.toBeNull();
    expect(back!.supplierId).toBe(3);
    expect(back!.receivedDate).toBe("2026-09-30");
    expect(back!.lines[0].item_code).toBe("CA-THU");
    expect(back!.lines[0].qty).toBe("50");
    expect(back!.lines[0].shelf_life_days).toBe(3);
    expect("rate" in back!.lines[0]).toBe(false);
  });

  it("SR-07-AC1: giá mua không nằm ở bất kỳ storage nào", () => {
    saveDraft(7, draftWithRate);
    expect(session.dump()).not.toContain("81234");
    expect(local.dump()).not.toContain("81234");
  });

  it("SR-07-AC2: khoá gắn userId, nằm ở sessionStorage, không đụng localStorage", () => {
    saveDraft(7, draftWithRate);
    expect(draftKey(7)).toBe("cave_draft_receive_batches:7");
    expect(session.getItem("cave_draft_receive_batches:7")).not.toBeNull();
    expect(local.length).toBe(0);
  });

  it("SR-07-AC2: người khác không đọc được nháp của người này", () => {
    saveDraft(7, draftWithRate);
    expect(loadDraft(8)).toBeNull();
  });

  it("SR-07-AC2: clearAllDrafts xoá mọi khoá nháp Nhập lô (tiền tố mới và cũ) ở cả local và session", () => {
    local.setItem(LEGACY_DRAFT_KEY, JSON.stringify({ lines: [{ rate: "81234" }] }));
    saveDraft(7, draftWithRate);
    saveDraft(8, draftWithRate);
    session.setItem("khoa_khac", "giu");
    local.setItem("khoa_khac", "giu");
    clearAllDrafts();
    expect(local.getItem(LEGACY_DRAFT_KEY)).toBeNull();
    expect(session.getItem("cave_draft_receive_batches:7")).toBeNull();
    expect(session.getItem("cave_draft_receive_batches:8")).toBeNull();
    expect(session.getItem("khoa_khac")).toBe("giu");
    expect(local.getItem("khoa_khac")).toBe("giu");
  });

  it("SR-07-AC4 (a): F5 cùng người → giữ đúng idempotency key trong nháp; key nằm cùng khoá theo userId", () => {
    saveDraft(7, { ...draftWithRate, idempotencyKey: "key-cua-7" });
    expect(loadDraft(7)!.idempotencyKey).toBe("key-cua-7");
    expect(resolveIdempotencyKey(7, () => "key-moi")).toBe("key-cua-7");
    expect(session.getItem("cave_draft_receive_batches:7")).toContain("key-cua-7");
    expect(local.length).toBe(0);
  });

  it("SR-07-AC4 (b): người khác mở form → key mới, không bao giờ dùng lại key của người trước", () => {
    saveDraft(7, { ...draftWithRate, idempotencyKey: "key-cua-7" });
    expect(resolveIdempotencyKey(8, () => "key-moi-cua-8")).toBe("key-moi-cua-8");
    // đăng xuất rồi người khác (hoặc cùng người) vào: nháp đã xoá → key mới
    clearAllDrafts();
    expect(resolveIdempotencyKey(7, () => "key-moi-sau-dang-xuat")).toBe("key-moi-sau-dang-xuat");
    expect(resolveIdempotencyKey(null, () => "key-chua-biet-user")).toBe("key-chua-biet-user");
  });

  it("SR-07-AC4 (c): sau gửi thành công (xoá nháp) → mở lại form ra key mới", () => {
    saveDraft(7, { ...draftWithRate, idempotencyKey: "key-da-dung" });
    clearDraft(7);
    expect(loadDraft(7)).toBeNull();
    expect(resolveIdempotencyKey(7, () => "key-lan-sau")).toBe("key-lan-sau");
  });

  it("nháp có idempotency key vẫn không chứa rate", () => {
    saveDraft(7, { ...draftWithRate, idempotencyKey: "k" });
    expect(session.dump()).not.toContain("81234");
    expect(session.dump()).not.toContain("rate");
  });

  it("nháp cũ/hỏng: JSON hỏng hoặc còn rate → không lỗi, không trả rate", () => {
    session.setItem("cave_draft_receive_batches:7", "{hỏng");
    expect(loadDraft(7)).toBeNull();
    session.setItem("cave_draft_receive_batches:7", JSON.stringify({ supplierId: 1, receivedDate: "2026-09-30", lines: [{ item_code: "X", qty: "1", rate: "999" }] }));
    const back = loadDraft(7);
    expect(back!.lines[0]).not.toHaveProperty("rate");
  });

  it("không có window (SSR): không ném lỗi", () => {
    delete (globalThis as unknown as { window?: unknown }).window;
    expect(() => saveDraft(7, draftWithRate)).not.toThrow();
    expect(loadDraft(7)).toBeNull();
    expect(() => clearAllDrafts()).not.toThrow();
  });

  // ---- P8b Lô 3: đổi tiền tố khoá nháp; khoá cũ phải được chuyển rồi xoá, và luôn bị dọn khi đăng xuất ----

  it("P8b-L3: tên tiền tố mới và cũ đúng như 02c (cũ giữ vĩnh viễn)", () => {
    expect(RECEIVE_BATCHES_DRAFT_PREFIX).toBe("cave_draft_receive_batches");
    expect(LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX).toBe("cave_draft_nhap_lo");
    expect(LEGACY_DRAFT_KEY).toBe(LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX);
    expect(legacyDraftKey(7)).toBe("cave_draft_nhap_lo:7");
  });

  it("P8b-L3: mở form → nháp session khoá cũ của CHÍNH người đó được chuyển sang khoá mới, bỏ rate, xoá khoá cũ", () => {
    session.setItem(legacyDraftKey(7), JSON.stringify({ ...draftWithRate, idempotencyKey: "key-cu-cua-7" }));
    const back = loadDraft(7);
    expect(back).not.toBeNull();
    expect(back!.supplierId).toBe(3);
    expect(back!.lines[0].item_code).toBe("CA-THU");
    expect("rate" in back!.lines[0]).toBe(false);
    expect(resolveIdempotencyKey(7, () => "key-moi")).toBe("key-cu-cua-7");
    expect(session.getItem(legacyDraftKey(7))).toBeNull();
    expect(session.getItem(draftKey(7))).not.toBeNull();
    expect(session.dump()).not.toContain("81234");
    expect(local.length).toBe(0);
  });

  it("P8b-L3: nháp khoá cũ của người khác không bị đọc hay chuyển; vẫn bị dọn khi đăng xuất", () => {
    session.setItem(legacyDraftKey(8), JSON.stringify(draftWithRate));
    expect(loadDraft(7)).toBeNull();
    expect(session.getItem(draftKey(8))).toBeNull();
    expect(session.getItem(legacyDraftKey(8))).not.toBeNull();
    clearAllDrafts();
    expect(session.getItem(legacyDraftKey(8))).toBeNull();
  });

  it("P8b-L3: khoá mới đã có thì giữ khoá mới, chỉ xoá khoá cũ (không ghi đè)", () => {
    saveDraft(7, { ...draftWithRate, receivedDate: "2026-10-01" });
    session.setItem(legacyDraftKey(7), JSON.stringify({ ...draftWithRate, receivedDate: "2026-01-01" }));
    migrateLegacyDraft(7);
    expect(loadDraft(7)!.receivedDate).toBe("2026-10-01");
    expect(session.getItem(legacyDraftKey(7))).toBeNull();
  });

  it("P8b-L3: khoá cũ hỏng → xoá, không ném lỗi, không tạo khoá mới", () => {
    session.setItem(legacyDraftKey(7), "{hỏng");
    expect(() => migrateLegacyDraft(7)).not.toThrow();
    expect(session.getItem(legacyDraftKey(7))).toBeNull();
    expect(session.getItem(draftKey(7))).toBeNull();
  });

  it("P8b-L3: khoá cũ ở localStorage (có giá mua) chỉ bị xoá, không được chuyển sang khoá mới", () => {
    local.setItem(LEGACY_DRAFT_KEY, JSON.stringify({ ...draftWithRate }));
    expect(loadDraft(7)).toBeNull();
    expect(session.length).toBe(0);
    purgeLegacyDraft();
    expect(local.getItem(LEGACY_DRAFT_KEY)).toBeNull();
    expect(local.dump()).not.toContain("81234");
  });

  it("P8b-L3: xoá nháp sau khi gửi thành công xoá cả khoá cũ còn sót của người đó", () => {
    session.setItem(legacyDraftKey(7), JSON.stringify(draftWithRate));
    saveDraft(7, draftWithRate);
    clearDraft(7);
    expect(session.getItem(draftKey(7))).toBeNull();
    expect(session.getItem(legacyDraftKey(7))).toBeNull();
  });

  it("P8b-L3: clearAllDrafts dọn vĩnh viễn cả hai tiền tố ở cả local lẫn session, giữ khoá khác", () => {
    local.setItem(LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX, "x");
    local.setItem(`${RECEIVE_BATCHES_DRAFT_PREFIX}:1`, "x");
    session.setItem(`${LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX}:1`, "x");
    session.setItem(`${RECEIVE_BATCHES_DRAFT_PREFIX}:2`, "x");
    local.setItem("khoa_khac", "giu");
    clearAllDrafts();
    expect(local.length).toBe(1);
    expect(local.getItem("khoa_khac")).toBe("giu");
    expect(session.length).toBe(0);
  });
});
