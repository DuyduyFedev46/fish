import { apiFetch, type MockRequest } from "@/shared/lib/http";
import { AiPolicy, MyConfig } from "../types";

const mockAiPolicy: AiPolicy = {
  version: 1,
  global_mode: "on",
  env: "staging",
  production_ready: false,
  red_zone: [
    {
      perm: "inventory.close_batch",
      label: "Chốt lô",
      open: false,
      commands: ["inventory.batch.close"],
      can_do: "Chỉ lô đủ điều kiện BR-LO-04 + kiểm kê đã duyệt + 7 ngày không có chi phí mới",
      cannot_do: "Biết chi phí phụ còn về hay không",
      legal_note: "Chủ chịu trách nhiệm về số liệu kho và chốt giá vốn lô.",
      delay_minutes: 30,
    },
    {
      perm: "sales.confirm_refund",
      label: "Xác nhận hoàn tiền",
      open: false,
      commands: ["sales.refund.confirm"],
      can_do: "Soát xét phiếu hoàn tiền theo quy định",
      cannot_do: "Tự động chuyển tiền ngoài ngân hàng",
      legal_note: "Chủ xác nhận giao dịch tiền thật.",
      delay_minutes: 0,
    },
    {
      perm: "sales.confirm_payment_manual",
      label: "Xác nhận thanh toán tay",
      open: false,
      commands: ["sales.salesorder.confirm_payment", "sales.paymenttransaction.resolve"],
      can_do: "Khớp giao dịch ngân hàng vào đơn hàng",
      cannot_do: "Xác minh sao kê ngoài hệ thống",
      legal_note: "Chịu trách nhiệm về việc khớp tiền.",
      delay_minutes: 0,
    },
  ],
  caps: [],
  users: [
    {
      user_id: 1,
      display_name: "Lộc (Chủ vựa)",
      groups: ["chu"],
      killed: false,
      config_version: 3,
      counts: { A: 12, B: 0, C: 20, OFF: 2 },
    },
    {
      user_id: 2,
      display_name: "Kho 1",
      groups: ["nv_kho"],
      killed: false,
      config_version: 1,
      counts: { A: 8, B: 0, C: 5, OFF: 0 },
    },
  ],
};

export async function getAiPolicy(signal?: AbortSignal): Promise<AiPolicy> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<AiPolicy>("/api/ai/policy/", {
    signal,
    mock: isMock ? (_req: MockRequest) => ({ status: 200, body: mockAiPolicy }) : undefined,
  });
}

export async function updateAiPolicy(
  payload: {
    base_version: number;
    global_mode?: "on" | "c_only" | "off";
    red_zone?: Record<string, boolean>;
    caps?: Record<string, unknown>;
    acknowledge_responsibility: boolean;
  },
  signal?: AbortSignal
): Promise<AiPolicy> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<AiPolicy>("/api/ai/policy/", {
    method: "PUT",
    body: JSON.stringify(payload),
    signal,
    mock: isMock
      ? (_req: MockRequest) => ({
          status: 200,
          body: {
            ...mockAiPolicy,
            version: payload.base_version + 1,
            global_mode: payload.global_mode || mockAiPolicy.global_mode,
          },
        })
      : undefined,
  });
}

export async function killUserAi(
  userId: number,
  killed: boolean,
  signal?: AbortSignal
): Promise<{ version: number; killed: boolean; user_id: number }> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<{ version: number; killed: boolean; user_id: number }>(
    `/api/ai/policy/users/${userId}/kill/`,
    {
      method: "POST",
      body: JSON.stringify({ killed }),
      signal,
      mock: isMock
        ? (_req: MockRequest) => ({
            status: 200,
            body: { version: 2, killed, user_id: userId },
          })
        : undefined,
    }
  );
}

export async function getUserAiConfig(userId: number, signal?: AbortSignal): Promise<MyConfig> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<MyConfig>(`/api/ai/policy/users/${userId}/config/`, {
    signal,
    mock: isMock
      ? (_req: MockRequest) => ({
          status: 200,
          body: {
            ai_enabled: true,
            version: 1,
            killed: false,
            updated_at: new Date().toISOString(),
            global_mode: "on",
            write_levels_allowed: ["OFF", "C"],
            groups: [],
          },
        })
      : undefined,
  });
}
