// Tab "Tất cả" của Gọi xác nhận: BE không có state=ALL nên FE gộp 4 danh sách (ED-15). Dựng `fetch` giả, dữ liệu giả.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ALL_QUEUE_STATES, fetchConfirmationQueueAll } from "./api";

let urls: string[];

function page(rows: Array<{ note_id: number; paid_at: string | null }>, next: string | null = null) {
  return { count: rows.length, next, previous: null, results: rows };
}

beforeEach(() => {
  urls = [];
});
afterEach(() => vi.unstubAllGlobals());

describe("fetchConfirmationQueueAll", () => {
  it("gọi đúng 4 trạng thái, không có state=ALL, gộp và sắp theo giờ trả tiền", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        urls.push(url);
        const state = new URL(url, "http://x").searchParams.get("state");
        const body =
          state === "PENDING" ? page([{ note_id: 1, paid_at: "2026-10-02T03:00:00Z" }]) :
          state === "CALLBACK" ? page([{ note_id: 2, paid_at: "2026-10-02T01:00:00Z" }]) :
          page([]);
        return { status: 200, ok: true, json: async () => body } as unknown as Response;
      }),
    );
    const res = await fetchConfirmationQueueAll(1);
    expect(urls).toHaveLength(ALL_QUEUE_STATES.length);
    expect(urls.some((u) => /state=ALL/i.test(u))).toBe(false);
    expect(ALL_QUEUE_STATES.every((st) => urls.some((u) => u.includes(`state=${st}`)))).toBe(true);
    expect(res.count).toBe(2);
    expect(res.results.map((r) => r.note_id)).toEqual([2, 1]);
    expect(res.next).toBeNull();
  });

  it("dòng chưa có giờ trả tiền xuống cuối, cũ trước mới sau", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const state = new URL(url, "http://x").searchParams.get("state");
        const body =
          state === "PENDING" ? page([{ note_id: 1, paid_at: null }, { note_id: 2, paid_at: "2026-10-02T03:00:00Z" }]) :
          state === "CALLBACK" ? page([{ note_id: 3, paid_at: "2026-10-02T01:00:00Z" }]) :
          page([]);
        return { status: 200, ok: true, json: async () => body } as unknown as Response;
      }),
    );
    const res = await fetchConfirmationQueueAll(1);
    expect(res.results.map((r) => r.note_id)).toEqual([3, 2, 1]);
  });

  it("còn trang sau khi một trạng thái còn next", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const state = new URL(url, "http://x").searchParams.get("state");
        const body = state === "PENDING" ? page([{ note_id: 1, paid_at: "2026-10-02T03:00:00Z" }], "http://x/?page=2") : page([]);
        return { status: 200, ok: true, json: async () => body } as unknown as Response;
      }),
    );
    expect((await fetchConfirmationQueueAll(1)).next).not.toBeNull();
  });

  it("trang vượt quá của một trạng thái (404) coi như hết dòng, không báo lỗi", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const state = new URL(url, "http://x").searchParams.get("state");
        if (state !== "PENDING") return { status: 404, ok: false, json: async () => ({ detail: "Not found." }) } as unknown as Response;
        return { status: 200, ok: true, json: async () => page([{ note_id: 9, paid_at: "2026-10-02T03:00:00Z" }]) } as unknown as Response;
      }),
    );
    const res = await fetchConfirmationQueueAll(2);
    expect(res.results.map((r) => r.note_id)).toEqual([9]);
  });

  it("một trạng thái lỗi 500 thì cả tab báo lỗi (không hiện danh sách thiếu)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const state = new URL(url, "http://x").searchParams.get("state");
        if (state === "ESCALATED") return { status: 500, ok: false, json: async () => ({}) } as unknown as Response;
        return { status: 200, ok: true, json: async () => page([]) } as unknown as Response;
      }),
    );
    await expect(fetchConfirmationQueueAll(1)).rejects.toBeTruthy();
  });
});
