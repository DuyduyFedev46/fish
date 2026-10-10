// PV-13-AC1/AC4/AC5: chuyển trạng thái của useDetail khi tải lại bị 404 / 500 / 403 / tải lần đầu bị 404.
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { flush, renderHook } from "@/shared/lib/fakeReactHooks";
import { useDetail } from "./useDetail";

vi.mock("react", async () => (await import("@/shared/lib/fakeReactHooks")).fakeReact);

type Doc = { id: number; customer_name: string };
const DOC: Doc = { id: 7, customer_name: "Khách giả A" };

function setup(results: Array<Doc | ApiError>) {
  let i = 0;
  const loader = vi.fn(async () => {
    const r = results[Math.min(i++, results.length - 1)];
    if (r instanceof ApiError) throw r;
    return r;
  });
  const h = renderHook(() => useDetail<Doc>(7, loader));
  return { h, loader };
}

describe("useDetail mất quyền giữa chừng", () => {
  it("đang ok, tải lại bị 404 → scope_lost và xoá dữ liệu khỏi state", async () => {
    const { h } = setup([DOC, new ApiError("Không tìm thấy.", 404)]);
    await flush();
    expect(h.result.status).toBe("ok");
    expect(h.result.data).toEqual(DOC);
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("scope_lost");
    expect(h.result.data).toBeNull();
  });

  it("tải lần đầu bị 404 → notfound (ED-19-AC6), không phải scope_lost", async () => {
    const { h } = setup([new ApiError("Không tìm thấy.", 404)]);
    await flush();
    expect(h.result.status).toBe("notfound");
    expect(h.result.data).toBeNull();
  });

  it("tải lại bị 500 → giữ màn cũ (ok), báo lỗi qua error", async () => {
    const { h } = setup([DOC, new ApiError("Lỗi máy chủ.", 500)]);
    await flush();
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("ok");
    expect(h.result.data).toEqual(DOC);
    expect(h.result.error).not.toBeNull();
  });

  it("tải lại bị 403 → giữ hành vi cũ (ok + error), không thành scope_lost", async () => {
    const { h } = setup([DOC, new ApiError("Không có quyền.", 403)]);
    await flush();
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("ok");
    expect(h.result.status).not.toBe("scope_lost");
  });

  it("tải lần đầu bị 403 → forbidden; lần đầu 500 → error", async () => {
    const a = setup([new ApiError("Không có quyền.", 403)]);
    await flush();
    expect(a.h.result.status).toBe("forbidden");
    const b = setup([new ApiError("Lỗi máy chủ.", 500)]);
    await flush();
    expect(b.h.result.status).toBe("error");
  });

  it("sau scope_lost, tải lại thành công thì trở về ok", async () => {
    const { h } = setup([DOC, new ApiError("Không tìm thấy.", 404), DOC]);
    await flush();
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("scope_lost");
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("ok");
    expect(h.result.data).toEqual(DOC);
  });
});
