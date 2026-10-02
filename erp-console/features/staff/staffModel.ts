// Hàm thuần của màn Nhân sự (ED-37/ED-38): tab, tìm, so sánh nhóm, lý do thao tác bị chặn. Không React, không gọi mạng.
// Luật nghiệp vụ (ai làm được gì) do BE quyết qua `available_actions`; ở đây chỉ CHỌN CÂU lý do khi một thao tác không có trong đó.

import { groupLabel } from "@/shared/lib/groups";
import { ROLE } from "@/shared/lib/roles";
import { STAFF_MSG as M } from "./messages";
import type { StaffAction, StaffActivityRow, StaffDelivering, StaffMember, StaffTab } from "./types";

export const STAFF_TABS: { key: StaffTab; label: string }[] = [
  { key: "active", label: M.tabActive },
  { key: "inactive", label: M.tabInactive },
  { key: "all", label: M.tabAll },
];

export function countByTab(rows: StaffMember[]): Record<StaffTab, number> {
  const active = rows.filter((r) => r.is_active).length;
  return { active, inactive: rows.length - active, all: rows.length };
}

export function rowsOfTab(rows: StaffMember[], tab: StaffTab): StaffMember[] {
  if (tab === "all") return rows;
  return rows.filter((r) => r.is_active === (tab === "active"));
}

export function asTab(v: string): StaffTab {
  return v === "inactive" || v === "all" ? v : "active";
}

/** `?id=12` → 12; thiếu hoặc không phải số nguyên dương → null. URL chỉ mang id số. */
export function parseStaffId(search: string): number | null {
  const raw = new URLSearchParams(search).get("id");
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

/** "Anh Tâm (kho1)" khi có tên hiển thị khác tên đăng nhập, không thì chỉ tên đăng nhập. */
export function whoOf(m: Pick<StaffMember, "display_name" | "username">): string {
  return m.display_name && m.display_name !== m.username ? `${m.display_name} (${m.username})` : m.username;
}

export function namesOf(codes: string[]): string {
  return codes.map(groupLabel).join(", ");
}

export type GroupsDiff = { added: string[]; removed: string[] };

export function groupsDiff(before: string[], after: string[]): GroupsDiff {
  return { added: after.filter((g) => !before.includes(g)), removed: before.filter((g) => !after.includes(g)) };
}

/** Thêm / bỏ nhóm Chủ là bước nguy hiểm: phải hỏi lại trước khi gửi. */
export function ownerChange(diff: GroupsDiff): "grant" | "revoke" | null {
  if (diff.added.includes(ROLE.owner)) return "grant";
  if (diff.removed.includes(ROLE.owner)) return "revoke";
  return null;
}

/** Thao tác có trong `available_actions` của BE không. FE KHÔNG tự suy luật. */
export function can(m: StaffMember, action: StaffAction): boolean {
  return m.available_actions.includes(action);
}

/**
 * Lý do ngắn khi `action` không làm được trên `m` (để hiện mờ trong menu "…"). Chỉ chọn câu, không quyết luật:
 * chính mình · Chủ cuối cùng (còn "Đổi nhóm" mà không còn "Cho nghỉ") · còn lại là không đủ quyền.
 */
export function blockedReason(action: "reset_password" | "deactivate" | "reactivate", m: StaffMember, viewerId: number | null): string {
  const self = viewerId !== null && m.id === viewerId;
  if (action === "reset_password") return self ? M.selfBlockedReset : M.noRightBlocked;
  if (action === "deactivate") {
    if (self) return M.selfBlockedDeactivate;
    if (m.groups.includes(ROLE.owner) && can(m, "set_groups")) return M.lastOwnerBlocked;
  }
  return M.noRightBlocked;
}

const MAX_CODES_SHOWN = 5;

/**
 * ED-38-AC3 / BR-GH-08: câu báo "còn phiếu Đang giao" cho hộp Cho nghỉ, hoặc null khi không có gì để chặn.
 * `notes` null (khối không tải được hoặc người xem thiếu quyền xem phiếu) → null: giữ hành vi cũ, để BE quyết khi bấm xác nhận.
 * Chỉ dùng số phiếu và mã phiếu, không có dữ liệu khách.
 */
export function deliveringBlock(notes: Pick<StaffDelivering, "code">[] | null): string | null {
  if (!notes || notes.length === 0) return null;
  const shown = notes.slice(0, MAX_CODES_SHOWN).map((n) => n.code).join(", ");
  return M.deactivateDelivering(notes.length, shown, notes.length - MAX_CODES_SHOWN);
}

const ACTION_VERB: Record<string, string> = {
  create: "Tạo",
  update: "Sửa",
  set_groups: "Đổi nhóm",
  deactivate: "Cho nghỉ",
  reactivate: "Cho làm lại",
  reset_password: "Đặt lại mật khẩu",
  execute_command: "Chạy lệnh",
};

/** Nhãn dòng nhật ký: ưu tiên ghi chú BE, không thì động từ đã dịch, cuối cùng là chính chuỗi BE trả. */
export function activityLabel(row: Pick<StaffActivityRow, "action" | "note">): string {
  return row.note?.trim() || ACTION_VERB[row.action] || row.action;
}
