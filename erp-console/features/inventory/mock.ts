// Mock module inventory — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Cùng seed với overview/orders.
// `unit_cost` chỉ có khi người đăng nhập có inventory.view_costprice (loc) — y như BE (S8-AC2/AC3).
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";

export function mockInventory(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  return dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
}
