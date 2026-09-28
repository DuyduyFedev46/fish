// Vòng đời worker (C.2 dòng 3):
// - Tạo worker khi DÙNG AI LẦN ĐẦU (không tạo sớm — AI tắt = 0 worker, C.4 #10).
// - Đóng màn AI / đăng xuất / tắt AI → shutdown() → terminate().
// - Nhàn 10 phút → shutdown("idle") kèm dispose().
// - Hàng đợi 1 việc: hỏi mới HUỶ việc cũ (abort + cancel message) — không xếp hàng dài.
// - n_ctx từ NEXT_PUBLIC_AI_MAX_CONTEXT_TOKENS (engine.ts) — không bao giờ 32k (H3).

export const AI_IDLE_MS = 10 * 60 * 1000;

export type InferenceInit = {
  engine: "llmock" | "wllama";
  nCtx: number;
  modelUrl: string | null;
};

export type AskOptions = {
  signal?: AbortSignal;
  onToken?: (text: string) => void;
};

export type ShutdownReason = "close" | "idle" | "unmount";

type Pending = {
  id: number;
  abort: AbortController;
  onToken?: (text: string) => void;
  resolve: (text: string) => void;
  reject: (err: Error) => void;
};

export class WorkerManager {
  private worker: Worker | null = null;
  private readyPromise: Promise<void> | null = null;
  private init: InferenceInit | null = null;
  private pending: Pending | null = null;
  private seq = 0;
  private idleTimer: ReturnType<typeof setTimeout> | null = null;

  private get isIdleTimeoutSupported(): boolean {
    return typeof setTimeout === "function";
  }

  /** Hỏi một câu — tạo worker lần đầu nếu chưa có; hỏi mới huỷ câu cũ đang chờ/đang chạy. */
  async ask(prompt: string, init: InferenceInit, opts: AskOptions = {}): Promise<string> {
    // Huỷ lượt trước (nếu có) — một việc một lúc (BR-AI-17, H4).
    this.pending?.abort.abort();
    this.pending?.reject(abortError());
    this.pending = null;

    const w = await this.ensure(init);
    const id = ++this.seq;
    const ctrl = new AbortController();
    const promise = new Promise<string>((resolve, reject) => {
      this.pending = { id, abort: ctrl, onToken: opts.onToken, resolve, reject };
      ctrl.signal.addEventListener("abort", () => {
        if (this.pending?.id !== id) return;
        w.postMessage({ type: "cancel", id });
        reject(abortError());
      });
      w.postMessage({ type: "infer", id, prompt });
      this.bumpIdle();
    });
    opts.signal?.addEventListener("abort", () => ctrl.abort());
    try {
      return await promise;
    } finally {
      if (this.pending?.id === id) this.pending = null;
      this.bumpIdle();
    }
  }

  /** Tạo worker + init lần đầu; init lỗi → ném lỗi tiếng Việt, worker vẫn dùng lại được sau. */
  private async ensure(init: InferenceInit): Promise<Worker> {
    if (this.worker && this.init?.engine === init.engine && this.init.nCtx === init.nCtx && this.init.modelUrl === init.modelUrl && this.readyPromise) {
      return this.worker;
    }
    this.shutdown("unmount"); // đổi engine/ctx/model → dựng lại
    const w = new Worker(new URL("./worker.ts", import.meta.url));
    this.worker = w;
    this.init = init;
    this.readyPromise = new Promise<void>((resolve, reject) => {
      w.onmessage = (e: MessageEvent<{ type: string; message?: string }>) => {
        const m = e.data;
        if (m.type === "ready") resolve();
        else if (m.type === "init-error") reject(new Error(m.message || "Khởi tạo trợ lý không xong."));
      };
      w.onerror = () => reject(new Error("Worker trợ lý lỗi."));
      w.postMessage({ type: "init", engine: init.engine, nCtx: init.nCtx, modelUrl: init.modelUrl });
    });
    // Sau khi ready, chuyển listener sang định tuyến kết quả suy luận.
    await this.readyPromise;
    w.onmessage = (e: MessageEvent<{ type: string; id?: number; text?: string; message?: string }>) => this.route(e.data);
    w.onerror = () => this.failPending(new Error("Worker trợ lý lỗi."));
    return w;
  }

  private route(m: { type: string; id?: number; text?: string; message?: string }): void {
    if (m.id !== undefined && this.pending && this.pending.id === m.id) {
      const p = this.pending;
      if (m.type === "token" && m.text) p.onToken?.(m.text);
      else if (m.type === "done") {
        this.pending = null;
        this.bumpIdle();
        p.resolve(m.text ?? "");
      } else if (m.type === "error") {
        this.pending = null;
        this.bumpIdle();
        p.reject(new Error(m.message || "Trợ lý chưa trả lời được."));
      }
    }
  }

  private failPending(err: Error): void {
    this.pending?.reject(err);
    this.pending = null;
  }

  /** Hoạt động AI → lùi đồng hồ nhàn 10 phút. */
  private bumpIdle(): void {
    if (!this.isIdleTimeoutSupported) return;
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => this.shutdown("idle"), AI_IDLE_MS);
  }

  /** Dừng worker + giải phóng engine (close/logout/tắt AI → "close"/"unmount"; nhàn → "idle"). */
  shutdown(reason: ShutdownReason): void {
    if (this.idleTimer) {
      clearTimeout(this.idleTimer);
      this.idleTimer = null;
    }
    const w = this.worker;
    this.worker = null;
    this.readyPromise = null;
    this.init = null;
    this.failPending(abortError());
    if (!w) return;
    try {
      if (reason === "idle") w.postMessage({ type: "dispose" });
      w.terminate();
    } catch {
      /* bỏ qua */
    }
  }
}

function abortError(): Error {
  return new DOMException("The operation was aborted.", "AbortError");
}

/** Singleton cho toàn màn AI. */
export const workerManager = new WorkerManager();
