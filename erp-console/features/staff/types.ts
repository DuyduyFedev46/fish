// Kiểu dữ liệu module staff — khớp contract THỰC TẾ /api/staff/ (BE L5, 03-dev-notes.md "Lô L5 — S41, S42").

/** Thao tác người ĐANG XEM làm được trên dòng này — BE tính cả luật lẫn quyền; FE chỉ đọc để hiện nút. */
export type StaffAction = "edit" | "set_groups" | "reset_password" | "deactivate" | "reactivate";

/** Một dòng GET /api/staff/ (cũng là body trả về của GET/POST/PATCH một người). Không có key mật khẩu/token. */
export type StaffMember = {
  id: number;
  username: string;
  display_name: string;
  /** "" khi user chưa có StaffProfile (vd admin). */
  phone: string;
  /** Thứ tự cố định owner, manager, warehouse_staff, delivery_staff. */
  groups: string[];
  is_active: boolean;
  /** ISO giờ VN hoặc null. */
  last_login: string | null;
  available_actions: StaffAction[];
};

/** Bộ lọc danh sách: đang làm (`?is_active=true`), đã nghỉ (`false`), tất cả (bỏ tham số). */
export type StaffFilter = "active" | "inactive" | "all";

/** POST /api/staff/ */
export type StaffCreateInput = {
  username: string;
  display_name: string;
  phone: string;
  groups: string[];
  password: string;
};

/** PATCH /api/staff/{id}/ */
export type StaffProfileInput = { display_name?: string; phone?: string };

/** PUT /api/staff/{id}/groups/ → 200 */
export type SetGroupsResult = { groups: string[]; added: string[]; removed: string[] };

/** Tab danh sách: đang làm / đã nghỉ / tất cả (lọc phía máy trên MỘT lần tải `all`). */
export type StaffTab = "active" | "inactive" | "all";

/** Một phiếu giao đang trên tay nhân viên (chỉ mã + trạng thái + giờ nhận; KHÔNG tên/SĐT/địa chỉ khách). */
export type StaffDelivering = {
  id: number;
  code: string;
  status_label: string;
  started_at: string | null;
};

/** Một dòng nhật ký hoạt động của nhân viên (GET /api/audit-logs/?actor=<id>). Chỉ trường cần hiện. */
export type StaffActivityRow = {
  id: number;
  action: string;
  object_repr: string | null;
  note: string | null;
  created_at: string;
};

export type StaffActivity = { rows: StaffActivityRow[]; total: number };
