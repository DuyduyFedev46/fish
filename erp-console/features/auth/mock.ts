// Mock module auth — chạy khi NEXT_PUBLIC_USE_MOCK=1. JSON dựng theo contract THỰC TẾ: S6 (03-dev-notes.md "Lô L3–L4")
// và S46 (logout, change-password) + S47 (group_labels, capabilities) (03-dev-notes.md "Lô L6").
//
// Tài khoản mock (mật khẩu ban đầu: "demo1234"):
//   loc   = chu                 → home "dashboard", xem giá vốn + lãi lỗ, có accounts.manage_staff
//   ql1   = quan_ly             → home "dashboard", không xem giá vốn
//   kho1  = nv_kho + nv_giao    → home "dashboard" (S6-AC2)
//   giao1 = nv_giao             → home "my-deliveries" (S6-AC3)
//   giao2 = nv_giao             → còn 2 phiếu Đang giao → Chủ cho nghỉ bị BR-GH-08 (S42-AC4)
//   ql9   = quan_ly + quyền lẻ accounts.manage_staff (không thuộc chu) → thử BR-PQ-17 403 (S41-AC6, S42-AC7)
//   sa1   = superuser + quan_ly → thử BR-PQ-18 (bỏ nhóm Chủ của loc — Chủ cuối cùng, S41-AC7)
//   admin = superuser, không Group → home "no-role" (S6-AC4, S47-AC5)
//   nghi1 = is_active=False     → đăng nhập 400 (S7-AC4)
//   kho5  = nv_kho, còn mật khẩu tạm (must_change_password) → chỉ mở được màn "Đặt mật khẩu mới" (S48-AC1)
//
// S48: Chủ tạo tài khoản / đặt lại mật khẩu → must_change_password=true; tự đổi mật khẩu → false (không bật lại);
// superuser không bị ép. Cổng chung (setMockGate) chặn mọi API nghiệp vụ bằng 403 AUTH_MUST_CHANGE_PASSWORD,
// trừ /api/auth/me/, /api/auth/change-password/, /api/auth/logout/ — y như lớp chặn chung của BE.
//
// Danh sách người dùng mock lưu localStorage (`cave_erp_mock_users`) để thao tác của module staff (S41/S42:
// tạo, đổi nhóm, cho nghỉ, đặt lại mật khẩu) và đổi mật khẩu (S46) có tác dụng thật lên đăng nhập mock.
//
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.log / clearLog() — request đã gọi (khai ở shared/lib/http.ts; kiểm S7-AC3)
//   window.__caveMock.expire()         — thu hồi mọi token → lần gọi kế tiếp trả 401 (kiểm S7-AC6)
//   window.__caveMock.resetUsers()     — về lại danh sách người dùng seed
//   window.__caveMock.patchUser(username, {groups, extra_perms, denied_perms, is_active}) — đổi quyền "từ máy khác" (S47-AC2/AC3)
//
// Module khác: mockRequireUser(req) = người dùng của token (null nếu token hỏng/đã thu hồi/đã nghỉ).
// Module staff: mockUsers(), saveMockUsers(), mockIssue… (kho người dùng dùng chung).

import { LOGIN_BAD, PW_PROBLEMS, beError } from "@/shared/lib/beErrors.mock";
import { GROUP_CODES, GROUP_LABEL } from "@/shared/lib/groups";
import { setMockGate, type MockRequest, type MockResponse } from "@/shared/lib/http";
import type { Me } from "./types";

const PASSWORD = "demo1234";
const REVOKED_KEY = "cave_erp_mock_revoked";
const USERS_KEY = "cave_erp_mock_users";
const TOKEN_PREFIX = "mock-token-";

