import { describe, it, expect } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { returnListQuery } from "./api";
import { mockGetDeliveryNoteDetail } from "@/features/deliveries/mock";
import { installDeliveryLineExtras, mockReturnsApi } from "./mock";
import {
  approveErrorText,
  batchChoices,
  canApprove,
  canCancel,
  canCreate,
  canDelete,
  createErrorOf,
  currentMonth,
  doneSteps,
  exceedsMessage,
  hasLongDigitRun,
  matchesQuery,
  nextStepText,
  normalizeQty,
  isOutsideLong,
  outsideText,
  parseReturnId,
  pendingCount,
  qtyExceedsOf,
  qtyFactsText,
  qtyOverRemaining,
  recentMonths,
  remainingQty,
  returnedOf,
  showSubmitAlert,
  stripRuleCode,
  validateNote,
} from "./returnsModel";
import type { ReturnItem, ReturnableLine } from "./types";

const token = (username: string) => `mock-token-${username}-${Date.now() + 60_000}`;
const call = (username: string, method: "GET" | "POST", path: string, body?: unknown) => mockReturnsApi({ method, path, body, token: token(username) });
const BASE = "/api/inventory/returns/";
type Page = { count: number; next: string | null; previous: string | null; results: ReturnItem[] };
const fmt = (n: number) => `${String(n).replace(".", ",")} kg`;

describe("returnListQuery", () => {
  it("bỏ trường rỗng, chỉ gửi page từ trang 2", () => {
    expect(returnListQuery({ status: "", month: "" }, 1)).toBe("");
    expect(returnListQuery({ status: "DRAFT", month: "2026-10" }, 1)).toBe("?status=DRAFT&month=2026-10");
    expect(returnListQuery({ status: "", month: "2026-10" }, 3)).toBe("?month=2026-10&page=3");
  });
});

describe("returnsModel — hiển thị", () => {
  it("parseReturnId chỉ nhận số nguyên dương", () => {
    expect(parseReturnId("?id=12")).toBe(12);
    expect(parseReturnId("?id=0")).toBeNull();
    expect(parseReturnId("?id=-3")).toBeNull();
    expect(parseReturnId("?id=1.5")).toBeNull();
    expect(parseReturnId("?id=abc")).toBeNull();
    expect(parseReturnId("")).toBeNull();
  });
  it("isOutsideLong: chỉ tô cảnh báo khi quá 2 giờ (đúng 2 giờ chưa tô, thiếu mốc không tô)", () => {
    expect(isOutsideLong(120)).toBe(false);
    expect(isOutsideLong(121)).toBe(true);
    expect(isOutsideLong(200)).toBe(true);
    expect(isOutsideLong(55)).toBe(false);
    expect(isOutsideLong(null)).toBe(false);
    expect(isOutsideLong(undefined)).toBe(false);
    expect(isOutsideLong(Number.NaN)).toBe(false);
  });
  it("outsideText: phút, giờ, giờ + phút, thiếu mốc", () => {
    expect(outsideText(55)).toBe("55 phút");
    expect(outsideText(70)).toBe("1 giờ 10 phút");
    expect(outsideText(120)).toBe("2 giờ");
    expect(outsideText(null)).toBe("—");
    expect(outsideText(-5)).toBe("—");
  });
  it("recentMonths: 12 tháng, mới trước, đúng khi qua năm", () => {
    const list = recentMonths(new Date("2026-02-10T05:00:00Z"));
    expect(list).toHaveLength(12);
    expect(list[0].value).toBe("2026-02");
    expect(list[1].value).toBe("2026-01");
    expect(list[2].value).toBe("2025-12");
    expect(currentMonth(new Date("2026-02-28T20:00:00Z"))).toBe("2026-03"); // 03:00 giờ VN ngày 1/3
  });
  it("matchesQuery và pendingCount", () => {
    const r = { code: "RT-7", delivery_note_code: "GH-1", batch_code: "CA-THU-1", item_name: "Cá thu" };
    expect(matchesQuery(r, "")).toBe(true);
    expect(matchesQuery(r, " rt-7 ")).toBe(true);
    expect(matchesQuery(r, "CÁ THU")).toBe(true);
    expect(matchesQuery(r, "tôm")).toBe(false);
    expect(pendingCount([{ status: "DRAFT" }, { status: "APPROVED" }, { status: "DRAFT" }])).toBe(2);
  });
  it("thanh trạng thái: Chờ duyệt có Tiếp theo, Đã duyệt thì không", () => {
    expect(nextStepText({ status: "DRAFT", outside_minutes: 135, batch_code: "B1" })).toContain("2 giờ 15 phút");
    expect(nextStepText({ status: "APPROVED", outside_minutes: 10, batch_code: "B1" })).toBeNull();
    expect(doneSteps({ status: "DRAFT", decision: "PENDING" })).toHaveLength(2);
    expect(doneSteps({ status: "APPROVED", decision: "WRITE_OFF" }).at(-1)).toBe("Huỷ bỏ, ghi lỗ");
    expect(doneSteps({ status: "APPROVED", decision: "RESTOCK" }).at(-1)).toBe("Tái nhập vào lô");
  });
});

