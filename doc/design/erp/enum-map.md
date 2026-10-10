# Bảng enum Cá Về: model, trường, giá trị, nhãn (01/10/2026, đối chiếu lại code 11/10/2026)

Nguồn: `backend/apps/**/models*.py` (TextChoices / choices / Boolean) và bảng nhãn FE **duy nhất** `erp-console/shared/lib/enums.ts` (`ENUMS`). Khi file này lệch `enums.ts` thì **`enums.ts` thắng**; tên chuẩn chứng từ và trạng thái xem `doc/thuat-ngu-va-trang-thai.md` §2–4 (Duy duyệt 07/10).
Cột "Nhãn dùng trên artboard" ưu tiên nhãn FE, nếu FE không có nhãn thì lấy nhãn model.
Ký hiệu ⚑: nhãn trong code vi phạm luật wording của Duy, nên artboard giữ nghĩa nhưng đổi sang lời thân thiện.

## Mã chứng từ (bộ sinh mã thật)
| Chứng từ | Bộ sinh | Định dạng |
|---|---|---|
| SalesOrder.code | `sales/utils.py gen_code("SO", …)` | `SO<yymmdd>-<6 HEX>`, ví dụ SO260930-1F4A2C |
| SalesInvoice.code | `gen_code("INV", …)` | `INV<yymmdd>-<6 HEX>` |
| DeliveryNote.code | `delivery/services.py` | `GH-<mã hoá đơn>-<5 HEX>` |
| CreditNote.code | `credit_notes/services.py` | `DC-<mã hoá đơn>` |
| PurchaseInvoice | không có số, `__str__` = `PI-<pk>` | hiển thị `#<id>` |
| StockEntry | `__str__` = `SE-<pk>` | — |
Mã `DH-…` chỉ có trong mock, placeholder và test của FE (`deliveries/mock.ts`, `confirmation/mock.ts`, placeholder tra đơn, fallback `DH-${id}`, `seed_demo`).

## sales
| Model.field | Giá trị → nhãn model | Nhãn FE | Nhãn dùng trên artboard |
|---|---|---|---|
| SalesOrder.status | BOOKED Giữ chỗ · PAID Đã thanh toán (**không còn dùng từ 07/10**, W37; giữ trong choices cho dữ liệu cũ) · PROCESSING Đang xử lý · COMPLETED Hoàn tất · CANCELLED Đã huỷ · AUTO_CANCELLED Hết giờ giữ chỗ | `ENUMS.salesOrderStatus` như model; AUTO_CANCELLED là chip riêng, nhóm lọc "Đã huỷ" gộp cả hai | như nhãn FE |
| SalesInvoice.status | ISSUED Đã xuất · CANCELLED Đã huỷ | — | Đã xuất / Đã huỷ |
| PaymentTransaction.match_status | MATCHED Khớp đơn · UNDERPAID Chuyển thiếu · ORPHAN Về sau khi đơn đã huỷ · UNMATCHED Không khớp đơn · OVERPAID Chuyển thừa | như model | như model |
| PaymentTransaction.resolution_status | OPEN Chờ xử lý · RESOLVED Đã xử lý | — | Chờ xử lý / Đã xử lý |
| PaymentTransaction.resolution | ATTACHED Đã gắn vào đơn · CONFIRMED Đã xác nhận đơn · REFUNDED Đã hoàn tiền | như model | như model |
| PaymentTransaction.source | WEBHOOK Ngân hàng báo · MANUAL Xác nhận tay · GATEWAY Cổng SePay | như model | như model |
| PaymentTransaction.environment | SANDBOX Chạy thử · PRODUCTION Chạy thật | như model | (không hiện) |
| CreditNote.kind (Phiếu trừ doanh thu) | CANCEL_ORDER Huỷ đơn đã thanh toán | — | — |
| CreditNote reason_code (`ENUMS.cancelReason`) | CUSTOMER_CHANGED_MIND · DAMAGED_WHEN_PACKING · GIVE_UP_AFTER_FAILED · UNREACHABLE · OTHER · UNREACHABLE_AUTO | Khách đổi ý · Hàng hư lúc soạn hàng · Giao thất bại, không giao lại · Không liên lạc được khách · Lý do khác · Hệ thống tự huỷ: không liên lạc được khách | nhãn FE |
| Refund.method | MANUAL_TRANSFER Chuyển khoản tay · GATEWAY Qua cổng SePay | như model | — |
| Refund.status | PENDING Chờ hoàn tiền · REFUNDED Đã hoàn tiền · FAILED Hoàn thất bại | như model | như model |

