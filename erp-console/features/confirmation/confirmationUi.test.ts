import { describe, expect, it } from "vitest";
import { searchQueryError } from "./components/SearchCustomerModal";
import {
  callResultsOf,
  callToast,
  callbackError,
  claimActive,
  claimedByOther,
  decisionsOf,
  detailHref,
  doneSteps,
  dueAt,
  extendError,
  idFromSearch,
  isPhoneValid,
  lineNames,
  matches,
  nextStepText,
  noteError,
  pathOf,
  PATH_STEPS,
  lastCallerName,
  reasonText,
  recipientChanges,
  telHref,
  validateRecipient,
} from "./confirmationUi";
import { MOCK_CONFIRMATION_ITEMS, getMockConfirmationQueue, mockGetConfirmationDetail, mockSearchCustomers } from "./mock";
import { QUEUE_TABS } from "./types";

const NOW = new Date("2026-10-02T03:00:00.000Z"); // 10:00 giờ Việt Nam

describe("đường dẫn và số điện thoại", () => {
  it("URL chỉ mang id số", () => {
    expect(detailHref(31)).toBe("/confirmation/detail/?id=31");
    expect(idFromSearch("31")).toBe(31);
    expect(idFromSearch("0")).toBeNull();
    expect(idFromSearch("abc")).toBeNull();
    expect(idFromSearch("1234567890")).toBeNull();
    expect(idFromSearch(null)).toBeNull();
  });
  it("tel: chỉ dựng khi đủ số", () => {
    expect(telHref("0909 123 456")).toBe("tel:0909123456");
    expect(telHref("09xx xxx 123")).toBeNull();
    expect(telHref(null)).toBeNull();
  });
});

describe("kết quả cuộc gọi và quyết định theo quyền", () => {
  it("giữ đúng thứ tự AC2 và bỏ kết quả không được phép", () => {
    expect(callResultsOf(["claim", "call:UNREACHABLE", "call:CONFIRMED", "call:CALLBACK"])).toEqual(["CONFIRMED", "CALLBACK", "UNREACHABLE"]);
    expect(callResultsOf(["claim"])).toEqual([]);
  });
  it("CSKH không có quyết định (AC5)", () => {
    expect(decisionsOf(["claim", "call:CONFIRMED"])).toEqual([]);
    expect(decisionsOf(["decide:CANCEL", "decide:EXTEND", "decide:DELIVER_WITHOUT_CONFIRM"])).toEqual(["DELIVER_WITHOUT_CONFIRM", "EXTEND", "CANCEL"]);
  });
  it("tab Gọi báo hoàn tiền đúng tên (AC1)", () => {
    expect(QUEUE_TABS.map((t) => t.label)).toEqual(["Cần gọi ngay", "Hẹn gọi lại", "Cần quyết định", "Gọi báo hoàn tiền", "Chờ gọi", "Tất cả"]);
  });
});

describe("kiểm tra nhập liệu", () => {
  it("giờ hẹn gọi lại phải sau bây giờ, câu lỗi nêu mốc dd/mm/yyyy hh:mm (AC3)", () => {
    expect(callbackError("", NOW)).toBe("Chọn thời điểm sau 02/10/2026 10:00.");
    expect(callbackError("2026-10-02T02:00:00.000Z", NOW)).toBe("Chọn thời điểm sau 02/10/2026 10:00.");
    expect(callbackError("2026-10-02T04:00:00.000Z", NOW)).toBeNull();
  });
  it("gia hạn tối đa 24 giờ", () => {
    expect(extendError("2026-10-02T04:00:00.000Z", NOW)).toBeNull();
    expect(extendError("2026-10-04T04:00:00.000Z", NOW)).toMatch(/tối đa 24 giờ/);
  });
  it("ghi chú không chứa số điện thoại hay dãy số dài", () => {
    expect(noteError("khách hẹn chiều")).toBeNull();
    expect(noteError("gọi số 0912 345 678 nhé")).toMatch(/số điện thoại/);
    expect(noteError("STK 1234.5678.90")).toMatch(/số tài khoản/);
    expect(noteError("a".repeat(201))).toMatch(/tối đa 200/);
  });
  it("số điện thoại người nhận", () => {
    expect(isPhoneValid("0912 345 678")).toBe(true);
    expect(isPhoneValid("+84912345678")).toBe(true);
    expect(isPhoneValid("12345")).toBe(false);
  });
  it("chỉ gửi trường đã đổi", () => {
    const before = { name: "A", phone: "0912345678", address: "x" };
    expect(recipientChanges(before, before)).toEqual({});
    expect(recipientChanges(before, { ...before, address: " y " })).toEqual({ delivery_address: "y" });
    expect(validateRecipient({ name: "", phone: "1", address: "" })).toEqual({
      name: "Nhập tên người nhận.",
      phone: "Số điện thoại chưa đúng. Nhập 10 chữ số, bắt đầu bằng 0.",
      address: "Nhập địa chỉ giao hàng.",
    });
  });
  it("tìm khách: số quá ngắn bị chặn, mã đơn thì được", () => {
    expect(searchQueryError("")).toMatch(/Nhập số điện thoại/);
    expect(searchQueryError("0912")).toMatch(/ít nhất 9 chữ số/);
    expect(searchQueryError("SO260928-3F9A01")).toBeNull();
    expect(searchQueryError("0912 345 678")).toBeNull();
  });
});