// ---- Quyền theo Group: COPY NGUYÊN `permissions` thật của GET /api/auth/me/ (BE L3–L4, 03-dev-notes.md,
// dữ liệu seed migration). Mọi quyền của nv_giao nằm trong nv_kho. Đổi ở BE thì chép lại ở đây. ----
const GROUP_PERMS: Record<string, string[]> = {
  chu: [
    "accounts.add_staffprofile", "accounts.change_staffprofile", "accounts.delete_staffprofile",
    "accounts.manage_staff", "accounts.view_auditlog", "accounts.view_staffprofile", "auth.add_group",
    "auth.add_user", "auth.change_group", "auth.change_user", "auth.delete_group", "auth.delete_user",
    "auth.view_group", "auth.view_user", "catalog.add_bundleline", "catalog.add_item", "catalog.add_itemgroup",
    "catalog.add_itemprice", "catalog.add_pricelist", "catalog.add_pricingrule", "catalog.change_bundleline",
    "catalog.change_item", "catalog.change_itemgroup", "catalog.change_itemprice", "catalog.change_pricelist",
    "catalog.change_pricingrule", "catalog.delete_bundleline", "catalog.delete_item", "catalog.delete_itemgroup",
    "catalog.delete_itemprice", "catalog.delete_pricelist", "catalog.delete_pricingrule", "catalog.view_bundleline",
    "catalog.view_item", "catalog.view_itemgroup", "catalog.view_itemprice", "catalog.view_pricelist",
    "catalog.view_pricingrule", "delivery.add_deliverynote", "delivery.change_deliverynote",
    "delivery.delete_deliverynote", "delivery.view_deliverynote", "inventory.add_batch",
    "inventory.add_returntostock", "inventory.add_stockentry", "inventory.add_stockreconciliation",
    "inventory.add_stockreconciliationline", "inventory.add_warehouse", "inventory.approve_returntostock",
    "inventory.approve_stockreconciliation", "inventory.change_batch", "inventory.change_returntostock",
    "inventory.change_stockentry", "inventory.change_stockreconciliation",
    "inventory.change_stockreconciliationline", "inventory.change_warehouse", "inventory.close_batch",
    "inventory.delete_batch", "inventory.delete_returntostock", "inventory.delete_stockentry",
    "inventory.delete_stockreconciliation", "inventory.delete_stockreconciliationline", "inventory.delete_warehouse",
    "inventory.publish_batch", "inventory.view_batch", "inventory.view_costprice", "inventory.view_returntostock",
    "inventory.view_stockentry", "inventory.view_stockledgerentry", "inventory.view_stockreconciliation",
    "inventory.view_stockreconciliationline", "inventory.view_warehouse", "purchasing.add_purchasecost",
    "purchasing.add_purchasecostallocation", "purchasing.add_purchaseinvoice", "purchasing.add_purchasereceipt",
    "purchasing.add_purchasereceiptline", "purchasing.add_supplier", "purchasing.change_purchasecost",
    "purchasing.change_purchasecostallocation", "purchasing.change_purchaseinvoice",
    "purchasing.change_purchasereceipt", "purchasing.change_purchasereceiptline", "purchasing.change_supplier",
    "purchasing.delete_purchasecost", "purchasing.delete_purchasecostallocation",
    "purchasing.delete_purchaseinvoice", "purchasing.delete_purchasereceipt",
    "purchasing.delete_purchasereceiptline", "purchasing.delete_supplier", "purchasing.view_purchasecost",
    "purchasing.view_purchasecostallocation", "purchasing.view_purchaseinvoice", "purchasing.view_purchasereceipt",
    "purchasing.view_purchasereceiptline", "purchasing.view_supplier", "reports.view_dashboard",
    "reports.view_profitreport", "sales.add_customer", "sales.add_paymenttransaction", "sales.add_refund",
    "sales.cancel_paid_order", "sales.change_customer", "sales.change_paymenttransaction", "sales.change_refund",
    "sales.change_salesinvoice", "sales.change_salesorder", "sales.confirm_payment_manual", "sales.confirm_refund",
    "sales.create_refund", "sales.delete_customer", "sales.delete_paymenttransaction", "sales.delete_refund",
    "sales.view_customer", "sales.view_paymenttransaction", "sales.view_refund", "sales.view_salesinvoice",
    "sales.view_salesinvoiceline", "sales.view_salesinvoicelinebatch", "sales.view_salesorder",
    "sales.view_salesorderline", "sales.view_salesorderlinebatch",
  ],
  quan_ly: [
    "accounts.view_staffprofile", "auth.view_user", "catalog.view_bundleline", "catalog.view_item",
    "catalog.view_itemgroup", "catalog.view_itemprice", "catalog.view_pricelist", "catalog.view_pricingrule",
    "delivery.add_deliverynote", "delivery.change_deliverynote", "delivery.view_deliverynote",
    "inventory.add_stockentry", "inventory.add_stockreconciliation", "inventory.add_stockreconciliationline",
    "inventory.approve_returntostock", "inventory.approve_stockreconciliation", "inventory.change_stockentry",
    "inventory.change_stockreconciliation", "inventory.change_stockreconciliationline", "inventory.publish_batch",
    "inventory.view_batch", "inventory.view_returntostock", "inventory.view_stockentry",
    "inventory.view_stockledgerentry", "inventory.view_stockreconciliation",
    "inventory.view_stockreconciliationline", "inventory.view_warehouse", "purchasing.add_purchasereceipt",
    "purchasing.add_purchasereceiptline", "purchasing.add_supplier", "purchasing.change_purchasereceipt",
    "purchasing.change_purchasereceiptline", "purchasing.change_supplier", "purchasing.view_purchaseinvoice",
    "purchasing.view_purchasereceipt", "purchasing.view_purchasereceiptline", "purchasing.view_supplier",
    "reports.view_dashboard", "sales.add_customer", "sales.add_refund", "sales.cancel_paid_order",
    "sales.change_customer", "sales.change_refund", "sales.create_refund", "sales.view_customer",
    "sales.view_paymenttransaction", "sales.view_refund", "sales.view_salesinvoice", "sales.view_salesinvoiceline",
    "sales.view_salesorder", "sales.view_salesorderline",
  ],
  nv_kho: [
    "accounts.view_staffprofile", "auth.view_user", "catalog.view_bundleline", "catalog.view_item",
    "catalog.view_itemgroup", "delivery.add_deliverynote", "delivery.change_deliverynote",
    "delivery.view_deliverynote", "inventory.add_returntostock", "inventory.add_stockentry",
    "inventory.add_stockreconciliation", "inventory.add_stockreconciliationline", "inventory.change_stockentry",
    "inventory.change_stockreconciliation", "inventory.change_stockreconciliationline", "inventory.view_batch",
    "inventory.view_returntostock", "inventory.view_stockentry", "inventory.view_stockledgerentry",
    "inventory.view_stockreconciliation", "inventory.view_stockreconciliationline", "inventory.view_warehouse",
    "purchasing.add_purchasereceipt", "purchasing.add_purchasereceiptline", "purchasing.change_purchasereceipt",
    "purchasing.change_purchasereceiptline", "purchasing.view_purchasereceipt",
    "purchasing.view_purchasereceiptline", "purchasing.view_supplier", "reports.view_dashboard",
    "sales.view_customer", "sales.view_salesinvoice", "sales.view_salesinvoiceline", "sales.view_salesorder",
    "sales.view_salesorderline",
  ],
  nv_giao: [
    "accounts.view_staffprofile", "auth.view_user", "delivery.change_deliverynote", "delivery.view_deliverynote",
    "inventory.add_returntostock", "inventory.view_returntostock", "sales.view_customer", "sales.view_salesorder",
    "sales.view_salesorderline",
  ],
};

