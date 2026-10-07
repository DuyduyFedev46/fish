// Kiểu dữ liệu module audit — khớp contract THỰC TẾ GET /api/audit-logs/ (BE accounts/audit/serializers.py).

export type AuditActorKind = "user" | "system" | "ai";

export type AuditLogRow = {
  id: number;
  actor_kind: AuditActorKind;
  /** Dòng AI: "ai:<tên đăng nhập>" (S03-AC2); dòng người: tên đăng nhập; dòng hệ thống: "system". */
  actor_display: string;
  /** Chỉ có ở dòng AI — mã (số) người dùng mà AI làm thay. BE KHÔNG trả đối tượng. */
  ai_actor: number | null;
  /** Động từ hành động (vd "create", "update", "execute_command", "confirm_proposal"). */
  action: string;
  model_name: string;
  object_id: number | null;
  object_repr: string | null;
  /** Thay đổi — BE đã bỏ khoá giá vốn khi người xem không có quyền; FE vẫn tự bỏ lần nữa (xem changeSummary). */
  changes: Record<string, unknown> | null;
  note: string | null;
  proposal_ref: string | null;
  created_at: string;
};

export type AuditLogParams = {
  actor_kind?: "" | AuditActorKind;
  action?: string;
  /** Mã người dùng (`?actor=`): chỉ các dòng do chính người đó làm (không gồm dòng AI/hệ thống). */
  actor?: number;
  /** Lô 17a (A3): `?date_from=YYYY-MM-DD` (giờ VN, gồm cả ngày đó). */
  date_from?: string;
  /** `?date_to=YYYY-MM-DD` (gồm cả ngày đó). */
  date_to?: string;
  /** `?q=` mã chứng từ hoặc mã đề xuất (2–40 ký tự, không dãy 9 chữ số). Đã qua `checkAuditQuery`. */
  q?: string;
};
