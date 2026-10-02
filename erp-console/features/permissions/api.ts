// API module permissions (ED-40) — contract THỰC TẾ BE B4 (02b §3 B4, R16): `/api/staff/groups/…`.
// (Story ghi `/api/permissions/matrix/`; BE thật đặt dưới `/api/staff/groups/`, FE theo BE.)
// Mọi endpoint đòi `accounts.manage_staff`; GHI chỉ Chủ/superuser (BE trả 403 với người khác, kể cả có manage_staff).
// Lỗi nghiệp vụ trả {detail, code}: UI hiện NGUYÊN VĂN `detail`. Không có giá vốn hay dữ liệu cá nhân khách trong các hàm này.

import { apiFetch } from "@/shared/lib/http";
import { mockPermissionsApi } from "./mock";
import type { CapabilityChanges, GroupDetail, GroupSummary } from "./types";

const BASE = "/api/staff/groups/";
const mock = () => (process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockPermissionsApi : undefined);

/** GET /api/staff/groups/ — mọi nhóm kèm trạng thái từng việc (không kèm registry). */
export function listGroups(signal?: AbortSignal): Promise<GroupSummary[]> {
  return apiFetch<GroupSummary[]>(BASE, { signal, mock: mock() });
}

/** GET /api/staff/groups/<code>/ — chi tiết nhóm: thành viên, registry các việc, phạm vi dữ liệu, dòng thời gian. */
export function getGroup(code: string, signal?: AbortSignal): Promise<GroupDetail> {
  return apiFetch<GroupDetail>(`${BASE}${encodeURIComponent(code)}/`, { signal, mock: mock() });
}

/**
 * PUT /api/staff/groups/<code>/capabilities/ — bật/tắt một hay nhiều việc, trả chi tiết nhóm mới.
 * Việc có `requires` đổi cùng yêu cầu với việc gốc (nếu không BE trả 400 CAPABILITY_REQUIRES). Tất cả hoặc không gì cả.
 */
export function setGroupCapabilities(code: string, changes: CapabilityChanges): Promise<GroupDetail> {
  return apiFetch<GroupDetail>(`${BASE}${encodeURIComponent(code)}/capabilities/`, {
    method: "PUT",
    body: { capabilities: changes },
    mock: mock(),
  });
}
