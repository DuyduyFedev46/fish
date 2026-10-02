import { describe, expect, it } from "vitest";
import { filterByTarget, InvalidTargetModelError, resolveMockTargetLabel, mockAiActions, mockFetchAiActionCounts, mockFetchAiActions } from "./mock";

describe("R1 lọc đề xuất theo chứng từ đích (mock)", () => {
  it("target_model dạng app.model hay model đều khớp", () => {
    const a = filterByTarget(mockAiActions.results, { target_model: "purchasing.purchasereceipt" });
    const b = filterByTarget(mockAiActions.results, { target_model: "purchasereceipt" });
    expect(a.length).toBeGreaterThan(0);
    expect(a).toEqual(b);
    expect(a.every((x) => x.target?.type === "purchasereceipt")).toBe(true);
  });
  it("target_id nhiều mã cách phẩy", () => {
    const r = filterByTarget(mockAiActions.results, { target_model: "inventory.batch", target_id: "CA01-260928-AB12C, CA02-260928-XY34Z" });
    expect(r.map((x) => x.target?.code).sort()).toEqual(["CA01-260928-AB12C", "CA02-260928-XY34Z"]);
  });
  it("kết hợp status + target", () => {
    const body = mockFetchAiActions({ status: "PENDING,ESCALATED", target_model: "purchasing.purchasereceipt", target_id: "PR-260928-01" }).body as { results: { status: string }[] };
    expect(body.results.map((x) => x.status)).toEqual(["PENDING"]);
  });
  it("counts theo loại chứng từ", () => {
    const c = mockFetchAiActionCounts({ status: "PENDING,ESCALATED" }).body.by_target_model;
    expect(c["purchasing.purchasereceipt"]).toBe(1);
    expect(c["inventory.batch"]).toBe(1);
  });
  it("TL-H1: 'sales.order' không có thật nên bị từ chối như BE (400 INVALID_TARGET_MODEL)", () => {
    expect(() => filterByTarget(mockAiActions.results, { target_model: "sales.order" })).toThrow(InvalidTargetModelError);
    const r = mockFetchAiActions({ status: "PENDING", target_model: "sales.order", target_id: "SO261002-4B7E20,41" });
    expect(r.status).toBe(400);
    expect((r.body as { code: string }).code).toBe("INVALID_TARGET_MODEL");
  });
  it("target_model lạ khác cũng 400: app lạ, model lạ, chuỗi rỗng sau dấu chấm", () => {
    for (const v of ["foo.bar", "sales.", "salesorder.x", "sales.order.extra", "cái gì đó"]) {
      expect(mockFetchAiActions({ target_model: v }).status).toBe(400);
    }
  });
  it("nhãn đúng của đơn, khoản tiền, phiếu hoàn và các dạng doc_type/tên model đều nhận", () => {
    expect(resolveMockTargetLabel("sales.salesorder")).toBe("sales.salesorder");
    expect(resolveMockTargetLabel("SALES.SalesOrder")).toBe("sales.salesorder");
    expect(resolveMockTargetLabel("order")).toBe("sales.salesorder");
    expect(resolveMockTargetLabel("salesorder")).toBe("sales.salesorder");
    expect(resolveMockTargetLabel("sales.paymenttransaction")).toBe("sales.paymenttransaction");
    expect(resolveMockTargetLabel("sales.refund")).toBe("sales.refund");
    expect(resolveMockTargetLabel("sales.order")).toBeNull();
    expect(mockFetchAiActions({ target_model: "sales.salesorder" }).status).toBe(200);
  });
});
