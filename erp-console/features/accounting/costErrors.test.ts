import { describe, expect, it } from "vitest";
import { mockCostCreate } from "./mock";
import { fieldErrorsOf } from "@/shared/ui/form/useSubmit";
import { ApiError } from "@/shared/lib/http";

// Lô bổ sung A #14: lỗi của BE khi ghi chi phí mua; khoá `amount` / `allocations` đi kèm để form hiện dưới đúng ô.
const token = (username: string) => `mock-token-${username}-${Date.now() + 60_000}`;
const post = (username: string, body: object) => mockCostCreate({ method: "POST", path: "/api/purchasing/costs/", body, token: token(username) });
const ok = { cost_type: "ICE", amount: "1000000", allocation_method: "BY_QTY", incurred_date: "2026-10-01", note: "", allocations: [{ batch: 201, amount: "1000000" }] };

describe("mockCostCreate: lỗi tiền theo BE (#14)", () => {
  it("hợp lệ → 201", () => {
    expect(post("loc", ok).status).toBe(201);
  });
  it("tổng từ 10^12 trở lên → 400 COST_AMOUNT_TOO_LARGE kèm khoá amount", () => {
    const res = post("loc", { ...ok, amount: "1000000000000", allocations: [{ batch: 201, amount: "1000000000000" }] });
    expect(res.status).toBe(400);
    const body = res.body as { code: string; detail: string; amount: string[] };
    expect(body.code).toBe("COST_AMOUNT_TOO_LARGE");
    expect(body.amount).toEqual([body.detail]);
    expect(body.detail).toContain("quá lớn");
  });
  it("sát ngưỡng 999.999.999.999 vẫn qua bước kiểm cột amount", () => {
    const res = post("loc", { ...ok, amount: "999999999999", allocations: [{ batch: 201, amount: "999999999999" }] });
    expect((res.body as { code?: string }).code).not.toBe("COST_AMOUNT_TOO_LARGE");
  });
  it("tiền không phải số hoặc thiếu → 400 INVALID_AMOUNT kèm khoá amount", () => {
    for (const amount of ["abc", "", undefined]) {
      const res = post("loc", { ...ok, amount });
      expect(res.status).toBe(400);
      expect(res.body).toMatchObject({ code: "INVALID_AMOUNT", amount: ["Số tiền chi phí không hợp lệ."] });
    }
  });
  it("phần chia làm giá vốn mỗi kg tràn → 400 COST_LANDED_OVERFLOW kèm khoá allocations", () => {
    const big = "500000000000";
    const res = post("loc", { ...ok, amount: big, allocations: [{ batch: 201, amount: big }] });
    expect(res.status).toBe(400);
    const body = res.body as { code: string; detail: string; allocations: string[] };
    expect(body.code).toBe("COST_LANDED_OVERFLOW");
    expect(body.allocations).toEqual([body.detail]);
  });
  it("không phải Chủ → 403 (không có quyền ghi chi phí)", () => {
    expect(post("ql1", ok).status).toBe(403);
    expect(post("kho1", ok).status).toBe(403);
  });
  it("form gom khoá amount thành lỗi dưới ô; allocations không phải ô nên không vào fieldErrors.amount", () => {
    const res = post("loc", { ...ok, amount: "abc" });
    const err = new ApiError("Số tiền chi phí không hợp lệ.", 400, "INVALID_AMOUNT", res.body);
    expect(fieldErrorsOf(err).amount).toBe("Số tiền chi phí không hợp lệ.");
  });
});
