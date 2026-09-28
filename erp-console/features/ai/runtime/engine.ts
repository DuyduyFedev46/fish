// Cửa vào runtime (components chỉ import từ đây — KHÔNG import thẳng worker/model-downloader):
// chọn engine, đọc n_ctx từ env, gửi câu hỏi, dọn dẹp worker.
// BR-AI-16: production luôn chạy model thật; LLMock chỉ khi NEXT_PUBLIC_USE_MOCK=1.

import { AI_MSG } from "../messages";
import { workerManager, type ShutdownReason } from "./worker-manager";

let runtimeModelUrl: string | null = null;

/** Ghi URL model hiện dùng (tải xong hoặc có trong cache IndexedDB thì mới gọi). */
export function setRuntimeModelUrl(url: string | null): void {
  runtimeModelUrl = url;
}

/** Engine chạy: env NEXT_PUBLIC_AI_ENGINE ghi đè; mock → llmock; production → wllama (BR-AI-16). */
export function selectEngineName(): "llmock" | "wllama" {
  const env = process.env.NEXT_PUBLIC_AI_ENGINE;
  if (env === "llmock" || env === "wllama") return env;
  return process.env.NEXT_PUBLIC_USE_MOCK === "1" ? "llmock" : "wllama";
}

export const DEFAULT_MAX_CONTEXT_TOKENS = 2048;

/**
 * n_ctx từ NEXT_PUBLIC_AI_MAX_CONTEXT_TOKENS (Phụ lục A); sai/chỉ nằm ngoài 512..8192 → 2048.
 * KHÔNG BAO GIỜ dùng mặc định 32k của thư viện (H3 — máy yếu treo).
 */
export function maxContextTokens(): number {
  const raw = process.env.NEXT_PUBLIC_AI_MAX_CONTEXT_TOKENS;
  const n = raw ? Number(raw) : NaN;
  if (!Number.isFinite(n) || n < 512 || n > 8192) return DEFAULT_MAX_CONTEXT_TOKENS;
  return Math.floor(n);
}

/**
 * Hỏi trợ lý (on-device, không gọi mạng — S08-AC5). Ném AbortError khi bị thay bằng câu mới
 * hoặc khi đóng màn — component nuốt AbortError, hiện lỗi với lỗi thật.
 * Lô 1–2 engine llmock không cần model; engine wllama mà chưa có modelUrl → lỗi fail-closed.
 */
export function askAi(prompt: string, opts: { signal?: AbortSignal; onToken?: (t: string) => void } = {}): Promise<string> {
  const engine = selectEngineName();
  if (engine === "wllama" && !runtimeModelUrl) return Promise.reject(new Error(AI_MSG.modelNotPicked));
  return workerManager.ask(prompt, { engine, nCtx: maxContextTokens(), modelUrl: runtimeModelUrl }, opts);
}

/** Dọn worker (đóng màn AI / nghỉ 10 phút / đăng xuất / tắt AI — C.2 dòng 3). */
export function shutdownRuntime(reason: ShutdownReason): void {
  workerManager.shutdown(reason);
}
