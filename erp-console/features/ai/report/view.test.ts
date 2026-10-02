// ED-41: phần thuần của "Báo cáo AI cuối ngày".
import { describe, expect, it } from "vitest";
import { canGoNext, clampDay, grandTotal, shiftDay, targetTypeLabel, totalsOf } from "./view";

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

describe("grandTotal", () => {
  it("cộng cả sáu cột như board W4d (29+3+5+1+1+2 = 41)", () => {
    expect(grandTotal({ A: 29, B: 3, C_confirmed: 5, C_expired: 1, undone: 1, escalated: 2 })).toBe(41);
  });
  it("ngày rỗng thì 0", () => {
    expect(grandTotal(totalsOf([]))).toBe(0);
  });
});