/** Người dùng trong kho mock (có vài field nội bộ BE không trả ra ngoài). */
export type MockUser = {
  id: number;
  username: string;
  display_name: string;
  phone: string;
  groups: string[];
  is_active: boolean;
  is_superuser: boolean;
  /** Quyền gán lẻ cho user (ngoài Group). */
  extra_perms: string[];
  password: string;
  /** Mốc thu hồi mọi token của người này (đăng xuất, đổi/đặt lại mật khẩu, cho nghỉ). */
  revoked_at: number;
  last_login: string | null;
  /** S48 — còn mật khẩu tạm (Chủ vừa tạo / đặt lại). Bản cũ trong localStorage không có key → coi như false. */
  must_change_password?: boolean;
  /**
   * CHỈ để thử (patchUser): quyền bị gỡ khỏi user dù Group có — giả lập admin gỡ quyền khỏi Group ở BE
   * (vd nv_kho mất reports.view_dashboard; code review trước deploy 1). BE không có field này.
   */
  denied_perms?: string[];
};

function seed(): MockUser[] {
  const u = (
    id: number,
    username: string,
    display_name: string,
    phone: string,
    groups: string[],
    more: Partial<MockUser> = {}
  ): MockUser => ({
    id,
    username,
    display_name,
    phone,
    groups,
    is_active: true,
    is_superuser: false,
    extra_perms: [],
    password: PASSWORD,
    revoked_at: 0,
    last_login: null,
    ...more,
  });
  return [
    u(1, "loc", "Lộc", "0909123456", ["chu"], { last_login: "2026-09-24T06:40:00+07:00" }),
    u(2, "ql1", "Chị Hạnh", "0909000111", ["quan_ly"], { last_login: "2026-09-24T07:15:00+07:00" }),
    u(3, "kho1", "Anh Tâm", "0909000222", ["nv_kho", "nv_giao"], { last_login: "2026-09-24T05:02:00+07:00" }),
    u(4, "giao1", "Anh Phúc", "0909000333", ["nv_giao"], { last_login: "2026-09-24T05:10:00+07:00" }),
    u(5, "admin", "Quản trị", "", [], { is_superuser: true }),
    u(6, "nghi1", "Anh Nghĩa", "0909000444", ["nv_kho"], { is_active: false, last_login: "2026-08-30T17:20:00+07:00" }),
    u(7, "giao2", "Anh Lâm", "0909000555", ["nv_giao"], { last_login: "2026-09-24T06:05:00+07:00" }),
    u(8, "ql9", "Chị Mai", "0909000666", ["quan_ly"], { extra_perms: ["accounts.manage_staff"] }),
    u(9, "sa1", "Kỹ thuật", "0909000777", ["quan_ly"], { is_superuser: true }),
    u(10, "kho5", "Chị Sáu", "0909000888", ["nv_kho"], { must_change_password: true }),
  ];
}