describe("returnsModel — quyền và nhập liệu", () => {
  it("canApprove cần quyền duyệt và phiếu Chờ duyệt", () => {
    expect(canApprove(["inventory.approve_returntostock"], { status: "DRAFT" })).toBe(true);
    expect(canApprove(["inventory.approve_returntostock"], { status: "APPROVED" })).toBe(false);
    expect(canApprove(["inventory.add_returntostock"], { status: "DRAFT" })).toBe(false);
    expect(canApprove(undefined, { status: "DRAFT" })).toBe(false);
    expect(canCreate(["inventory.add_returntostock"])).toBe(true);
    expect(canCreate([])).toBe(false);
  });
  it("normalizeQty: dấu phẩy, tối đa 3 số lẻ, phải dương", () => {
    expect(normalizeQty("1,5")).toBe("1.5");
    expect(normalizeQty(" 2 ")).toBe("2");
    expect(normalizeQty("0")).toBeNull();
    expect(normalizeQty("-1")).toBeNull();
    expect(normalizeQty("1.2345")).toBeNull();
    expect(normalizeQty("1e3")).toBeNull();
    expect(normalizeQty("")).toBeNull();
    expect(normalizeQty("abc")).toBeNull();
  });
  it("remainingQty không âm và không dính sai số nhị phân", () => {
    expect(remainingQty(1.2, 0.7)).toBe(0.5);
    expect(remainingQty(1, 1.5)).toBe(0);
  });
  it("ghi chú: chặn dãy 9 chữ số trở lên kể cả ngăn cách, chặn quá dài", () => {
    expect(hasLongDigitRun("gọi 0912345678")).toBe(true);
    expect(hasLongDigitRun("gọi 0912 345 678")).toBe(true);
    expect(hasLongDigitRun("0912.345.678")).toBe(true);
    expect(hasLongDigitRun("xe 51A-12345")).toBe(false);
    expect(validateNote("khách không nghe máy")).toBeNull();
    expect(validateNote("0912345678")).not.toBeNull();
    expect(validateNote("a".repeat(501))).not.toBeNull();
  });
  it("batchChoices gộp dòng cùng lô", () => {
    const line = (batch_id: string, qty_kg: string) => ({ batch_id, qty_kg, item_name: "Cá" }) as unknown as ReturnableLine;
    const out = batchChoices([line("B1", "1.2"), line("B2", "2"), line("B1", "0.3")]);
    expect(out).toHaveLength(2);
    expect(out[0].delivered).toBe(1.5);
    expect(out[0].returned).toBeNull();
  });
  it("batchChoices lấy returned_qty một lần cho lô nhiều dòng (BE đã trả tổng cả lô, không cộng dồn)", () => {
    const line = (batch_id: string, qty_kg: string, returned_qty?: string) => ({ batch_id, qty_kg, item_name: "Cá", batch_pk: 7, returned_qty }) as unknown as ReturnableLine;
    const out = batchChoices([line("B1", "1.2", "0.500"), line("B1", "0.3", "0.500")]);
    expect(out[0].delivered).toBe(1.5);
    expect(out[0].returned).toBe(0.5);
  });
  it("returnedOf: thiếu hoặc hỏng → null", () => {
    expect(returnedOf({})).toBeNull();
    expect(returnedOf({ returned_qty: "" })).toBeNull();
    expect(returnedOf({ returned_qty: "abc" })).toBeNull();
    expect(returnedOf({ returned_qty: "1.250" })).toBe(1.25);
  });
  it("qtyFactsText: đủ ba số khi biết số đã hoàn, chỉ số đã giao khi chưa biết", () => {
    expect(qtyFactsText(2, 1.5, fmt)).toBe("Đã giao 2 kg, đã hoàn 1,5 kg, còn hoàn được 0,5 kg");
    expect(qtyFactsText(2, null, fmt)).toBe("Đã giao 2 kg");
  });
  it("qtyOverRemaining chặn khi vượt số còn hoàn được", () => {
    expect(qtyOverRemaining("0.5", 2, 1.5, fmt)).toBeNull();
    expect(qtyOverRemaining("0.6", 2, 1.5, fmt)).toContain("chỉ còn hoàn được 0,5 kg");
    expect(qtyOverRemaining("0.1", 2, 2, fmt)).toContain("chỉ còn hoàn được 0 kg");
    expect(qtyOverRemaining("2.1", 2, null, fmt)).not.toBeNull();
    expect(qtyOverRemaining("2", 2, null, fmt)).toBeNull();
  });
  // TL9-M2: sau lỗi BE gắn vào ô (vd vượt kg), người dùng sửa ô thì câu đó không được nhảy lên đầu hộp.
  it("showSubmitAlert: lỗi đã gắn vào ô không hiện ở đầu hộp, kể cả khi lỗi dưới ô đã bị xoá", () => {
    expect(showSubmitAlert("Số kg hoàn vượt số đã giao của lô.", true)).toBe(false);
    expect(showSubmitAlert("Máy chủ đang bận.", false)).toBe(true);
    expect(showSubmitAlert(null, false)).toBe(false);
  });
});

