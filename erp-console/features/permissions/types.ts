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
  /** PV-10: phiên bản cấu hình của nhóm (chuỗi). Gửi lại khi lưu để BE phát hiện người khác vừa sửa (409). */
  version: string;
  /** Giá trị phạm vi đã lưu của 6 đối tượng sửa được (orders, deliveries, confirmation, returns, receipts, customers). */
  data_scope_values: Record<string, string>;
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

/** Một lựa chọn của ô phạm vi; `rank` càng lớn càng rộng. */
export type ScopeOption = { value: string; label: string; rank: number };

/** Một dòng của khối "Phạm vi dữ liệu" (8 dòng D1..D8 theo thứ tự `orders, invoices, deliveries, confirmation, returns, receipts, customers, audit_log`). */
export type DataScopeRow = {
  key: string;
  label: string;
  value: string;
  /** false: chỉ đọc (Hoá đơn bán theo Đơn hàng, Nhật ký, hoặc nhóm Chủ). */
  editable: boolean;
  /** Đối tượng có tên/SĐT/địa chỉ khách: mở rộng phải xác nhận. */
  customer_data: boolean;
  /** Mã việc ở registry mà tắt thì ô mờ; `null` khi gốc là quyền ngoài registry (hoặc việc chưa có tới Lô 3). */
  gate_capability: string | null;
  /** Khác null: ô mờ, chữ này giải thích. */
  inactive_reason: string | null;
  note: string | null;
  options: ScopeOption[];
};

/** GET /api/staff/groups/<code>/ (cũng là thân trả về của PUT …/capabilities/). */
export type GroupDetail = Omit<GroupSummary, "members"> & {
  members: GroupMember[];
  registry: RegistryItem[];
  data_scopes: DataScopeRow[];
  timeline: GuidanceTimelineEntry[];
};

/** PUT /api/staff/groups/<code>/capabilities/ — khoá = key việc, giá trị = bật (true) / tắt (false). */
export type CapabilityChanges = Record<string, boolean>;

/** Thay đổi phạm vi: khoá = mã đối tượng, giá trị = mã giá trị mới. */
export type ScopeChanges = Record<string, string>;

/** Thân PUT …/capabilities/ (PV-08, PV-10): `version` bắt buộc; `capabilities` và `scopes` chỉ gồm khoá đã đổi. */
export type GroupSaveBody = {
  version: string;
  capabilities?: CapabilityChanges;
  scopes?: ScopeChanges;
  confirm_customer_data_widening?: true;
};

/** Thân POST …/permissions-preview/ (PV-09): như PUT, không cần `version`/xác nhận. */
export type GroupPreviewBody = { capabilities?: CapabilityChanges; scopes?: ScopeChanges };

/** Kết quả xem trước (PV-09, PV-10 phía BE). Chỉ có tên NHÂN VIÊN, không có dữ liệu khách. */
export type ScopePreview = {
  widens_customer_data: boolean;
  widened: { key: string; from: string; to: string }[];
  affected_members: { id: number; display_name: string }[];
  affected_count: number;
  message: string;
  already_wider_elsewhere: { id: number; display_name: string; via_group: string; key: string }[];
  narrowed: { key: string; from: string; to: string; rows_losing_access: number }[];
};