function ls(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** Kho người dùng mock hiện tại (bản sao — sửa xong gọi saveMockUsers). */
export function mockUsers(): MockUser[] {
  const raw = ls()?.getItem(USERS_KEY);
  if (raw) {
    try {
      return JSON.parse(raw) as MockUser[];
    } catch {
      /* hỏng → seed */
    }
  }
  return seed();
}

export function saveMockUsers(list: MockUser[]): void {
  try {
    ls()?.setItem(USERS_KEY, JSON.stringify(list));
  } catch {
    /* bỏ qua */
  }
}

const ALL_PERMS = Array.from(new Set(Object.values(GROUP_PERMS).flat())).sort();

/** `capabilities` của /api/auth/me/ — chép nguyên bảng BE L6 (`CAPABILITY_LABELS`), đúng thứ tự và nhãn. */
const CAPABILITIES: [string, string][] = [
  ["inventory.publish_batch", "Mở bán lô"],
  ["sales.cancel_paid_order", "Huỷ đơn đã thanh toán"],
  ["sales.create_refund", "Tạo phiếu hoàn"],
  ["inventory.approve_returntostock", "Duyệt hàng hoàn"],
  ["inventory.approve_stockreconciliation", "Duyệt kiểm kê"],
  ["inventory.close_batch", "Chốt lô"],
  ["purchasing.add_purchasecost", "Nhập chi phí mua"],
  ["sales.confirm_refund", "Xác nhận đã hoàn tiền"],
  ["sales.confirm_payment_manual", "Xác nhận thanh toán thủ công"],
  ["accounts.manage_staff", "Quản lý nhân viên"],
  ["inventory.view_costprice", "Xem giá vốn"],
  ["reports.view_profitreport", "Xem báo cáo lãi lỗ"],
  ["reports.view_dashboard", "Xem Tổng quan"],
];

const GROUP_ORDER: readonly string[] = GROUP_CODES;

/** Thứ tự nhóm cố định chu, quan_ly, nv_kho, nv_giao (như BE `sorted_groups`). */
export function sortGroups(groups: string[]): string[] {
  return Array.from(new Set(groups)).sort((a, b) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b));
}

export function mockPermsOf(u: MockUser): string[] {
  if (u.is_superuser) return ALL_PERMS;
  const denied = u.denied_perms || [];
  return Array.from(new Set([...u.groups.flatMap((g) => GROUP_PERMS[g] || []), ...u.extra_perms]))
    .filter((p) => !denied.includes(p))
    .sort();
}