describe("returnsModel — lỗi BE", () => {
  it("stripRuleCode bỏ mã quy tắc", () => {
    expect(stripRuleCode("Lô này không nằm trong phiếu giao (BR-HV-01).")).toBe("Lô này không nằm trong phiếu giao.");
    expect(stripRuleCode("BR-HV-02: Phải chọn quyết định")).not.toMatch(/BR-/);
  });
  it("RETURN_QTY_EXCEEDS → lỗi ở ô số kg có số đã giao, đã hoàn, còn lại", () => {
    const err = new ApiError("x", 400, "RETURN_QTY_EXCEEDS", { delivered_qty: "2.000", already_returned_qty: "1.500" });
    expect(qtyExceedsOf(err)).toEqual({ delivered: 2, already: 1.5 });
    const out = createErrorOf(err, fmt);
    expect(out.field).toBe("qty");
    expect(out.message).toContain("2 kg");
    expect(out.message).toContain("1,5 kg");
    expect(out.message).toContain("0,5 kg");
    expect(out.message).not.toMatch(/BR-/);
    expect(exceedsMessage(1, 1, fmt)).toContain("0 kg");
  });
  it("thiếu số liệu kèm theo vẫn không vỡ", () => {
    expect(qtyExceedsOf(new ApiError("x", 400, "RETURN_QTY_EXCEEDS"))).toBeNull();
    expect(createErrorOf(new ApiError("Số kg hoàn vượt (BR-HV-03)", 400, "RETURN_QTY_EXCEEDS"), fmt).message).not.toMatch(/BR-/);
  });
  it("mã lỗi khác nhau gắn đúng ô", () => {
    expect(createErrorOf(new ApiError("x", 400, "RETURN_BATCH_NOT_IN_NOTE"), fmt).field).toBe("batch");
    expect(createErrorOf(new ApiError("x", 400, "RETURN_NOTE_STATUS"), fmt).field).toBe("deliveryNote");
    expect(createErrorOf(new ApiError("x", 404, "NOT_FOUND"), fmt).field).toBe("deliveryNote");
    expect(createErrorOf(new Error("mạng"), fmt).field).toBeNull();
  });
  it("RETURN_BATCH_CLOSED gắn ô Lô, câu tiếng Việt không lộ mã", () => {
    const out = createErrorOf(new ApiError("Lô đã chốt (BR-HV-04)", 400, "RETURN_BATCH_CLOSED"), fmt);
    expect(out.field).toBe("batch");
    expect(out.message).toMatch(/đã chốt/);
    expect(out.message).not.toMatch(/BR-|RETURN_/);
  });
  it("400 của ô ghi chú từ BE gắn ô Ghi chú: lấy câu của BE, thiếu câu thì dùng câu FE", () => {
    const withText = createErrorOf(new ApiError("Dữ liệu chưa hợp lệ.", 400, undefined, { note: ["Ghi chú không được chứa dãy số dài (số điện thoại, số tài khoản)."] }), fmt);
    expect(withText.field).toBe("note");
    expect(withText.message).toMatch(/dãy số dài/);
    const noText = createErrorOf(new ApiError("x", 400, undefined, { note: [] }), fmt);
    expect(noText.field).toBe("note");
    expect(noText.message).toBe(validateNote("gọi 0912345678"));
  });
  it("approveErrorText", () => {
    expect(approveErrorText(new ApiError("x", 400, "RETURN_DECISION_REQUIRED"))).toMatch(/quyết định|Tái nhập|Huỷ/i);
    expect(approveErrorText(new ApiError("x", 403, "FORBIDDEN"))).toMatch(/quyền/);
    expect(approveErrorText(new ApiError("Lỗi (BR-HV-02)", 500, "X"))).not.toMatch(/BR-/);
  });
});

