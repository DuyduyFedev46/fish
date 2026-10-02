// Mock Sổ nhập xuất (R6) — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Dữ liệu dòng nằm ở features/inventory/mock.ts
// (một kho chung với danh sách lô, nên thao tác ở lô hiện ngay ở sổ). Tại đây chỉ có bộ lọc và phân trang như BE.
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dateKeyInVietnam } from "@/shared/lib/format";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { MOCK_MOVEMENT_TYPES, mockLedgerRows } from "@/features/inventory/mock";

const PAGE_SIZE = 20;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const badFilter = (detail: string): MockResponse => ({ status: 400, body: { code: "INVALID_FILTER", detail } });

/** GET /api/inventory/ledger/ — mới nhất trước, 20 dòng/trang. Lọc: batch (id), movement_type (nhiều loại, dấu phẩy), warehouse (id), item, date_from, date_to. */
export function mockLedgerList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes("inventory.view_stockledgerentry")) {
    return { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
  }
  const q = new URLSearchParams(req.path.split("?")[1] || "");
  const batch = q.get("batch");
  const warehouse = q.get("warehouse");
  const types = (q.get("movement_type") || "").split(",").filter(Boolean);
  const from = q.get("date_from") || "";
  const to = q.get("date_to") || "";
  if (batch && !/^\d+$/.test(batch)) return badFilter("Bộ lọc lô không hợp lệ.");
  if (warehouse && !/^\d+$/.test(warehouse)) return badFilter("Bộ lọc kho không hợp lệ.");
  if (types.some((t) => !MOCK_MOVEMENT_TYPES.includes(t))) return badFilter("Loại nhập xuất không hợp lệ.");
  if ((from && !DATE_RE.test(from)) || (to && !DATE_RE.test(to))) return badFilter("Ngày không hợp lệ.");
  const rows = mockLedgerRows().filter((e) => {
    const day = dateKeyInVietnam(e.created_at);
    return (
      (!batch || String(e.batch) === batch) &&
      (!warehouse || String(e.warehouse) === warehouse) &&
      (!types.length || types.includes(e.movement_type)) &&
      (!from || day >= from) &&
      (!to || day <= to)
    );
  });
  const page = Math.max(1, Number(q.get("page") || 1) || 1);
  const start = (page - 1) * PAGE_SIZE;
  const base = "/api/inventory/ledger/";
  return {
    status: 200,
    body: {
      count: rows.length,
      next: start + PAGE_SIZE < rows.length ? `${base}?page=${page + 1}` : null,
      previous: page > 1 ? `${base}?page=${page - 1}` : null,
      results: rows.slice(start, start + PAGE_SIZE),
    },
  };
}
