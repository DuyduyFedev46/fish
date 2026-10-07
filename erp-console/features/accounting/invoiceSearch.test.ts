import { describe, expect, it } from "vitest";
import { invoiceSearchTerm } from "./invoiceSearch";

describe("invoiceSearchTerm", () => {
  it("mã hoá đơn / mã đơn được gửi", () => {
    expect(invoiceSearchTerm(" HD-12 ")).toEqual({ term: "HD-12", blocked: false });
    expect(invoiceSearchTerm("SO261007-4F2A1C")).toEqual({ term: "SO261007-4F2A1C", blocked: false });
    expect(invoiceSearchTerm("12345678")).toEqual({ term: "12345678", blocked: false });
  });
  it("chuỗi giống số điện thoại không gửi, kể cả khi có dấu cách hoặc chấm", () => {
    for (const v of ["0912345678", "0912 345 678", "091.234.5678"]) expect(invoiceSearchTerm(v)).toEqual({ term: "", blocked: true });
  });
});
