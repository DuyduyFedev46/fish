// Mock /api/staff/ (S41, S42) — chạy khi NEXT_PUBLIC_USE_MOCK=1. Mô phỏng ĐÚNG contract thực tế BE L5
// (03-dev-notes.md "Lô L5 — S41, S42"): JSON, thông điệp lỗi nguyên văn, thứ tự kiểm, `available_actions`.
// Dùng chung kho người dùng mock của features/auth (tạo/cho nghỉ/đặt lại mật khẩu có tác dụng lên đăng nhập mock).
//
// Thứ tự kiểm như BE: manage_staff (403) → tự thao tác (400) → nhóm lạ (400) → BR-PQ-17 thẩm quyền (403)
//   → BR-PQ-18 (400) → BR-GH-08 (400).
// Phiếu Đang giao giả lập: giao2 còn 2 phiếu (BR-GH-08, S42-AC4).

import {
  MOCK_UNAUTHORIZED,
  mockPasswordProblems,
  mockPermsOf,
  mockRequireRecord,
  mockRevokeUserTokens,
  mockUsers,
  saveMockUsers,
  sortGroups,
  type MockUser,
} from "@/features/auth/mock";
import { beError } from "@/shared/lib/beErrors.mock";
import { GROUP_CODES } from "@/shared/lib/groups";
import { GROUP, PERM } from "@/shared/lib/nav";
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { STAFF_MSG } from "./messages";
import type { StaffAction, StaffMember } from "./types";

// E2E đọc thông báo của màn qua window.__caveMock.staffMsg (không gõ lại chuỗi trong kịch bản).
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = { ...(w.__caveMock || {}), staffMsg: STAFF_MSG };
}

const VALID_GROUPS: readonly string[] = GROUP_CODES;
/** Quyền mở /api/staff/ (BE `CanManageStaff`) — cùng hằng số với menu (shared/lib/nav.ts). */
const MANAGE_STAFF = PERM.manageStaff;
const DELIVERING: Record<string, string[]> = {
  giao2: ["GH-INV-DH01-A1B2C", "GH-INV-DH02-K7M3Q"],
};

const isChu = (u: MockUser) => u.groups.includes(GROUP.chu);
const activeChus = (list: MockUser[]) => list.filter((u) => u.is_active && isChu(u));

/** BR-PQ-17 thẩm quyền trên tài khoản đích (không tính thêm/bỏ nhóm chu — kiểm riêng). */
function authorityError(viewer: MockUser, target: MockUser): MockResponse | null {
  if (target.is_superuser && !viewer.is_superuser) return beError("SUPERUSER_ONLY");
  if (isChu(target) && !isChu(viewer) && !viewer.is_superuser) return beError("CHU_ACCOUNT_ONLY");
  return null;
}

/** `available_actions` theo người ĐANG XEM (BE L5, ghi chú contract). */
function actionsFor(viewer: MockUser, target: MockUser, list: MockUser[]): StaffAction[] {
  if (viewer.id === target.id) return ["edit"];
  if (target.is_superuser && !viewer.is_superuser) return [];
  if (isChu(target) && !isChu(viewer) && !viewer.is_superuser) return [];
  if (!target.is_active) return ["edit", "reactivate"];
  const lastChu = isChu(target) && activeChus(list).length <= 1;
  return lastChu ? ["edit", "set_groups", "reset_password"] : ["edit", "set_groups", "reset_password", "deactivate"];
}

function row(viewer: MockUser, u: MockUser, list: MockUser[]): StaffMember {
  return {
    id: u.id,
    username: u.username,
    display_name: u.display_name || u.username,
    phone: u.phone,
    groups: sortGroups(u.groups),
    is_active: u.is_active,
    last_login: u.last_login,
    available_actions: actionsFor(viewer, u, list),
  };
}

function unknownFields(body: Record<string, unknown>, allowed: string[]): MockResponse | null {
  const extra = Object.keys(body).filter((k) => !allowed.includes(k));
  return extra.length ? beError("FIELD_NOT_ALLOWED", { fields: extra.join(", ") }) : null;
}

