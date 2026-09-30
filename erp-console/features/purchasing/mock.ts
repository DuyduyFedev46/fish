import type { MockRequest } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import type { NhapLoPayload, NhapLoResponse, Supplier } from "./types";

export const MOCK_SUPPLIERS: Supplier[] = [
  { id: 1, name: "Đầu mối Cảng cá Phan Thiết", phone: "0901234567", is_active: true },
  { id: 2, name: "Vựa cá Lagi (Anh Ba)", phone: "0912345678", is_active: true },
  { id: 3, name: "Hợp tác xã Đánh bắt Vũng Tàu", phone: "0987654321", is_active: true },
];

export function mockListSuppliers(_req: MockRequest): { status: number; body: { results: Supplier[] } } {
  return {
    status: 200,
    body: { results: MOCK_SUPPLIERS },
  };
}

let mockBatchSeq = 100;
export const mockReceiptsStore = new Map<number, NhapLoResponse>();

export function mockSubmitNhapLo(req: MockRequest): { status: number; body: NhapLoResponse | { detail: string; code: string } } {
  let body = req.body as NhapLoPayload | undefined;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      // ignore
    }
  }
  if (!body || !body.lines || body.lines.length === 0) {
    return {
      status: 400,
      body: { detail: "Danh sách mặt hàng nhập không được rỗng.", code: "BR-MH-02" },
    };
  }

  const receiptId = Math.floor(Math.random() * 900) + 100;
  const receivedDate = body.received_date || todayInVietnam();

  const batches = body.lines.map((line) => {
    mockBatchSeq += 1;
    const days = line.shelf_life_days || 60;
    const exp = todayInVietnam(new Date(Date.now() + days * 86400 * 1000));
    return {
      batch_id: `${line.item_code}-${receivedDate.replace(/-/g, "").slice(2)}-${mockBatchSeq}`,
      status: "DRAFT",
      expiry_date: exp,
      qty_available: line.qty,
    };
  });

  const resp: NhapLoResponse = {
    receipt: {
      id: receiptId,
      supplier: body.supplier,
      warehouse: body.warehouse || 1,
      received_date: receivedDate,
      status: "SUBMITTED",
      created_by: 1,
      lines: body.lines.map((l, idx) => ({
        id: idx + 1,
        item: idx + 1,
        item_code: l.item_code,
        qty: l.qty,
        shelf_life_days: l.shelf_life_days,
        batch: idx + 1,
      })),
    },
    batches,
  };

  mockReceiptsStore.set(receiptId, resp);

  return { status: 201, body: resp };
}

export function mockCancelPurchaseReceipt(req: MockRequest): {
  status: number;
  body: import("./types").CancelPurchaseReceiptResponse | { detail: string; code: string };
} {
  const match = req.path.match(/\/receipts\/(\d+)\/cancel\/?/);
  const receiptId = match ? Number(match[1]) : 0;
  if (!receiptId) {
    return {
      status: 400,
      body: { detail: "Mã phiếu nhập không hợp lệ.", code: "BR-MH-07" },
    };
  }

  const existing = mockReceiptsStore.get(receiptId);
  if (existing) {
    existing.receipt.status = "CANCELLED";
    existing.batches = existing.batches.map((b) => ({
      ...b,
      status: "CANCELLED",
    }));
  }

  return {
    status: 200,
    body: {
      id: receiptId,
      status: "CANCELLED",
    },
  };
}
