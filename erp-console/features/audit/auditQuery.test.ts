import { describe, expect, it } from "vitest";
import { auditRangeError, checkAuditQuery } from "./auditQuery";

describe("checkAuditQuery (khớp A3 của BE)", () => {
  it("mã hợp lệ được cắt khoảng trắng và gửi đi", () => {
    expect(checkAuditQuery("  SO261007-4F2A1C ")).toEqual({ ok: true, q: "SO261007-4F2A1C" });
    expect(checkAuditQuery("#12")).toEqual({ ok: true, q: "#12" });
  });
  it("rỗng hoặc 1 ký tự: chưa gửi, không báo lỗi", () => {
    expect(checkAuditQuery("")).toMatchObject({ ok: false, message: null });
    expect(checkAuditQuery("S")).toMatchObject({ ok: false, message: null });
  });
  it("dãy từ 9 chữ số (giống SĐT) bị chặn và câu lỗi không lặp lại chuỗi đã gõ", () => {
    const r = checkAuditQuery("0912345678");
    expect(r).toMatchObject({ ok: false, message: "Chỉ tìm theo mã chứng từ." });
    expect(JSON.stringify(r)).not.toContain("0912345678");
  });
  it("chữ có dấu, khoảng trắng giữa chuỗi hoặc quá 40 ký tự bị chặn", () => {
    expect(checkAuditQuery("Nguyễn")).toMatchObject({ ok: false });
    expect(checkAuditQuery("SO 12")).toMatchObject({ ok: false });
    expect(checkAuditQuery("A".repeat(41))).toMatchObject({ ok: false });
  });
  it("8 chữ số vẫn là mã hợp lệ (dưới ngưỡng SĐT)", () => {
    expect(checkAuditQuery("12345678")).toMatchObject({ ok: true });
  });
});

describe("auditRangeError", () => {
  it("chỉ báo khi từ > đến", () => {
    expect(auditRangeError("2026-10-05", "2026-10-01")).not.toBeNull();
    expect(auditRangeError("2026-10-01", "2026-10-05")).toBeNull();
    expect(auditRangeError("", "2026-10-05")).toBeNull();
  });
});
