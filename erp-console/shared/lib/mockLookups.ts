// Mock cho shared/lib/lookups.ts (chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1). Dữ liệu GIẢ, không có tên/SĐT/địa chỉ khách.
// Cố tình kèm `landed_unit_cost` ở lô để vitest/e2e chứng minh thẻ KHÔNG hiện giá vốn.
import type { MockResponse } from "./http";
import type { LookupKind } from "./lookups";

const DATA: Record<LookupKind, Record<string, unknown>> = {
  batch: {
    id: 7, batch_id: "CA01-261001-AB12C", item: 3, item_code: "CA01", item_name: "Cá thu một nắng",
    qty_available: "18.500", qty_reserved: "2.000", received_date: "2026-10-01", expiry_date: "2026-10-08",
    warehouse_name: "Kho lạnh 1", status: "SELLING", landed_unit_cost: "123456.00",
  },
  item: { id: 3, code: "CA01", name: "Cá thu một nắng", group_name: "Cá biển", item_type: "SIMPLE", is_active: true },
  delivery: {
    id: 5, code: "GH261001-0007", status: "PREPARING", order: { id: 102, code: "SO261001-A1B2C3" },
    lines_summary: "Cá thu 2 kg", total_kg: "2.000", created_at: "2026-10-01T03:00:00Z",
    recipient_name: "Người nhận mẫu", recipient_phone: "0900000123",
  },
  order: {
    id: 102, code: "SO261001-A1B2C3", status: "PAID", total_amount: "540000", created_at: "2026-10-01T02:00:00Z",
    customer: { name: "Khách mẫu", phone: "0900000456", address: "Địa chỉ mẫu" },
  },
};

export function mockLookup(kind: LookupKind, id: number | string): MockResponse {
  if (String(id) === "404") return { status: 404, body: { detail: "Không tìm thấy." } };
  return { status: 200, body: { ...DATA[kind], id } };
}