function groupsError(groups: unknown): MockResponse | null {
  if (!Array.isArray(groups) || groups.some((g) => typeof g !== "string")) return beError("GROUPS_NOT_ARRAY");
  const bad = (groups as string[]).filter((g) => !VALID_GROUPS.includes(g));
  if (bad.length) return beError("GROUP_UNKNOWN", { groups: bad.join(", "), valid: VALID_GROUPS.join(", ") });
  return null;
}

function create(viewer: MockUser, list: MockUser[], body: Record<string, unknown>): MockResponse {
  const bad = unknownFields(body, ["username", "display_name", "phone", "groups", "password"]);
  if (bad) return bad;
  const username = typeof body.username === "string" ? body.username.trim() : "";
  const phone = typeof body.phone === "string" ? body.phone.trim() : "";
  const password = typeof body.password === "string" ? body.password : "";
  const groups = body.groups === undefined ? [] : body.groups;
  if (!username) return beError("USERNAME_REQUIRED");
  if (!/^[\w.@+-]+$/.test(username)) return beError("USERNAME_INVALID");
  if (list.some((u) => u.username.toLowerCase() === username.toLowerCase())) return beError("USERNAME_EXISTS");
  if (!phone) return beError("PHONE_REQUIRED");
  if (!password) return beError("PASSWORD_REQUIRED");
  const weak = mockPasswordProblems(password, username);
  if (weak) return beError("PASSWORD_WEAK", { problems: weak });
  const gErr = groupsError(groups);
  if (gErr) return gErr;
  if ((groups as string[]).includes(GROUP.chu) && !isChu(viewer) && !viewer.is_superuser) return beError("CHU_GROUP_ONLY");
  const u: MockUser = {
    id: Math.max(...list.map((x) => x.id)) + 1,
    username,
    display_name: typeof body.display_name === "string" ? body.display_name.trim() : "",
    phone,
    groups: sortGroups(groups as string[]),
    is_active: true,
    is_superuser: false,
    extra_perms: [],
    password,
    revoked_at: 0,
    last_login: null,
    must_change_password: true, // S48-AC1: mật khẩu tạm → lần đăng nhập đầu phải đổi
  };
  list.push(u);
  saveMockUsers(list);
  return { status: 201, body: row(viewer, u, list) };
}

function patch(viewer: MockUser, list: MockUser[], target: MockUser, body: Record<string, unknown>): MockResponse {
  const bad = unknownFields(body, ["display_name", "phone"]);
  if (bad) return bad;
  const auth = viewer.id === target.id ? null : authorityError(viewer, target);
  if (auth) return auth;
  if ("phone" in body) {
    const phone = typeof body.phone === "string" ? body.phone.trim() : "";
    if (!phone) return beError("PHONE_REQUIRED");
    target.phone = phone;
  } else if (!target.phone) {
    return beError("PHONE_REQUIRED");
  }
  if (typeof body.display_name === "string") target.display_name = body.display_name.trim();
  saveMockUsers(list);
  return { status: 200, body: row(viewer, target, list) };
}

function setGroups(viewer: MockUser, list: MockUser[], target: MockUser, body: Record<string, unknown>): MockResponse {
  const bad = unknownFields(body, ["groups"]);
  if (bad) return bad;
  if (viewer.id === target.id) return beError("SELF_GROUPS");
  const gErr = groupsError(body.groups);
  if (gErr) return gErr;
  const next = sortGroups(body.groups as string[]);
  const before = sortGroups(target.groups);
  const added = next.filter((g) => !before.includes(g));
  const removed = before.filter((g) => !next.includes(g));
  const viewerStrong = isChu(viewer) || viewer.is_superuser;
  if (target.is_superuser && !viewer.is_superuser) return beError("SUPERUSER_ONLY");
  if ((added.includes(GROUP.chu) || removed.includes(GROUP.chu)) && !viewerStrong) return beError("CHU_GROUP_ONLY");
  if (isChu(target) && !viewerStrong) return beError("CHU_ACCOUNT_ONLY");
  if (removed.includes(GROUP.chu) && target.is_active && activeChus(list).length <= 1) return beError("LAST_CHU_GROUP");
  target.groups = next;
  saveMockUsers(list);
  return { status: 200, body: { groups: next, added, removed } };
}

