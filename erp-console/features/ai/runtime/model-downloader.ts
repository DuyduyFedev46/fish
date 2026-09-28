// Tải model GGUF TUẦN TỰ full-file (C.2 dòng 4): KHÔNG có "core trước, full sau".
// - Chia đoạn Range 64 MB (≤ 512 MB/đoạn — H5), tải lần lượt, hợp nhất bằng Blob.
// - % + tốc độ (cửa sổ trượt) + ETA; tạm dừng / tải tiếp / huỷ.
// - Giữa các đoạn kiểm tra lại mạng: đang dùng di động → TỰ tạm dừng (S08-AC2), chờ người bấm "Tải tiếp".
// - Server không hỗ trợ Range (python http.server phục vụ file test) → chuyển một lượt streaming.
// - Cache IndexedDB do components/AiAssistantPanel ghi khi onDone — file này không đụng IndexedDB.

import { detectAiCapability } from "./feature-detect";

export const GGUF_CHUNK_BYTES = 64 * 1024 * 1024;

export type DownloadPhase = "idle" | "downloading" | "paused" | "done" | "cancelled" | "error";

export type DownloadState = {
  phase: DownloadPhase;
  receivedBytes: number;
  totalBytes: number | null;
  /** 0–100, làm tròn. */
  percent: number;
  bytesPerSec: number;
  /** Giây còn lại; null = chưa đo được tốc độ. */
  etaSeconds: number | null;
};

type Handlers = {
  onState: (s: DownloadState) => void;
  onDone: (blob: Blob, meta: { etag: string | null; bytes: number }) => void;
};

export class GgufDownloader {
  private url: string;
  private handlers: Handlers;
  private parts: Uint8Array[] = [];
  private received = 0;
  private total: number | null = null;
  private etag: string | null = null;
  private phase: DownloadPhase = "idle";
  private ctrl: AbortController | null = null;
  private gen = 0;
  /** Tốc độ: mẫu [bytes, lúc (ms)] trong 5 giây gần nhất. */
  private speedSamples: { b: number; t: number }[] = [];
  private lastSpeed = 0;

  constructor(url: string, handlers: Handlers) {
    this.url = url;
    this.handlers = handlers;
  }

  state(): DownloadState {
    return {
      phase: this.phase,
      receivedBytes: this.received,
      totalBytes: this.total,
      percent: this.total && this.total > 0 ? Math.round((this.received / this.total) * 100) : 0,
      bytesPerSec: Math.round(this.lastSpeed),
      etaSeconds: this.eta(),
    };
  }

  private eta(): number | null {
    if (!this.lastSpeed || this.lastSpeed <= 0) return null;
    if (!this.total || this.total <= this.received) return null;
    return Math.round((this.total - this.received) / this.lastSpeed);
  }

  private sampleSpeed(bytes: number): void {
    const now = Date.now();
    const win = now - 5000;
    this.speedSamples = this.speedSamples.filter((s) => s.t >= win);
    this.speedSamples.push({ b: bytes, t: now });
    const first = this.speedSamples[0];
    const span = Math.max(1, (now - first.t) / 1000);
    const sum = this.speedSamples.reduce((acc, s) => acc + s.b, 0);
    this.lastSpeed = sum / span;
  }

  private emit(): void {
    this.handlers.onState(this.state());
  }

  private setPhase(p: DownloadPhase): void {
    this.phase = p;
    this.emit();
  }

  /** Bắt đầu / tải tiếp từ vị trí đang dừng. */
  start(): void {
    if (this.phase === "downloading" || this.phase === "done") return;
    if (this.phase === "cancelled" || this.phase === "error") this.reset();
    void this.run();
  }

  private reset(): void {
    this.parts = [];
    this.received = 0;
    this.total = null;
    this.etag = null;
    this.lastSpeed = 0;
    this.speedSamples = [];
    this.phase = "idle";
  }

  /** Tạm dừng — giữ các đoạn đã tải, "Tải tiếp" nối từ đó. */
  pause(): void {
    if (this.phase !== "downloading") return;
    this.gen += 1;
    this.ctrl?.abort();
    this.ctrl = null;
    this.setPhase("paused");
  }

