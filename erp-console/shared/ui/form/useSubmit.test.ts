import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { conflictOf, fieldErrorsOf, isConflictError, primaryLabel, stateAfterError } from "./useSubmit";

describe("useSubmit helpers", () => {
  it("409 hoặc STALE_STATE là xung đột; lỗi khác thì không", () => {
    expect(isConflictError(new ApiError("x", 409, "STALE_STATE"))).toBe(true);
    expect(isConflictError(new ApiError("x", 400, "STALE_STATE"))).toBe(true);
    expect(isConflictError(new ApiError("x", 409, "STALE_VERSION"))).toBe(true);
    expect(isConflictError(new ApiError("x", 409, undefined, { updated_at: "2026-10-01T01:00:00Z" }))).toBe(true);
    expect(isConflictError(new ApiError("x", 500))).toBe(false);
    expect(isConflictError(new Error("x"))).toBe(false);
  });
  it("409 không phải xung đột phiên bản (CLAIMED, CONTENT_WARNINGS, AI_ACTION_ALREADY_DECIDED, POLICY_CHANGED, không code) là lỗi thường", () => {
    for (const code of ["CLAIMED", "CONTENT_WARNINGS", "AI_ACTION_ALREADY_DECIDED", "POLICY_CHANGED", undefined]) {
      expect(isConflictError(new ApiError("Việc đã có người nhận.", 409, code))).toBe(false);
    }
  });
  it("conflictOf đọc người sửa / giờ nếu BE kèm, không thì rỗng", () => {
    expect(conflictOf(new ApiError("x", 409, undefined, { updated_by_name: "Lộc", updated_at: "2026-10-01T01:00:00Z" }))).toEqual({
      updatedByName: "Lộc",
      updatedAt: "2026-10-01T01:00:00Z",
    });
    expect(conflictOf(new ApiError("x", 409))).toEqual({ updatedAt: undefined, updatedByName: undefined });
  });
  it("fieldErrorsOf gom lỗi theo trường từ 400 của DRF", () => {
    const err = new ApiError("x", 400, undefined, { qty: ["Phải lớn hơn 0."], note: "Quá dài", skip: 5 });
    expect(fieldErrorsOf(err)).toEqual({ qty: "Phải lớn hơn 0.", note: "Quá dài" });
    expect(fieldErrorsOf(new ApiError("x", 500, undefined, { qty: ["a"] }))).toEqual({});
  });
  it("nhãn nút chính đổi thành 'Thử lại' sau lỗi", () => {
    expect(primaryLabel("Lưu phiếu", false)).toBe("Lưu phiếu");
    expect(primaryLabel("Lưu phiếu", true)).toBe("Thử lại");
  });
});

describe("trạng thái sau lỗi gửi (stateAfterError)", () => {
  it("409 CLAIMED: giữ câu lý do của BE, không bật xung đột", () => {
    const st = stateAfterError(new ApiError("Việc đã có người nhận.", 409, "CLAIMED"));
    expect(st.error).toBe("Việc đã có người nhận.");
    expect(st.conflict).toBeNull();
    expect(st.failed).toBe(true);
  });
  it("409 STALE_STATE: bật xung đột, không alert đỏ", () => {
    const st = stateAfterError(new ApiError("Phiếu vừa được người khác cập nhật.", 409, "STALE_STATE", { updated_by_name: "Lộc", updated_at: "2026-10-01T03:30:00Z" }));
    expect(st.error).toBeNull();
    expect(st.conflict).toEqual({ updatedByName: "Lộc", updatedAt: "2026-10-01T03:30:00Z" });
  });
});