## delivery
| Model.field | Giá trị → nhãn model | Nhãn FE | Artboard |
|---|---|---|---|
| DeliveryNote.status | CONFIRMING Chờ gọi xác nhận · PREPARING Đang soạn hàng · READY Chờ lấy hàng · DELIVERING Đang giao · COMPLETED Đã giao · FAILED Giao thất bại · CANCELLED Đã huỷ theo đơn | `ENUMS.deliveryStatus` như model | như model |
| DeliveryNote (tem, suy ra) | label.printed / valid_print_no | "Chưa in tem" · "Đã in (lần N)" | nhãn FE (tem chỉ in 4 số cuối SĐT, quyết định 10/10) |
| DeliveryLabel.reason | FIRST In lần đầu · REPRINT In lại · ADDRESS_CHANGED Đổi thông tin nhận | — | — |
| ConfirmTask.state | PENDING Chờ gọi · CALLBACK Hẹn gọi lại · ESCALATED Cần quyết định · REFUND_CALL Gọi báo hoàn tiền · DONE Đã xong | như model; tab hàng chờ "Đến giờ gọi" | như model |
| ConfirmTask.escalation_reason | UNREACHABLE Không nghe máy · WRONG_NUMBER Sai số điện thoại · WANT_CANCEL Khách muốn huỷ đơn · WANT_CHANGE Khách muốn đổi món | như model | như model |
| ConfirmCall.result | CONFIRMED Đã xác nhận · CONFIRMED_CHANGED Đã xác nhận, có đổi thông tin · UNREACHABLE Không nghe máy · WRONG_NUMBER Sai số điện thoại · CALLBACK Hẹn gọi lại · WANT_CHANGE Khách muốn đổi món · WANT_CANCEL Khách muốn huỷ đơn · NOTIFIED Đã báo hoàn tiền | như model | như model |
| Quyết định đơn chưa xác nhận (FE) | DELIVER_WITHOUT_CONFIRM · EXTEND · CANCEL | Bỏ qua gọi xác nhận · Gia hạn gọi · Huỷ đơn | nhãn FE |
| mark_failed | `DeliveryNote.failure_reason` (B5, Lô 4): NOT_MET Không gặp khách · REFUSED Khách từ chối nhận · WRONG_ADDRESS Sai địa chỉ · DAMAGED Hàng hư khi giao · OTHER Khác; `failure_note` bắt buộc khi OTHER | — | giữ trường "Lý do" (bắt buộc) + "Ghi chú" (bắt buộc khi Khác) |

