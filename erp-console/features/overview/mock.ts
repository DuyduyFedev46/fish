// Mock module overview — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1.
// GET /api/dashboard/summary/: token hỏng → 401; còn lại trả seed chung (shared/lib/dashboardSummary.mock.ts),
// giá vốn theo quyền của người đăng nhập. Thử lỗi: localStorage cave_erp_mock_dashboard = "fail" | "empty".
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { dashboardSummaryMockResponse } from "@/shared/lib/dashboardSummary.mock";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";

export function mockOverview(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  return dashboardSummaryMockResponse({
    username: me.username,
    can_cost: me.can_view_cost,
    can_view_dashboard: me.permissions.includes("reports.view_dashboard"),
  });
}