describe("hiển thị theo trạng thái", () => {
  it("thanh trạng thái theo việc gọi (board W1c2): Chờ gọi > Cần quyết định > Hoàn tất", () => {
    expect(PATH_STEPS.map((x) => x.label)).toEqual(["Chờ gọi", "Cần quyết định", "Hoàn tất"]);
    expect(pathOf({ note_status: "CONFIRMING", confirm_state: "PENDING" })).toEqual({ current: "WAITING", badEnd: null });
    expect(pathOf({ note_status: "CONFIRMING", confirm_state: "CALLBACK" })).toEqual({ current: "WAITING", badEnd: null });
    expect(pathOf({ note_status: "CONFIRMING", confirm_state: "ESCALATED" })).toEqual({ current: "DECIDE", badEnd: null });
    expect(pathOf({ note_status: "CANCELLED", confirm_state: "REFUND_CALL" }).badEnd).toEqual({ label: "Gọi báo hoàn tiền", after: "DECIDE" });
    expect(pathOf({ note_status: "PREPARING", confirm_state: null })).toEqual({ current: "DONE", badEnd: null });
    expect(pathOf({ note_status: "CANCELLED", confirm_state: null }).badEnd?.label).toBe("Đã huỷ theo đơn");
  });
  it("việc tiếp theo và việc đã làm", () => {
    const esc = { note_status: "CONFIRMING", confirm_state: "ESCALATED" as const, decide_deadline: "2026-10-01T02:55:00Z" };
    expect(nextStepText(esc)).toMatch(/^Chọn giao không xác nhận, gia hạn gọi thêm hoặc huỷ đơn trước 01\/10\/2026 09:55$/);
    expect(nextStepText({ ...esc, decide_deadline: null })).toBe("Chọn giao không xác nhận, gia hạn gọi thêm hoặc huỷ đơn");
    expect(nextStepText(esc, false)).toMatch(/Quản lý/);
    expect(nextStepText({ note_status: "CANCELLED", confirm_state: "REFUND_CALL" })).toMatch(/hoàn tiền/);
    expect(doneSteps({ attempts: 3, paid_at: "2026-10-01T01:00:00Z" })).toEqual(["Khách trả tiền", "Gọi 3 lần"]);
    expect(doneSteps({ attempts: 0, paid_at: null })).toEqual([]);
  });
  it("cột Lý do và người gọi gần nhất", () => {
    expect(reasonText({ confirm_state: "ESCALATED", escalation_label: "Không nghe máy", total_amount: "540000", refund: null })).toBe("Không nghe máy");
    expect(reasonText({ confirm_state: "PENDING", escalation_label: null, total_amount: "540000", refund: null })).toBe("—");
    expect(reasonText({ confirm_state: "REFUND_CALL", escalation_label: "Không nghe máy", total_amount: "280000", refund: null })).toMatch(/^Hoàn 280\.000/);
    const call = (id: number, at: string, name: string | null) => ({ id, at, by: name ? { id, display_name: name } : null, result: "UNREACHABLE", result_label: "", note: "" });
    expect(lastCallerName([])).toBeNull();
    expect(lastCallerName([call(1, "2026-10-01T01:00:00Z", "A"), call(2, "2026-10-01T02:00:00Z", "B"), call(3, "2026-10-01T01:30:00Z", "C")])).toBe("B");
    expect(lastCallerName([call(1, "2026-10-01T01:00:00Z", null)])).toBeNull();
  });
  it("mốc hạn gọi theo trạng thái", () => {
    const base = { callback_at: "A", decide_deadline: "D", window_ends_at: "W", next_call_after: null };
    expect(dueAt({ ...base, confirm_state: "CALLBACK" })).toBe("A");
    expect(dueAt({ ...base, confirm_state: "ESCALATED" })).toBe("D");
    expect(dueAt({ ...base, confirm_state: "PENDING" })).toBe("W");
    expect(dueAt({ ...base, confirm_state: "REFUND_CALL" })).toBeNull();
  });
  it("người giữ đơn", () => {
    const held = { claimed_by: { id: 5, display_name: "X" }, claimed_until: "2026-10-02T03:30:00.000Z" };
    expect(claimActive(held, NOW.getTime())).toBe(true);
    expect(claimActive({ ...held, claimed_until: "2026-10-02T02:30:00.000Z" }, NOW.getTime())).toBe(false);
    expect(claimedByOther(held, 5, NOW.getTime())).toBe(false);
    expect(claimedByOther(held, 6, NOW.getTime())).toBe(true);
  });
  it("câu toast sau khi ghi cuộc gọi", () => {
    expect(callToast("CONFIRMED", { confirm_state: null, attempts: 0, duplicate: false }, 3)).toMatch(/Soạn hàng/);
    expect(callToast("UNREACHABLE", { confirm_state: "PENDING", attempts: 1, duplicate: false }, 3)).toBe("Đã ghi không nghe máy (lần 1/3).");
    expect(callToast("UNREACHABLE", { confirm_state: "ESCALATED", attempts: 3, duplicate: false }, 3)).toMatch(/Quản lý/);
    expect(callToast("CALLBACK", { confirm_state: "CALLBACK", attempts: 0, duplicate: false }, 3, "2026-10-02T04:00:00.000Z")).toBe("Đã hẹn gọi lại lúc 02/10/2026 11:00.");
    expect(callToast("CONFIRMED", { confirm_state: null, attempts: 0, duplicate: true }, 3)).toMatch(/trước đó/);
  });
  it("tên hàng bỏ số kg, tìm trên dòng đã tải", () => {
    expect(lineNames("Tôm sú 2 kg · Mực 1,5 kg")).toBe("Tôm sú · Mực");
    const row = { order_code: "DH-1", customer_name: "An", recipient_name: null, lines_summary: "Cá thu", phone: "0912345678" };
    expect(matches(row, "an")).toBe(true);
    expect(matches(row, "0912 345")).toBe(true);
    expect(matches({ ...row, phone: null }, "0912345")).toBe(false);
    expect(matches(row, "zzz")).toBe(false);
  });
});