function buildMe(u: MockUser): Me {
  const perms = mockPermsOf(u);
  const groups = sortGroups(u.groups);
  const home: Me["home"] =
    groups.length === 0 ? "no-role" : groups.length === 1 && groups[0] === "nv_giao" ? "my-deliveries" : "dashboard";
  return {
    id: u.id,
    username: u.username,
    display_name: u.display_name || u.username,
    phone: u.phone,
    groups,
    permissions: perms,
    can_view_cost: perms.includes("inventory.view_costprice"),
    can_view_profit: perms.includes("reports.view_profitreport"),
    home,
    // S47 (BE L6):
    group_labels: groups.map((g) => ({ code: g, label: GROUP_LABEL[g] || g })),
    capabilities: CAPABILITIES.filter(([code]) => perms.includes(code)).map(([code, label]) => ({ code, label })),
    // S48:
    must_change_password: mustChange(u),
  };
}

/** S48: superuser không bị ép đổi mật khẩu (S48-AC6). */
function mustChange(u: MockUser): boolean {
  return !!u.must_change_password && !u.is_superuser;
}

// ---- Token ----
function revokedAt(): number {
  return Number(ls()?.getItem(REVOKED_KEY) || "0");
}

const REVOKED_TOKENS_KEY = "cave_erp_mock_revoked_tokens";

function revokedTokens(): string[] {
  try {
    return JSON.parse(ls()?.getItem(REVOKED_TOKENS_KEY) || "[]") as string[];
  } catch {
    return [];
  }
}

let lastIssued = 0;
function issueToken(u: MockUser): string {
  // Nhúng thời điểm cấp (tăng dần) để thu hồi theo mốc được.
  lastIssued = Math.max(Date.now(), lastIssued + 1, u.revoked_at + 1);
  return `${TOKEN_PREFIX}${u.username}-${lastIssued}`;
}

function userFromToken(token: string | null): MockUser | null {
  if (!token || !token.startsWith(TOKEN_PREFIX)) return null;
  const rest = token.slice(TOKEN_PREFIX.length);
  const cut = rest.lastIndexOf("-");
  const username = rest.slice(0, cut);
  const issued = Number(rest.slice(cut + 1));
  if (!issued || issued <= revokedAt() || revokedTokens().includes(token)) return null;
  const u = mockUsers().find((x) => x.username === username);
  return u && u.is_active && issued > u.revoked_at ? u : null;
}

/** Thu hồi mọi token của một người trong `list` (DRF: một token cho mỗi người — C8). Nhớ saveMockUsers. */
export function mockRevokeUserTokens(list: MockUser[], id: number): void {
  const u = list.find((x) => x.id === id);
  if (u) u.revoked_at = Math.max(Date.now(), lastIssued);
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    expire: () => {
      window.localStorage.setItem(REVOKED_KEY, String(Date.now()));
      return "Đã thu hồi mọi token mock — request kế tiếp sẽ nhận 401.";
    },
    resetUsers: () => {
      window.localStorage.removeItem(USERS_KEY);
      return "Đã về danh sách người dùng seed.";
    },
    patchUser: (username: string, patch: Partial<MockUser>) => {
      const list = mockUsers();
      const u = list.find((x) => x.username === username);
      if (!u) return "Không có người dùng này.";
      Object.assign(u, patch);
      saveMockUsers(list);
      return `Đã sửa ${username}.`;
    },
  };
}

export const MOCK_UNAUTHORIZED: MockResponse = beError("UNAUTHORIZED");

/** S48: đường vẫn mở khi còn mật khẩu tạm (contract thật BE L6b: token, me, logout, change-password). */
const MUST_CHANGE_ALLOWED = ["/api/auth/me/", "/api/auth/change-password/", "/api/auth/logout/", "/api/auth/token/"];

if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
  setMockGate((req) => {
    if (MUST_CHANGE_ALLOWED.some((p) => req.path.startsWith(p))) return null;
    const u = userFromToken(req.token);
    return u && mustChange(u) ? beError("AUTH_MUST_CHANGE_PASSWORD") : null;
  });
}

