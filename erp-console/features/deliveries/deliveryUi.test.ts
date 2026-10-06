import { describe, expect, it } from "vitest";
import {
  hasLongDigitRun,
  lineNames,
  loadedOnlyNote,
  canAssign,
  detailHref,
  doneSteps,
  failureFieldOfCode,
  groupMine,
  idFromSearch,
  nextStepText,
  pathOf,
  telHref,
  validateFailureInput,
} from "./deliveryUi";

describe("deliveryUi: thanh trạng thái và việc tiếp theo", () => {
  it("FAILED hỏng sau bước Đang giao; CANCELLED không có bước đã qua", () => {
    expect(pathOf({ status: "FAILED" })).toEqual({ current: "DELIVERING", badEnd: { label: "Giao thất bại", after: "DELIVERING" } });
    expect(pathOf({ status: "CANCELLED" }).badEnd?.label).toBe("Đã huỷ theo đơn");
    expect(pathOf({ status: "READY" })).toEqual({ current: "READY", badEnd: null });
  });

  it("READY chưa gán người giao thì việc tiếp theo là giao phiếu; đã gán thì là nhận hàng", () => {
    expect(nextStepText({ status: "READY", assigned_to: null, failed_attempts: 0 })).toMatch(/Chọn người giao/);
    expect(nextStepText({ status: "READY", assigned_to: 4, failed_attempts: 0 })).toMatch(/nhận hàng/);
    expect(nextStepText({ status: "COMPLETED", assigned_to: 4, failed_attempts: 0 })).toBeNull();
    expect(nextStepText({ status: "FAILED", assigned_to: 4, failed_attempts: 2 })).toMatch(/quyết định/);
  });

  it("doneSteps tăng dần theo trạng thái", () => {
    expect(doneSteps({ status: "CONFIRMING" })).toEqual([]);
    expect(doneSteps({ status: "READY" })).toHaveLength(2);
    expect(doneSteps({ status: "COMPLETED" })).toHaveLength(5);
    expect(doneSteps({ status: "CANCELLED" })).toEqual([]);
  });
});

describe("deliveryUi: F2o chỉ hiện khi có 'assign' và phiếu chưa lên xe", () => {
  it("có quyền + READY → được; thiếu 'assign' → không; DELIVERING dù có 'assign' → không", () => {
    expect(canAssign({ status: "READY", available_actions: ["assign", "reprint_label"] })).toBe(true);
    expect(canAssign({ status: "READY", available_actions: ["reprint_label"] })).toBe(false);
    expect(canAssign({ status: "DELIVERING", available_actions: ["assign"] })).toBe(false);
    expect(canAssign({ status: "CONFIRMING", available_actions: ["assign"] })).toBe(true);
  });
});

describe("deliveryUi: F2l báo giao thất bại (khớp B5)", () => {
  it("bắt buộc lý do; lý do lạ cũng bị chặn", () => {
    expect(validateFailureInput("", "")?.field).toBe("reason");
    expect(validateFailureInput("HACK", "")?.field).toBe("reason");
    expect(validateFailureInput("NOT_MET", "")).toBeNull();
  });

  it("'Khác' bắt buộc ghi chú; khoảng trắng không tính", () => {
    expect(validateFailureInput("OTHER", "   ")?.field).toBe("note");
    expect(validateFailureInput("OTHER", "Khách đi vắng, hẹn ngày mai")).toBeNull();
  });

  it("ghi chú có dãy 9 chữ số trở lên bị chặn (SĐT), 8 chữ số thì được", () => {
    expect(validateFailureInput("NOT_MET", "gọi 0909123456 không nghe")?.field).toBe("note");
    expect(validateFailureInput("NOT_MET", "gọi số 12345678 không nghe")).toBeNull();
    expect(hasLongDigitRun("090 912 3456")).toBe(true); // BE gộp cả dấu cách
  });

  it("ghi chú quá 200 ký tự bị chặn", () => {
    expect(validateFailureInput("NOT_MET", "a".repeat(201))?.field).toBe("note");
    expect(validateFailureInput("NOT_MET", "a".repeat(200))).toBeNull();
  });

  it("mã lỗi 400 của BE trỏ đúng ô", () => {
    expect(failureFieldOfCode("DELIVERY_FAILURE_REASON_REQUIRED")).toBe("reason");
    expect(failureFieldOfCode("DELIVERY_FAILURE_NOTE_PII")).toBe("note");
    expect(failureFieldOfCode("DELIVERY_FAILURE_NOTE_REQUIRED")).toBe("note");
    expect(failureFieldOfCode("STALE_STATE")).toBeNull();
    expect(failureFieldOfCode(undefined)).toBeNull();
  });
});