  /** Huỷ hẳn — bỏ toàn bộ đoạn đã tải. */
  cancel(): void {
    this.gen += 1;
    this.ctrl?.abort();
    this.ctrl = null;
    this.parts = [];
    this.received = 0;
    this.lastSpeed = 0;
    this.speedSamples = [];
    this.setPhase("cancelled");
  }

  private async run(): Promise<void> {
    const gen = ++this.gen;
    this.ctrl = new AbortController();
    const signal = this.ctrl.signal;
    this.setPhase("downloading");
    this.speedSamples = [];
    this.lastSpeed = 0;
    try {
      // Kiểm tra mạng ngay khi bắt đầu.
      if (detectAiCapability().network === "cellular") {
        this.setPhase("paused");
        return;
      }
      // Thử Range trước: bytes=0-1 để đọc tổng dung lượng + ETag.
      const probe = await fetch(this.url, { headers: { Range: "bytes=0-1" }, signal });
      if (probe.status === 206) {
        this.etag = probe.headers.get("ETag");
        const cr = probe.headers.get("Content-Range");
        const m = cr && /bytes \d+-\d+\/(\d+|\*)/.exec(cr);
        this.total = m && m[1] !== "*" ? Number(m[1]) : this.total;
        await probe.arrayBuffer().catch(() => undefined); // bỏ 2 byte probe
        this.emit();
        await this.downloadRange(gen, signal);
      } else if (probe.status === 200) {
        // Server không hỗ trợ Range (file test) → một lượt streaming.
        await probe.body?.cancel();
        await this.downloadSinglePass(gen, signal);
      } else {
        throw new Error(`HTTP ${probe.status}`);
      }
      if (gen !== this.gen) return; // đã bị pause/cancel giữa chừng
      const blob = new Blob(this.parts as BlobPart[]);
      this.phase = "done";
      this.emit();
      this.handlers.onDone(blob, { etag: this.etag, bytes: this.received });
    } catch (err) {
      if (gen !== this.gen) return; // abort do pause/cancel — không phải lỗi
      if (signal.aborted) return;
      this.setPhase("error");
    }
  }

  /** Tải từng đoạn 64 MB; trước mỗi đoạn kiểm tra Wi-Fi → di động thì tạm dừng. */
  private async downloadRange(gen: number, signal: AbortSignal): Promise<void> {
    for (;;) {
      if (gen !== this.gen) return;
      if (detectAiCapability().network === "cellular") {
        this.setPhase("paused");
        return;
      }
      const start = this.received;
      const end = start + GGUF_CHUNK_BYTES - 1;
      const res = await fetch(this.url, { headers: { Range: `bytes=${start}-${end}` }, signal });
      if (gen !== this.gen) return;
      if (res.status === 206) {
        const buf = new Uint8Array(await res.arrayBuffer());
        if (buf.length === 0) {
          // Server trả đoạn rỗng (quá cuối file) → coi như xong.
          return;
        }
        this.parts.push(buf);
        this.received += buf.length;
        if (this.total === null) {
          const cr = res.headers.get("Content-Range");
          const m = cr && /bytes \d+-\d+\/(\d+)/.exec(cr);
          if (m) this.total = Number(m[1]);
        }
        if (!this.etag) this.etag = res.headers.get("ETag");
        this.sampleSpeed(buf.length);
        this.emit();
        if (this.total !== null && this.received >= this.total) return;
      } else if (res.status === 200) {
        // Server bỏ Range giữa chừng → huỷ, chuyển một lượt từ đầu.
        await res.body?.cancel();
        this.reset();
        await this.downloadSinglePass(gen, signal);
        return;
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    }
  }

  /** Một lượt streaming khi server không hỗ trợ Range — không nối tiếp được nên bỏ đoạn cũ nếu có. */
  private async downloadSinglePass(gen: number, signal: AbortSignal): Promise<void> {
    if (this.received > 0) this.reset();
    const res = await fetch(this.url, { signal });
    if (gen !== this.gen) return;
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    this.etag = res.headers.get("ETag");
    const len = res.headers.get("Content-Length");
    this.total = len ? Number(len) : null;
    const reader = res.body.getReader();
    for (;;) {
      if (gen !== this.gen) return;
      const { done, value } = await reader.read();
      if (done) return;
      if (!value) continue;
      this.parts.push(value);
      this.received += value.byteLength;
      this.sampleSpeed(value.byteLength);
      this.emit();
    }
  }
}
