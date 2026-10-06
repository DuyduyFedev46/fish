import { describe, expect, it } from "vitest";
import {
  mockGetDeliverers,
  mockListDeliveryNotes,
  mockGetDeliveryNoteDetail,
  mockPostDeliveryAssign,
  mockPostDeliveryNoteStatus,
  mockDeliveryNotes,
} from "./mock";
import type { Deliverer, DeliveryListResponse, DeliveryNoteDetail } from "./types";

// Lô 4: mock khớp contract B5 (báo giao thất bại), B6 (người giao + giao phiếu), R4 (assigned_to=me, SĐT ở chi tiết).
function token(username: string): string {
  return `mock-token-${username}-${Date.now() + 1000}`;
}
const req = (username: string, path: string, method: "GET" | "POST" = "GET", body?: unknown) => ({ method, path, body, token: token(username) });
const note = (id: number) => mockDeliveryNotes().find((n) => n.id === id)!;

describe("B6 deliverers", () => {
  it("ql1 (có quyền giao người) thấy người giao kèm số phiếu đang giao / chờ lấy", () => {
    const res = mockGetDeliverers(req("ql1", "/api/delivery/deliverers/"));
    expect(res.status).toBe(200);
    const list = res.body as Deliverer[];
    expect(Array.isArray(list)).toBe(true);
    const phuc = list.find((d) => d.display_name === "Anh Phúc");
    expect(phuc).toMatchObject({ id: 4 });
    expect(phuc!.delivering_count).toBeGreaterThanOrEqual(1);
    expect(typeof phuc!.ready_count).toBe("number");
  });

  it("giao1 (không có quyền giao người) bị 403", () => {
    expect(mockGetDeliverers(req("giao1", "/api/delivery/deliverers/")).status).toBe(403);
  });
});

describe("B6 assign", () => {
  it("giao thành công, đổi người; cùng người → already", () => {
    const first = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/37/assign/", "POST", { assigned_to: 7, expected_assigned_to: 4 }));
    expect(first.status).toBe(200);
    expect((first.body as { assigned_to: number; already: boolean }).assigned_to).toBe(7);
    expect((first.body as { already: boolean }).already).toBe(false);
    const again = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/37/assign/", "POST", { assigned_to: 7, expected_assigned_to: 7 }));
    expect((again.body as { already: boolean }).already).toBe(true);
    note(37).assigned_to = 4; // trả lại dữ liệu mẫu
  });

  it("expected_assigned_to lệch → 409 STALE_STATE (chỉ có code + assigned_to)", () => {
    const res = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/37/assign/", "POST", { assigned_to: 7, expected_assigned_to: null }));
    expect(res.status).toBe(409);
    expect((res.body as { code: string }).code).toBe("STALE_STATE");
    expect((res.body as { assigned_to: number }).assigned_to).toBe(4);
  });

  it("phiếu đang giao → 400 DELIVERY_ASSIGN_STATE; người không thuộc nhóm giao → 400 DELIVERY_ASSIGNEE_INVALID", () => {
    const state = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/36/assign/", "POST", { assigned_to: 7, expected_assigned_to: 4 }));
    expect(state.status).toBe(400);
    expect((state.body as { code: string }).code).toBe("DELIVERY_ASSIGN_STATE");
    const bad = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/37/assign/", "POST", { assigned_to: 99, expected_assigned_to: 4 }));
    expect((bad.body as { code: string }).code).toBe("DELIVERY_ASSIGNEE_INVALID");
  });

  it("không có quyền → 403", () => {
    expect(mockPostDeliveryAssign(req("giao1", "/api/delivery/notes/37/assign/", "POST", { assigned_to: 4 })).status).toBe(403);
  });

  it("phiếu 45: lần giao đầu bị người khác giao trước (409), lần sau thì được", () => {
    const body = { assigned_to: 4, expected_assigned_to: null };
    const first = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/45/assign/", "POST", body));
    expect(first.status).toBe(409);
    const second = mockPostDeliveryAssign(req("ql1", "/api/delivery/notes/45/assign/", "POST", { assigned_to: 4, expected_assigned_to: 7 }));
    expect(second.status).toBe(200);
    note(45).assigned_to = null;
  });

  it("available_actions có 'assign' cho ql1 ở phiếu READY, không có cho giao1", () => {
    const asManager = mockGetDeliveryNoteDetail(req("ql1", "/api/delivery/notes/37/")).body as DeliveryNoteDetail;
    expect(asManager.available_actions).toContain("assign");
    const asCourier = mockGetDeliveryNoteDetail(req("giao1", "/api/delivery/notes/37/")).body as DeliveryNoteDetail;
    expect(asCourier.available_actions).not.toContain("assign");
  });
});

