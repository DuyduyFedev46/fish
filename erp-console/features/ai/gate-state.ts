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

let enabled = false;
const listeners = new Set<() => void>();

/** Chỉ `getAiStatus` (features/ai/api.ts) gọi hàm này. */
export function publishAiEnabled(v: boolean): void {
  if (enabled === v) return;
  enabled = v;
  listeners.forEach((cb) => cb());
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
