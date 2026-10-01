import { describe, expect, it } from "vitest";
import { conflictMessage } from "./ConflictBanner";

describe("conflictMessage", () => {
  it("có tên người sửa và giờ", () => {
    const m = conflictMessage("phiếu", "Lộc", "2026-10-01T03:30:00Z");
    expect(m).toContain("Phiếu vừa được Lộc sửa lúc");
    expect(m).toContain("10:30"); // 03:30 UTC = 10:30 giờ Việt Nam
    expect(m).toContain("Tải lại để xem bản mới.");
  });
  it("không có thông tin người sửa", () => {
    expect(conflictMessage("đơn")).toBe("Đơn vừa được người khác sửa. Tải lại để xem bản mới.");
  });
});
