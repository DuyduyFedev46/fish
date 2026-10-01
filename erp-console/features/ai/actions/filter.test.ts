import { describe, expect, it } from "vitest";
import { filterByTarget, mockAiActions, mockFetchAiActionCounts, mockFetchAiActions } from "./mock";

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
    const body = mockFetchAiActions({ status: "PENDING,ESCALATED", target_model: "purchasing.purchasereceipt", target_id: "PR-260928-01" }).body;
    expect(body.results.map((x) => x.status)).toEqual(["PENDING"]);
  });
  it("counts theo loại chứng từ", () => {
    const c = mockFetchAiActionCounts({ status: "PENDING,ESCALATED" }).body.by_target_model;
    expect(c["purchasing.purchasereceipt"]).toBe(1);
    expect(c["inventory.batch"]).toBe(1);
  });
});
