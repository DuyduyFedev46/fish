// SR-25 (Lô 8): tiền = VNĐ có dấu chấm, ngày giờ luôn theo Asia/Ho_Chi_Minh (GMT+7) bất kể múi giờ máy.
// Chạy ở nhiều múi giờ để bắt lỗi "theo giờ máy":
//   TZ=America/New_York npx vitest run shared/lib/format.test.ts
//   TZ=UTC npx vitest run shared/lib/format.test.ts
import { describe, expect, it } from "vitest";
import {
  date,
  dateKeyInVietnam,
  dateTime,
  dateTimeFull,
  money,
  remaining,
  timeHM,
  timeHMS,
  todayInVietnam,
  vnInputToIso,
  vnd,
} from "@/shared/lib/format";

// 17:30 UTC ngày 30/09 = 00:30 ngày 01/10 giờ Việt Nam.
const CROSS_MIDNIGHT = "2026-09-30T17:30:00Z";

describe("vnd (AC1, UI-RULES §1.6: tiền có 'đ')", () => {
  it("chuỗi Decimal từ API 260000.00 -> 260.000 đ", () => {
    expect(vnd("260000.00")).toBe("260.000 đ");
  });
  it("số và chuỗi nguyên", () => {
    expect(vnd(540000)).toBe("540.000 đ");
    expect(vnd("1234567")).toBe("1.234.567 đ");
    expect(vnd("0")).toBe("0 đ");
  });
  it("money: cùng số nhưng không đơn vị (ô bảng)", () => {
    expect(money("540000")).toBe("540.000");
    expect(money("260000.00")).toBe("260.000");
    expect(money(null)).toBe("—");
    expect(money("abc")).toBe("—");
  });
  it("rác / rỗng -> —", () => {
    expect(vnd("abc")).toBe("—");
    expect(vnd("")).toBe("—");
    expect(vnd(null)).toBe("—");
    expect(vnd(undefined)).toBe("—");
    expect(vnd(Number.NaN)).toBe("—");
  });
});

describe("ngày giờ theo giờ Việt Nam (AC2)", () => {
  it("dateTime luôn đủ ngày giờ có năm, giờ VN (UI-RULES §1.5)", () => {
    expect(dateTime("2026-10-01T02:32:00Z")).toBe("01/10/2026 09:32");
  });
  it("dateTime qua nửa đêm VN", () => {
    expect(dateTime(CROSS_MIDNIGHT)).toBe("01/10/2026 00:30");
  });
  it("dateTimeFull", () => {
    expect(dateTimeFull(CROSS_MIDNIGHT)).toBe("01/10/2026 00:30");
  });
  it("date", () => {
    expect(date(CROSS_MIDNIGHT)).toBe("01/10/2026");
  });
  it("timeHM / timeHMS", () => {
    expect(timeHM(CROSS_MIDNIGHT)).toBe("00:30");
    expect(timeHMS("2026-09-30T05:07:09Z")).toBe("12:07:09");
  });
  it("giờ ban ngày", () => {
    expect(dateTime("2026-09-30T07:05:00Z")).toBe("30/09/2026 14:05");
  });
  it("rỗng / rác -> —", () => {
    for (const f of [dateTime, dateTimeFull, date, timeHM, timeHMS]) {
      expect(f(null)).toBe("—");
      expect(f(undefined)).toBe("—");
      expect(f("")).toBe("—");
      expect(f("không phải ngày")).toBe("—");
    }
  });
});

describe("ô datetime-local là giờ VN (AC4)", () => {
  it("15:00 nhập vào = 08:00 UTC", () => {
    expect(vnInputToIso("2026-09-30T15:00")).toBe("2026-09-30T08:00:00.000Z");
    expect(vnInputToIso("2026-09-30T00:30:15")).toBe("2026-09-29T17:30:15.000Z");
  });
  it("rỗng / sai định dạng -> rỗng", () => {
    expect(vnInputToIso("")).toBe("");
    expect(vnInputToIso(null)).toBe("");
    expect(vnInputToIso("30/09/2026 15:00")).toBe("");
  });
});

describe("ngày 'hôm nay' theo giờ VN (AC4)", () => {
  it("todayInVietnam qua nửa đêm VN", () => {
    expect(todayInVietnam(new Date(CROSS_MIDNIGHT))).toBe("2026-10-01");
    expect(todayInVietnam(new Date("2026-09-30T16:59:59Z"))).toBe("2026-09-30");
  });
  it("dateKeyInVietnam", () => {
    expect(dateKeyInVietnam(CROSS_MIDNIGHT)).toBe("2026-10-01");
    expect(dateKeyInVietnam("bad")).toBe("");
  });
});

describe("remaining: đếm ngược mm:ss", () => {
  const at = Date.parse("2026-10-01T02:00:00Z");
  it("còn 2 phút 5 giây", () => {
    expect(remaining("2026-10-01T02:02:05Z", at)).toBe("02:05");
  });
  it("phút quá 59 vẫn là mm:ss", () => {
    expect(remaining("2026-10-01T03:05:12Z", at)).toBe("65:12");
  });
  it("đã qua mốc -> hết giờ; không mốc / rác -> null", () => {
    expect(remaining("2026-10-01T01:59:00Z", at)).toBe("hết giờ");
    expect(remaining(null, at)).toBeNull();
    expect(remaining("rác", at)).toBeNull();
  });
});
