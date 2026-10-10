// PV-13-AC1/AC4/AC5 cho useCustomerDetail: tải lại bị 404 phải xoá tên/SĐT/địa chỉ khách khỏi state.
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { flush, renderHook } from "@/shared/lib/testing/fakeReactHooks";
import type { CustomerDetail } from "./types";
import { useCustomerDetail } from "./useCustomerDetail";

vi.mock("react", async () => (await import("@/shared/lib/testing/fakeReactHooks")).fakeReact);

const results: Array<CustomerDetail | ApiError> = [];
vi.mock("./api", () => ({
  getCustomer: async () => {
    const r = results.shift();
    if (r instanceof ApiError) throw r;
    return r;
  },
}));

const DOC = { id: 3, name: "Khách giả B", phone: "0900000000", address: "Địa chỉ giả" } as unknown as CustomerDetail;

function setup(list: Array<CustomerDetail | ApiError>) {
  results.length = 0;
  results.push(...list);
  return renderHook(() => useCustomerDetail(3));
}

describe("useCustomerDetail mất quyền giữa chừng", () => {
  it("đang ok, tải lại bị 404 → scope_lost và data null", async () => {
    const h = setup([DOC, new ApiError("Không tìm thấy.", 404)]);
    await flush();
    expect(h.result.status).toBe("ok");
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("scope_lost");
    expect(h.result.data).toBeNull();
  });
  it("lần đầu 404 → notfound", async () => {
    const h = setup([new ApiError("Không tìm thấy.", 404)]);
    await flush();
    expect(h.result.status).toBe("notfound");
  });
  it("tải lại 500 → giữ ok + error", async () => {
    const h = setup([DOC, new ApiError("Lỗi máy chủ.", 500)]);
    await flush();
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("ok");
    expect(h.result.data).toEqual(DOC);
    expect(h.result.error).not.toBeNull();
  });
  it("tải lại 403 → giữ ok (hành vi cũ)", async () => {
    const h = setup([DOC, new ApiError("Không có quyền.", 403)]);
    await flush();
    await h.result.reload();
    await flush();
    expect(h.result.status).toBe("ok");
  });
});
