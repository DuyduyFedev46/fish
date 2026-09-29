import { apiFetch, type MockRequest } from "@/shared/lib/http";
import type { MyConfig } from "../types";

export const mockMyConfig: MyConfig = {
  ai_enabled: true,
  version: 1,
  killed: false,
  updated_at: new Date().toISOString(),
  global_mode: "on",
  write_levels_allowed: ["OFF", "C", "B"],
  groups: [
    {
      group: "thu_mua",
      label: "Thu mua",
      read_level: "A",
      write_level: "C",
      commands: [
        {
          id: "inventory.batch.list",
          title: "Xem tồn kho theo lô",
          kind: "read",
          level: "A",
          source: "default",
          choices: ["OFF", "A"],
          max_level: "A",
          locked_reason: null,
          red_zone: false,
          limits: null,
        },
        {
          id: "purchasing.purchasereceipt.submit",
          title: "Gửi phiếu nhập kho",
          kind: "write",
          level: "C",
          source: "default",
          choices: ["OFF", "C"],
          max_level: "C",
          locked_reason: null,
          red_zone: false,
          limits: null,
        },
        {
          id: "purchasing.purchasereceipt.nhap_lo",
          title: "Nhập lô mua tại cảng",
          kind: "write",
          level: "C",
          source: "default",
          choices: ["OFF", "C", "B"],
          max_level: "B",
          locked_reason: null,
          red_zone: false,
          limits: {
            kg: { mine: null, cap: "200" },
            vnd: { mine: null, cap: "30000000" },
          },
        },
      ],
    },
    {
      group: "ban_hang",
      label: "Bán hàng",
      read_level: "A",
      write_level: "C",
      commands: [],
    },
    {
      group: "cskh",
      label: "CSKH",
      read_level: "A",
      write_level: "C",
      commands: [],
    },
  ],
};

export async function getMyConfig(signal?: AbortSignal): Promise<MyConfig> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<MyConfig>("/api/ai/my-config/", {
    signal,
    mock: isMock ? (_req: MockRequest) => ({ status: 200, body: mockMyConfig }) : undefined,
  });
}

export async function updateMyConfig(
  payload: {
    base_version: number;
    groups?: Record<string, { read?: string; write?: string }>;
    overrides?: Record<string, string>;
    limits?: Record<string, unknown>;
    acknowledge_responsibility: boolean;
  },
  signal?: AbortSignal
): Promise<MyConfig> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<MyConfig>("/api/ai/my-config/", {
    method: "PUT",
    body: JSON.stringify(payload),
    signal,
    mock: isMock
      ? (_req: MockRequest) => ({
          status: 200,
          body: {
            ...mockMyConfig,
            version: payload.base_version + 1,
            updated_at: new Date().toISOString(),
          },
        })
      : undefined,
  });
}

export async function killMyConfig(
  killed: boolean,
  signal?: AbortSignal
): Promise<{ version: number; killed: boolean }> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<{ version: number; killed: boolean }>("/api/ai/my-config/kill/", {
    method: "POST",
    body: JSON.stringify({ killed }),
    signal,
    mock: isMock
      ? (_req: MockRequest) => ({
          status: 200,
          body: { version: mockMyConfig.version + 1, killed },
        })
      : undefined,
  });
}