describe("mock hàng hoàn (theo contract BE Lô 9)", () => {
  it("quyền xem: Chủ, Quản lý, NV kho thấy tất cả; NV giao chỉ phiếu của mình; CSKH không có quyền → 403", () => {
    const all = (call("loc", "GET", BASE).body as Page).results;
    expect(all.length).toBeGreaterThanOrEqual(5);
    expect((call("ql1", "GET", BASE).body as Page).count).toBe((call("kho1", "GET", BASE).body as Page).count);
    const mine = (call("giao1", "GET", BASE).body as Page).results;
    expect(mine.length).toBeGreaterThan(0);
    expect(mine.length).toBeLessThan(all.length);
    expect(call("cs1", "GET", BASE).status).toBe(403);
  });
  it("NV giao mở phiếu của người khác → 404", () => {
    const other = (call("loc", "GET", BASE).body as Page).results.find((r) => !(call("giao1", "GET", BASE).body as Page).results.some((m) => m.id === r.id))!;
    expect(call("giao1", "GET", `${BASE}${other.id}/`).status).toBe(404);
    expect(call("kho1", "GET", `${BASE}${other.id}/`).status).toBe(200);
  });
  it("lọc theo trạng thái", () => {
    const draft = (call("loc", "GET", `${BASE}?status=DRAFT`).body as Page).results;
    expect(draft.every((r) => r.status === "DRAFT")).toBe(true);
  });
  it("tạo vượt số đã giao → 400 RETURN_QTY_EXCEEDS kèm số liệu; lô sai phiếu → 400; thiếu kg → 400", () => {
    const over = call("kho1", "POST", BASE, { delivery_note: 33, batch: 201, qty: "5" });
    expect(over.status).toBe(400);
    expect((over.body as { code: string; delivered_qty: string }).code).toBe("RETURN_QTY_EXCEEDS");
    expect((over.body as { delivered_qty: string }).delivered_qty).toBe("1.000");
    expect(call("kho1", "POST", BASE, { delivery_note: 33, batch: 202, qty: "0.1" }).status).toBe(400);
    expect(call("kho1", "POST", BASE, { delivery_note: 33, batch: 201, qty: "0" }).status).toBe(400);
  });
  it("ghi chú có dãy 9 chữ số → 400 theo ô note (như BE), không tạo phiếu", () => {
    const before = (call("loc", "GET", BASE).body as Page).count;
    const res = call("kho1", "POST", BASE, { delivery_note: 39, batch: 201, qty: "0.1", note: "gọi 0900 000 777" });
    expect(res.status).toBe(400);
    expect(Array.isArray((res.body as { note: string[] }).note)).toBe(true);
    expect((call("loc", "GET", BASE).body as Page).count).toBe(before);
  });
  it("tạo hợp lệ → 201 ở trạng thái Chờ duyệt", () => {
    const ok = call("kho1", "POST", BASE, { delivery_note: 39, batch: 201, qty: "0.1", note: "xe hỏng" });
    expect(ok.status).toBe(201);
    expect((ok.body as ReturnItem).status).toBe("DRAFT");
  });
  it("duyệt: kho1 không có quyền → 403; thiếu quyết định → 400; duyệt hai lần → 409 STALE_STATE", () => {
    const id = (call("loc", "GET", `${BASE}?status=DRAFT`).body as Page).results[0].id;
    expect(call("kho1", "POST", `${BASE}${id}/approve/`, { decision: "RESTOCK" }).status).toBe(403);
    expect(call("ql1", "POST", `${BASE}${id}/approve/`, {}).status).toBe(400);
    expect(call("ql1", "POST", `${BASE}${id}/approve/`, { decision: "RESTOCK" }).status).toBe(200);
    const again = call("ql1", "POST", `${BASE}${id}/approve/`, { decision: "WRITE_OFF" });
    expect(again.status).toBe(409);
    expect((again.body as { code: string }).code).toBe("STALE_STATE");
  });
  it("dòng thời gian không chứa ghi chú tự do", () => {
    const first = (call("loc", "GET", BASE).body as Page).results.find((r) => r.note)!;
    const res = call("loc", "GET", `/api/guidance/return/${first.id}/`);
    expect(res.status).toBe(200);
    expect(JSON.stringify(res.body)).not.toContain(first.note);
  });
});

