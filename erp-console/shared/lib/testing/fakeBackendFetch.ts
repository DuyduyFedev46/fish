// Giả `fetch` cho test vitest ở chế độ THẬT (NEXT_PUBLIC_USE_MOCK=0): đọc thân yêu cầu như DRF `request.data`.
// Thân phải là chuỗi JSON của MỘT object; nếu là chuỗi JSON của một chuỗi (mã hoá hai lần) thì trả 400
// `Invalid data. Expected a dictionary, but got str.` y như backend thật (P: lưu cài đặt AI, SR-AIS-01).

import { vi } from "vitest";

export type SentRequest = { method: string; path: string; rawBody: string | undefined; parsedBody: unknown };

export function installFakeBackendFetch(okBody: unknown = {}): { sent: SentRequest[] } {
  const sent: SentRequest[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: { method?: string; body?: string }) => {
      const rawBody = init.body;
      let parsedBody: unknown = undefined;
      if (rawBody !== undefined) parsedBody = JSON.parse(rawBody);
      sent.push({ method: init.method ?? "GET", path: String(url).replace(/^https?:\/\/[^/]+/, ""), rawBody, parsedBody });
      if (rawBody !== undefined && (typeof parsedBody !== "object" || parsedBody === null || Array.isArray(parsedBody))) {
        return new Response(JSON.stringify({ non_field_errors: ["Invalid data. Expected a dictionary, but got str."] }), { status: 400 });
      }
      return new Response(JSON.stringify(okBody), { status: 200 });
    })
  );
  return { sent };
}
