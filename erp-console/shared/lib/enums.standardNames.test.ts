// Lô áp tên chuẩn (02b mục 3.2): so từng dòng T của doc/thuat-ngu-va-trang-thai.md mục 4 với ENUMS và menu.
// Cột "Chuẩn". Dòng chỉ có ở BE hoặc Shop (T1 Shop, T24-T30 Shop, T43...) không nằm ở đây.
// TODO Pha B: thêm actionLabel() cho T67-T76 và P1, P3-P9, P11 khi auditModel.ts (W37 L3) đã gộp.
import { describe, expect, it } from "vitest";
import { ENUMS, enumLabel, type EnumName } from "@/shared/lib/enums";
import { NAV } from "@/shared/lib/nav";

/** [mã dòng, bảng ENUMS, mã DB, nhãn chuẩn] */
const ROWS: Array<[string, EnumName, string, string]> = [
  ["T1", "salesOrderStatus", "BOOKED", "Giữ chỗ"],
  ["T2", "salesOrderStatus", "AUTO_CANCELLED", "Hết giờ giữ chỗ"],
  ["T3", "paymentMatchStatus", "MATCHED", "Khớp đơn"],
  ["T4", "paymentMatchStatus", "UNDERPAID", "Chuyển thiếu"],
  ["T5", "paymentMatchStatus", "ORPHAN", "Về sau khi đơn đã huỷ"],
  ["T6", "paymentMatchStatus", "UNMATCHED", "Không khớp đơn"],
  ["T7", "paymentMatchStatus", "OVERPAID", "Chuyển thừa"],
  ["T8", "paymentResolution", "ATTACHED", "Đã gắn vào đơn"],
  ["T9", "paymentResolution", "CONFIRMED", "Đã xác nhận đơn"],
  ["T10", "paymentSource", "WEBHOOK", "Ngân hàng báo"],
  ["T11", "paymentSource", "MANUAL", "Xác nhận tay"],
  ["T11", "paymentSource", "GATEWAY", "Cổng SePay"],
  ["T12", "paymentEnvironment", "SANDBOX", "Chạy thử"],
  ["T13", "paymentEnvironment", "PRODUCTION", "Chạy thật"],
  ["T14", "cancelReason", "CUSTOMER_CHANGED_MIND", "Khách đổi ý"],
  ["T15", "cancelReason", "DAMAGED_WHEN_PACKING", "Hàng hư lúc soạn hàng"],
  ["T16", "cancelReason", "GIVE_UP_AFTER_FAILED", "Giao thất bại, không giao lại"],
  ["T17", "cancelReason", "UNREACHABLE", "Không liên lạc được khách"],
  ["T18", "cancelReason", "OTHER", "Lý do khác"],
  ["T19", "cancelReason", "UNREACHABLE_AUTO", "Hệ thống tự huỷ: không liên lạc được khách"],
  ["T20", "refundMethod", "GATEWAY", "Qua cổng SePay"],
  ["T21", "refundStatus", "PENDING", "Chờ hoàn tiền"],
  ["T22", "refundStatus", "REFUNDED", "Đã hoàn tiền"],
  ["T23", "refundStatus", "FAILED", "Hoàn thất bại"],
  ["T24", "deliveryStatus", "CONFIRMING", "Chờ gọi xác nhận"],
  ["T25", "deliveryStatus", "PREPARING", "Đang soạn hàng"],
  ["T26", "deliveryStatus", "READY", "Chờ lấy hàng"],
  ["T27", "deliveryStatus", "DELIVERING", "Đang giao"],
  ["T28", "deliveryStatus", "COMPLETED", "Đã giao"],
  ["T29", "deliveryStatus", "FAILED", "Giao thất bại"],
  ["T30", "deliveryStatus", "CANCELLED", "Đã huỷ theo đơn"],
  ["T31", "confirmCallResult", "CONFIRMED_CHANGED", "Đã xác nhận, có đổi thông tin"],
  ["T32", "confirmCallResult", "WRONG_NUMBER", "Sai số điện thoại"],
  ["T33", "confirmCallResult", "WANT_CHANGE", "Khách muốn đổi món"],
  ["T34", "confirmCallResult", "WANT_CANCEL", "Khách muốn huỷ đơn"],
  ["T35", "confirmEscalationReason", "WRONG_NUMBER", "Sai số điện thoại"],
  ["T36", "confirmEscalationReason", "WANT_CANCEL", "Khách muốn huỷ đơn"],
  ["T37", "confirmEscalationReason", "WANT_CHANGE", "Khách muốn đổi món"],
  ["T38", "confirmTaskState", "DONE", "Đã xong"],
  ["T39", "confirmQueueTab", "DEFAULT", "Đến giờ gọi"],
  ["T40", "unconfirmedDecision", "DELIVER_WITHOUT_CONFIRM", "Bỏ qua gọi xác nhận"],
  ["T41", "unconfirmedDecision", "EXTEND", "Gia hạn gọi"],
  ["T42", "unconfirmedDecision", "CANCEL", "Huỷ đơn"],
  ["T44", "stockMovementType", "WRITE_OFF", "Huỷ hàng, ghi lỗ"],
  ["T45", "returnToStockDecision", "WRITE_OFF", "Huỷ hàng, ghi lỗ"],
  ["T46", "returnToStockDecision", "RESTOCK", "Tái nhập"],
  ["T46", "returnToStockDecision", "PENDING", "Chờ quyết định"],
  ["T47", "returnToStockStatus", "DRAFT", "Chờ duyệt"],
  ["T48", "staffStatus", "INACTIVE", "Đã nghỉ"],
  ["T49", "auditActorKind", "user", "Người"],
  ["T50", "itemType", "BUNDLE", "Combo"],
  ["T53", "pricingRuleActive", "true", "Đang áp dụng"],
  ["T54", "entryPageRole", "privacy", "Chính sách bảo mật"],
  ["T55", "entryPageRole", "terms", "Điều kiện giao dịch chung"],
  ["T56", "entryPageRole", "refund", "Chính sách đổi trả và hoàn tiền"],
  ["T57", "entryPageRole", "seller_info", "Thông tin người bán"],
  ["T58", "entryReturnReason", "missing_info", "Thiếu thông tin hoặc hình ảnh"],
  ["T59", "entryReturnReason", "wrong_content", "Nội dung chưa chuẩn"],
  ["T60", "entryReturnReason", "legal_risk", "Rủi ro pháp lý hoặc bản quyền"],
  ["T61", "entryReturnReason", "other", "Lý do khác"],
  ["T62", "entryUnpublishReason", "wrong_price", "Giá chưa đúng"],
  ["T63", "entryUnpublishReason", "complaint", "Khiếu nại hoặc rủi ro pháp lý"],
  ["T64", "entryUnpublishReason", "out_of_season", "Hết mùa vụ"],
  ["T65", "entryUnpublishReason", "wrong_content", "Nội dung chưa chuẩn"],
  ["T66", "entryUnpublishReason", "other", "Lý do khác"],
];

