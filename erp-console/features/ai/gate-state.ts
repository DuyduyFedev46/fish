// Trạng thái "AI bật VÀ đã đồng ý" dùng chung cho màn nghiệp vụ (SR-20, BR-AI-17).
//
// Vì sao có file này: `GuidancePanel` (Tiếp theo · Đã làm) nằm ở 4 màn nghiệp vụ. Trước đây nó tự gọi
// `/api/ai/status/` và import tĩnh runtime AI, nên chunk có `new Worker`/`wllama` bị tải kể cả khi AI tắt.
// Giờ chỉ có cánh cổng trợ lý (AiAssistantGate, gọi status khi người dùng mở tab Trợ lý) gọi status; kết quả
// được `getAiStatus` ghi vào đây, màn nghiệp vụ chỉ ĐỌC. Chưa ai hỏi status → coi như tắt (fail-closed).
//
// File này MỎNG có chủ đích: không import runtime/, voice/, chat/ — chunk layout nạp tĩnh nó.

import { useSyncExternalStore } from "react";
import { hasAiConsent, subscribeAiConsent } from "./consent";

/** Mỗi "người hỏi status" là một chủ: cờ = có ít nhất một chủ đang báo bật. Trang chi tiết (AiDocBlockGate) là chủ riêng
 * và nhả khi rời trang, nên cờ không dính theo lịch sử điều hướng (review Lô 2, L2). Cổng trợ lý ở khung dùng chủ chung. */
export type AiGateOwner = symbol;
const SHARED_OWNER: AiGateOwner = Symbol("shared");
const owners = new Map<AiGateOwner, boolean>();
let enabled = false;
const listeners = new Set<() => void>();

function recompute(): void {
  const next = [...owners.values()].some(Boolean);
  if (next === enabled) return;
  enabled = next;
  listeners.forEach((cb) => cb());
}

/** Chỉ `getAiStatus` (features/ai/api.ts) gọi hàm này. `owner` bỏ trống = chủ chung (không bao giờ nhả). */
export function publishAiEnabled(v: boolean, owner: AiGateOwner = SHARED_OWNER): void {
  owners.set(owner, v);
  recompute();
}

/** Chủ riêng nhả phần của mình (rời trang). Chủ chung không nhả. */
export function releaseAiEnabled(owner: AiGateOwner): void {
  if (owner === SHARED_OWNER) return;
  owners.delete(owner);
  recompute();
}

/** Cờ "AI bật" thô (chưa tính đồng ý) — để test. */
export function isAiFlagOn(): boolean {
  return enabled;
}

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  const offConsent = subscribeAiConsent(cb);
  return () => {
    listeners.delete(cb);
    offConsent();
  };
}

function snapshot(): boolean {
  return enabled && hasAiConsent();
}

/** true khi AI đang bật ở hệ thống VÀ người dùng đã đồng ý tải model. Server/lần render đầu: false. */
export function useAiEnabledAndConsented(): boolean {
  return useSyncExternalStore(subscribe, snapshot, () => false);
}