describe("Huỷ phiếu hàng hoàn (Lô bổ sung A #8)", () => {
  const me = (id: number, permissions: string[]) => ({ id, permissions });
  const row = (status: ReturnItem["status"], created_by: number | null) => ({ status, created_by });

  it("canCancel: người duyệt/sửa huỷ được phiếu Chờ duyệt; người tạo huỷ phiếu của mình; phiếu đã duyệt hoặc đã huỷ thì không", () => {
    const add = "inventory.add_returntostock";
    expect(canCancel(me(1, [add, "inventory.approve_returntostock"]), row("DRAFT", 9))).toBe(true);
    expect(canCancel(me(1, [add, "inventory.change_returntostock"]), row("DRAFT", 9))).toBe(true);
    // TLA-FE-L4: thiếu cổng chung `add_returntostock` (Chủ tắt "Ghi hàng hoàn về kho" của nhóm) thì BE 403 → FE ẩn mục.
    expect(canCancel(me(1, ["inventory.approve_returntostock"]), row("DRAFT", 9))).toBe(false);
    expect(canCancel(me(1, ["inventory.change_returntostock"]), row("DRAFT", 1))).toBe(false);
    expect(canCancel(me(4, ["inventory.add_returntostock"]), row("DRAFT", 4))).toBe(true);
    expect(canCancel(me(4, ["inventory.add_returntostock"]), row("DRAFT", 9))).toBe(false);
    expect(canCancel(me(4, ["inventory.view_returntostock"]), row("DRAFT", 4))).toBe(false);
    expect(canCancel(me(1, [add, "inventory.approve_returntostock"]), row("APPROVED", 9))).toBe(false);
    expect(canCancel(me(1, [add, "inventory.approve_returntostock"]), row("CANCELLED", 9))).toBe(false);
    expect(canCancel(null, row("DRAFT", 9))).toBe(false);
  });
  it("doneSteps của phiếu đã huỷ có 'Huỷ phiếu', không có quyết định", () => {
    expect(doneSteps({ status: "CANCELLED", decision: "PENDING" })).toEqual(["Ghi số kg", "Ghi giờ về kho", "Huỷ phiếu"]);
  });
  it("mock: người tạo huỷ phiếu của mình; huỷ lần hai và duyệt phiếu đã huỷ → 409 STALE_STATE", () => {
    const made = call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: "0.1" }).body as ReturnItem;
    const done = call("kho1", "POST", `${BASE}${made.id}/cancel/`);
    expect(done.status).toBe(200);
    expect((done.body as ReturnItem).status).toBe("CANCELLED");
    const again = call("kho1", "POST", `${BASE}${made.id}/cancel/`);
    expect(again.status).toBe(409);
    expect(again.body).toMatchObject({ code: "STALE_STATE", detail: "Phiếu hàng hoàn đã được xử lý, hãy tải lại." });
    expect(call("ql1", "POST", `${BASE}${made.id}/approve/`, { decision: "RESTOCK" }).status).toBe(409);
  });
  it("mock: người có quyền duyệt huỷ phiếu của người khác; người không tạo và không có quyền duyệt → 403 câu của BE", () => {
    const made = call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: "0.1" }).body as ReturnItem;
    const refused = call("giao1", "POST", `${BASE}${made.id}/cancel/`);
    expect(refused.status).toBe(403);
    expect((refused.body as { detail: string }).detail).toBe("Chỉ người có quyền duyệt hoặc người tạo phiếu mới huỷ được phiếu hàng hoàn.");
    expect(call("ql1", "POST", `${BASE}${made.id}/cancel/`).status).toBe(200);
  });
  it("mock: GET không phải cách huỷ (405); phiếu không có → 404; thiếu quyền nhập hàng hoàn (CSKH) → 403", () => {
    expect(call("loc", "GET", `${BASE}1/cancel/`).status).toBe(405);
    expect(call("loc", "POST", `${BASE}9999/cancel/`).status).toBe(404);
    expect(call("cs1", "POST", `${BASE}1/cancel/`).status).toBe(403);
  });
  it("mock: số kg của phiếu đã huỷ không còn tính vào số đã hoàn của phiếu giao", () => {
    // Hỏi số còn hoàn được từ chính lỗi của mock (đã giao − đã hoàn, phiếu huỷ không tính).
    const over = call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: "99" });
    expect(over.status).toBe(400);
    const d = over.body as { delivered_qty: string; already_returned_qty: string };
    const left = (Number(d.delivered_qty) - Number(d.already_returned_qty)).toFixed(3);
    expect(Number(left)).toBeGreaterThan(0);
    const big = call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: left });
    expect(big.status).toBe(201);
    expect(call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: "0.001" }).status).toBe(400);
    expect(call("kho1", "POST", `${BASE}${(big.body as ReturnItem).id}/cancel/`).status).toBe(200);
    expect(call("kho1", "POST", BASE, { delivery_note: 36, batch: 203, qty: left }).status).toBe(201);
  });
  it("lọc trạng thái Đã huỷ chỉ ra phiếu đã huỷ", () => {
    const rows = (call("loc", "GET", `${BASE}?status=CANCELLED`).body as Page).results;
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.status === "CANCELLED")).toBe(true);
  });
});

