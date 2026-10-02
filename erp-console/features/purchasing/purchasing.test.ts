import { describe, it, expect, beforeEach, vi } from "vitest";
import { submitReceiveBatches } from "./api";
import { clearDraft, loadDraft, saveDraft } from "./components/draftStorage";
import { mockSubmitReceiveBatches, mockCancelPurchaseReceipt } from "./mock";
import { ReceiveBatchesPayload } from "./types";

// Nháp Nhập lô nằm ở sessionStorage theo userId (SR-07), không phải localStorage dùng chung nữa.
const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
    get length() {
      return Object.keys(store).length;
    },
    key: (i: number) => Object.keys(store)[i] ?? null,
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => {
      store[key] = val;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

describe("Purchasing feature tests (DW-17)", () => {
  beforeEach(() => {
    (globalThis as any).window = { sessionStorage: storageMock, localStorage: storageMock };
    storageMock.clear();
    vi.restoreAllMocks();
  });

  it("DW-17-AC3: lưu và nạp lại nháp theo người dùng (sessionStorage), giá mua không được lưu", () => {
    const draft = {
      supplierId: 1,
      receivedDate: "2026-09-29",
      lines: [
        {
          item_code: "CA-THU",
          qty: "50",
          rate: "180000",
          shelf_life_days: 3,
        },
      ],
    };

    saveDraft(7, draft);
    const restored = loadDraft(7);
    expect(restored).not.toBeNull();
    expect(restored?.supplierId).toBe(1);
    expect(restored?.lines.length).toBe(1);
    expect(restored?.lines[0].qty).toBe("50");
    expect("rate" in (restored?.lines[0] ?? {})).toBe(false);
    expect(loadDraft(8)).toBeNull();

    clearDraft(7);
    expect(loadDraft(7)).toBeNull();
  });

  it("DW-17-AC1: mockSubmitReceiveBatches generates batch DRAFT and receipt SUBMITTED", () => {
    const payload: ReceiveBatchesPayload = {
      supplier: 1,
      received_date: "2026-09-29",
      idempotency_key: "test-idem-key-123",
      lines: [
        {
          item_code: "CA-BOP",
          qty: "35.5",
          rate: "220000",
          shelf_life_days: 4,
        },
        {
          item_code: "CA-THU",
          qty: "40",
          rate: "180000",
          shelf_life_days: 3,
        },
      ],
    };

    const res = mockSubmitReceiveBatches({
      method: "POST",
      path: "/api/purchasing/receipts/receive-batches/",
      body: payload,
      token: "mock-token",
    });

    expect(res.status).toBe(201);
    const body = res.body as any;
    expect(body.receipt).toBeDefined();
    expect(body.receipt.status).toBe("SUBMITTED");
    expect(body.batches.length).toBe(2);
    expect(body.batches[0].status).toBe("DRAFT");
    expect(body.batches[0].qty_available).toBe("35.5");
    expect(body.batches[1].status).toBe("DRAFT");
    expect(body.batches[1].qty_available).toBe("40");
  });

  it("Lô bổ sung A #22: mock từ chối giá mua 0, âm hoặc thiếu bằng 400 theo từng dòng; dòng đúng không bị đánh lỗi", () => {
    const send = (rates: Array<string | undefined>) =>
      mockSubmitReceiveBatches({
        method: "POST",
        path: "/api/purchasing/receipts/receive-batches/",
        body: { supplier: 1, lines: rates.map((rate) => ({ item_code: "CA-THU", qty: "5", rate, shelf_life_days: null })) },
        token: "mock-token",
      });
    for (const bad of ["0", "0.00", "-5", "", undefined]) {
      const res = send(["180000", bad]);
      expect(res.status).toBe(400);
      const lines = (res.body as unknown as { lines: Array<{ rate?: string[] }> }).lines;
      expect(lines[0]).toEqual({});
      expect(lines[1].rate).toEqual(["Giá mua phải lớn hơn 0."]);
    }
    expect(send(["180000"]).status).toBe(201);
  });

  it("DW-17-AC1 & AC8: submitReceiveBatches calls API and handles success response", async () => {
    const mockResponse = {
      receipt: {
        id: 99,
        supplier: 1,
        warehouse: 1,
        received_date: "2026-09-29",
        status: "SUBMITTED",
        created_by: 1,
        lines: [],
      },
      batches: [
        {
          batch_id: "CA-THU-260929-101",
          status: "DRAFT",
          expiry_date: "2026-10-02",
          qty_available: 50,
        },
      ],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve(mockResponse),
        })
      )
    );

    const payload: ReceiveBatchesPayload = {
      supplier: 1,
      received_date: "2026-09-29",
      lines: [
        {
          item_code: "CA-THU",
          qty: "50",
          rate: "180000",
        },
      ],
    };

    const res = await submitReceiveBatches(payload);
    expect(res.receipt.id).toBe(99);
    expect(res.receipt.status).toBe("SUBMITTED");
    expect(res.batches.length).toBe(1);
    expect(res.batches[0].batch_id).toBe("CA-THU-260929-101");
  });

  it("DW-18-AC1 & AC2: mockCancelPurchaseReceipt cancels receipt and batches", () => {
    // Tạo 1 phiếu nhập trước trong mockReceiptsStore
    const payload: ReceiveBatchesPayload = {
      supplier: 1,
      received_date: "2026-09-29",
      lines: [
        {
          item_code: "CA-THU",
          qty: "30",
          rate: "150000",
        },
      ],
    };

    const submitRes = mockSubmitReceiveBatches({
      method: "POST",
      path: "/api/purchasing/receipts/receive-batches/",
      body: payload,
      token: "mock-token",
    });
    const receiptId = (submitRes.body as any).receipt.id;

    const cancelRes = mockCancelPurchaseReceipt({
      method: "POST",
      path: `/api/purchasing/receipts/${receiptId}/cancel/`,
      token: "mock-token",
    });

    expect(cancelRes.status).toBe(200);
    const body = cancelRes.body as any;
    expect(body.id).toBe(receiptId);
    expect(body.status).toBe("CANCELLED");
  });

  it("DW-18-AC1: cancelPurchaseReceipt calls POST API and returns cancelled status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ id: 88, status: "CANCELLED" }),
        })
      )
    );

    const { cancelPurchaseReceipt } = await import("./api");
    const res = await cancelPurchaseReceipt(88);
    expect(res.id).toBe(88);
    expect(res.status).toBe("CANCELLED");
  });
});
