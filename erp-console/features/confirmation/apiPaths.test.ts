// P8b Lô 3: FE gọi đường dẫn API MỚI (`/api/confirmation/...`, `/api/purchasing/receipts/receive-batches/`), không còn gọi đường dẫn cũ.
// Dựng `fetch` giả, ghi lại URL thật rồi so với contract trong 02c §3 Lô 3. Dữ liệu giả.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  changeRecipient,
  claimConfirmationTask,
  decideConfirmation,
  fetchConfirmationDetail,
  fetchConfirmationQueue,
  recordConfirmationCall,
  searchCustomers,
  unconfirmDelivery,
} from "./api";
import { submitReceiveBatches } from "@/features/purchasing/api";

let calls: Array<{ url: string; method: string }>;
const allUrls: string[] = [];

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: { method?: string }) => {
      calls.push({ url, method: init?.method ?? "GET" });
      allUrls.push(url);
      return { status: 200, ok: true, json: async () => ({}) } as unknown as Response;
    })
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function lastPath(): string {
  const url = calls[calls.length - 1].url;
  return url.replace(/^https?:\/\/[^/]+/, "");
}

describe("đường dẫn API Gọi xác nhận và Nhập lô (P8b Lô 3)", () => {
  it("hàng chờ và chi tiết", async () => {
    await fetchConfirmationQueue({ state: "CALLBACK" });
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/\?state=CALLBACK$/);
    await fetchConfirmationDetail(5);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/$/);
  });

  it("các thao tác trên một phiếu", async () => {
    await claimConfirmationTask(5);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/claim\/$/);
    await recordConfirmationCall(5, {} as never);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/calls\/$/);
    await unconfirmDelivery(5, {} as never);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/unconfirm\/$/);
    await changeRecipient(5, {} as never);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/recipient\/$/);
    await decideConfirmation(5, {} as never);
    expect(lastPath()).toMatch(/\/api\/confirmation\/queue\/5\/decide\/$/);
  });

  it("tìm kiếm dùng POST, từ khoá nằm trong body, không lên URL (bất biến 9)", async () => {
    await searchCustomers("tu-khoa-gia");
    expect(lastPath()).toMatch(/\/api\/confirmation\/search\/$/);
    expect(calls[calls.length - 1].method).toBe("POST");
    expect(calls[calls.length - 1].url).not.toContain("tu-khoa-gia");
  });

  it("Nhập lô gọi receive-batches", async () => {
    await submitReceiveBatches({ supplier: 1, received_date: "2026-10-01", lines: [] } as never);
    expect(lastPath()).toMatch(/\/api\/purchasing\/receipts\/receive-batches\/$/);
  });

  it("không có đường dẫn cũ nào được gọi ở các test trên", () => {
    expect(allUrls.length).toBeGreaterThan(0);
    expect(allUrls.filter((u) => /\/api\/cskh\/|nhap-lo/.test(u))).toEqual([]);
  });
});
