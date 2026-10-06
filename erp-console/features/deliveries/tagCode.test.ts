import { describe, expect, it } from "vitest";
import { mockLookupDeliveryTag } from "./mock";
import { TAG_CODE_RE, TAG_MESSAGES, checkTagCode, normalizeTagCode, tagWarning } from "./tagCode";
import type { TagLookup } from "./types";

// CS-17: kiểm mã tem ở máy khách + mock theo contract BE. Mọi số điện thoại dưới đây là chữ bịa.
const tokenFor = (username: string) => `mock-token-${username}-${Date.now() + 1000}`;
const lookup = (username: string, code: string) =>
  mockLookupDeliveryTag({ method: "GET", path: `/api/delivery/notes/lookup/?code=${encodeURIComponent(code)}`, token: tokenFor(username) });

describe("CS-17: kiểm mã tem trước khi gọi API", () => {
  it("nhận mã đúng định dạng, kể cả khi máy quét USB kèm khoảng trắng / xuống dòng và chữ thường", () => {
    expect(checkTagCode("GH-HD-0001-AB12C.1")).toEqual({ ok: true, code: "GH-HD-0001-AB12C.1" });
    expect(checkTagCode("  gh-hd-0001-ab12c.12\n")).toEqual({ ok: true, code: "GH-HD-0001-AB12C.12" });
    expect(normalizeTagCode(" GH-A B.1 ")).toBe("GH-AB.1");
  });

  it("chặn số điện thoại gõ nhầm, tên khách, mã thiếu số lần in: không cho gọi API", () => {
    for (const bad of ["0900000123", "0900 000 123", "Nguyen Van A", "GH-HD-0001-AB12C", "GH-HD-0001-AB12C.", "GH-HD-0001-AB12C.1234", "GH-.1", "XX-HD-0001.1", "GH-HD 0001/AB.1"]) {
      const res = checkTagCode(bad);
      expect(res.ok, bad).toBe(false);
    }
  });

  it("câu lỗi không lặp lại chuỗi người dùng đã gõ", () => {
    const res = checkTagCode("0900000123");
    expect(res.ok).toBe(false);
    if (!res.ok) {
      expect(res.message).toBe(TAG_MESSAGES.invalid);
      expect(res.message).not.toContain("0900000123");
    }
    const empty = checkTagCode("   ");
    expect(empty.ok).toBe(false);
    if (!empty.ok) expect(empty.message).toBe(TAG_MESSAGES.empty);
  });

  it("regex khớp BE: GH- + 3..40 ký tự [A-Z0-9-] + .số 1..3 chữ số", () => {
    expect(TAG_CODE_RE.test("GH-ABC.1")).toBe(true);
    expect(TAG_CODE_RE.test("GH-AB.1")).toBe(false);
    expect(TAG_CODE_RE.test(`GH-${"A".repeat(40)}.999`)).toBe(true);
    expect(TAG_CODE_RE.test(`GH-${"A".repeat(41)}.1`)).toBe(false);
  });
});

describe("CS-17: cảnh báo của kết quả tra", () => {
  it("tem cũ (BR-GH-16) = vàng, nêu lần tem còn hiệu lực", () => {
    expect(tagWarning({ warning: "BR-GH-16", valid_print_no: 2 })).toEqual({ kind: "warn", text: "Tem này không còn hiệu lực, dùng tem lần 2." });
    expect(tagWarning({ warning: "BR-GH-16", valid_print_no: null })?.kind).toBe("warn");
  });
  it("đơn đã huỷ (BR-GH-07) = đỏ", () => {
    expect(tagWarning({ warning: "BR-GH-07", valid_print_no: null })).toEqual({ kind: "error", text: "Đơn đã huỷ, không soạn, xé tem." });
  });
  it("tem còn hiệu lực: không cảnh báo; câu chữ không có mã luật", () => {
    expect(tagWarning({ warning: null, valid_print_no: 1 })).toBeNull();
    for (const w of ["BR-GH-16", "BR-GH-07"] as const) expect(tagWarning({ warning: w, valid_print_no: 2 })!.text).not.toMatch(/BR-/);
  });
});

describe("CS-17: mock lookup theo contract BE", () => {
  it("tem lần 1 còn hiệu lực: 200, không cảnh báo", () => {
    const res = lookup("kho1", "GH-HD-0032-READY.1");
    expect(res.status).toBe(200);
    expect(res.body).toMatchObject({ note_id: 32, status: "READY", print_no: 1, valid_print_no: 1, warning: null });
  });
  it("tem lần 1 khi đã in lại lần 2: cảnh báo BR-GH-16 kèm lần hiệu lực", () => {
    const res = lookup("kho1", "GH-HD-0046-REPR.1");
    expect(res.body).toMatchObject({ note_id: 46, print_no: 1, valid_print_no: 2, warning: "BR-GH-16" });
    expect((lookup("kho1", "GH-HD-0046-REPR.2").body as TagLookup).warning).toBeNull();
  });
  it("phiếu đã huỷ: BR-GH-07, valid_print_no null", () => {
    expect(lookup("loc", "GH-HD-0047-CANC.1").body).toMatchObject({ note_id: 47, status: "CANCELLED", valid_print_no: null, warning: "BR-GH-07" });
  });
  it("404: phiếu không có, chưa in, hoặc chưa từng in lần đó", () => {
    expect(lookup("kho1", "GH-HD-9999-NONE.1").status).toBe(404);
    expect(lookup("kho1", "GH-HD-0031-PREP.1").status).toBe(404); // chưa in tem
    expect(lookup("kho1", "GH-HD-0032-READY.2").status).toBe(404); // chưa từng in lần 2
  });
  it("400: sai định dạng, lỗi không lặp lại giá trị đã gửi", () => {
    const res = lookup("kho1", "0900000123");
    expect(res.status).toBe(400);
    expect(JSON.stringify(res.body)).not.toContain("0900000123");
  });
  it("403 cho CSKH và NV giao, 200 cho Chủ, Quản lý, NV kho", () => {
    for (const u of ["cs1", "giao1"]) expect(lookup(u, "GH-HD-0032-READY.1").status, u).toBe(403);
    for (const u of ["loc", "ql1", "kho1"]) expect(lookup(u, "GH-HD-0032-READY.1").status, u).toBe(200);
  });
  it("phản hồi không có tên, SĐT, địa chỉ, mã đơn, giá", () => {
    const res = lookup("loc", "GH-HD-0046-REPR.1");
    const text = JSON.stringify(res.body);
    expect(text).not.toMatch(/Khách|Đường|DH-|phone|address|customer|price|cost/i);
  });
});
