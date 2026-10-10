// PV-13-AC3: "Tải thêm" gặp 404 (phạm vi vừa hẹp lại) → tải lại trang 1, không báo lỗi; lỗi khác vẫn báo moreError.
import { describe, expect, it, vi } from "vitest";
import { ApiError, type Paginated } from "@/shared/lib/http";
import { flush, renderHook } from "@/shared/lib/fakeReactHooks";
import { usePagedList } from "./usePagedList";

vi.mock("react", async () => (await import("@/shared/lib/fakeReactHooks")).fakeReact);
vi.mock("@/shared/ui/states/offlineSource", () => ({ useOfflineRegistration: () => undefined }));

type Row = { id: number };
const page = (ids: number[], next: boolean): Paginated<Row> => ({ count: ids.length, next: next ? "x" : null, previous: null, results: ids.map((id) => ({ id })) });

describe("usePagedList.loadMore", () => {
  it("404 ở trang 2 → tải lại trang 1, rows theo kết quả mới, moreError null", async () => {
    const calls: number[] = [];
    let narrowed = false;
    const loader = vi.fn(async (_p: object, n: number) => {
      calls.push(n);
      if (n === 2) throw new ApiError("Không tìm thấy.", 404);
      return narrowed ? page([1], false) : page([1, 2, 3], true);
    });
    const h = renderHook(() => usePagedList<Row, object>(loader, {}, true));
    await flush();
    expect(h.result.rows?.map((r) => r.id)).toEqual([1, 2, 3]);
    narrowed = true;
    await h.result.loadMore();
    await flush();
    expect(calls).toEqual([1, 2, 1]);
    expect(h.result.moreError).toBeNull();
    expect(h.result.error).toBeNull();
    expect(h.result.rows?.map((r) => r.id)).toEqual([1]);
    expect(h.result.hasMore).toBe(false);
  });

  it("500 ở trang 2 → vẫn báo moreError và giữ dòng cũ", async () => {
    const loader = vi.fn(async (_p: object, n: number) => {
      if (n === 2) throw new ApiError("Lỗi máy chủ.", 500);
      return page([1, 2], true);
    });
    const h = renderHook(() => usePagedList<Row, object>(loader, {}, true));
    await flush();
    await h.result.loadMore();
    await flush();
    expect(h.result.moreError).not.toBeNull();
    expect(h.result.rows?.map((r) => r.id)).toEqual([1, 2]);
  });

  it("làm mới (reload) khi phạm vi hẹp lại → danh sách ngắn lại, không có lỗi", async () => {
    let narrowed = false;
    const loader = vi.fn(async () => (narrowed ? page([2], false) : page([1, 2], false)));
    const h = renderHook(() => usePagedList<Row, object>(loader, {}, true));
    await flush();
    narrowed = true;
    await h.result.reload();
    await flush();
    expect(h.result.rows?.map((r) => r.id)).toEqual([2]);
    expect(h.result.error).toBeNull();
  });
});