/** Cho module khác: người dùng mock của token, null nếu token hỏng/đã thu hồi/đã nghỉ. */
export function mockRequireUser(req: MockRequest): Me | null {
  const u = userFromToken(req.token);
  return u ? buildMe(u) : null;
}

/** Cho module staff: bản ghi đầy đủ của người gọi (cần is_superuser). */
export function mockRequireRecord(req: MockRequest): MockUser | null {
  return userFromToken(req.token);
}

/** Vài mật khẩu "quá phổ biến" để mock thử (Django dùng danh sách 20 000 mật khẩu). */
const COMMON_PASSWORDS = ["12345678", "password", "matkhau123", "11111111", "abc12345"];

/**
 * Kiểm mật khẩu như Django AUTH_PASSWORD_VALIDATORS (câu tiếng Việt, nối bằng dấu cách). Rỗng = đạt.
 * Mô phỏng: ≥ 8 ký tự, không quá phổ biến, không toàn số, không quá giống tên đăng nhập.
 */
export function mockPasswordProblems(password: string, username: string): string {
  const out: string[] = [];
  if (password.length < 8) out.push(PW_PROBLEMS.PW_TOO_SHORT);
  if (COMMON_PASSWORDS.includes(password.toLowerCase())) out.push(PW_PROBLEMS.PW_COMMON);
  if (/^\d+$/.test(password)) out.push(PW_PROBLEMS.PW_NUMERIC);
  if (username && password.toLowerCase().includes(username.toLowerCase())) out.push(PW_PROBLEMS.PW_SIMILAR);
  return out.join(" ");
}

// POST /api/auth/token/
export function mockLogin(req: MockRequest): MockResponse {
  const { username, password } = (req.body || {}) as { username?: string; password?: string };
  const list = mockUsers();
  const u = list.find((x) => x.username.toLowerCase() === (username || "").trim().toLowerCase());
  if (!u || password !== u.password || !u.is_active) {
    return LOGIN_BAD;
  }
  u.last_login = new Date().toISOString();
  const token = issueToken(u);
  saveMockUsers(list);
  return { status: 200, body: { token } };
}

// GET /api/auth/me/
export function mockMe(req: MockRequest): MockResponse {
  const u = userFromToken(req.token);
  return u ? { status: 200, body: buildMe(u) } : MOCK_UNAUTHORIZED;
}

// POST /api/auth/logout/ (S46) — 204. DRF một token/người → thu hồi token của người đó (mọi máy, C8).
export function mockLogout(req: MockRequest): MockResponse {
  const u = userFromToken(req.token);
  if (!u) return MOCK_UNAUTHORIZED;
  const list = mockUsers();
  mockRevokeUserTokens(list, u.id);
  saveMockUsers(list);
  return { status: 204, body: null };
}

// POST /api/auth/change-password/ (S46) — thứ tự kiểm như BE L6: field lạ → mật khẩu hiện tại → độ mạnh.
export function mockChangePassword(req: MockRequest): MockResponse {
  const u = userFromToken(req.token);
  if (!u) return MOCK_UNAUTHORIZED;
  const body = (req.body || {}) as Record<string, unknown>;
  const extra = Object.keys(body).filter((k) => k !== "old_password" && k !== "new_password");
  if (extra.length) return beError("CP_FIELD_NOT_ALLOWED", { fields: extra.join(", ") });
  const oldPw = typeof body.old_password === "string" ? body.old_password : "";
  const newPw = typeof body.new_password === "string" ? body.new_password : "";
  if (!oldPw || oldPw !== u.password) return beError("AUTH_OLD_PASSWORD");
  if (!newPw) return beError("AUTH_NEW_REQUIRED");
  const weak = mockPasswordProblems(newPw, u.username);
  if (weak) return beError("AUTH_WEAK_PASSWORD", { problems: weak });
  const list = mockUsers();
  const rec = list.find((x) => x.id === u.id)!;
  rec.password = newPw;
  rec.must_change_password = false; // S48-AC2/AC6: tự đổi xong thì hết bị ép, không bật lại cờ
  mockRevokeUserTokens(list, rec.id); // máy khác của người này → 401 (S46-AC2)
  const token = issueToken(rec);
  saveMockUsers(list);
  return { status: 200, body: { token } };
}