## inventory
| Model.field | Giá trị → nhãn model | Nhãn FE | Artboard |
|---|---|---|---|
| Batch.status | DRAFT Nháp · SELLING Đang bán · NEAR_EXPIRY Cận hạn · SOLD_OUT Hết hàng · EXPIRED Quá hạn · CANCELLED Đã huỷ · CLOSED Đã chốt | như model | như model |
| StockLedgerEntry.movement_type (type_label = get_display) | RECEIPT Nhập lô · SALE Bán ra · RETURN_RESTOCK Hàng hoàn tái nhập · RECONCILE Điều chỉnh kiểm kê · WRITE_OFF Hạch toán lỗ / huỷ · CANCEL_RESTORE Hoàn kho do huỷ đơn · SUPPLIER_RETURN Trả nhà cung cấp | type_label từ BE | như model; WRITE_OFF → "Huỷ hàng, ghi lỗ" ⚑ |
| StockEntry.purpose | MATERIAL_RECEIPT Nhập vật tư · ADJUSTMENT Điều chỉnh (+ `reason` "Lý do" tự do) | — | như model. Không ghi vào sổ nhập xuất |
| StockReconciliation.status | DRAFT Nháp · SUBMITTED Chờ duyệt · APPROVED Đã duyệt | — | như model (Duy chốt 02/10, #6/#20) |
| StockReconciliationLine.reason | TextField tự do | — | — |
| ReturnToStock.status | DRAFT Chờ duyệt · APPROVED Đã duyệt · CANCELLED Đã huỷ | — | như model (CANCELLED: Duy chốt 02/10, #8) |
| ReturnToStock.decision | PENDING Chờ quyết định · RESTOCK Tái nhập · WRITE_OFF Huỷ bỏ (hạch toán lỗ) | — | Tái nhập · "Huỷ hàng, ghi lỗ" ⚑ |
| ReturnToStock.note | "Ghi chú" (không có trường lý do) | — | cột "Ghi chú" |
| Warehouse.is_group | Là nhóm kho | — | Kho / Nhóm kho |

## purchasing
| Model.field | Giá trị → nhãn | Artboard |
|---|---|---|
| PurchaseReceipt.status | DRAFT Nháp · SUBMITTED Đã ghi nhận · CANCELLED Đã huỷ | như model |
| PurchaseCost.cost_type | ICE Đá · TRANSPORT Vận chuyển · LOADING Bốc vác · OTHER Khác | như model |
| PurchaseCost.allocation_method | BY_QTY Theo số kg · BY_VALUE Theo giá trị | như model |
| PurchaseInvoice.is_paid | "Đã trả tiền" (Boolean) | Đã trả tiền / Chưa trả tiền |
| Supplier.supplier_type | INDIVIDUAL Cá nhân · COMPANY Doanh nghiệp | như model |
| Supplier.is_active | "Đang hợp tác" (Boolean) | Đang hợp tác / Ngừng hợp tác |

## catalog
| Model.field | Giá trị → nhãn | Nhãn FE | Artboard |
|---|---|---|---|
| Item.item_type | SIMPLE Mặt hàng thường · BUNDLE Combo | tag "Combo" | Mặt hàng thường / Combo |
| Item.is_active | "Đang kinh doanh" | inactive → "Đang ẩn" | Đang kinh doanh / Đang ẩn |
| ItemPrice | không có trạng thái, ghi chú hay người đặt (chỉ rate, valid_from, valid_upto) | — | bỏ cột Trạng thái (và Ghi chú ở W2h) |
| PricingRule.is_active | "Đang áp dụng" (Boolean) | Đang áp dụng / Đã tắt | nhãn FE |
| PricingRule.apply_on | ITEM Theo mặt hàng (mua ≥ N kg) · ORDER Theo đơn (tổng ≥ M đồng) | — | Theo mặt hàng / Theo đơn |
| PricingRule.discount_type | AMOUNT Giảm số tiền · PERCENT Giảm phần trăm | — | như model |

## content
| Model.field | Giá trị → nhãn | Nhãn FE | Artboard |
|---|---|---|---|
| Entry.status | draft Nháp · pending_review Chờ duyệt · published Đã đăng · unpublished Đã gỡ | như model | như model |
| Entry.kind | post Bài viết · page Trang | — | Bài viết / Trang |
| Entry.source | human Người dùng · ai AI | — | chip "AI" |
| Entry.page_role | privacy · terms · refund · seller_info | Chính sách bảo mật · Điều kiện giao dịch chung · Chính sách đổi trả và hoàn tiền · Thông tin người bán | nhãn FE (Shop lô 5 thêm vai trò mới, xem 02b Shop §3.7) |
| return_reason (services RETURN_REASONS) | missing_info · wrong_content · legal_risk · other | Thiếu thông tin hoặc hình ảnh · Nội dung chưa chuẩn · Rủi ro pháp lý hoặc bản quyền · Lý do khác | nhãn FE |
| unpublish reason (UNPUBLISH_REASONS) | wrong_price · complaint · out_of_season · wrong_content · other | Giá chưa đúng · Khiếu nại / rủi ro pháp lý · Hết mùa vụ · Nội dung chưa chuẩn · Khác | nhãn FE |
| Category.is_active | Boolean | Đang hoạt động / Ngừng dùng | nhãn FE |

## accounts
| Model.field | Giá trị → nhãn | Nhãn FE | Artboard |
|---|---|---|---|
| StaffProfile.status | ACTIVE Đang làm · INACTIVE Nghỉ | Đang làm · Đã nghỉ · Tất cả | nhãn FE. Không có "Mới tạo" |
| AuditLog.actor_kind | user Người dùng · system Hệ thống · ai AI (thay người dùng) | — | Người / AI / Hệ thống |

## ai
| Model.field | Giá trị → nhãn | Nhãn FE | Artboard |
|---|---|---|---|
| AiAction.kind | read Đọc · write Ghi | Đọc / Ghi | Đọc / Ghi |
| AiAction.level | A/B/C "Mức A/B/C"; mức của từng người: OFF/A/C/B | Tắt (OFF) · Mức A (Tự đọc) · Mức C (Soạn nháp) · Mức B (Tự ghi + hoàn tác) | ⚑ giữ lời thân thiện đang vẽ (Tắt · Tự đọc · Hỏi trước khi làm · Tự ghi) |
| AiAction.status | PENDING Chờ duyệt · CONFIRMED Đã duyệt · REJECTED Đã từ chối · EXPIRED Hết hạn · SCHEDULED Đã lên lịch · DONE Đã thực hiện · UNDONE Đã hoàn tác · CANCELLED Đã huỷ · ESCALATED Đã chuyển việc · FAILED Thất bại | — | như model |
| AiPolicyVersion.global_mode | on Bật · c_only Chỉ mức C · off Tắt | Bình thường (ON) · Chỉ mức C (C_ONLY) · Tắt khẩn cấp (OFF) | ⚑ Bật · Luôn hỏi trước · Tắt |
