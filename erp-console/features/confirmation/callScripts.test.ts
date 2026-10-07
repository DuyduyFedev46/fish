import { beforeEach, describe, expect, it } from "vitest";
import { SCRIPT_MAX, SCRIPT_MESSAGES, SCRIPT_SITUATIONS, scriptError, slotsOf } from "./callScripts";
import { mockCreateCallScript, mockListCallScripts, mockUpdateCallScript, resetMockCallScripts, scriptsForQueueItem } from "./mockScripts";
import { mockRequireUser } from "@/features/auth/mock";
import type { CallScript } from "./types";

// CS-18: kịch bản gọi soạn sẵn. Nội dung và số điện thoại dưới đây là chữ bịa.
const token = (u: string) => `mock-token-${u}-${Date.now() + 1000}`;
const req = (user: string, method: "GET" | "POST" | "PATCH", path: string, body?: unknown) => ({ method, path, body, token: token(user) });
const me = (user: string) => mockRequireUser(req(user, "GET", "/"));

beforeEach(() => resetMockCallScripts());

describe("CS-18: kiểm nội dung ở máy khách (BR-GH-19)", () => {
  it("rỗng, quá dài, có số điện thoại hay dãy số dài đều bị chặn; chữ bình thường qua", () => {
    expect(scriptError("")).toBe(SCRIPT_MESSAGES.empty);
    expect(scriptError("   ")).toBe(SCRIPT_MESSAGES.empty);
    expect(scriptError("a".repeat(SCRIPT_MAX + 1))).toBe(SCRIPT_MESSAGES.tooLong);
    expect(scriptError("a".repeat(SCRIPT_MAX))).toBeNull();
    expect(scriptError("Gọi số 0900 000 123 nhé")).toBe(SCRIPT_MESSAGES.pii);
    expect(scriptError("Liên hệ 090.000.0123")).toBe(SCRIPT_MESSAGES.pii);
    expect(scriptError("Rã đông 8 tiếng, dùng trong 24 giờ, giảm 15%")).toBeNull();
  });
  it("bốn tình huống đúng thứ tự; tình huống chưa soạn có script null", () => {
    expect(SCRIPT_SITUATIONS.map((s) => s.value)).toEqual(["FIRST_ORDER", "RETURNING", "COMBO", "GENERAL"]);
    const slots = slotsOf([{ situation: "GENERAL", situation_label: "Lời dặn chung", content: "x", is_active: true }]);
    expect(slots.map((s) => s.script === null)).toEqual([true, true, true, false]);
  });
});

describe("CS-18: mock API theo contract BE", () => {
  it("GET: Chủ thấy cả kịch bản đã tắt; Quản lý và CSKH chỉ thấy đang bật; NV kho và NV giao 403 (AC4)", () => {
    const owner = (mockListCallScripts(req("loc", "GET", "/api/confirmation/scripts/")).body as { results: CallScript[] }).results;
    expect(owner.some((s) => !s.is_active)).toBe(true);
    for (const u of ["ql1", "cs1"]) {
      const rows = (mockListCallScripts(req(u, "GET", "/api/confirmation/scripts/")).body as { results: CallScript[] }).results;
      expect(rows.length).toBeGreaterThan(0);
      expect(rows.every((s) => s.is_active), u).toBe(true);
    }
    for (const u of ["kho1", "giao1"]) expect(mockListCallScripts(req(u, "GET", "/api/confirmation/scripts/")).status, u).toBe(403);
  });

  it("POST và PATCH: chỉ Chủ; Quản lý và CSKH 403 (AC4)", () => {
    for (const u of ["ql1", "cs1"]) {
      expect(mockCreateCallScript(req(u, "POST", "/api/confirmation/scripts/", { situation: "RETURNING", content: "Chào", is_active: true })).status, u).toBe(403);
      expect(mockUpdateCallScript(req(u, "PATCH", "/api/confirmation/scripts/GENERAL/", { is_active: false })).status, u).toBe(403);
    }
    expect(mockCreateCallScript(req("loc", "POST", "/api/confirmation/scripts/", { situation: "RETURNING", content: "Chào anh chị", is_active: true })).status).toBe(201);
  });

  it("400: nội dung rỗng, quá 2000 ký tự, có số điện thoại (BR-GH-19), tình huống đã có hoặc sai (AC3)", () => {
    const post = (b: unknown) => mockCreateCallScript(req("loc", "POST", "/api/confirmation/scripts/", b));
    expect(post({ situation: "RETURNING", content: "", is_active: true }).status).toBe(400);
    expect(post({ situation: "RETURNING", content: "a".repeat(2001), is_active: true }).status).toBe(400);
    const pii = post({ situation: "RETURNING", content: "Gọi 0900000123", is_active: true });
    expect(pii.status).toBe(400);
    expect((pii.body as { code: string }).code).toBe("BR-GH-19");
    expect(post({ situation: "FIRST_ORDER", content: "Trùng", is_active: true }).status).toBe(400);
    expect(post({ situation: "KHAC", content: "Chào", is_active: true }).status).toBe(400);
  });

  it("PATCH: sửa nội dung, tắt/bật; 404 khi chưa có kịch bản", () => {
    expect(mockUpdateCallScript(req("loc", "PATCH", "/api/confirmation/scripts/RETURNING/", { is_active: false })).status).toBe(404);
    const res = mockUpdateCallScript(req("loc", "PATCH", "/api/confirmation/scripts/GENERAL/", { content: "Nội dung mới", is_active: false }));
    expect(res.body).toMatchObject({ situation: "GENERAL", content: "Nội dung mới", is_active: false });
  });
});

describe("CS-18: khoá scripts của chi tiết hàng chờ (AC1, AC2)", () => {
  const item = { note_id: 31, lines_summary: "Tôm sú loại 1 2,000 kg" };
  it("khách lần đầu: FIRST_ORDER rồi GENERAL; khách quen: RETURNING (nếu bật) rồi GENERAL", () => {
    expect(scriptsForQueueItem(item, me("cs1")).map((s) => s.situation)).toEqual(["FIRST_ORDER", "GENERAL"]);
    expect(scriptsForQueueItem({ ...item, note_id: 28 }, me("cs1")).map((s) => s.situation)).toEqual(["GENERAL"]); // chưa soạn RETURNING
  });
  it("Chủ tắt kịch bản thì CSKH mở lại không thấy", () => {
    mockUpdateCallScript(req("loc", "PATCH", "/api/confirmation/scripts/FIRST_ORDER/", { is_active: false }));
    expect(scriptsForQueueItem(item, me("cs1")).map((s) => s.situation)).toEqual(["GENERAL"]);
  });
  it("đơn có combo thêm COMBO khi đang bật", () => {
    mockUpdateCallScript(req("loc", "PATCH", "/api/confirmation/scripts/COMBO/", { is_active: true }));
    expect(scriptsForQueueItem({ ...item, lines_summary: "Combo hải sản 1 phần" }, me("cs1")).map((s) => s.situation)).toEqual(["FIRST_ORDER", "COMBO", "GENERAL"]);
  });
  it("người không có quyền xem kịch bản (NV giao): rỗng", () => {
    expect(scriptsForQueueItem(item, me("giao1"))).toEqual([]);
  });
});