function deactivate(viewer: MockUser, list: MockUser[], target: MockUser): MockResponse {
  if (viewer.id === target.id) return beError("SELF_DEACTIVATE");
  const auth = authorityError(viewer, target);
  if (auth) return auth;
  if (!target.is_active) return beError("ALREADY_INACTIVE");
  if (isChu(target) && activeChus(list).length <= 1) return beError("LAST_CHU_DEACTIVATE");
  const notes = DELIVERING[target.username];
  if (notes?.length) return beError("DELIVERING_LEFT", { count: notes.length, notes: notes.join(", ") });
  target.is_active = false;
  mockRevokeUserTokens(list, target.id); // xoá token → lần gọi kế tiếp của người đó 401 (S42-AC1)
  saveMockUsers(list);
  return { status: 200, body: { is_active: false } };
}

function reactivate(viewer: MockUser, list: MockUser[], target: MockUser): MockResponse {
  const auth = viewer.id === target.id ? null : authorityError(viewer, target);
  if (auth) return auth;
  if (target.is_active) return beError("ALREADY_ACTIVE");
  target.is_active = true;
  saveMockUsers(list);
  return { status: 200, body: { is_active: true } };
}

function resetPassword(viewer: MockUser, list: MockUser[], target: MockUser, body: Record<string, unknown>): MockResponse {
  const bad = unknownFields(body, ["new_password"]);
  if (bad) return bad;
  if (viewer.id === target.id) return beError("SELF_RESET");
  const auth = authorityError(viewer, target);
  if (auth) return auth;
  const pw = typeof body.new_password === "string" ? body.new_password : "";
  if (!pw) return beError("PASSWORD_REQUIRED");
  const weak = mockPasswordProblems(pw, target.username);
  if (weak) return beError("PASSWORD_WEAK", { problems: weak });
  target.password = pw;
  target.must_change_password = true; // S48-AC6: Chủ đặt lại → cờ bật lại
  mockRevokeUserTokens(list, target.id); // máy đang đăng nhập của người đó → 401 (S42-AC3)
  saveMockUsers(list);
  return { status: 200, body: {} };
}

/** Một handler cho mọi đường /api/staff/… (api.ts truyền chung). */
export function mockStaffApi(req: MockRequest): MockResponse {
  const viewer = mockRequireRecord(req);
  if (!viewer) return MOCK_UNAUTHORIZED;
  if (!mockPermsOf(viewer).includes(MANAGE_STAFF)) return beError("DRF_FORBIDDEN");

  const [pathOnly, query = ""] = req.path.split("?");
  const parts = pathOnly.replace(/^\/api\/staff\/?/, "").split("/").filter(Boolean);
  const list = mockUsers();
  const body = (req.body && typeof req.body === "object" ? req.body : {}) as Record<string, unknown>;

  if (parts.length === 0) {
    if (req.method === "GET") {
      const flag = new URLSearchParams(query).get("is_active");
      const rows = list
        .filter((u) => (flag === "true" ? u.is_active : flag === "false" ? !u.is_active : true))
        .sort((a, b) => a.username.localeCompare(b.username))
        .map((u) => row(viewer, u, list));
      return { status: 200, body: rows };
    }
    if (req.method === "POST") return create(viewer, list, body);
    return beError("METHOD_NOT_ALLOWED", { method: req.method });
  }

  const target = list.find((u) => u.id === Number(parts[0]));
  if (!target) return beError("NOT_FOUND");
  const action = parts[1];

  if (!action) {
    if (req.method === "GET") return { status: 200, body: row(viewer, target, list) };
    if (req.method === "PATCH") return patch(viewer, list, target, body);
    return beError("METHOD_NOT_ALLOWED", { method: req.method });
  }
  if (action === "groups" && req.method === "PUT") return setGroups(viewer, list, target, body);
  if (action === "deactivate" && req.method === "POST") return deactivate(viewer, list, target);
  if (action === "reactivate" && req.method === "POST") return reactivate(viewer, list, target);
  if (action === "reset-password" && req.method === "POST") return resetPassword(viewer, list, target, body);
  return beError("NOT_FOUND");
}
