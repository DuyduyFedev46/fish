// API "Chính sách AI" của Chủ (ED-42 / W4c): đọc/ghi chính sách, tắt/bật AI từng người, xem cấu hình từng người (chỉ đọc).
// Thân PUT/POST là object một lớp JSON (SR-AIS-01). Nhánh mock ở ./mock.ts, chỉ nối khi NEXT_PUBLIC_USE_MOCK=1.

import { apiFetch } from "@/shared/lib/http";
import type { AiPolicy, MyConfig, PolicyCaps } from "../types";
import { mockGetPolicy, mockKillUser, mockUpdatePolicy, mockUserConfig } from "./mock";

export interface UpdateAiPolicyPayload {
  base_version: number;
  global_mode?: "on" | "c_only" | "off";
  red_zone?: Record<string, boolean>;
  caps?: PolicyCaps;
  acknowledge_responsibility: boolean;
}

export async function getAiPolicy(signal?: AbortSignal): Promise<AiPolicy> {
  return apiFetch<AiPolicy>("/api/ai/policy/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockGetPolicy() : undefined,
  });
}

export async function updateAiPolicy(payload: UpdateAiPolicyPayload, signal?: AbortSignal): Promise<AiPolicy> {
  return apiFetch<AiPolicy>("/api/ai/policy/", {
    method: "PUT",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockUpdatePolicy : undefined,
  });
}

export async function killUserAi(
  userId: number,
  killed: boolean,
  signal?: AbortSignal,
): Promise<{ version: number; killed: boolean; user_id: number }> {
  return apiFetch<{ version: number; killed: boolean; user_id: number }>(`/api/ai/policy/users/${userId}/kill/`, {
    method: "POST",
    body: { killed },
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockKillUser(userId, killed) : undefined,
  });
}

export async function getUserAiConfig(userId: number, signal?: AbortSignal): Promise<MyConfig> {
  return apiFetch<MyConfig>(`/api/ai/policy/users/${userId}/config/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockUserConfig(userId) : undefined,
  });
}