describe("B5 báo giao thất bại", () => {
  const fail = (body: Record<string, unknown>, id = 39) =>
    mockPostDeliveryNoteStatus(req("giao2", `/api/delivery/notes/${id}/status/`, "POST", { to_status: "FAILED", from_status: "DELIVERING", ...body }));

  it("thiếu lý do → 400 DELIVERY_FAILURE_REASON_REQUIRED", () => {
    const res = fail({});
    expect(res.status).toBe(400);
    expect((res.body as { code: string }).code).toBe("DELIVERY_FAILURE_REASON_REQUIRED");
  });

  it("'Khác' không ghi chú → 400 NOTE_REQUIRED; ghi chú có SĐT → 400 NOTE_PII; quá 200 ký tự → 400 NOTE_INVALID", () => {
    expect((fail({ failure_reason: "OTHER" }).body as { code: string }).code).toBe("DELIVERY_FAILURE_NOTE_REQUIRED");
    expect((fail({ failure_reason: "NOT_MET", failure_note: "gọi 0909123456" }).body as { code: string }).code).toBe("DELIVERY_FAILURE_NOTE_PII");
    expect((fail({ failure_reason: "NOT_MET", failure_note: "gọi 0912 345 678" }).body as { code: string }).code).toBe("DELIVERY_FAILURE_NOTE_PII");
    expect((fail({ failure_reason: "NOT_MET", failure_note: "a".repeat(201) }).body as { code: string }).code).toBe("DELIVERY_FAILURE_NOTE_INVALID");
  });

  it("hợp lệ → FAILED, ghi lý do, tăng số lần; phiếu không còn DELIVERING thì 409", () => {
    const before = note(39).failed_attempts;
    const ok = fail({ failure_reason: "NOT_MET", failure_note: "Khách đi vắng" });
    expect(ok.status).toBe(200);
    const body = ok.body as { status: string; failure_reason: string; failed_attempts: number; needs_decision: boolean };
    expect(body.status).toBe("FAILED");
    expect(body.failure_reason).toBe("NOT_MET");
    expect(body.failed_attempts).toBe(before + 1);
    expect(fail({ failure_reason: "NOT_MET" }).status).toBe(409);
    // trả lại dữ liệu mẫu
    Object.assign(note(39), { status: "DELIVERING", status_label: "Đang giao", failed_attempts: before, failure_reason: undefined, failure_note: undefined });
  });
});

describe("R4 assigned_to=me và SĐT ở chi tiết", () => {
  it("giao1 + assigned_to=me chỉ thấy phiếu của mình; xin id người khác bị 403", () => {
    const res = mockListDeliveryNotes(req("giao1", "/api/delivery/notes/?assigned_to=me&status=READY,DELIVERING,FAILED"));
    const rows = (res.body as DeliveryListResponse).results;
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((n) => n.assigned_to === 4)).toBe(true);
    expect(rows.every((n) => ["READY", "DELIVERING", "FAILED"].includes(n.status))).toBe(true);
    expect(mockListDeliveryNotes(req("giao1", "/api/delivery/notes/?assigned_to=7")).status).toBe(403);
  });

  it("Lô bổ sung A #17: assigned_to=me có phone cho phiếu Đang giao/Giao thất bại, null cho phiếu còn lại; danh sách khác không có khoá phone", () => {
    const mine = (mockListDeliveryNotes(req("giao1", "/api/delivery/notes/?assigned_to=me")).body as DeliveryListResponse).results;
    const active = mine.filter((n) => n.status === "DELIVERING" || n.status === "FAILED");
    expect(active.length).toBeGreaterThan(0);
    expect(active.every((n) => typeof n.phone === "string" && n.phone.length > 0)).toBe(true);
    expect(mine.filter((n) => n.status !== "DELIVERING" && n.status !== "FAILED").every((n) => n.phone === null)).toBe(true);
    const other = (mockListDeliveryNotes(req("ql1", "/api/delivery/notes/?status=DELIVERING")).body as DeliveryListResponse).results;
    expect(other.every((n) => !("phone" in n))).toBe(true);
  });

  it("chi tiết có phone; giao1 không mở được phiếu của người khác", () => {
    const detail = mockGetDeliveryNoteDetail(req("giao1", "/api/delivery/notes/36/")).body as DeliveryNoteDetail;
    expect(detail.phone).toBeTruthy();
    expect(mockGetDeliveryNoteDetail(req("giao1", "/api/delivery/notes/39/")).status).toBe(404);
  });
});

describe("Lô bổ sung A #18: mốc Bắt đầu giao và Giao thất bại", () => {
  it("phiếu Đang giao có delivery_started_at, chưa có failed_at; phiếu Chờ lấy chưa có cả hai", () => {
    const rows = (mockListDeliveryNotes(req("ql1", "/api/delivery/notes/")).body as DeliveryListResponse).results;
    const delivering = rows.find((n) => n.status === "DELIVERING")!;
    expect(delivering.delivery_started_at).toBeTruthy();
    expect(delivering.failed_at).toBeNull();
    const ready = rows.find((n) => n.status === "READY")!;
    expect(ready.delivery_started_at).toBeNull();
    expect(ready.failed_at).toBeNull();
  });

  it("báo thất bại ghi failed_at; giao lại ghi đè delivery_started_at", () => {
    const post = (to: string, extra: object = {}) => mockPostDeliveryNoteStatus(req("giao2", "/api/delivery/notes/39/status/", "POST", { to_status: to, ...extra }));
    const snapshot = { ...note(39) };
    const failed = post("FAILED", { failure_reason: "NOT_MET", failure_note: "Khách đi vắng" });
    expect(failed.status).toBe(200);
    const f = failed.body as { failed_at: string; delivery_started_at: string };
    expect(Date.parse(f.failed_at)).toBeGreaterThan(0);
    const again = post("DELIVERING");
    expect(again.status).toBe(200);
    const a = again.body as { delivery_started_at: string; failed_at: string };
    expect(Date.parse(a.delivery_started_at)).toBeGreaterThanOrEqual(Date.parse(f.failed_at) - 1000);
    expect(a.failed_at).toBe(f.failed_at);
    Object.assign(note(39), snapshot);
  });
});

describe("B11 mock `loc` (Chủ) giống BE: có quyền in tem và đóng gói", () => {
  it("phiếu Soạn hàng chưa in: loc có print_label và set_status:READY", () => {
    const item = (mockListDeliveryNotes(req("loc", "/api/delivery/notes/?status=PREPARING")).body as DeliveryListResponse).results.find((n) => n.id === 31)!;
    expect(item.available_actions).toEqual(expect.arrayContaining(["print_label", "set_status:READY"]));
  });
});
