// Mock module overview — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1.
// GET /api/dashboard/summary/: token hỏng → 401; còn lại trả seed chung (shared/lib/dashboardSummary.mock.ts),
// giá vốn theo quyền của người đăng nhập. Thử lỗi: localStorage cave_erp_mock_dashboard = "fail" | "empty".
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { mockExpiredOpenCount } from "@/features/inventory/mock";
import { mockOrdersOverviewSlice } from "@/features/orders/mock";
import { ROLE } from "@/shared/lib/roles";

export function mockOverview(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const res = dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
  if (res.status !== 200) return res;
  const body = withShopOrderCodes(res.body) as { kpis?: Record<string, unknown>; recent_orders?: unknown[] };
  // S6-AC5/AC6: khi kho đơn mock đã có bộ mẫu hoặc đã nhận kết quả giao hàng, số đơn chưa xong và danh sách đơn gần đây lấy từ đó.
  const slice = mockOrdersOverviewSlice();
  if (!slice || !body.kpis) return { ...res, body };
  return { ...res, body: { ...body, kpis: { ...body.kpis, pending_orders: slice.pending }, recent_orders: slice.recent } };
}

/**
 * Seed chung (shared/lib/dashboardSummary.mock.ts) còn mã đơn kiểu cũ "DH-240924-011"; BE thật trả "SO260930-753F06" (ED-08-AC2).
 * Đổi tiền tố ngay tại mock của màn này để thử đúng dạng mã thật mà không phải sửa seed dùng chung.
 */
function withShopOrderCodes(body: unknown): unknown {
  const b = body as { recent_orders?: { code: string }[] };
  if (!Array.isArray(b?.recent_orders)) return body;
  return { ...b, recent_orders: b.recent_orders.map((o) => ({ ...o, code: o.code.replace(/^DH-/, "SO") })) };
}

export function mockAttention(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const isOwner = me.groups.includes(ROLE.owner) || me.username === "loc";
  const canConfirm = isOwner || me.permissions.includes("delivery.confirm_with_customer") || me.groups.includes(ROLE.customerService) || me.groups.includes(ROLE.manager);
  const canDecide = isOwner || me.permissions.includes("delivery.decide_unconfirmed") || me.groups.includes(ROLE.manager);
  const canPrint = isOwner || me.permissions.includes("delivery.print_label") || me.groups.includes(ROLE.warehouseStaff) || me.groups.includes(ROLE.manager);

  // P8 Lô 5: quyền inventory.cancel_expired_batch (Chủ) — 02b §5.4: thêm khoá expired_batches_open, tính vào điều kiện 403.
  const canProcessExpired = isOwner;

  if (!canConfirm && !canDecide && !canPrint && !canProcessExpired) {
    return { status: 403, body: { detail: "Không có quyền xem mục cần chú ý." } };
  }

  const res: Record<string, number> = {};
  if (canConfirm) {
    res.confirmation_queue_waiting = 0;
    res.refund_calls_open = 0;
  }
  if (canDecide) {
    res.confirmation_escalated = 0;
    res.confirmation_auto_cancel_blocked = 0;
  }
  if (canPrint) {
    res.labels_not_printed = 0;
    res.labels_to_void = 0;
  }
  if (canProcessExpired) {
    res.expired_batches_open = mockExpiredOpenCount();
  }
  return { status: 200, body: res };
}