describe("tên chuẩn: ENUMS khớp mục 4 (T1-T66)", () => {
  it.each(ROWS)("%s %s.%s = %s", (_code, table, value, label) => {
    expect(enumLabel(ENUMS[table], value)).toBe(label);
  });

  it("Q-2: chip AUTO_CANCELLED là xám (mute), khác Đã huỷ", () => {
    expect(ENUMS.salesOrderStatus.AUTO_CANCELLED.tone).toBe("mute");
  });

  it("quy ước OTHER: lý do là 'Lý do khác', loại giữ 'Khác' (mục 0 của 02b)", () => {
    expect(ENUMS.cancelReason.OTHER.label).toBe("Lý do khác");
    expect(ENUMS.purchaseCostType.OTHER.label).toBe("Khác");
    expect(ENUMS.deliveryFailureReason.OTHER.label).toBe("Khác");
  });
});

describe("tên chuẩn: menu (C1, C3)", () => {
  const labelOf = (key: string) => NAV.find((n) => n.key === key)?.label;
  it("Hàng hoàn (Q-3) và Hoàn tiền chờ chuyển", () => {
    expect(labelOf("returns")).toBe("Hàng hoàn");
    expect(labelOf("refunds")).toBe("Hoàn tiền chờ chuyển");
  });
});
