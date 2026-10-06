// Lô áp tên chuẩn (02b mục 3.2): so từng dòng T của doc/thuat-ngu-va-trang-thai.md mục 4 với ENUMS và menu.
// Cột "Chuẩn". Dòng chỉ có ở BE hoặc Shop (T1 Shop, T24-T30 Shop, T43...) không nằm ở đây.
import { describe, expect, it } from "vitest";
import { ENUMS, enumLabel, type EnumName } from "@/shared/lib/enums";
import { actionLabel, AUDIT_ACTION_LABELS, AUDIT_FILTER_ACTIONS } from "@/features/audit/auditModel";
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

/** [mã dòng, `action` của AuditLog, nhãn chuẩn] — T67-T76 và P1, P3-P9, P11. `AuditLog.action` không đổi, chỉ đổi nhãn. */
const ACTIONS: Array<[string, string, string]> = [
  ["P1", "confirm_payment_manual", "Xác nhận đã nhận tiền"],
  ["P2", "publish_batch", "Mở bán lô"],
  ["P3", "cancel_expired_batch", "Huỷ lô quá hạn (ghi lỗ)"],
  ["P4", "approve_returntostock", "Duyệt hàng hoàn"],
  ["P5", "return_to_warehouse", "Mang hàng về kho"],
  ["P5", "cancel_returntostock", "Huỷ phiếu hàng hoàn"],
  ["P6", "issue_credit_note", "Lập phiếu trừ doanh thu"],
  ["P7", "create_refund", "Lập phiếu hoàn tiền"],
  ["P7", "retry_refund", "Thử hoàn tiền lại"],
  ["P8", "return_batch_to_supplier", "Trả nhà cung cấp"],
  ["P9", "assign_deliverynote", "Chọn người giao"],
  ["P11", "delivery_confirm_skipped", "Bỏ qua gọi xác nhận"],
  ["P11", "delivery_extended", "Gia hạn gọi"],
  ["T2", "order_auto_cancelled", "Đơn hết giờ giữ chỗ, tự huỷ"],
  ["T2", "cancel_unpaid_expired", "Đơn hết giờ giữ chỗ, tự huỷ"],
  ["T67", "batch_near_expiry", "Lô sang Cận hạn"],
  ["T67", "batch_expired", "Lô sang Quá hạn"],
  ["T67", "batch_sold_out", "Lô hết hàng"],
  ["T68", "batch_selling", "Lô sang Đang bán"],
  ["T68", "batch_back_in_stock", "Lô có hàng lại (hàng hoàn tái nhập)"],
  ["T69", "label_printed", "In tem giao"],
  ["T69", "label_reprinted", "In lại tem giao"],
  ["T70", "update_reconciliation_lines", "Sửa số đếm kiểm kê"],
  ["T71", "delete_returntostock", "Ẩn phiếu hàng hoàn"],
  ["T72", "change_group_capabilities", "Đổi phân quyền nhóm"],
  ["T73", "item_image_add", "Thêm ảnh mặt hàng"],
  ["T73", "item_image_replace", "Thay ảnh mặt hàng"],
  ["T73", "item_image_remove", "Gỡ ảnh mặt hàng"],
  ["T74", "content_publish", "Đăng bài"],
  ["T74", "content_republish", "Đăng lại bài"],
  ["T74", "content_restore_version", "Khôi phục bản cũ"],
  ["T75", "create_callscript", "Thêm kịch bản gọi"],
  ["T75", "update_callscript", "Sửa kịch bản gọi"],
  ["T76", "admin_edit", "Sửa trong trang quản trị kỹ thuật"],
  ["W37", "complete_order", "Đơn hoàn tất"],
];

describe("tên chuẩn: nhãn thao tác Nhật ký (actionLabel)", () => {
  it.each(ACTIONS)("%s %s = %s", (_code, action, label) => {
    expect(actionLabel(action)).toBe(label);
  });

  it("W34: không còn nhãn của mã BE không ghi (auto_cancel, confirm_payment) và bộ lọc không có confirm_proposal", () => {
    expect(AUDIT_ACTION_LABELS).not.toHaveProperty("auto_cancel");
    expect(AUDIT_ACTION_LABELS).not.toHaveProperty("confirm_payment");
    expect(AUDIT_FILTER_ACTIONS).not.toContain("confirm_proposal");
  });
});
