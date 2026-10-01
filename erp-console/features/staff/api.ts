// API module staff (S41, S42) — contract THỰC TẾ BE L5. Mọi endpoint đòi `accounts.manage_staff`.
// Lỗi nghiệp vụ trả {detail, code}; UI hiện NGUYÊN VĂN `detail` (BR-PQ-08/17/18, BR-GH-08, BR-PQ-01).
// Không có DELETE (BR-PQ-02).

import { apiFetch } from "@/shared/lib/http";
import { matches } from "@/shared/lib/search";
import { groupLabel } from "@/shared/lib/groups";
import { normalizeRoles } from "@/shared/lib/roles";
import { mockStaffApi } from "./mock";
import type {
  SetGroupsResult,
  StaffCreateInput,
  StaffFilter,
  StaffMember,
  StaffProfileInput,
} from "./types";

const BASE = "/api/staff/";

// P8b Lô 3: tên Group BE trả có thể là tên cũ hoặc tên tiếng Anh (Lô 4) → chuẩn hoá ngay khi nhận.
function normalizeMember(m: StaffMember): StaffMember {
  return { ...m, groups: normalizeRoles(m.groups) };
}

function normalizeGroupsResult(r: SetGroupsResult): SetGroupsResult {
  return { groups: normalizeRoles(r.groups), added: normalizeRoles(r.added), removed: normalizeRoles(r.removed) };
}

/** GET /api/staff/?is_active=true|false (bỏ trống = tất cả; BE sắp theo username). Không phân trang. */
export async function listStaff(filter: StaffFilter): Promise<StaffMember[]> {
  const q = filter === "active" ? "?is_active=true" : filter === "inactive" ? "?is_active=false" : "";
  const rows = await apiFetch<StaffMember[]>(BASE + q, {
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
  return rows.map(normalizeMember);
}

/** POST /api/staff/ → 201 một dòng đầy đủ. */
export async function createStaff(input: StaffCreateInput): Promise<StaffMember> {
  const m = await apiFetch<StaffMember>(BASE, {
    method: "POST",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
  return normalizeMember(m);
}

/** PATCH /api/staff/{id}/ — chỉ display_name, phone. */
export async function updateStaff(id: number, input: StaffProfileInput): Promise<StaffMember> {
  const m = await apiFetch<StaffMember>(`${BASE}${id}/`, {
    method: "PATCH",
    body: input,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
  return normalizeMember(m);
}

/** PUT /api/staff/{id}/groups/ — THAY toàn bộ tập nhóm. */
export async function setStaffGroups(id: number, groups: string[]): Promise<SetGroupsResult> {
  const r = await apiFetch<SetGroupsResult>(`${BASE}${id}/groups/`, {
    method: "PUT",
    body: { groups },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
  return normalizeGroupsResult(r);
}

/** POST /api/staff/{id}/deactivate/ — cho nghỉ: is_active=False + xoá token (đăng xuất mọi máy). */
export function deactivateStaff(id: number): Promise<{ is_active: boolean }> {
  return apiFetch<{ is_active: boolean }>(`${BASE}${id}/deactivate/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
}

/** POST /api/staff/{id}/reactivate/ — không cấp token; người đó đăng nhập lại bằng mật khẩu cũ. */
export function reactivateStaff(id: number): Promise<{ is_active: boolean }> {
  return apiFetch<{ is_active: boolean }>(`${BASE}${id}/reactivate/`, {
    method: "POST",
    body: {},
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
}

/** POST /api/staff/{id}/reset-password/ → 200 {}; xoá token cũ của người đó. */
export function resetStaffPassword(id: number, newPassword: string): Promise<Record<string, never>> {
  return apiFetch<Record<string, never>>(`${BASE}${id}/reset-password/`, {
    method: "POST",
    body: { new_password: newPassword },
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStaffApi : undefined,
  });
}

/** Tìm phía máy: tên, tên đăng nhập, SĐT, nhãn nhóm (bỏ dấu). */
export function filterStaff(rows: StaffMember[], q: string): StaffMember[] {
  return rows.filter((r) => matches(q, r.display_name, r.username, r.phone, r.groups.map(groupLabel).join(" ")));
}

/** Mật khẩu tạm ngẫu nhiên để Chủ đọc cho nhân viên (10 ký tự, bỏ chữ dễ nhầm 0/O, 1/l/I). BE vẫn kiểm lại. */
export function suggestPassword(): string {
  const chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const buf = new Uint32Array(10);
  crypto.getRandomValues(buf);
  return Array.from(buf, (n) => chars[n % chars.length]).join("");
}