describe("deliveryUi: Việc giao của tôi", () => {
  it("chia 4 nhóm đúng trạng thái, bỏ trạng thái khác", () => {
    const g = groupMine([{ status: "DELIVERING" }, { status: "READY" }, { status: "FAILED" }, { status: "COMPLETED" }, { status: "CANCELLED" }, { status: "DELIVERING" }]);
    expect(g.DELIVERING).toHaveLength(2);
    expect(g.READY).toHaveLength(1);
    expect(g.FAILED).toHaveLength(1);
    expect(g.COMPLETED).toHaveLength(1);
  });

  it("telHref giữ chữ số và +; số quá ngắn hoặc trống thì không dựng link", () => {
    expect(telHref("0900 000 036")).toBe("tel:0900000036");
    expect(telHref("+84 900 000 036")).toBe("tel:+84900000036");
    expect(telHref("123")).toBeNull();
    expect(telHref(null)).toBeNull();
    expect(telHref("")).toBeNull();
  });
});

describe("deliveryUi: đường dẫn chi tiết chỉ mang id số", () => {
  it("detailHref không chứa dữ liệu khách; idFromSearch chỉ nhận số nguyên dương", () => {
    expect(detailHref(36)).toBe("/deliveries/detail/?id=36");
    expect(idFromSearch("36")).toBe(36);
    expect(idFromSearch("0")).toBeNull();
    expect(idFromSearch("-3")).toBeNull();
    expect(idFromSearch("12abc")).toBeNull();
    expect(idFromSearch("<script>")).toBeNull();
    expect(idFromSearch(null)).toBeNull();
  });
});

describe("deliveryUi: ghi chú giao thất bại cùng luật has_long_digit_run của BE", () => {
  it("chặn SĐT có dấu cách, dấu chấm, gạch ngang; cho qua ngày giờ ngắn", () => {
    expect(hasLongDigitRun("0912 345 678")).toBe(true);
    expect(hasLongDigitRun("091.234.5678")).toBe(true);
    expect(hasLongDigitRun("091-234-5678")).toBe(true);
    expect(hasLongDigitRun("0912345678")).toBe(true);
    expect(hasLongDigitRun("Khách hẹn giao lại ngày mai")).toBe(false);
    expect(hasLongDigitRun("hẹn 14h ngày 12/05")).toBe(false);
    expect(validateFailureInput("NOT_MET", "gọi 0912 345 678 không nghe")?.field).toBe("note");
    expect(validateFailureInput("NOT_MET", "Khách hẹn giao lại ngày mai")).toBeNull();
  });
});

describe("deliveryUi: Hàng chỉ có tên mặt hàng, số kg nằm ở trường Số kg", () => {
  it("bỏ phần kg của từng dòng (cả dạng 2.000 của BE và 2,000)", () => {
    expect(lineNames("Tôm sú loại 1 2.000 kg · Mực lá Phan Thiết 1.000 kg")).toBe("Tôm sú loại 1 · Mực lá Phan Thiết");
    expect(lineNames("Cá thu Côn Đảo 1,500 kg")).toBe("Cá thu Côn Đảo");
    expect(lineNames("")).toBe("");
    expect(lineNames(null)).toBe("");
  });
  it("câu 'Tiếp theo' của phiếu Soạn hàng đúng chữ AC (ED-17-AC2)", () => {
    expect(nextStepText({ status: "PREPARING", assigned_to: null, failed_attempts: 0 })).toBe("In tem, đóng gói, rồi bấm Đã đóng gói");
  });
});

describe("deliveryUi: nợ 6 — tìm trong các phiếu đã tải", () => {
  it("câu báo nêu số phiếu đã tải và nhắc Tải thêm", () => {
    expect(loadedOnlyNote(50)).toBe("Chỉ tìm trong 50 phiếu đã tải. Bấm Tải thêm để tìm tiếp.");
  });
});
