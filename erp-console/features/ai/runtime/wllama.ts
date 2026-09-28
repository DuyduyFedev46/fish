// Khung gọi @wllama/wllama — Lô 1–3 CHỈ LÀ KHUNG (model thật chờ S17, BR-AI-16: production luôn model thật).
// import động + webpackIgnore: gói wllama CHƯA CÀI, nên không được để webpack cố phân giải lúc build;
// lúc chạy mà thiếu thư viện → ném lỗi tiếng Việt fail-closed (người dùng vẫn nhập tay được).
// LÔ 4 (S17 chốt model) — bật thật theo 4 bước:
//   1. `npm i @wllama/wllama` trong erp-console/.
//   2. Bỏ `/* webpackIgnore: true */` dưới đây (và xoá wllama.d.ts).
//   3. Chép wasm + js của wllama vào public/wllama/ theo README của thư viện; đối chiếu API thật
//      (loadModelFromUrl n_ctx, createChatCompletion onToken/nPredict) rồi sửa facade bên dưới cho khớp.
//   4. Worker hiện là classic worker (không importScripts) → đổi sang `new Worker(url, {type:"module"})`
//      HOẶC dùng importScripts để nạp wllama trong worker (xem worker-manager.ts).
// n_ctx: LUÔN theo NEXT_PUBLIC_AI_MAX_CONTEXT_TOKENS (mặc định 2048) — KHÔNG BAO GIỜ để mặc định 32k (H3).

import { AI_MSG } from "../messages";

export type WllamaFacade = {
  loadModelFromUrl(url: string, opts: { n_ctx: number }): Promise<unknown>;
  createChatCompletion(input: unknown, opts: unknown): Promise<string>;
  dispose(): void;
};

let lib: WllamaFacade | null = null;
let loaded = false;

async function loadLib(): Promise<WllamaFacade> {
  if (loaded) {
    if (!lib) throw new Error(AI_MSG.wllamaMissing);
    return lib;
  }
  try {
    const mod = (await import(
      /* webpackIgnore: true */
      "@wllama/wllama"
    )) as { Wllama?: new (...a: unknown[]) => WllamaFacade };
    if (!mod.Wllama) throw new Error(AI_MSG.wllamaMissing);
    lib = new mod.Wllama() as WllamaFacade;
    loaded = true;
    return lib;
  } catch {
    loaded = true;
    throw new Error(AI_MSG.wllamaMissing);
  }
}

/** Khởi tạo engine wllama + nạp model (từ URL công khai hoặc cache). */
export async function initWllama(opts: { nCtx: number; modelUrl: string | null }): Promise<void> {
  if (!opts.modelUrl) throw new Error(AI_MSG.modelNotPicked);
  const facade = await loadLib();
  await facade.loadModelFromUrl(opts.modelUrl, { n_ctx: opts.nCtx });
}

/**
 * Chạy một lượt hỏi. `isGone()` báo lượt này đã bị thay/huỷ — worker kiểm tra trước khi đẩy token.
 * API thật của wllama (onToken callback) sẽ được đối chiếu khi cài ở Lô 4.
 */
export async function inferWllama(
  id: number,
  prompt: string,
  onToken: (text: string) => void,
  isGone: () => boolean,
): Promise<void> {
  const facade = await loadLib();
  const out = await facade.createChatCompletion(
    { messages: [{ role: "user", content: prompt }] },
    { onToken: (token: string) => !isGone() && onToken(token) },
  );
  void id;
  void out;
}

/** Giải phóng engine (worker dispose / nghỉ 10 phút). */
export function disposeWllama(): void {
  if (lib) {
    try {
      lib.dispose();
    } catch {
      /* bỏ qua */
    }
    lib = null;
  }
}
