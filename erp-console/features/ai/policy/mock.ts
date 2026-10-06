// Mock "Chính sách AI" — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Mô phỏng BE (`apps/ai/policy`): PUT cần xác nhận trách nhiệm (BR-AI-14) và đúng phiên bản (409 AI_POLICY_CONFLICT);
// PUT cục bộ (chỉ `global_mode`) vẫn được; tắt/bật AI một nhân viên đổi thật `killed` trong danh sách. Dữ liệu GIẢ, không có tên/SĐT thật.

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { ROLE } from "@/shared/lib/roles";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import { mockGetMyConfig } from "../settings/mock";
import type { AiPolicy } from "../types";
import type { UpdateAiPolicyPayload } from "./api";

const state: AiPolicy = {
  version: 4,
  global_mode: "on",
  env: "staging",
  production_ready: false,
  red_zone: [
    {
      perm: "inventory.close_batch",
      label: "Chốt lô",
      open: false,
      commands: ["inventory.batch.close"],
      can_do: "Chỉ chốt lô đủ điều kiện, đã kiểm kê xong và 7 ngày không có chi phí mới.",
      cannot_do: "Biết chi phí phụ còn về hay không.",
      legal_note: "Chủ chịu trách nhiệm về số liệu kho và giá vốn đã chốt.",
      delay_minutes: 30,
    },
    {
      perm: "sales.confirm_refund",
      label: "Xác nhận đã hoàn tiền",
      open: false,
      commands: ["sales.refund.confirm"],
      can_do: "Soát phiếu hoàn tiền theo quy định.",
      cannot_do: "Tự chuyển tiền ngoài ngân hàng.",
      legal_note: "Chủ xác nhận giao dịch tiền thật.",
      delay_minutes: 0,
    },
    {
      perm: "sales.confirm_payment_manual",
      label: "Xác nhận đã nhận tiền",
      open: false,
      commands: ["sales.salesorder.confirm_payment", "sales.paymenttransaction.resolve"],
      can_do: "Khớp giao dịch ngân hàng vào đơn hàng.",
      cannot_do: "Kiểm tra sao kê ngoài hệ thống.",
      legal_note: "Chịu trách nhiệm về việc khớp tiền.",
      delay_minutes: 0,
    },
  ],
  caps: { [RECEIVE_BATCHES_COMMAND_ID]: { kg: "200", vnd: "30000000", daily: 20 } },
  users: [
    { user_id: 1, display_name: "Chủ vựa (demo)", groups: [ROLE.owner], killed: false, config_version: 3, counts: { A: 12, B: 1, C: 20, OFF: 2 } },
    { user_id: 2, display_name: "Quản lý 1 (demo)", groups: [ROLE.manager], killed: false, config_version: 2, counts: { A: 9, B: 0, C: 14, OFF: 1 } },
    { user_id: 3, display_name: "Kho 1 (demo)", groups: [ROLE.warehouseStaff], killed: false, config_version: 1, counts: { A: 8, B: 1, C: 5, OFF: 0 } },
    { user_id: 4, display_name: "Giao 1 (demo)", groups: [ROLE.deliveryStaff], killed: true, config_version: 1, counts: { A: 8, B: 0, C: 5, OFF: 0 } },
  ],
};

function snapshot(): AiPolicy {
  return JSON.parse(JSON.stringify(state)) as AiPolicy;
}

export function mockGetPolicy(): MockResponse {
  return { status: 200, body: snapshot() };
}

export function mockUpdatePolicy(req: MockRequest): MockResponse {
  // Đọc thân đã qua JSON như BE thấy.
  const sent = req.body as UpdateAiPolicyPayload;
  if (!sent.acknowledge_responsibility) {
    return { status: 400, body: { detail: "Bạn phải xác nhận chịu trách nhiệm cho chính sách AI.", code: "BR-AI-14" } };
  }
  if (sent.base_version !== state.version) {
    return { status: 409, body: { detail: "Chính sách AI đã thay đổi ở phiên khác.", code: "AI_POLICY_CONFLICT" } };
  }
  state.version = sent.base_version + 1;
  if (sent.global_mode) state.global_mode = sent.global_mode;
  if (sent.caps) state.caps = sent.caps;
  if (sent.red_zone) {
    const open = sent.red_zone;
    state.red_zone = state.red_zone.map((rz) => ({ ...rz, open: open[rz.perm] !== undefined ? open[rz.perm] : rz.open }));
  }
  return { status: 200, body: snapshot() };
}

export function mockKillUser(userId: number, killed: boolean): MockResponse {
  const u = state.users.find((x) => x.user_id === userId);
  if (!u) return { status: 404, body: { detail: "Không tìm thấy nhân viên.", code: "NOT_FOUND" } };
  u.killed = killed;
  return { status: 200, body: { version: u.config_version + 1, killed, user_id: userId } };
}

export function mockUserConfig(userId: number): MockResponse {
  const u = state.users.find((x) => x.user_id === userId);
  if (!u) return { status: 404, body: { detail: "Không tìm thấy nhân viên.", code: "NOT_FOUND" } };
  return { status: 200, body: { ...mockGetMyConfig(), killed: u.killed, version: u.config_version } };
}
