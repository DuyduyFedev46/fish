// API module permissions (ED-40) — contract THỰC TẾ BE B4 (02b §3 B4, R16): `/api/staff/groups/…`.
// (Story ghi `/api/permissions/matrix/`; BE thật đặt dưới `/api/staff/groups/`, FE theo BE.)
// Mọi endpoint đòi `accounts.manage_staff`; GHI chỉ Chủ/superuser (BE trả 403 với người khác, kể cả có manage_staff).
// Lỗi nghiệp vụ trả {detail, code}: UI hiện NGUYÊN VĂN `detail`. Không có giá vốn hay dữ liệu cá nhân khách trong các hàm này.

import { apiFetch } from "@/shared/lib/http";
import { mockPermissionsApi } from "./mock";
import type { GroupDetail, GroupPreviewBody, GroupSaveBody, GroupSummary, ScopePreview } from "./types";

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
 * PUT /api/staff/groups/<code>/capabilities/ — lưu việc và/hoặc phạm vi của nhóm trong MỘT lần, trả chi tiết nhóm mới (có `version` mới).
 * `version` lấy từ lần GET gần nhất (PV-10): người khác vừa đổi nhóm → 409 GROUP_CHANGED. Mở rộng dữ liệu khách mà thiếu
 * `confirm_customer_data_widening: true` → 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED kèm `impact` (PV-09).
 * Việc có `requires` đổi cùng yêu cầu với việc gốc (nếu không BE trả 400 CAPABILITY_REQUIRES). Tất cả hoặc không gì cả.
 * Chỉ Chủ hoặc superuser ghi được (BE trả 403 với người khác, kể cả có manage_staff).
 */
export function saveGroupChanges(code: string, body: GroupSaveBody): Promise<GroupDetail> {
  return apiFetch<GroupDetail>(`${BASE}${encodeURIComponent(code)}/capabilities/`, { method: "PUT", body, mock: mock() });
}

/**
 * POST /api/staff/groups/<code>/permissions-preview/ — xem trước ai bị ảnh hưởng, KHÔNG ghi gì (PV-09, PV-10 phía BE).
 * Lô F1: BE chưa có endpoint này và PUT mới (version, scopes) tới Lô 5, nên hai hàm chỉ chạy được ở bản mock; KHÔNG deploy FE này trước Lô 5.
 */
export function previewGroupChanges(code: string, body: GroupPreviewBody): Promise<ScopePreview> {
  return apiFetch<ScopePreview>(`${BASE}${encodeURIComponent(code)}/permissions-preview/`, { method: "POST", body, mock: mock() });
}
