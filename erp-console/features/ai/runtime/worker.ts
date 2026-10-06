// Worker suy luận on-device (C.2 dòng 3) — chạy ngoài luồng chính để UI không khựng (BR-AI-17).
// Giao thức (một kênh postMessage):
//   VÀO:  init {engine:"llmock"|"wllama", nCtx, modelUrl}   → RA: ready | init-error {message}
//   VÀO:  infer {id, prompt}                                → RA: token {id, text} · done {id, text} · error {id, message}
//   VÀO:  cancel {id}                                       (bỏ mọi token còn bay của id đó)
//   VÀO:  dispose                                           (tắt engine, xong tự kết thúc)
// KHÔNG log prompt (S08-AC8). KHÔNG gọi mạng khi suy luận (on-device, S08-AC5).
// Lô 1–3: engine llmock (câu giả). Lô 4 (S17): engine wllama qua ./wllama.

import { disposeWllama, inferWllama, initWllama } from "./wllama";

type InMsg =
  | { type: "init"; engine: "llmock" | "wllama"; nCtx: number; modelUrl: string | null }
  | { type: "infer"; id: number; prompt: string }
  | { type: "cancel"; id: number }
  | { type: "dispose" };

type OutMsg =
  | { type: "ready" }
  | { type: "init-error"; message: string }
  | { type: "token"; id: number; text: string }
  | { type: "done"; id: number; text: string }
  | { type: "error"; id: number; message: string };

// dom lib: `self.postMessage` trỏ tới kiểu Window — ép sang kiểu worker thật.
const ctx = self as unknown as {
  postMessage(m: OutMsg): void;
  onmessage: ((e: MessageEvent<InMsg>) => void) | null;
};

let engine: "llmock" | "wllama" | null = null;
let nCtx = 2048;
let modelUrl: string | null = null;
let ready = false;
/** id đang suy luận — token nào lạc id thì bỏ (hàng đợi 1 việc, việc mới huỷ việc cũ). */
let activeId = 0;
const cancelled = new Set<number>();

function isGone(id: number): boolean {
  return cancelled.has(id) || activeId !== id;
}

// ================= LLMock — Lô 1–2: câu GIẢ, không đọc sổ sách thật =================

function llmockAnswer(prompt: string): string {
  const p = prompt.toLowerCase();
  if (p.includes("cá thu")) {
    return "Hiện còn 12 kg cá thu tươi trong kho (B-01, B-03). Lô B-01 còn 1 ngày hết hạn dùng — nên bán trước. (Số liệu giả.)";
  }
  if (p.includes("hạn") || p.includes("hết hạn")) {
    return "Lô sắp tới hạn nhất là B-01 · Cá thu (còn 1 ngày). B-02 · Cá hồi còn 3 ngày. Nên ưu tiên xuất B-01 trước vì hạn dùng sớm hơn. (Số liệu giả.)";
  }
  if (p.includes("đơn")) {
    return "Hôm nay có 4 đơn đang chờ giao và 1 đơn chờ thanh toán. Đơn SO-20260927-041 đang Giữ chỗ. (Số liệu giả.)";
  }
  if (p.includes("lô") || p.includes("báo cáo")) {
    return "Đang có 6 lô mở bán. B-06 · Cá chim mới mở hôm qua, còn 20 kg. Muốn xem lãi lỗ thì mở màn Báo cáo lãi lỗ. (Số liệu giả.)";
  }
  return "Mình đang ở chế độ thử với dữ liệu giả nên chưa đọc được sổ sách thật. Bạn thử hỏi về tồn kho, lô cận hạn hay đơn đang chờ nhé. (Số liệu giả.)";
}

async function inferLlMock(id: number, prompt: string): Promise<void> {
  const answer = llmockAnswer(prompt);
  for (let i = 0; i < answer.length; i += 4) {
    if (isGone(id)) return;
    ctx.postMessage({ type: "token", id, text: answer.slice(i, i + 4) });
    await new Promise((r) => setTimeout(r, 30));
  }
  if (!isGone(id)) ctx.postMessage({ type: "done", id, text: answer });
}

// ================= Vòng đời =================

async function handleInit(m: Extract<InMsg, { type: "init" }>): Promise<void> {
  engine = m.engine;
  nCtx = m.nCtx;
  modelUrl = m.modelUrl;
  if (engine === "wllama") {
    try {
      await initWllama({ nCtx, modelUrl });
    } catch (err) {
      ctx.postMessage({ type: "init-error", message: err instanceof Error ? err.message : String(err) });
      return;
    }
  }
  ready = true;
  ctx.postMessage({ type: "ready" });
}

async function handleInfer(m: Extract<InMsg, { type: "infer" }>): Promise<void> {
  if (!ready || !engine) {
    ctx.postMessage({ type: "error", id: m.id, message: "Chưa sẵn sàng." });
    return;
  }
  activeId = m.id;
  try {
    if (engine === "wllama") {
      await inferWllama(m.id, m.prompt, (text) => {
        if (!isGone(m.id)) ctx.postMessage({ type: "token", id: m.id, text });
      }, () => isGone(m.id));
    } else {
      await inferLlMock(m.id, m.prompt);
    }
  } catch (err) {
    if (!isGone(m.id)) {
      ctx.postMessage({ type: "error", id: m.id, message: err instanceof Error ? err.message : String(err) });
    }
  }
}

ctx.onmessage = (e: MessageEvent<InMsg>) => {
  const m = e.data;
  switch (m.type) {
    case "init":
      void handleInit(m);
      return;
    case "infer":
      void handleInfer(m);
      return;
    case "cancel":
      cancelled.add(m.id);
      return;
    case "dispose":
      try {
        disposeWllama();
      } catch {
        /* bỏ qua */
      }
      ready = false;
      engine = null;
      return;
  }
};