describe("mock chi tiết phiếu giao có batch_pk và returned_qty (contract BE cho Lô 9)", () => {
  type Detail = { lines: ReturnableLine[] };
  const detail = (id: number) => (mockGetDeliveryNoteDetail({ method: "GET", path: `/api/delivery/notes/${id}/`, token: token("giao1") }).body as unknown as Detail);
  it("mỗi dòng có batch_pk số nguyên và returned_qty 3 chữ số thập phân", () => {
    installDeliveryLineExtras();
    for (const l of detail(38).lines) {
      expect(Number.isInteger(l.batch_pk)).toBe(true);
      expect(l.returned_qty).toMatch(/^\d+\.\d{3}$/);
    }
  });
  it("returned_qty cộng cả phiếu Chờ duyệt lẫn Đã duyệt của lô trên phiếu đó", () => {
    installDeliveryLineExtras();
    expect(detail(38).lines[0].returned_qty).toBe("0.500");
    call("kho1", "POST", BASE, { delivery_note: 38, batch: 204, qty: "0.2" });
    expect(detail(38).lines[0].returned_qty).toBe("0.700");
  });
});

describe("xoá phiếu hàng hoàn (#8, BR-PQ-10)", () => {
  const make = (qty = "0.1") => {
    return call("kho1", "POST", BASE, { delivery_note: 34, batch: 202, qty }).body as ReturnItem;
  };

  it("canDelete chỉ theo available_actions của BE", () => {
    expect(canDelete({ available_actions: ["approve", "cancel", "delete"] })).toBe(true);
    expect(canDelete({ available_actions: ["approve", "cancel"] })).toBe(false);
    expect(canDelete({ available_actions: [] })).toBe(false);
    expect(canDelete({})).toBe(false);
  });
  it("mock: chỉ Chủ có khoá delete; phiếu đã duyệt thì không ai có", () => {
    const made = make();
    expect((call("loc", "GET", `${BASE}${made.id}/`).body as ReturnItem).available_actions).toContain("delete");
    expect((call("ql1", "GET", `${BASE}${made.id}/`).body as ReturnItem).available_actions).not.toContain("delete");
    expect((call("loc", "GET", `${BASE}3/`).body as ReturnItem).available_actions).not.toContain("delete");
    const list = call("loc", "GET", BASE).body as Page;
    expect(list.results.find((r) => r.id === 6)?.available_actions).toContain("delete");
    call("loc", "POST", `${BASE}${made.id}/delete/`);
  });
  it("mock: Chủ xoá Nháp → 200 rồi 404; khỏi danh sách", () => {
    const made = make();
    const done = call("loc", "POST", `${BASE}${made.id}/delete/`);
    expect(done.status).toBe(200);
    expect(done.body).toEqual({ status: "deleted", id: made.id });
    expect(call("loc", "GET", `${BASE}${made.id}/`).status).toBe(404);
    expect(call("loc", "POST", `${BASE}${made.id}/delete/`).status).toBe(404);
    expect((call("loc", "GET", BASE).body as Page).results.some((r) => r.id === made.id)).toBe(false);
  });
  it("mock: Quản lý 403; phiếu đã duyệt 400 RETURN_DELETE_NOT_ALLOWED đúng câu BE", () => {
    const made = make();
    expect(call("ql1", "POST", `${BASE}${made.id}/delete/`).status).toBe(403);
    const refused = call("loc", "POST", `${BASE}3/delete/`);
    expect(refused.status).toBe(400);
    expect(refused.body).toMatchObject({ code: "RETURN_DELETE_NOT_ALLOWED", detail: "Phiếu hàng hoàn đã duyệt (đã nhập lại kho hoặc ghi lỗ) không xoá được (BR-PQ-10)." });
    call("loc", "POST", `${BASE}${made.id}/delete/`);
  });
});

