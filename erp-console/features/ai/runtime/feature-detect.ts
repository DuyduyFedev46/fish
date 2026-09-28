// Feature-detect máy (C.2, S08-AC2/AC3) — chỉ đọc API trình duyệt, không đoán.
// - WebGPU: navigator.gpu — bắt buộc để wllama chạy (Lô 4).
// - RAM: navigator.deviceMemory (Chromium; iOS/Safari không có → null).
// - Mạng: navigator.connection.type — chỉ cần biết Wi-Fi hay di động (BR-AI-12, best-effort).
// - iOS: dùng đúng 1 lần User-Agent ở đây (K10) — wllama chưa chạy được trên iOS/Safari.
// Máy không đạt → vẫn nhập tay bình thường, KHÔNG đẩy việc lên cloud (S08-AC3).

export const MIN_RAM_GB = 8; // C5-C3: dưới 8 GB → fail-closed

export type NetType = "wifi" | "cellular" | "unknown";

export type AiCapability = {
  webgpu: boolean;
  /** GB (số nguyên, chỉ Chromium báo); null = không đo được. */
  deviceMemoryGb: number | null;
  ios: boolean;
  network: NetType;
};

export function detectAiCapability(): AiCapability {
  const nav = typeof navigator === "undefined" ? undefined : navigator;
  let webgpu = false;
  let ios = false;
  let network: NetType = "unknown";
  if (nav) {
    webgpu = "gpu" in nav;
    const ua = nav.userAgent || "";
    // Duyệt UA đúng một lần, chỉ để nhận iPhone/iPad (K10) — không dùng cho gì khác.
    ios = /iPad|iPhone|iPod/.test(ua) || (ua.includes("Mac") && "ontouchend" in document);
    const conn = (nav as Navigator & { connection?: { type?: string } }).connection;
    if (conn && typeof conn.type === "string") {
      network = conn.type === "wifi" || conn.type === "ethernet" ? "wifi" : conn.type === "cellular" ? "cellular" : "unknown";
    }
  }
  let deviceMemoryGb: number | null = null;
  if (nav) {
    const dm = (nav as Navigator & { deviceMemory?: number }).deviceMemory;
    deviceMemoryGb = typeof dm === "number" && dm > 0 ? Math.floor(dm) : null;
  }
  return { webgpu, deviceMemoryGb, ios, network };
}

export type DownloadBlockReason = "ios" | "low_ram" | "ram_unknown" | "cellular" | "network_unknown" | "no_webgpu";

export type DownloadVerdict = { ok: true } | { ok: false; reason: DownloadBlockReason };

/**
 * Máy có được tải model không (S08-AC1/AC2/AC3, C5-C3):
 * - iOS → không (wllama chưa hỗ trợ).
 * - Thiếu WebGPU → không.
 * - RAM < 8 GB → không; không đo được → hỏi ("Vẫn thử tải" — mặc định không).
 * - Mạng di động → không tự tải (nhắc đổi Wi-Fi); không rõ → hỏi ("Kiểm tra lại").
 */
export function canDownloadModel(cap: AiCapability): DownloadVerdict {
  if (cap.ios) return { ok: false, reason: "ios" };
  if (!cap.webgpu) return { ok: false, reason: "no_webgpu" };
  if (cap.deviceMemoryGb !== null && cap.deviceMemoryGb < MIN_RAM_GB) return { ok: false, reason: "low_ram" };
  if (cap.deviceMemoryGb === null) return { ok: false, reason: "ram_unknown" };
  if (cap.network === "cellular") return { ok: false, reason: "cellular" };
  if (cap.network === "unknown") return { ok: false, reason: "network_unknown" };
  return { ok: true };
}
