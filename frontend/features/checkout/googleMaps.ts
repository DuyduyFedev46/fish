// Nạp Google Maps (SHOP-3-04, 02b §1.9, BR-BH-29). Script CHỈ được nạp khi khách bấm "Bản đồ", bằng một thẻ <script> tự chèn,
// không thêm thư viện loader. Chưa cấu hình `NEXT_PUBLIC_GOOGLE_MAPS_KEY` thì không bao giờ tạo thẻ script, không gửi request
// nào tới Google: bấm "Bản đồ" mở thẳng hộp thoại C5. Không dùng Geolocation, không lưu toạ độ.

import type { GoogleNs } from "./googleMaps.d";

// Đọc đúng MỘT chỗ. Truyền lúc build như các biến NEXT_PUBLIC_* khác; không commit key.
const MAPS_KEY = (process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? "").trim();

/** Chờ tối đa bao lâu cho script nạp xong trước khi coi là lỗi (02b §1.9). */
export const MAPS_LOAD_TIMEOUT_MS = 10000;

const SCRIPT_ID = "caveve-google-maps";
let failures = 0;
let inflight: Promise<GoogleNs> | null = null;

/** Có key thì bản đồ dùng được; rỗng là thiếu key. */
export function hasMapsKey(): boolean {
  return MAPS_KEY !== "";
}

/**
 * Đã lỗi hai lần trong phiên: lần bấm sau mở thẳng C5, không thử nạp lại nữa.
 * (Lần lỗi đầu cho phép thử lại một lần ở lần bấm kế tiếp.)
 */
export function mapsGaveUp(): boolean {
  return failures >= 2;
}

/** Nên mở thẳng C5 (không mở hộp thoại bản đồ): thiếu key hoặc đã lỗi hai lần. */
export function shouldOpenFallbackDirectly(): boolean {
  return !hasMapsKey() || mapsGaveUp();
}

function readyNamespace(): GoogleNs | null {
  const g = typeof window === "undefined" ? undefined : window.google;
  return g && g.maps && typeof g.maps.importLibrary === "function" ? g : null;
}

function cleanup(): void {
  document.getElementById(SCRIPT_ID)?.remove();
  delete (window as { __caveveMapsReady?: () => void }).__caveveMapsReady;
}

/**
 * Nạp script Google Maps một lần. Reject ngay khi không có key; reject sau `MAPS_LOAD_TIMEOUT_MS` hoặc khi script lỗi
 * (và gỡ thẻ script hỏng để lần bấm sau thử lại). Hai lần lỗi thì thôi, xem `mapsGaveUp`.
 */
export function loadGoogleMaps(): Promise<GoogleNs> {
  if (!hasMapsKey()) return Promise.reject(new Error("no-maps-key"));
  const ready = readyNamespace();
  if (ready) return Promise.resolve(ready);
  if (inflight) return inflight;

  inflight = new Promise<GoogleNs>((resolve, reject) => {
    let settled = false;
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      if (error) {
        failures += 1;
        cleanup();
        reject(error);
        return;
      }
      const ns = readyNamespace();
      if (ns) resolve(ns);
      else {
        failures += 1;
        cleanup();
        reject(new Error("maps-not-ready"));
      }
    };
    const timer = window.setTimeout(() => finish(new Error("maps-timeout")), MAPS_LOAD_TIMEOUT_MS);
    window.__caveveMapsReady = () => finish();

    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.async = true;
    script.defer = true;
    script.onerror = () => finish(new Error("maps-script-error"));
    script.src =
      "https://maps.googleapis.com/maps/api/js" +
      `?key=${encodeURIComponent(MAPS_KEY)}&v=weekly&loading=async&language=vi&region=VN&callback=__caveveMapsReady`;
    document.head.appendChild(script);
  }).finally(() => {
    inflight = null;
  });
  return inflight;
}