describe("mock: dòng ngoài phạm vi che dữ liệu khách (bất biến 9)", () => {
  const out = MOCK_CONFIRMATION_ITEMS.find((i) => !i.in_scope)!;
  const inScope = MOCK_CONFIRMATION_ITEMS.find((i) => i.in_scope && i.confirm_state === "PENDING")!;

  it("danh sách cho CSKH: dòng ngoài phạm vi không có tên, số, địa chỉ; chỉ có phone_masked", () => {
    const rows = getMockConfirmationQueue({ state: "PENDING" }).results;
    const masked = rows.find((r) => r.note_id === out.note_id)!;
    expect(masked.in_scope).toBe(false);
    expect(masked.customer_name).toBeNull();
    expect(masked.phone).toBeNull();
    expect(masked.address).toBeNull();
    expect(masked.phone_masked).toMatch(/^\d{2}xx xxx \d{3}$/);
    const full = rows.find((r) => r.note_id === inScope.note_id)!;
    expect(full.phone).toMatch(/^0\d{9}$/);
  });
  it("dòng danh sách không kèm lịch sử cuộc gọi", () => {
    for (const r of getMockConfirmationQueue({ state: "PENDING" }).results) expect(r).not.toHaveProperty("calls");
  });
  it("chi tiết ngoài phạm vi: 404", () => {
    expect(mockGetConfirmationDetail({ method: "GET", path: "", token: null }, out.note_id).status).toBe(404);
  });
  it("tra cứu: kết quả ngoài phạm vi chỉ trả số đã che", () => {
    const res = mockSearchCustomers({ method: "POST", path: "", token: null }, "0900000555");
    if ("results" in res.body) {
      const hit = res.body.results.find((r) => r.note_id === out.note_id)!;
      expect(hit.in_scope).toBe(false);
      expect(hit.phone).toBeUndefined();
      expect(hit.customer_name).toBeUndefined();
      expect(hit.phone_masked).toBe(out.phone_masked);
    } else throw new Error("search phải trả results");
  });
});
