import { describe, it, expect, beforeEach, vi } from "vitest";
import { submitNhapLo, getNhapLoDraft, saveNhapLoDraft, clearNhapLoDraft } from "./api";
import { mockSubmitNhapLo, mockCancelPurchaseReceipt } from "./mock";
import { NhapLoPayload } from "./types";

const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
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
    (globalThis as any).localStorage = storageMock;
    storageMock.clear();
    vi.restoreAllMocks();
  });

  it("DW-17-AC3: saves and restores draft in localStorage", () => {
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

    saveNhapLoDraft(draft);
    const restored = getNhapLoDraft();
    expect(restored).not.toBeNull();
    expect((restored as any)?.supplierId).toBe(1);
    expect((restored as any)?.lines.length).toBe(1);
    expect((restored as any)?.lines[0].qty).toBe("50");

    clearNhapLoDraft();
    expect(getNhapLoDraft()).toBeNull();
  });

  it("DW-17-AC1: mockSubmitNhapLo generates batch DRAFT and receipt SUBMITTED", () => {
    const payload: NhapLoPayload = {
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

    const res = mockSubmitNhapLo({
      method: "POST",
      path: "/api/purchasing/receipts/nhap-lo/",
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

  it("DW-17-AC1 & AC8: submitNhapLo calls API and handles success response", async () => {
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

    const payload: NhapLoPayload = {
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

    const res = await submitNhapLo(payload);
    expect(res.receipt.id).toBe(99);
    expect(res.receipt.status).toBe("SUBMITTED");
    expect(res.batches.length).toBe(1);
    expect(res.batches[0].batch_id).toBe("CA-THU-260929-101");
  });

  it("DW-18-AC1 & AC2: mockCancelPurchaseReceipt cancels receipt and batches", () => {
    // Tạo 1 phiếu nhập trước trong mockReceiptsStore
    const payload: NhapLoPayload = {
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

    const submitRes = mockSubmitNhapLo({
      method: "POST",
      path: "/api/purchasing/receipts/nhap-lo/",
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

