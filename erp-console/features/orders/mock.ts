// Mock module orders — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Cùng seed với overview/inventory
// (shared/lib/dashboardSummary.mock.ts) nên số liệu 3 màn luôn khớp nhau như khi gọi thật.
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";

export function mockOrders(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  return dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
}
