import { apiFetch } from "@/shared/lib/http";
import type { MyConfig } from "../types";
import type { MyConfigSavePayload } from "./payload";
import { mockGetMyConfig, mockKillMyConfig, mockUpdateMyConfig } from "./mock";

// Điều kiện mock viết nguyên văn tại từng chỗ dùng (không gán ra biến): bundler mới cắt nhánh mock khỏi bản build thật.
// Mọi thân yêu cầu truyền là OBJECT: `apiFetch` tự JSON.stringify (không tự stringify lần nữa, SR-AIS-01).

export async function getMyConfig(signal?: AbortSignal): Promise<MyConfig> {
  return apiFetch<MyConfig>("/api/ai/my-config/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockGetMyConfig() }) : undefined,
  });
}

/** Thân phải đủ `groups`, `overrides`, `limits` (BE thay thế toàn bộ, xem ./payload.ts) — dựng bằng `buildMyConfigPayload`. */
export async function updateMyConfig(
  payload: MyConfigSavePayload,
  signal?: AbortSignal
): Promise<MyConfig> {
  return apiFetch<MyConfig>("/api/ai/my-config/", {
    method: "PUT",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockUpdateMyConfig(req.body) : undefined,
  });
}

export async function killMyConfig(killed: boolean, signal?: AbortSignal): Promise<{ version: number; killed: boolean }> {
  return apiFetch<{ version: number; killed: boolean }>("/api/ai/my-config/kill/", {
    method: "POST",
    body: { killed },
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockKillMyConfig(req.body) : undefined,
  });
}
