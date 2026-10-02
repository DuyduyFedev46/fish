// Kiểu dữ liệu module permissions (ED-40) — khớp contract THỰC TẾ BE B4 (`/api/staff/groups/…`, 02b §3 B4, R16).
// Không có giá vốn, mật khẩu hay dữ liệu cá nhân khách trong các kiểu này; chỉ có tên nhân viên (người trong nhóm).

import type { GuidanceTimelineEntry } from "@/features/guidance/types";

/** Trạng thái một việc đối với một nhóm. `partial` = nhóm có một phần quyền của việc (vd cấu hình tay ở trang quản trị). */
export type CapabilityState = "on" | "off" | "partial";

/** Một việc trong registry (chỉ có ở chi tiết nhóm). */
export type RegistryItem = {
  key: string;
  label: string;
  section: string;
  /** Chỉ nhóm Chủ được bật (T9, BR-PQ-32): ô khoá ở nhóm khác. */
  owner_only: boolean;
  /** Các việc phải đang bật thì việc này mới dùng được; hai bên đổi cùng lúc. */
  requires: string[];
};

/** Dòng GET /api/staff/groups/ (danh sách, KHÔNG kèm registry). */
export type GroupSummary = {
  id: number;
  /** Mã nhóm (`owner`, `manager`, …) — dùng trong URL và API. */
  code: string;
  label: string;
  member_count: number;
  /** Người ĐANG LÀM trong nhóm. */
  members: { id: number; display_name: string }[];
  can_view_cost: boolean;
  /** ISO giờ VN hoặc null (chưa đổi lần nào). */
  last_changed_at: string | null;
  last_changed_by: string | null;
  capabilities: Record<string, CapabilityState>;
};

/** Thành viên ở chi tiết nhóm (gồm cả người đã nghỉ). */
export type GroupMember = {
  id: number;
  display_name: string;
  username: string;
  /** Mã các nhóm khác của người này. */
  other_groups: string[];
  is_active: boolean;
  added_at: string | null;
};

/** Phạm vi dữ liệu (chỉ đọc): chuỗi hiển thị do BE dựng. */
export type GroupScopes = { orders: string; deliveries: string; customers: string };

/** GET /api/staff/groups/<code>/ (cũng là thân trả về của PUT …/capabilities/). */
export type GroupDetail = Omit<GroupSummary, "members"> & {
  members: GroupMember[];
  registry: RegistryItem[];
  scopes: GroupScopes;
  timeline: GuidanceTimelineEntry[];
};

/** PUT /api/staff/groups/<code>/capabilities/ — khoá = key việc, giá trị = bật (true) / tắt (false). */
export type CapabilityChanges = Record<string, boolean>;
