// ED-42: phần thuần của "Báo cáo AI cuối ngày".
import { describe, expect, it } from "vitest";
import type { AiDailyReport } from "../types";
import { canGoNext, clampDay, dayTotal, shiftDay, targetTypeLabel, totalsOf } from "./view";

describe("totalsOf", () => {
  it("cộng từng cột; rỗng thì toàn 0", () => {
    expect(totalsOf([])).toEqual({ A: 0, B: 0, C_confirmed: 0, C_expired: 0, undone: 0, escalated: 0 });
    const row = (n: number) => ({ user_id: n, display_name: "x", A: n, B: 1, C_confirmed: 2, C_expired: 0, undone: 1, escalated: 0 });
    expect(totalsOf([row(1), row(2)])).toEqual({ A: 3, B: 2, C_confirmed: 4, C_expired: 0, undone: 2, escalated: 0 });
  });
});

describe("đổi ngày", () => {
  it("lùi/tiến qua cuối tháng và cuối năm", () => {
    expect(shiftDay("2026-10-01", -1)).toBe("2026-09-30");
    expect(shiftDay("2026-12-31", 1)).toBe("2027-01-01");
    expect(shiftDay("bad", 1)).toBe("bad");
  });
  it("không cho sang ngày sau hôm nay", () => {
    expect(canGoNext("2026-10-02", "2026-10-03")).toBe(true);
    expect(canGoNext("2026-10-03", "2026-10-03")).toBe(false);
  });
  it("clampDay kéo ngày tương lai hoặc sai về hôm nay", () => {
    expect(clampDay("2026-10-09", "2026-10-03")).toBe("2026-10-03");
    expect(clampDay("", "2026-10-03")).toBe("2026-10-03");
    expect(clampDay("2026-09-01", "2026-10-03")).toBe("2026-09-01");
  });
});

describe("targetTypeLabel", () => {
  it("loại đã biết bằng tiếng Việt, loại lạ thì Chứng từ", () => {
    expect(targetTypeLabel("purchasereceipt")).toBe("Phiếu nhập");
    expect(targetTypeLabel("batch")).toBe("Lô");
    expect(targetTypeLabel("weird_model")).toBe("Chứng từ");
  });
});

describe("dayTotal", () => {
  const item = (id: string, level: "A" | "B" | "C", status: string) => ({
    id, command: "x.y", title: "t", level, status, owner_display: "u", created_at: "2026-10-03T09:00:00+07:00", target: null, result_ref: null,
  });
  it("việc mức B rồi bị hoàn tác chỉ tính 1 (cột B và cột Đã hoàn tác cùng đếm nó)", () => {
    const report = {
      date: "2026-10-03",
      by_user: [{ user_id: 1, display_name: "x", A: 0, B: 1, C_confirmed: 0, C_expired: 0, undone: 1, escalated: 0 }],
      items: [item("a", "B", "UNDONE")],
    } as unknown as AiDailyReport;
    const t = totalsOf(report.by_user);
    expect(t.A + t.B + t.C_confirmed + t.C_expired + t.undone + t.escalated).toBe(2); // cộng cột sẽ đếm đôi
    expect(dayTotal(report)).toBe(1);
  });
  it("bằng số dòng nhật ký; ngày rỗng thì 0", () => {
    expect(dayTotal({ items: [item("a", "A", "DONE"), item("b", "C", "CONFIRMED")] } as unknown as AiDailyReport)).toBe(2);
    expect(dayTotal({ items: [] })).toBe(0);
  });
});
