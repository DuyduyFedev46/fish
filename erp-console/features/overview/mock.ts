// Mock module overview — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1.
// GET /api/dashboard/summary/: token hỏng → 401; còn lại trả seed chung (shared/lib/dashboardSummary.mock.ts),
// giá vốn theo quyền của người đăng nhập. Thử lỗi: localStorage cave_erp_mock_dashboard = "fail" | "empty".
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { mockExpiredOpenCount } from "@/features/inventory/mock";

export function mockOverview(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  return dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
}

export function mockAttention(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const isChu = me.groups.includes("chu") || me.username === "loc";
  const canConfirm = isChu || me.permissions.includes("delivery.confirm_with_customer") || me.groups.includes("cskh") || me.groups.includes("quan_ly");
  const canDecide = isChu || me.permissions.includes("delivery.decide_unconfirmed") || me.groups.includes("quan_ly");
  const canPrint = isChu || me.permissions.includes("delivery.print_label") || me.groups.includes("nv_kho") || me.groups.includes("quan_ly");

  // P8 Lô 5: quyền inventory.cancel_expired_batch (Chủ) — 02b §5.4: thêm khoá expired_batches_open, tính vào điều kiện 403.
  const canProcessExpired = isChu;

  if (!canConfirm && !canDecide && !canPrint && !canProcessExpired) {
    return { status: 403, body: { detail: "Không có quyền xem mục cần chú ý." } };
  }

  const res: Record<string, number> = {};
  if (canConfirm) {
    res.cskh_queue_waiting = 0;
    res.refund_calls_open = 0;
  }
  if (canDecide) {
    res.cskh_escalated = 0;
    res.cskh_auto_cancel_blocked = 0;
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

