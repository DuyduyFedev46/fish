import { describe, expect, it, vi } from "vitest";
import { type CodeFinder, parseCodeRef, resolveCodeRef } from "./codeLookup";

describe("parseCodeRef: nhận dạng mẫu mã", () => {
  it("đơn, phiếu giao, lô, phiếu theo id", () => {
    expect(parseCodeRef(" so261007-4f2a1c ")).toEqual({ kind: "order", code: "SO261007-4F2A1C" });
    expect(parseCodeRef("GH-HD-0033-DELI")).toEqual({ kind: "note", code: "GH-HD-0033-DELI" });
    expect(parseCodeRef("CA-THU-260928-VT01")).toEqual({ kind: "batch", code: "CA-THU-260928-VT01" });
    expect(parseCodeRef("L0914-CT01")).toEqual({ kind: "batch", code: "L0914-CT01" });
    expect(parseCodeRef("LO-0912")).toEqual({ kind: "batch", code: "LO-0912" });
    expect(parseCodeRef("PR-12")).toMatchObject({ kind: "id", href: "/purchasing/detail/?id=12" });
    expect(parseCodeRef("kk-3")).toMatchObject({ href: "/stocktake/detail/?id=3" });
    expect(parseCodeRef("RT-7")).toMatchObject({ href: "/returns/detail/?id=7" });
    expect(parseCodeRef("#41")).toMatchObject({ href: "/orders/refunds/detail/?id=41" });
  });
  it("tên, SĐT, từ thường, chuỗi có khoảng trắng hoặc dấu → null (không gọi API)", () => {
    for (const v of ["", "0912345678", "0912 345 678", "Nguyễn Văn An", "ca thu", "An", "hoa", "tom-su", "An-Binh", "Chị Hạnh", "x".repeat(41), "09-1234-5678-90"]) {
      expect(parseCodeRef(v), v).toBeNull();
    }
  });
});

describe("resolveCodeRef", () => {
  const finder = (over: Partial<CodeFinder> = {}): CodeFinder => ({
    order: vi.fn(async () => 5),
    note: vi.fn(async () => null),
    batch: vi.fn(async () => 9),
    ...over,
  });
  it("tìm thấy → đường dẫn chi tiết theo id; không có → none", async () => {
    const f = finder();
    expect(await resolveCodeRef({ kind: "order", code: "SO261007-4F2A1C" }, f)).toEqual({ status: "found", href: "/orders/detail/?id=5" });
    expect(await resolveCodeRef({ kind: "batch", code: "LO-0912" }, f)).toEqual({ status: "found", href: "/inventory/detail/?id=9" });
    expect(await resolveCodeRef({ kind: "note", code: "GH-X-1" }, f)).toEqual({ status: "none", code: "GH-X-1" });
  });
  it("mã theo id mở thẳng, không gọi finder", async () => {
    const f = finder();
    const ref = parseCodeRef("PR-12");
    expect(ref && (await resolveCodeRef(ref, f))).toEqual({ status: "found", href: "/purchasing/detail/?id=12" });
    expect(f.order).not.toHaveBeenCalled();
    expect(f.note).not.toHaveBeenCalled();
    expect(f.batch).not.toHaveBeenCalled();
  });
});
