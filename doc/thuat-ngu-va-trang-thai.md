# Thuật ngữ, trạng thái và chỗ còn chữ "AI"

Ngày 06/10/2026. Đọc code trên `main` tại commit `deb3441` ("Merge Lô 15 FE (ED-06, ED-08, ED-41, ED-42)…").
Người viết: Tech Lead. File này chỉ mô tả hiện trạng, không đổi quyết định nào trong `doc/decisions.md`.
Nguồn: `backend/apps/**/models*`, `erp-console/shared/lib/enums.ts` (bảng nhãn FE duy nhất), `erp-console/features/**`,
`frontend/`, `doc/design/erp/enum-map.md` (bản 01/10, nay đã cũ một phần), glossary `doc/features/2026-09-30-dat-ten-tieng-anh/` (02c §1, 01 §2).

Ký hiệu:
- ⚠ = có lệch: nhãn BE ≠ nhãn FE, FE hiện mã thô, hai màn hiện khác chữ cho cùng một trạng thái, hoặc nhãn lẫn tiếng Anh hay mã.
- "BE" = nhãn trong `choices` của model (Django Admin, `*_label` / `status_label` API trả về, câu lỗi, dòng thời gian BE dựng).
- "ERP" = chữ màn `erp-console` thật sự vẽ. Nếu màn vẽ `*_label` của BE thì ghi "dùng nhãn BE".
- Tông màu ERP: good = xanh lá, warn = hổ phách, crit = đỏ, info = xanh biển, mute = xám (`enums.ts:4`).

---

## 1. Bảng thuật ngữ (tiếng Việt nghiệp vụ ↔ tên trong code)

Quy ước đặt tên (P8b, Duy chốt 01/10): định danh trong code là tiếng Anh chuẩn, chữ hiển thị là tiếng Việt.

### 1.1 Chung
| Tiếng Việt | Trong code | Ghi chú |
|---|---|---|
| Cá Về (tên sản phẩm) | chuỗi `cangca` còn ở hạ tầng | không phải brand |
| Chứng từ | model nghiệp vụ (đơn, hoá đơn, phiếu…) | không xoá, huỷ bằng trạng thái (bất biến 3) |
| Hệ thống (người làm) | `actor=None`, `actor_kind="system"` | job, webhook |
| Giá vốn | `landed_unit_cost` (field), quyền `view_costprice` | bất biến 1 |
| Giá mua | `purchase_rate`, `PurchaseReceiptLine.rate` | nhạy cảm như giá vốn |
| Lãi lỗ | `profit`, `pnl`, model `ProfitReport`, quyền `view_profitreport` | |
| Tầng 1 / 2 / 3 (phân quyền) | model perm qua Group / `Meta.permissions` / `get_queryset` + `GroupDataScope` | BR-PQ |
| Giờ Việt Nam | `VN_TIME_ZONE`, `today_in_vietnam()`, `todayInVietnam()` | DB lưu UTC |

### 1.2 Bán hàng (app `sales`, ERP `/orders/`, `/customers/`, Shop `/shop/`)
| Tiếng Việt | Model / field / module | Ghi chú |
|---|---|---|
| Đơn hàng, đơn | `SalesOrder` (`sales/models/orders.py:10`), module `sales/orders/` | chỉ Hệ thống tạo (BR-PQ-11) |
| Dòng đơn | `SalesOrderLine` | |
| Giữ chỗ (theo lô) | `SalesOrderLineBatch`, `status=BOOKED`, `booked_expires_at` | TTL `SALES_ORDER_TTL_MINUTES` |
| Mã đơn | `SalesOrder.code` (`SO<yymmdd>-<6 HEX>`) | |
| Khách hàng | `Customer` (`phone`, `name`) | dữ liệu cá nhân, bất biến 9 |
| Hoá đơn bán | `SalesInvoice`, dòng `SalesInvoiceLine` | `INV<yymmdd>-…` |
| Phân bổ lô đã bán | `SalesInvoiceLineBatch.unit_cost` | giá vốn, append-only |
| Chứng từ đảo doanh thu ⚠ | `SalesCreditNote` (`DC-<mã hoá đơn>`), `kind=CANCEL_ORDER` | ba tên khác nhau, xem ⚠W29 |
| Mã lý do huỷ | `SalesCreditNote.reason_code`, bảng `CANCEL_REASON_LABELS` (`sales/orders/services.py:311`) | |
| Bảng giá / giá niêm yết | `PriceList` / `ItemPrice` | |
| Ưu đãi | `PricingRule` | không phải "mã giảm giá" |
| Bằng chứng đồng ý xử lý dữ liệu | quyền `view_privacy_consent`, `sales/orders/consent.py` | |

### 1.3 Thanh toán / Hoàn tiền (`sales/payments/`, `sales/refunds/`, `adapter/`)
| Tiếng Việt | Trong code | Ghi chú |
|---|---|---|
| Giao dịch tiền về | `PaymentTransaction` (`bank_txn_id`, `match_status`, `source`) | IPN SePay |
| Hàng chờ thanh toán (tiền lệch) | `resolution_status=OPEN`, ERP `/orders/payments/` | việc của Chủ |
| Xác nhận tay / xác nhận đã nhận tiền ⚠ | quyền `sales.confirm_payment_manual`, audit `confirm_payment_manual` | hai tên, xem ⚠W30 |
| Tự xác nhận khớp | audit `auto_confirm_exact_match`, `sales/payments/auto_confirm.py` | chỉ chạy khi `AI_ENABLED` |
| Phiếu hoàn (tiền) | `Refund` (`method`, `status`, `bank_txn_ref`) | quyền `create_refund`, `confirm_refund` |
| Cổng SePay / webhook | `Source.GATEWAY` / `Source.WEBHOOK`; adapter FastAPI | |
| Môi trường cổng | `PaymentTransaction.environment` (`SANDBOX`/`PRODUCTION`) | |

### 1.4 Kho / Lô (app `inventory`, ERP `/inventory/`, `/returns/`, `/stocktake/`, `/ledger/`)
| Tiếng Việt | Trong code | Ghi chú |
|---|---|---|
| Lô hàng, lô | `Batch` (`batch_id`, `expiry_date`, `status`) | xuất FEFO qua `sellable_batches` |
| Mở bán lô | `publish_batch` (quyền + service) | Meta ghi "Publish lô ra Shop" ⚠W32 |
| Chốt lô | `close_batch` | đông cứng lãi lỗ (BR-LO-05) |
| Huỷ lô quá hạn | `cancel_expired_batch` | ghi lỗ |
| Cận hạn / Quá hạn / Hết hàng | `NEAR_EXPIRY` / `EXPIRED` / `SOLD_OUT` | job `update_batch_statuses` |
| Kho | `Warehouse` (`is_group` = nhóm kho) | |
| Sổ nhập xuất (chuyển động kho) | `StockLedgerEntry` (`movement_type`) | append-only |
| Điều chỉnh tồn | `StockEntry` (`purpose`) | |
| Kiểm kê, phiếu kiểm kê | `StockReconciliation` + `StockReconciliationLine`, module `inventory/stocktake/` | |
| Hàng hoàn về kho ⚠ | `ReturnToStock` (`decision`, `status`), module `inventory/returns/` | nhiều tên, xem ⚠W17 |
| Tái nhập / Huỷ bỏ, ghi lỗ | `Decision.RESTOCK` / `Decision.WRITE_OFF` | |
| Trả nhà cung cấp | `BatchSupplierReturn`, audit `return_batch_to_supplier` | |

### 1.5 Mua hàng (app `purchasing`, ERP `/purchasing/`, `/suppliers/`, `/accounting/purchase-invoices/`)
| Tiếng Việt | Trong code |
|---|---|
| Nhập lô (tại cảng) | `receive_batches` (action), service `create_and_submit_receipt` |
| Phiếu nhập (kho) | `PurchaseReceipt`, dòng `PurchaseReceiptLine` |
| Nhà cung cấp (NCC) | `Supplier` (`supplier_type`, `is_active` = "đang hợp tác") |
| Hoá đơn mua | `PurchaseInvoice` (`is_paid`) |
| Chi phí mua / chi phí phụ | `PurchaseCost` (`cost_type`, `allocation_method`), `PurchaseCostAllocation` |

### 1.6 Danh mục (app `catalog`, ERP `/catalog/`)
| Tiếng Việt | Trong code |
|---|---|
| Mặt hàng | `Item` (`code`, `item_type`, `is_active` = đang kinh doanh) |
| Nhóm hàng | `ItemGroup` |
| Combo | `Item.item_type=BUNDLE`, `BundleLine` (thành phần combo) |
| Ảnh mặt hàng | `ItemImage`, quyền `change_item_image` |

### 1.7 Giao hàng / Gọi xác nhận (app `delivery`, ERP `/deliveries/`, `/my-deliveries/`, `/confirmation/`)
| Tiếng Việt | Trong code | Ghi chú |
|---|---|---|
| Phiếu giao (hàng) | `DeliveryNote` (`GH-<mã hoá đơn>-<5 HEX>`) | |
| Người giao trên một phiếu | `courier` (code), field `assigned_to` | vai là `delivery_staff` |
| Soạn hàng / đóng gói | `PREPARING`, quyền `pack_deliverynote` | |
| Tem giao, in tem | `LabelPrint`, quyền `print_label` | |
| Giao thất bại | `FAILED`, `failure_reason`, `failure_note` | |
| Gọi xác nhận đơn | module `delivery/confirmation/`, `ConfirmationTask` (`state`) | verbose "Mục chờ gọi CSKH" |
| Cuộc gọi | `CustomerCall` (`result`) | |
| Kịch bản gọi | `CallScript` (`situation`) | chưa có màn ERP |
| Quyết định đơn không liên lạc được | quyền `decide_unconfirmed`, mã `DELIVER_WITHOUT_CONFIRM` / `EXTEND` / `CANCEL` | |
| Đổi thông tin nhận | quyền `change_recipient`, `recipient_name/phone` | dữ liệu cá nhân |

### 1.8 Nội dung (app `content`, ERP `/content/`, Shop `/bai-viet/`, `/trang/`)
| Tiếng Việt | Trong code |
|---|---|
| Bài viết / Trang | `Entry.kind = post / page` |
| Phiên bản đã đăng | `EntryVersion` |
| Chuyên mục | `Category` |
| Trang go-live (chính sách) | `Entry.page_role` |
| Đăng, gỡ, trả về nháp | quyền `content.publish_entry` |

### 1.9 Nhân sự / Phân quyền (app `accounts`, ERP `/staff/`, `/permissions/`)
| Tiếng Việt | Group / code | Nhãn hiển thị (BE `accounts/auth/services.py:33` = FE `shared/lib/groups.ts:11`) |
|---|---|---|
| Chủ | `owner` | Chủ |
| Quản lý | `manager` | Quản lý |
| NV kho | `warehouse_staff` | Nhân viên kho |
| NV giao | `delivery_staff` | Nhân viên giao |
| CSKH | `customer_service` | CSKH |
| Hồ sơ nhân viên | `StaffProfile` (`status`, `must_change_password`) | |
| Việc (ô ma trận phân quyền) | `Capability` ở `accounts/capabilities/registry.py` | |
| Phạm vi dữ liệu (Tầng 3) | `GroupDataScope` (`object_key`, `value`), `accounts/data_scopes/catalog.py` | |
| Khoá phiên bản cấu hình nhóm | `GroupAccessConfig.row_version` | |

Quyền Tầng 2 (`Meta.permissions`) và tên việc người dùng thấy:
| Codename | Nhãn Meta (Admin) | Ô ma trận (`registry.py`) | "Tài khoản của tôi" (`auth/services.py:43`) |
|---|---|---|---|
| `inventory.publish_batch` | Publish lô ra Shop ⚠ | Mở bán lô | Mở bán lô |
| `inventory.close_batch` | Chốt lô (đông cứng lãi/lỗ) | Chốt lô | Chốt lô |
| `inventory.view_costprice` | Xem giá vốn / đơn giá mua | Xem giá vốn | Xem giá vốn |
| `inventory.cancel_expired_batch` | Huỷ lô quá hạn (hạch toán lỗ) | (không có ô) | Huỷ lô quá hạn |
| `inventory.approve_returntostock` | Duyệt hàng hoàn về kho | Duyệt hàng hoàn về kho | Duyệt hàng hoàn ⚠ |
| `inventory.approve_stockreconciliation` | Duyệt kiểm kê | Duyệt kiểm kê | Duyệt kiểm kê |
| `sales.confirm_payment_manual` | Xác nhận thanh toán thủ công ⚠ | Xác nhận đã nhận tiền | Xác nhận đã nhận tiền |
| `sales.cancel_paid_order` | Huỷ đơn đã thanh toán | Huỷ đơn đã thanh toán | Huỷ đơn đã thanh toán |
| `sales.create_refund` | Tạo phiếu hoàn tiền | Lập phiếu hoàn | Lập phiếu hoàn |
| `sales.confirm_refund` | Xác nhận đã hoàn tiền (tiền rời tài khoản) | Xác nhận đã hoàn tiền | Xác nhận đã hoàn tiền |
| `sales.view_customer_list` | Xem khách hàng | Xem khách hàng | Xem khách hàng |
| `sales.view_privacy_consent` | Xem bằng chứng đồng ý… | (không có ô) | Xem bằng chứng đồng ý… |
| `delivery.confirm_with_customer` | Gọi xác nhận đơn | Gọi xác nhận đơn | Gọi xác nhận đơn |
| `delivery.pack_deliverynote` + `print_label` | Đóng gói phiếu giao / In / huỷ tem giao | Soạn hàng, in tem | hai dòng riêng |
| `delivery.assign_deliverynote` | Giao phiếu cho người giao | Giao phiếu cho người giao | Giao hoặc đổi người giao của phiếu giao |
| `accounts.manage_staff` | Quản lý nhân viên (tạo tài khoản, đổi Group) | Tạo tài khoản, đổi nhóm | Quản lý nhân viên |
| `reports.view_profitreport` | Xem báo cáo giá vốn / lãi lỗ | Xem báo cáo lãi lỗ | Xem báo cáo lãi lỗ |
| `reports.view_dashboard` | Xem Tổng quan vận hành | (không có ô) | Xem Tổng quan |
| `content.publish_entry` | Đăng, gỡ, trả về nháp bài… | Đăng bài lên Shop | Đăng bài viết và trang |
| `catalog.change_item_image` | Thêm / thay / gỡ ảnh mặt hàng | (không có ô) | Sửa ảnh mặt hàng |
| `ai.manage_ai_policy` | Quản lý chính sách AI | Cài đặt chính sách AI ⚠ | Quản lý chính sách AI ⚠ |

### 1.10 Nhật ký (AuditLog) và AI (app `ai`)
| Tiếng Việt | Trong code |
|---|---|
| Nhật ký hoạt động | `AuditLog` (`action`, `actor_kind`, `changes`), ERP `/audit-logs/`, append-only |
| Mã đề xuất AI | `AuditLog.proposal_ref`, `AiAction.id` |
| Việc AI / đề xuất | `AiAction` (`command`, `kind`, `level`, `status`) |
| AI của tôi / cấu hình AI | `AiConfigVersion` (`killed` = tắt khẩn) |
| Chính sách AI | `AiPolicyVersion` (`global_mode`) |
| Cờ AI | FE `NEXT_PUBLIC_AI_FEATURES` (`erp-console/shared/lib/features.ts:6`), BE `AI_ENABLED` (`config/settings.py:266`). Hai cờ riêng ⚠W39 |

---

## 2. Toàn bộ trạng thái và lựa chọn

40 trường có `choices` trong model, cộng 8 bộ mã sống ngoài model (lý do huỷ, lý do trả nháp, quyết định, phạm vi dữ liệu…)
và 6 trường Boolean có nhãn riêng ở ERP. Tổng 54 bảng, 199 giá trị.

Đa số màn ERP vẽ nhãn qua `<Chip table={ENUMS.x}>` (`shared/lib/enums.ts`), nên "nhãn ERP" bên dưới là nhãn `enums.ts` trừ khi ghi khác.
Mã lạ ERP chưa biết sẽ hiện **mã thô** (`enums.ts:309-313`).

### 2.1 Bán hàng

**SalesOrder.status** — BE `sales/models/orders.py:13` · ERP `enums.ts:21`
| DB | Nhãn BE | Nhãn ERP | Shop (`OrderLookup.tsx:148`, dùng nhãn BE) | Màu |
|---|---|---|---|---|
| BOOKED | Giữ chỗ | Giữ chỗ | Giữ chỗ | warn |
| PAID | Đã thanh toán | Đã thanh toán | Đã thanh toán | info |
| PROCESSING | Đang xử lý | Đang xử lý | Đang xử lý; khi phiếu giao CONFIRMING: "Đã thanh toán – chờ vựa gọi xác nhận" (`shop_api.py:94`) | info |
| COMPLETED | Hoàn tất | Hoàn tất | Hoàn tất | good |
| CANCELLED | Đã huỷ | Đã huỷ | Đã huỷ | mute |
| AUTO_CANCELLED ⚠W1 | Tự huỷ (quá TTL) | Đã huỷ (lý do riêng "Hết giờ giữ chỗ", `sales/orders/reasons.py:66`) | **Tự huỷ (quá TTL)** | mute |

**SalesInvoice.status** — BE `sales/models/invoices.py:14` · ERP `enums.ts:29`: ISSUED Đã xuất / Đã xuất (good) · CANCELLED Đã huỷ / Đã huỷ.

**PaymentTransaction.match_status** — BE `sales/models/payments.py:18` · ERP `enums.ts:33`, lọc `orders/labels.ts:23`
| DB | Nhãn BE (hiện ở dòng thời gian đơn, `sales/orders/timeline.py:129`) | Nhãn ERP chip | Màu |
|---|---|---|---|
| MATCHED | Khớp — đã xác nhận ⚠W3 | Khớp | good |
| UNDERPAID | Thiếu tiền — chờ Chủ ⚠W3 | Thiếu tiền | warn |
| ORPHAN | Đến sau khi đơn đã huỷ — chờ Chủ ⚠W3 | Về sau khi đơn tự huỷ (nghĩa hẹp hơn BE) | warn |
| UNMATCHED | Không khớp đơn — chờ Chủ ⚠W3 | Không khớp đơn | crit |
| OVERPAID | Chuyển thừa — đơn đã thanh toán, chờ Chủ ⚠W3 | Chuyển thừa | warn |

**PaymentTransaction.resolution_status** — BE `payments.py:25` · ERP `enums.ts:40`: OPEN Chờ xử lý (warn) · RESOLVED Đã xử lý (good). Khớp.

**PaymentTransaction.resolution** — BE `payments.py:30` · ERP `enums.ts:44` ⚠W5
| DB | BE | ERP |
|---|---|---|
| ATTACHED | Gắn vào đơn | Đã gắn vào đơn |
| CONFIRMED | Xác nhận đơn (khách đã bù) | Đã xác nhận đơn |
| REFUNDED | Đã hoàn tiền | Đã hoàn tiền |

**PaymentTransaction.source** — BE `payments.py:35` · ERP `enums.ts:49` ⚠W4: WEBHOOK "Webhook SePay" (cả BE và ERP, lẫn tiếng Anh) · MANUAL Xác nhận tay · GATEWAY Cổng SePay.

**PaymentTransaction.environment** — BE `payments.py:40`: SANDBOX "Sandbox (thử)" · PRODUCTION "Production (thật)". ERP không có nhãn, hiện chưa vẽ ⚠W6.

**SalesCreditNote.kind** — BE `credit_notes.py:21`: CANCEL_ORDER "Huỷ đơn đã thanh toán". ERP không vẽ.

**Mã lý do huỷ đơn** (`SalesCreditNote.reason_code`, không có `choices`) — BE `sales/orders/services.py:311-322` ⚠W7
| Mã | Nhãn BE (cột "Lý do" danh sách đơn, dòng thời gian) | Hộp huỷ đơn ERP (`orders/labels.ts:32`) | Hộp quyết định gọi xác nhận (`confirmation/confirmationUi.ts:253`) | `ENUMS.cancelReason` (`enums.ts:54`, không màn nào dùng) |
|---|---|---|---|---|
| CUSTOMER_CHANGED_MIND | Khách đổi ý | Khách đổi ý | Khách đổi ý | Khách đổi ý |
| DAMAGED_WHEN_PACKING | Hư hỏng khi soạn hàng | Hư khi đóng hàng | — | Hư khi đóng hàng |
| GIVE_UP_AFTER_FAILED | Bỏ giao sau khi thất bại | Bỏ sau khi giao thất bại | — | Bỏ sau khi giao thất bại |
| UNREACHABLE | Không liên lạc được khách | — | Không liên lạc được khách | (thiếu) |
| OTHER | Khác (dòng thời gian: "Lý do khác") | Khác | Lý do khác | Khác |
| UNREACHABLE_AUTO | Hệ thống tự huỷ — không liên lạc được | — | — | (thiếu) |

**Lý do hiển thị ở danh sách đơn** (`order_reason`, `sales/orders/reasons.py:22-75`, ERP vẽ nguyên `reason.label`, `orders/filters.ts:20`):
AUTO_CANCELLED "Hết giờ giữ chỗ" · CANCELLED + mã ở bảng trên · UNDERPAID "Chuyển thiếu tiền" · mã `failure_reason` hoặc DELIVERY_FAILED "Giao thất bại".

**Refund.method** — BE `refunds.py:24` · ERP `enums.ts:60`: MANUAL_TRANSFER Chuyển khoản tay · GATEWAY "Qua cổng (chưa hiện thực)" / ERP "Qua cổng" ⚠W8.

**Refund.status** — BE `refunds.py:28` · ERP `enums.ts:64`
| DB | BE | ERP | Shop (`customer_notices.py:54,62`) | Màu |
|---|---|---|---|---|
| PENDING | Chờ hoàn | Chờ hoàn | Đang chờ hoàn ⚠W9 | warn |
| REFUNDED | Đã hoàn | Đã hoàn | Đã hoàn | good |
| FAILED | Thất bại | Thất bại (Nhật ký có thể hiện nhầm cho phiếu giao, ⚠W11) | (Shop bỏ qua phiếu FAILED) | crit |

### 2.2 Giao hàng / Gọi xác nhận

**DeliveryNote.status** — BE `delivery/models.py:17` · ERP `enums.ts:71`
| DB | BE | ERP | Shop (`OrderLookup.tsx:231`) | Màu |
|---|---|---|---|---|
| CONFIRMING | Chờ xác nhận | Chờ xác nhận | **mã thô "CONFIRMING"** ⚠W2 (BE có gửi "Chờ vựa gọi xác nhận" ⚠W10 nhưng FE không dùng) | warn |
| PREPARING | Soạn hàng | Soạn hàng | **"PREPARING"** ⚠W2 | info |
| READY | Chờ lấy hàng | Chờ lấy hàng | **"READY"** ⚠W2 | info |
| DELIVERING | Đang giao | Đang giao | **"DELIVERING"** ⚠W2 | info |
| COMPLETED | Hoàn tất | Hoàn tất | **"COMPLETED"** ⚠W2 | good |
| FAILED | Giao thất bại | Giao thất bại (Nhật ký: "Thất bại" ⚠W11) | **"FAILED"** ⚠W2 | crit |
| CANCELLED | Đã huỷ theo đơn | Đã huỷ theo đơn (Nhật ký: "Đã huỷ" ⚠W11) | **"CANCELLED"** ⚠W2 | mute |

Tem giao (suy ra, không lưu DB) — ERP `enums.ts:81,318`: "Chưa in tem" (warn) · "Đã in (lần N)" (good).

**DeliveryNote.failure_reason** — BE `delivery/models.py:40` · ERP `enums.ts:91` (màn chi tiết dùng nhãn BE `failure_reason_label`): NOT_MET Không gặp khách · REFUSED Khách từ chối nhận · WRONG_ADDRESS Sai địa chỉ · DAMAGED Hàng hư khi giao · OTHER Khác. Khớp.

**LabelPrint.reason** — BE `delivery/models.py:188` · ERP `enums.ts:85`: FIRST In lần đầu · REPRINT In lại · ADDRESS_CHANGED Đổi thông tin nhận. Khớp.

**ConfirmationTask.state** — BE `delivery/models.py:93` · ERP `enums.ts:98`, tab `confirmation/types.ts:207`, thanh bước `confirmationUi.ts:83`
| DB | BE | ERP chip | Tab hàng chờ | Màu |
|---|---|---|---|---|
| PENDING | Chờ gọi | Chờ gọi | "Chờ gọi"; tab mặc định "Cần gọi ngay" gộp nhiều trạng thái ⚠W14 | warn |
| CALLBACK | Hẹn gọi lại | Hẹn gọi lại | Hẹn gọi lại | info |
| ESCALATED | Cần quyết định | Cần quyết định | Cần quyết định | crit |
| REFUND_CALL | Gọi báo hoàn tiền | Gọi báo hoàn tiền | Gọi báo hoàn tiền | warn |
| DONE | Hoàn tất | (API trả `confirm_state=null`, màn vẽ trạng thái phiếu giao thay) | — | good |

**ConfirmationTask.escalation_reason** — BE `delivery/models.py:100`; ERP vẽ `escalation_label` do serializer dựng (`delivery/confirmation/serializers.py:103-109`), `ENUMS.confirmEscalationReason` (`enums.ts:105`) không màn nào dùng ⚠W13
| DB | BE model | Serializer (màn thấy) |
|---|---|---|
| UNREACHABLE | Không nghe máy | Không nghe máy |
| WRONG_NUMBER | Sai số | Sai số |
| WANT_CANCEL | Khách muốn huỷ | Khách muốn huỷ |
| WANT_CHANGE | Khách muốn đổi | Khách muốn đổi món – huỷ + hoàn + đặt lại |

`ConfirmationTask.auto_cancel_blocked_code` (không `choices`): "" hoặc "BR-LO-05" (`confirmation/services.py:777`). API trả mã thô `auto_cancel_blocked` (`serializers.py:182`) ⚠W40 nếu màn nào in ra.

**CustomerCall.result** — BE `delivery/models.py:150` · ERP `enums.ts:111` ⚠W12
| DB | BE | ERP | Màu |
|---|---|---|---|
| CONFIRMED | Đã xác nhận | Đã xác nhận | good |
| CONFIRMED_CHANGED | Xác nhận có đổi thông tin | Đã xác nhận, có đổi | good |
| UNREACHABLE | Không nghe máy | Không nghe máy | warn |
| WRONG_NUMBER | Sai số | Sai số điện thoại | crit |
| CALLBACK | Hẹn gọi lại | Hẹn gọi lại | info |
| WANT_CHANGE | Khách muốn đổi món/số lượng | Khách muốn đổi món | info |
| WANT_CANCEL | Khách muốn huỷ | Khách muốn huỷ đơn | warn |
| NOTIFIED | Đã báo hoàn tiền | Đã báo hoàn tiền | good |

**Quyết định đơn chưa xác nhận** (mã API, không lưu field riêng) — ERP `enums.ts:122`: DELIVER_WITHOUT_CONFIRM Giao không xác nhận · EXTEND Gia hạn thêm · CANCEL Huỷ đơn. BE không có nhãn.

**CallScript.situation** — BE `delivery/models.py:229`: FIRST_ORDER Khách mua lần đầu · RETURNING Khách quen · COMBO Đơn có combo · GENERAL Lời dặn chung. ERP chưa có màn (chỉ Admin) ⚠W41.

### 2.3 Kho / Lô

**Batch.status** — BE `inventory/models/batches.py:14` · ERP `enums.ts:129`
| DB | BE | ERP | Màu |
|---|---|---|---|
| DRAFT | Nháp | Nháp | mute |
| SELLING | Đang bán | Đang bán | good |
| NEAR_EXPIRY | Cận hạn | Cận hạn | warn |
| SOLD_OUT | Hết hàng | Hết hàng | mute |
| EXPIRED | Quá hạn | Quá hạn | crit |
| CANCELLED | Đã huỷ | Đã huỷ | mute |
| CLOSED | Đã chốt | Đã chốt | mute |

**StockLedgerEntry.movement_type** — BE `inventory/models/stock.py:14` · ERP `enums.ts:138`
| DB | BE | ERP | Màu |
|---|---|---|---|
| RECEIPT | Nhập lô | Nhập lô | good |
| SALE | Bán ra | Bán ra | info |
| RETURN_RESTOCK | Hàng hoàn tái nhập | Hàng hoàn tái nhập | good |
| RECONCILE | Điều chỉnh kiểm kê | Điều chỉnh kiểm kê | info |
| WRITE_OFF ⚠W15 | Hạch toán lỗ / huỷ | Ghi lỗ, huỷ hàng | warn |
| CANCEL_RESTORE | Hoàn kho do huỷ đơn | Hoàn kho do huỷ đơn | mute |
| SUPPLIER_RETURN | Trả nhà cung cấp | Trả nhà cung cấp | mute |

**StockEntry.purpose** — BE `stock.py:48` · ERP `enums.ts:147`: MATERIAL_RECEIPT Nhập vật tư (info) · ADJUSTMENT Điều chỉnh. Khớp.

**StockReconciliation.status** — BE `inventory/models/stocktake.py:17` · ERP `enums.ts:151`, tab `stocktake/stocktakeUi.ts:193`: DRAFT Nháp · SUBMITTED Chờ duyệt (warn) · APPROVED Đã duyệt (good). Khớp.

**ReturnToStock.status** — BE `inventory/models/returns.py:30` · ERP `enums.ts:156`, tab `returns/returnsModel.ts:16`
| DB | BE | ERP | Nhật ký "Thay đổi" | Màu |
|---|---|---|---|---|
| DRAFT | Chờ duyệt (mã DRAFT nhưng nghĩa là chờ duyệt) | Chờ duyệt | **Nháp** ⚠W11 | warn |
| APPROVED | Đã duyệt | Đã duyệt | Đã duyệt | good |
| CANCELLED | Đã huỷ | Đã huỷ | Đã huỷ | mute |

Ngoài trạng thái còn **xoá mềm** (`deleted_at`, audit `delete_returntostock`, `inventory/returns/services.py:61`), phiếu xoá mềm không hiện.

**ReturnToStock.decision** — BE `returns.py:25` · ERP `enums.ts:161`
| DB | BE (dòng thời gian đơn: "Duyệt hàng về kho: …", `timeline.py:268`) | ERP | Màu |
|---|---|---|---|
| PENDING | Chờ quyết định | Chờ quyết định | warn |
| RESTOCK | Tái nhập | Tái nhập | good |
| WRITE_OFF ⚠W16 | Huỷ bỏ (hạch toán lỗ) | Huỷ bỏ, ghi lỗ | warn |

### 2.4 Mua hàng

**PurchaseReceipt.status** — BE `purchasing/models/receipts.py:14` · ERP `enums.ts:172`: DRAFT Nháp · SUBMITTED Đã ghi nhận (good) · CANCELLED Đã huỷ. Khớp.

**Supplier.supplier_type** — BE `suppliers.py:8`; ERP danh sách và chi tiết dùng nhãn BE `supplier_type_label`, form chép riêng ở `suppliers/suppliersModel.ts:10` và `SupplierFormModal.tsx:32`; `ENUMS.supplierType` (`enums.ts:192`) không dùng: INDIVIDUAL Cá nhân · COMPANY Doanh nghiệp. Chữ khớp nhưng có 4 bản chép.

**PurchaseCost.cost_type** — BE `costs.py:17` · ERP `enums.ts:177`: ICE Đá · TRANSPORT Vận chuyển · LOADING Bốc vác · OTHER Khác. Khớp.

**PurchaseCost.allocation_method** — BE `costs.py:23` · ERP `enums.ts:183`: BY_QTY Theo số kg · BY_VALUE Theo giá trị. Khớp.

### 2.5 Danh mục

**Item.item_type** — BE `catalog/models/items.py:37` · ERP `enums.ts:202`: SIMPLE Mặt hàng thường · BUNDLE "Combo dạng gói (có công thức)" / ERP "Combo" (info) ⚠W21.

**PricingRule.apply_on** — BE `pricing.py:83` · ERP `enums.ts:214` ⚠W22: ITEM "Theo mặt hàng (mua ≥ N kg)" / "Theo mặt hàng" · ORDER "Theo đơn (tổng ≥ M đồng)" / "Theo đơn".

**PricingRule.discount_type** — BE `pricing.py:87` · ERP `enums.ts:218`: AMOUNT Giảm số tiền · PERCENT Giảm phần trăm. Khớp.

### 2.6 Nội dung

**Entry.status** — BE `content/models/entries.py:12` · ERP `enums.ts:224`: draft Nháp · pending_review Chờ duyệt (warn) · published Đã đăng (good) · unpublished Đã gỡ. Khớp. (Giá trị DB viết thường, khác các app khác viết HOA.)

**Entry.kind** — BE `entries.py:11` · ERP `enums.ts:230`: post Bài viết · page Trang.

**Entry.page_role** — BE `entries.py:18` · ERP `enums.ts:238`, ô chọn `content/components/EntrySettings.tsx:16` ⚠W23
| DB | BE = `ENUMS.entryPageRole` | Ô chọn "Vai trò trang" |
|---|---|---|
| privacy | Bảo mật | Chính sách bảo mật |
| terms | Điều kiện giao dịch | Điều khoản mua hàng |
| refund | Đổi trả hoàn tiền | Chính sách đổi trả |
| seller_info | Thông tin người bán | Thông tin người bán |

**Entry.source** — BE `entries.py:24` · ERP `enums.ts:234`: human Người dùng · ai "AI" (info). Xem mục 3.

**Lý do trả về nháp** (`Entry.return_reason`, không `choices`, tập mã `content/entries/services.py:560`). BE không có nhãn. Hai bản FE ⚠W24:
| Mã | Hộp trả về nháp (`content/messages.ts:298`) | `ENUMS.entryReturnReason` (`enums.ts:244`, không dùng) |
|---|---|---|
| missing_info | Thiếu thông tin hoặc hình ảnh | Thiếu thông tin, hình ảnh |
| wrong_content | Nội dung chưa chuẩn, cần sửa | Nội dung chưa chuẩn, cần sửa |
| legal_risk | Rủi ro pháp lý hoặc bản quyền | Rủi ro pháp lý, bản quyền |
| other | Lý do khác | Khác |

**Lý do gỡ bài** (tập mã `content/entries/services.py:784`, không lưu field riêng). Hai bản FE ⚠W25:
`content/messages.ts:306` "Giá chưa đúng · Khiếu nại hoặc rủi ro pháp lý · Hết mùa vụ · Nội dung chưa chuẩn · Lý do khác" và `enums.ts:250` (không dùng) "… Khiếu nại, rủi ro pháp lý … Khác".

### 2.7 Nhân sự / Phân quyền / Nhật ký

**StaffProfile.status** — BE `accounts/models.py:21` · ERP `enums.ts:263`: ACTIVE Đang làm (good) · INACTIVE "Nghỉ" / ERP "Đã nghỉ" ⚠W19.

**AuditLog.actor_kind** — BE `accounts/models.py:69` · ERP nút lọc `audit/auditModel.ts:255`, `ENUMS.auditActorKind` (`enums.ts:267`, không dùng) ⚠W20: user "Người dùng" / ERP "Người" · system Hệ thống · ai "AI (thay người dùng)" / ERP "AI".

**Group** (vai): xem mục 1.9. Khớp BE và FE.

**GroupDataScope.value** (phạm vi dữ liệu, `accounts/data_scopes/catalog.py:56-135`). Nhãn chỉ ở BE, màn ERP chưa làm (Lô 5).
| object_key (nhãn) | Giá trị → nhãn |
|---|---|
| orders (Đơn hàng) | assigned_deliveries Đơn có phiếu giao gán cho tôi · assigned_or_confirmation Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận · all Tất cả đơn |
| invoices (Hoá đơn bán) | chỉ đọc, theo `orders` |
| deliveries (Phiếu giao) | assigned Phiếu gán cho tôi · all Tất cả phiếu |
| confirmation (Gọi xác nhận) | pending_or_called_recently Phiếu đang chờ gọi hoặc tôi đã gọi trong N ngày · all_pending Mọi phiếu chờ gọi |
| returns (Hàng hoàn về kho) | assigned_deliveries Phiếu của phiếu giao gán cho tôi · all Tất cả phiếu |
| receipts (Phiếu nhập) | created_by_me_today Do tôi tạo trong ngày · created_by_me Do tôi tạo · all Tất cả phiếu |
| customers (Khách hàng) | none Không xem · assigned_deliveries Khách của phiếu giao gán cho tôi (trong cửa sổ) · all Tất cả khách |
| audit_log (Nhật ký hoạt động) | none Không xem · all Tất cả (chỉ đọc) |

**Nhãn thao tác Nhật ký** (`AuditLog.action`, ERP `audit/auditModel.ts:13-94`; mã lạ hiện "Thao tác khác"). ⚠W33: các `action` BE đang ghi mà ERP **không có nhãn**, nên màn Nhật ký hiện "Thao tác khác":
| action BE | Nơi ghi |
|---|---|
| `batch_near_expiry`, `batch_expired`, `batch_sold_out`, `batch_selling`, `batch_back_in_stock` | `inventory/batches/services.py:469-480` (job hằng ngày) |
| `label_printed`, `label_reprinted` | `delivery/labels/services.py:149` |
| `update_reconciliation_lines` | `inventory/stocktake/services.py:28` |
| `delete_returntostock` | `inventory/returns/services.py:82` |
| `change_group_capabilities` | `accounts/capabilities/services.py:29` (lưu ma trận phân quyền) |
| `item_image_add`, `item_image_replace` | `catalog/images/services.py:148,159` |
| `content_publish`, `content_republish`, `content_restore_version` | `content/entries/services.py:523-527` |
| `create_callscript`, `update_callscript` | `delivery/confirmation/call_scripts.py:45` |
| `admin_edit` | `common/admin.py:17` (sửa trong Django Admin) |
| `propose_<lệnh>`, `schedule_<lệnh>`, `execute_<lệnh>`, `confirm_<lệnh>`, `reject_<lệnh>`, `cancel_schedule_<lệnh>`, `undo_<lệnh>`, `escalate_<lệnh>`, `fail_<lệnh>`, `escalate_overdue_<lệnh>` | `ai/execution/pipeline.py`, `ai/actions/services.py`, `ai/management/commands/run_due_ai_actions.py` |

Ngược lại, ERP có nhãn cho mã **BE không ghi** (code chết, ⚠W34): `auto_cancel`, `confirm_payment`, `execute_command`, `propose`, `confirm_proposal`, `reject_proposal`, `create`, `update`, `publish`. Ô lọc thao tác còn mục `confirm_proposal` (`auditModel.ts:122`) không bao giờ ra dòng nào.

Nhật ký cột "Thay đổi" dịch mã trạng thái bằng cách dò lần lượt 6 bảng (`auditModel.ts:162-175`), gặp bảng nào có mã trước thì lấy. Hậu quả ⚠W11: phiếu giao FAILED hiện "Thất bại" (lấy của phiếu hoàn), phiếu giao CANCELLED hiện "Đã huỷ" (lấy của đơn), phiếu hàng hoàn DRAFT hiện "Nháp" (lấy của kiểm kê, màn hàng hoàn ghi "Chờ duyệt").

### 2.8 AI (chỉ thấy khi bật cờ)

**AiAction.kind** — BE `ai/models/actions.py:12` · ERP `enums.ts:274` (không dùng): read Đọc · write Ghi.

**AiAction.level** — BE `actions.py:16` · ERP `enums.ts:278` ⚠W27: A "Mức A" / "Tự đọc" (info) · B "Mức B" / "Tự ghi" (good) · C "Mức C" / "Hỏi trước khi làm" (warn) · (ERP thêm OFF "Tắt"). Dòng thời gian BE ghi "(Mức C)".

**AiAction.status** — BE `actions.py:21` · ERP `enums.ts:284`: PENDING Chờ duyệt (warn) · CONFIRMED Đã duyệt (good) · REJECTED Đã từ chối · EXPIRED Hết hạn · SCHEDULED Đã lên lịch (info) · DONE Đã thực hiện (good) · UNDONE Đã hoàn tác · CANCELLED Đã huỷ · ESCALATED Đã chuyển việc (info) · FAILED Thất bại (crit). Khớp.

**AiPolicyVersion.global_mode** — BE `ai/models/policy.py:10` · ERP `enums.ts:296` ⚠W28: on Bật · c_only "Chỉ mức C" / "Luôn hỏi trước" · off Tắt.

### 2.9 Boolean có nhãn ở ERP
| Field | true | false | ERP |
|---|---|---|---|
| `PurchaseInvoice.is_paid` | Đã trả tiền (good) | Chưa trả tiền (warn) | `enums.ts:188` |
| `Supplier.is_active` | Đang hợp tác (good) | Ngừng hợp tác | `enums.ts:196` |
| `Item.is_active` | Đang kinh doanh (good) | Đang ẩn | `enums.ts:206` |
| `PricingRule.is_active` | Đang bật (good); BE verbose "Đang áp dụng" ⚠W22 | Đã tắt | `enums.ts:210` |
| `Category.is_active` | Đang hoạt động (good) | Ngừng dùng | `enums.ts:257` |
| `Warehouse.is_group` | Nhóm kho | Kho | `enums.ts:166` |

### 2.10 Danh sách ⚠ lệch nhãn (41 mục)

| # | Chỗ lệch | Mức |
|---|---|---|
| W1 | Đơn AUTO_CANCELLED: Shop hiện "Tự huỷ (quá TTL)" (chữ TTL), ERP "Đã huỷ", lý do "Hết giờ giữ chỗ", Nhật ký "Tự huỷ đơn hết giờ giữ chỗ" | Cao (khách thấy) |
| W2 | Shop tra đơn in **mã thô** trạng thái giao (`frontend/app/shop/orders/OrderLookup.tsx:231` dùng `delivery.status` thay vì `delivery.status_label`) | Cao (khách thấy) |
| W3 | Khoản tiền: dòng thời gian đơn dùng nhãn BE dài ("Khớp — đã xác nhận", "… — chờ Chủ"), chip ERP dùng nhãn ngắn; ORPHAN nghĩa khác ("đã huỷ" vs "tự huỷ") | TB |
| W4 | "Webhook SePay" lẫn tiếng Anh (chi tiết khoản tiền, dòng thời gian đơn) | Thấp |
| W5 | resolution: "Gắn vào đơn" vs "Đã gắn vào đơn"; "Xác nhận đơn (khách đã bù)" vs "Đã xác nhận đơn" | Thấp |
| W6 | environment "Sandbox/Production" tiếng Anh, ERP chưa có nhãn | Thấp |
| W7 | Mã lý do huỷ có 4 bản nhãn khác nhau (BE, hộp huỷ đơn, hộp quyết định, `ENUMS.cancelReason` không dùng và thiếu 2 mã) | TB |
| W8 | Refund GATEWAY "Qua cổng (chưa hiện thực)" vs "Qua cổng" | Thấp |
| W9 | Phiếu hoàn PENDING: Shop "Đang chờ hoàn", ERP "Chờ hoàn" (khác khán giả, chấp nhận được) | Thấp |
| W10 | Phiếu giao CONFIRMING: Shop (BE gửi) "Chờ vựa gọi xác nhận", ERP "Chờ xác nhận" (cố ý) | Thấp |
| W11 | Nhật ký cột "Thay đổi" dịch sai trạng thái phiếu giao FAILED/CANCELLED và hàng hoàn DRAFT | TB |
| W12 | Kết quả cuộc gọi: 4 nhãn BE ≠ ERP | Thấp |
| W13 | Lý do cần quyết định WANT_CHANGE: serializer "Khách muốn đổi món – huỷ + hoàn + đặt lại", model "Khách muốn đổi"; `ENUMS.confirmEscalationReason` không dùng | Thấp |
| W14 | Hàng chờ gọi: tab "Cần gọi ngay" và tab "Chờ gọi" cùng tồn tại, người dùng khó phân biệt | Thấp |
| W15 | Sổ nhập xuất WRITE_OFF "Hạch toán lỗ / huỷ" vs "Ghi lỗ, huỷ hàng" | Thấp |
| W16 | Hàng hoàn WRITE_OFF: dòng thời gian đơn "Huỷ bỏ (hạch toán lỗ)", màn hàng hoàn "Huỷ bỏ, ghi lỗ" | TB |
| W17 | Một chứng từ `ReturnToStock` có 5 tên: "Hàng hoàn về kho" (menu), "Trả hàng về kho"/"phiếu trả về kho" (Nhật ký `auditModel.ts:19,29,30`), "Mang hàng về kho"/"hàng về kho" (dòng thời gian BE), "Duyệt hàng hoàn" (Tài khoản) | TB |
| W18 | `ReturnToStock.Status.DRAFT` mang nhãn "Chờ duyệt": mã không khớp nghĩa | Thấp (không đổi DB) |
| W19 | Nhân viên INACTIVE: BE "Nghỉ", ERP "Đã nghỉ" | Thấp |
| W20 | actor_kind: "Người dùng"/"AI (thay người dùng)" vs "Người"/"AI" | Thấp |
| W21 | BUNDLE: "Combo dạng gói (có công thức)" vs "Combo" | Thấp |
| W22 | PricingRule apply_on / is_active: BE dài, ERP ngắn; "Đang áp dụng" vs "Đang bật" | Thấp |
| W23 | Vai trò trang: 2 bộ chữ ("Bảo mật" vs "Chính sách bảo mật"…) | TB |
| W24 | Lý do trả về nháp: 2 bộ chữ FE, một bộ không dùng | Thấp |
| W25 | Lý do gỡ bài: 2 bộ chữ FE, một bộ không dùng | Thấp |
| W26 | Nguồn bài viết "AI" (xem mục 3) | TB khi cờ tắt |
| W27 | Mức AI: "Mức A/B/C" (BE, dòng thời gian) vs "Tự đọc/Tự ghi/Hỏi trước khi làm" | Thấp |
| W28 | Chế độ AI c_only: "Chỉ mức C" vs "Luôn hỏi trước" | Thấp |
| W29 | `SalesCreditNote` có 3 tên: "Chứng từ đảo doanh thu" (model, dòng thời gian), "Lập hoá đơn điều chỉnh" (Nhật ký `auditModel.ts:51`), "Trừ doanh thu đơn huỷ" (báo cáo); glossary 01 ghi "phiếu giảm trừ" | TB |
| W30 | `confirm_payment_manual`: "Xác nhận thanh toán thủ công" (Nhật ký, Admin) vs "Xác nhận đã nhận tiền" (Phân quyền, Tài khoản, nút) | Thấp |
| W31 | `ai.manage_ai_policy`: "Cài đặt chính sách AI" (Phân quyền) vs "Quản lý chính sách AI" (Tài khoản) | Thấp |
| W32 | Meta perm "Publish lô ra Shop" lẫn tiếng Anh (Django Admin) | Thấp |
| W33 | 18 `action` BE + các action AI động không có nhãn ở Nhật ký → "Thao tác khác" | TB |
| W34 | 9 nhãn Nhật ký cho mã BE không ghi; ô lọc `confirm_proposal` rỗng | Thấp (code chết) |
| W35 | `shared/ui/StatusChip.tsx`, `shared/lib/status.ts`, `shared/ui/RightRail.tsx`, `shared/ui/AiBar.tsx` không còn ai import | Thấp (code chết) |
| W36 | Dòng thời gian chi tiết: dòng AI hiện "AI" hai lần ("AI AI của Lộc"), `shared/ui/detail/Timeline.tsx:51` + nhãn BE "AI của …" | Thấp |
| W37 | `SalesOrder.Status.PAID` và `COMPLETED` không có code nào chuyển tới (chỉ `seed_demo`): đơn giao xong vẫn "Đang xử lý" ở ERP và Shop; nhánh `orderDetailModel.ts:90` (`COMPLETED` → lập phiếu hoàn) không bao giờ chạy | TB (nghiệp vụ, cần BA/PO xem) |
| W38 | Thanh bước chi tiết đơn (`orders/orderDetailModel.ts:27`) trộn trạng thái đơn (BOOKED, PAID) với trạng thái phiếu giao (PREPARING, DELIVERING) | Thấp |
| W39 | Hai cờ AI riêng: FE `NEXT_PUBLIC_AI_FEATURES`, BE `AI_ENABLED`. BE bật mà FE tắt thì BE vẫn sinh bước "AI soạn nháp…" (`common/guidance/steps.py:70`) và dòng AI | TB |
| W40 | `auto_cancel_blocked` trả mã thô "BR-LO-05" | Thấp |
| W41 | `CallScript.situation` chưa có màn ERP (chỉ Admin) | Thấp |

Khuyến nghị chung: `enums.ts` là nguồn nhãn duy nhất cho ERP, nhưng còn 8 bảng không ai dùng và 6 nơi chép nhãn riêng
(`orders/labels.ts`, `confirmation/confirmationUi.ts:253`, `content/messages.ts:298-311`, `EntrySettings.tsx:16`,
`suppliers/suppliersModel.ts:10`, `SupplierFormModal.tsx:32`). Gom về `enums.ts` rồi xoá bản chép. Với nhãn BE mà màn hoặc Shop
in thẳng (`status_label`, nhãn dòng thời gian), nên sửa nhãn trong `choices` cho khớp ERP. Sửa nhãn `choices` sinh migration
chỉ đổi metadata, không đụng dữ liệu.

### 2.11 Sơ đồ chuyển trạng thái

Ký hiệu: `A → B` · ai làm · action / hàm (quyền).

**Đơn (SalesOrder)**
- (mới) → BOOKED · khách đặt trên Shop · `POST /api/shop/orders/` (Hệ thống tạo).
- BOOKED → PROCESSING · Hệ thống khi tiền về khớp đủ (`sales/payments/services.py:321`), hoặc Chủ xác nhận tay (`confirm_payment_manual`, quyền cùng tên). Kèm xuất hoá đơn và tạo phiếu giao.
- BOOKED → AUTO_CANCELLED · Hệ thống, job `cancel_expired_orders` (`sales/orders/services.py:301`, audit `cancel_unpaid_expired`).
- PROCESSING (hoặc PAID) → CANCELLED · Chủ/Quản lý `cancel_paid_order` (quyền `sales.cancel_paid_order`), hoặc Hệ thống tự huỷ do không liên lạc được (`UNREACHABLE_AUTO`). Kèm phiếu giao → CANCELLED, lập chứng từ đảo. Chặn khi phiếu đang DELIVERING.
- PAID, COMPLETED: không có đường vào (⚠W37).

**Khoản tiền (PaymentTransaction)**
- (mới) → MATCHED / UNDERPAID / ORPHAN / UNMATCHED / OVERPAID · Hệ thống khi nhận IPN (webhook, cổng) hoặc Chủ xác nhận tay.
- Khác MATCHED → `resolution_status=OPEN` → RESOLVED với `resolution` ATTACHED / CONFIRMED / REFUNDED · Chủ (`resolve_payment`, `attach_payment`, quyền `confirm_payment_manual`).

**Phiếu hoàn (Refund)**
- (mới) → PENDING · Chủ/Quản lý `create_refund` (quyền `sales.create_refund`).
- PENDING → REFUNDED · Chủ `confirm_refund` (quyền `sales.confirm_refund`).
- PENDING → FAILED · Chủ `mark_refund_failed`. FAILED → PENDING · `retry_refund`.

**Phiếu giao (DeliveryNote)** (`delivery/services.py:46`)
- (mới) → CONFIRMING (bật gọi xác nhận) hoặc PREPARING · Hệ thống khi đơn có tiền.
- CONFIRMING → PREPARING · CSKH ghi cuộc gọi CONFIRMED/CONFIRMED_CHANGED, hoặc Chủ/Quản lý "Giao không xác nhận" (`decide_unconfirmed`).
- PREPARING → CONFIRMING · "Huỷ xác nhận đơn" (`confirmation/services.py:375`, chặn khi đã in tem).
- PREPARING → READY · NV kho đóng gói (`pack_deliverynote`; cần cả `change_deliverynote`).
- READY → DELIVERING → COMPLETED / FAILED · người giao (`delivery_advance_status`, `delivery_mark_failed`; quyền `change_deliverynote`).
- FAILED → DELIVERING · hẹn giao lại. COMPLETED: không quay lui (BR-GH-05).
- CONFIRMING / PREPARING / READY / FAILED → CANCELLED · theo đơn bị huỷ.

**Gọi xác nhận (ConfirmationTask)**
- (mới) → PENDING · Hệ thống, cùng lúc phiếu giao CONFIRMING.
- PENDING → CALLBACK (khách hẹn, hoặc Chủ/QL "Gia hạn thêm") · → ESCALATED (sai số, khách muốn huỷ/đổi, quá số lần không nghe máy hoặc hết cửa sổ) · → DONE (khách xác nhận) · CSKH `delivery_call_recorded`.
- ESCALATED → DONE (Giao không xác nhận / Huỷ đơn) hoặc CALLBACK (Gia hạn) · Chủ/QL `decide_unconfirmed`. Quá hạn quyết định → Hệ thống tự huỷ đơn.
- Đơn bị huỷ → REFUND_CALL (`confirmation/services.py:805`) → DONE khi CSKH ghi NOTIFIED.

**Phiếu nhập (PurchaseReceipt)**
- (mới) → DRAFT → SUBMITTED trong một bước · NV kho/QL/Chủ "Nhập lô" (`receive_batches` → `create_and_submit_receipt`, quyền `add_purchasereceipt`); sinh lô DRAFT.
- DRAFT → SUBMITTED · `submit_receipt` (`purchasing/receipts/services.py:32`) cho phiếu Nháp tạo riêng.
- SUBMITTED → CANCELLED · `cancel_purchase_receipt`; các lô của phiếu → CANCELLED.

**Hàng hoàn về kho (ReturnToStock)**
- (mới) → DRAFT (Chờ duyệt, decision PENDING) · người giao "Mang hàng về kho" (`return_to_warehouse`).
- DRAFT → APPROVED với decision RESTOCK / WRITE_OFF · Chủ/QL `approve_returntostock` (quyền cùng tên).
- DRAFT → CANCELLED · người tạo hoặc người có quyền duyệt (`cancel_returntostock`). Xoá mềm: Chủ (`delete_returntostock`).

**Kiểm kê (StockReconciliation)**
- (mới) → DRAFT · `create_stockreconciliation` (quyền `add_stockreconciliation`).
- DRAFT → SUBMITTED · `submit_stockreconciliation`. SUBMITTED → DRAFT · `return_stockreconciliation_to_draft`.
- SUBMITTED → APPROVED · Chủ/QL `approve_stockreconciliation` (quyền cùng tên). Ghi chuyển động RECONCILE.

**Lô (Batch)**
- (mới) → DRAFT · khi phiếu nhập SUBMITTED.
- DRAFT → SELLING · `publish_batch` (quyền cùng tên).
- SELLING ↔ NEAR_EXPIRY, → SOLD_OUT, SOLD_OUT → SELLING/NEAR_EXPIRY (hàng hoàn tái nhập), DRAFT/SELLING/NEAR_EXPIRY/SOLD_OUT → EXPIRED · Hệ thống, job `update_batch_statuses` (`inventory/batches/services.py:500`).
- EXPIRED → CANCELLED · Chủ `cancel_expired_batch`. Phiếu nhập huỷ → lô CANCELLED.
- → CLOSED · Chủ `close_batch` (quyền cùng tên), điểm cuối.

**Bài viết / Trang (Entry)**
- draft → pending_review · người viết `content_submit`.
- draft / pending_review → published · người có `content.publish_entry` (`content_publish`; đăng lại `content_republish`, khôi phục bản `content_restore_version`).
- pending_review → draft · `content_return` (bắt buộc lý do).
- published → unpublished · `content_unpublish` (bắt buộc lý do).

---

## 3. Chỗ còn chữ "AI" khi cờ `NEXT_PUBLIC_AI_FEATURES` tắt (mặc định)

Đã kiểm: menu AI (`nav.ts:460,471,485,497`), trang `/ai/*` (`AiFeatureGuard` → "Không tìm thấy trang này"), khối Trợ lý AI ở
chi tiết (`DetailPage.tsx:21`, `AiBlockFrame.tsx:63`, `AiDocBlockGate`), dòng đề xuất ở Tổng quan (`AiProposalsRow.tsx:23`),
"AI của tôi" ở menu avatar (`Shell.tsx:127`) và Tài khoản (`AccountScreen.tsx:52`, qua `canView`), nút lọc "AI" và ô lọc
thao tác AI ở Nhật ký (`AuditLogScreen.tsx:95,165`), cột "Đề xuất" ở Nhật ký (`AuditLogScreen.tsx:128`), "Nhờ người xử lý"
(`guidance/escalation.ts:13`) đều đã ẩn theo cờ. Shop (`frontend/`) không có chữ AI nào.

Những chỗ dưới đây **vẫn hiện** khi cờ tắt (12 chỗ người dùng thấy được, 5 chỗ chỉ ở Admin/trình đọc màn hình/code chết):

| # | Màn / route | File:dòng | Chữ hiện ra | Đề xuất |
|---|---|---|---|---|
| A1 | Phân quyền `/permissions/`, nhóm "Quản trị" | `backend/apps/accounts/capabilities/registry.py:91` | ô việc "Cài đặt chính sách AI" | Ẩn theo cờ: BE bỏ việc `ai_policy` khỏi registry trả về khi `AI_ENABLED` tắt (hoặc FE lọc key `ai_policy`). Không đổi quyền đang gán |
| A2 | Tài khoản của tôi `/account/`, mục "Việc được làm" (Chủ) | `backend/apps/accounts/auth/services.py:63` | "Quản lý chính sách AI" | Ẩn theo cờ (BE bỏ khỏi `capabilities` của `/api/auth/me/` khi AI tắt) |
| A3 | Nhật ký `/audit-logs/`, dòng do AI làm | `erp-console/features/audit/components/AuditLogScreen.tsx:48`, `features/audit/messages.ts:25` | nhãn "AI" cạnh tên | Ẩn dòng theo quyết định Duy 06/10 (BE đang làm). Khi bật cờ thì giữ |
| A4 | Nhật ký, dòng người dùng đổi cài đặt AI | `features/audit/auditModel.ts:83-85` | "Đổi cài đặt AI", "Tắt trợ lý AI", "Đổi chính sách AI" | Ẩn theo cờ. Các dòng này `actor_kind=user` nên bộ lọc "ẩn dòng AI" của BE (lọc theo `actor_kind`) sẽ **không** bắt; cần lọc thêm `action` bắt đầu `ai_` |
| A5 | Nhật ký, dòng người duyệt/từ chối đề xuất (`confirm_<lệnh>`, `reject_<lệnh>`, `escalate_<lệnh>`) | `ai/actions/services.py:135,169,394` | "Thao tác khác" (không chữ AI, nhưng là dòng AI) | Ẩn theo cờ cùng A4 (lọc dòng có `proposal_ref` khác rỗng) |
| A6 | Dòng thời gian ở chi tiết phiếu nhập, lô, kiểm kê, hàng hoàn, khách, NCC, mặt hàng, nhân viên | `erp-console/shared/ui/detail/Timeline.tsx:51` + `backend/apps/common/guidance/audit_timeline.py:72` | "AI" + "AI của <tên>" (thành "AI AI của …") | Ẩn dòng AI theo cờ ở BE như Nhật ký; khi bật cờ thì bỏ một chữ "AI" lặp |
| A7 | Dòng thời gian chi tiết đơn `/orders/detail/` | `backend/apps/sales/orders/timeline.py:188` | "AI của <tên>" | Ẩn theo cờ cùng A6 |
| A8 | Chi tiết khoản tiền, phiếu hoàn (dòng thời gian) | `backend/apps/sales/payments/timeline.py:46`, `sales/refunds/timeline.py:48` | "AI của <tên>" | Ẩn theo cờ cùng A6 |
| A9 | Nội dung `/content/`, cột thứ 6 | `erp-console/features/content/messages.ts:24`, `components/ContentListScreen.tsx:116` | tiêu đề cột "AI" | Ẩn cột theo cờ |
| A10 | Nội dung, chip ở cột trên | `erp-console/shared/lib/enums.ts:236` | chip "AI" cho bài `source=ai` | Ẩn theo cờ cùng A9 (dữ liệu giữ) |
| A11 | Nội dung, cột "Ghi chú" | `features/content/contentModel.ts:374`, `messages.ts:36` | "AI soạn nháp" | Ẩn theo cờ (trả rỗng) |
| A12 | Mọi trang chi tiết (trình đọc màn hình) | `erp-console/shared/ui/detail/DetailPage.tsx:30` | aria-label "Trợ lý và lịch sử" | Đổi chữ: "Lịch sử" khi cờ tắt |
| A13 | Django Admin (superuser) | `backend/apps/ai/models/*`, `accounts/models.py:72,91-99` | model "Hành động AI", "Phiên bản cấu hình/chính sách AI"; field "Mã đề xuất AI", "Mức tự chủ AI", "AI thay cho ai" | Để nguyên (vết kiểm toán, chỉ superuser) |
| A14 | Django Admin, quyền nhóm | `backend/apps/ai/models/policy.py:39` | "Quản lý chính sách AI" | Để nguyên |
| A15 | Màn tạm "sắp có" (nếu Nhật ký về lại Placeholder) | `erp-console/shared/lib/nav.ts:441` | "kể cả việc do trợ lý AI đề xuất (ai:<tên>)" | Đổi chữ: "Mọi thay đổi trong hệ thống." (hiện không màn nào vẽ) |
| A16 | Không màn nào mount | `shared/ui/RightRail.tsx:18,80`, `shared/ui/AiBar.tsx:23,43` | "Trợ lý", "Trợ lý vận hành Sắp có", "AI đề xuất" | Xoá code chết |
| A17 | `/dev-patterns/` (chỉ bản mock) | `app/(console)/dev-patterns/PatternDemo.tsx` | khối AI mẫu | Để nguyên (bản build thật hiện 404) |

Không phải AI, giữ nguyên: "Nhờ Chủ vựa đặt lại" (`LoginScreen.tsx:139`), "Nhờ Chủ thêm nhóm…" (`AccountScreen.tsx:156`, `NoRoleScreen.tsx:46`,
`AssignCourierModal.tsx:137`, `app/print/label/page.tsx:38`) là lời nhắn thường.

Thông báo lỗi BE có chữ AI (`ai/actions/*`, `ai/execution/*`, `run_due_ai_actions.py`) chỉ trả ra từ `/api/ai/*`; khi cờ FE tắt
không màn nào gọi nên người dùng không thấy. Rủi ro còn lại là W39: nếu môi trường bật `AI_ENABLED=1` ở BE mà FE tắt, BE vẫn
sinh bước "AI soạn nháp …" và dòng AI. Đề xuất: BE ẩn mọi nhãn AI theo **một** cờ (đọc `AI_ENABLED`), FE build cờ khớp BE.

### Top 10 nên sửa trước
1. W2 — Shop tra đơn in mã thô trạng thái giao (`frontend/app/shop/orders/OrderLookup.tsx:231`): đổi sang `delivery.status_label`. Khách thấy.
2. W1 — Shop hiện "Tự huỷ (quá TTL)": đổi nhãn `SalesOrder.Status.AUTO_CANCELLED` thành "Hết giờ giữ chỗ" hoặc "Đã huỷ (hết giờ giữ chỗ)". Khách thấy.
3. A1 + A2 — "chính sách AI" ở Phân quyền và Tài khoản: ẩn theo cờ ở BE (Chủ thấy hằng ngày).
4. A3–A8 — dòng AI ở Nhật ký và mọi dòng thời gian: lọc theo cờ ở BE, gồm cả dòng `ai_*` và dòng có `proposal_ref` (bộ lọc theo `actor_kind` chưa đủ).
5. A9–A11 — cột "AI", chip "AI", ghi chú "AI soạn nháp" ở màn Nội dung: ẩn theo cờ.
6. W37 — đơn không bao giờ sang "Hoàn tất"; Shop và ERP hiện "Đang xử lý" sau khi giao xong. Cần BA/PO quyết (có thể là thiếu nghiệp vụ, không chỉ nhãn).
7. W11 — Nhật ký dịch sai trạng thái phiếu giao và hàng hoàn: dịch theo `model_name` của dòng thay vì dò lần lượt.
8. W33 — 18 thao tác BE hiện "Thao tác khác" ở Nhật ký: thêm nhãn (nhất là `batch_*`, `label_printed`, `change_group_capabilities`, `content_publish`).
9. W7 + W16 + W3 — cùng một lý do/kết quả mà chi tiết đơn (nhãn BE) và hộp thoại (nhãn ERP) khác chữ: sửa nhãn `choices`/bảng BE cho khớp ERP.
10. W17 + W29 + W23 — một chứng từ nhiều tên ("Hàng hoàn về kho", "Chứng từ đảo doanh thu", vai trò trang): Duy chốt một tên, rồi gom nhãn về `enums.ts`.

---

## 4. Đề xuất tên chuẩn (PO, chờ Duy duyệt)

> PO · 06/10/2026 · Trạng thái: **CHỜ DUYỆT** · Theo quyết định Duy 06/10 (tối) "Một tên cho mỗi chứng từ" (`doc/decisions.md`).
> Nguồn: mục 1 và 2.10 ở trên, `doc/URD.md` (§5–6), `doc/business-process-spec.md` (P-05…P-08), `doc/ops/go-live-phap-ly.md`.

**Nguyên tắc chọn tên**
1. Lấy chữ Lộc và nhân viên đang nói, theo URD và spec: "hàng hoàn", "phiếu hoàn tiền", "phiếu giao", "giữ chỗ", "tái nhập", "huỷ bỏ".
2. Nhãn ngắn, không tiếng Anh, không mã (không "TTL", "Webhook", "Publish", "BR-…"). Riêng tên riêng "SePay" được giữ vì Lộc dùng tên này.
3. **Một tên dùng ở mọi nơi**: `choices`/`verbose_name`/`Meta.permissions` của BE, `enums.ts` của ERP, Nhật ký, dòng thời gian, ma trận phân quyền, "Tài khoản của tôi". Shop chỉ có nhãn riêng khi khách cần chữ dễ hiểu hơn. Khi đó bảng ghi cả hai.
4. **Không đổi giá trị DB, không đổi `AuditLog.action` đã ghi.** Chỉ đổi nhãn. Đổi nhãn trong `choices` sinh migration chỉ sửa metadata, không đụng dữ liệu.
5. Tránh hai tên gần giống nhau cho hai thứ khác nhau. Ví dụ "phiếu hoàn" (tiền) và "phiếu hàng hoàn" (hàng), hoặc "Hoàn tất" dùng chung cho đơn, phiếu giao và việc gọi.
6. Không đụng phần AI (W26, W27, W28, W31, W36, W39 và mọi giá trị `ai`): lô dọn chữ AI đang làm.

Cột "Chuẩn" là chữ áp cho BE, ERP và Nhật ký. Cột "Shop" để trống nghĩa là Shop dùng đúng chữ chuẩn hoặc Shop không hiện. Dòng có **[Q-n]** cần Duy chọn, xem mục 4.4.

### 4.1 Bảng 1: Chứng từ và đối tượng (9 mục)

| # | Đối tượng (code) | Tên chuẩn | Tên đang dùng (vị trí) | Lý do |
|---|---|---|---|---|
| C1 | `ReturnToStock` (W17) | **Hàng hoàn**. Một tờ gọi là **phiếu hàng hoàn**. Menu và màn: "Hàng hoàn" **[Q-3]**. Việc người giao làm: "Mang hàng về kho". Việc Chủ/Quản lý làm: "Duyệt hàng hoàn" | "Hàng hoàn về kho" (menu `nav.ts:313`, BE `returns.py:75`, Meta); "Trả hàng về kho", "phiếu trả về kho" (Nhật ký `auditModel.ts:19,29,30`); "Mang hàng về kho", "phiếu hàng về kho", "Duyệt hàng về kho" (dòng thời gian đơn `timeline.py:257-274`); "Duyệt hàng hoàn" (Tài khoản) | URD (§5, dòng 42 và 157) và spec P-08 đều nói "hàng hoàn", "duyệt hàng hoàn". Bỏ chữ "trả" vì dễ lẫn với "Trả nhà cung cấp" (C8). Giữ "Mang hàng về kho" vì đó là động tác, không phải tên chứng từ |
| C2 | `SalesCreditNote` (W29) | **Phiếu trừ doanh thu** **[Q-1]** | "Chứng từ đảo doanh thu" (BE `credit_notes.py:44`, dòng thời gian, spec BR-HT-06/10); "Lập hoá đơn điều chỉnh" (Nhật ký `auditModel.ts:51`); "Trừ doanh thu đơn huỷ" (báo cáo `reportView.ts:47`); "phiếu giảm trừ" (glossary 01) | "Trừ doanh thu" là chữ báo cáo đang dùng và Lộc đọc là hiểu. "Đảo" là từ kế toán. **Cấm "hoá đơn điều chỉnh"**: đây là khái niệm hoá đơn điện tử (NĐ 123/2020, sửa đổi bởi NĐ 70/2025). Cá Về chưa xuất hoá đơn điện tử, nên dùng chữ này dễ làm người đọc tưởng đã điều chỉnh hoá đơn với thuế |
| C3 | `Refund` | **Phiếu hoàn tiền**. Luôn viết đủ, không viết "phiếu hoàn" trơn | "Phiếu hoàn tiền" (BE `refunds.py:73`, URD); "Phiếu hoàn chờ chuyển" (menu `nav.ts:218`); "Lập phiếu hoàn" (ma trận, Tài khoản, Nhật ký `auditModel.ts:47`) | "Phiếu hoàn" trơn dễ nhầm với phiếu hàng hoàn (C1). Menu đổi thành "Hoàn tiền chờ chuyển" |
| C4 | `DeliveryNote` | **Phiếu giao** | "Phiếu giao hàng" (BE `delivery/models.py:74`, URD); "Phiếu giao" (ERP, ma trận quyền) | ERP và nhân viên đã quen "phiếu giao". Ngắn, vừa cột và chip. Admin đổi `verbose_name` theo |
| C5 | `PaymentTransaction` | **Khoản tiền về** | "Giao dịch thanh toán" (BE `payments.py:84`); "Giao dịch tiền về" (mục 1.3 file này); "Khoản tiền về" (`nav.ts:201`); "tiền về" (Nhật ký) | Bảng này chỉ ghi tiền vào tài khoản. "Thanh toán" không nói rõ chiều tiền, trong khi phiếu hoàn tiền là tiền ra |
| C6 | `PurchaseReceipt` | **Phiếu nhập** | "Phiếu nhập kho" (BE `receipts.py:41`); "Phiếu nhập" (ERP, Nhật ký) | Ngắn, ERP đã dùng. Động tác vẫn là "Nhập lô" |
| C7 | `StockEntry` | **Phiếu điều chỉnh tồn** | "Phiếu điều chỉnh kho" (BE `stock.py:65`); "Phiếu điều chỉnh tồn" (ERP `StockEntriesTab.tsx:106`) | Phiếu này đổi số tồn, không đổi kho. ERP đã dùng |
| C8 | `BatchSupplierReturn` | **Trả nhà cung cấp** | "Trả NCC lô quá hạn" (BE `supplier_returns.py:39`); "Trả lô về nhà cung cấp" (Nhật ký `auditModel.ts:18`); "Trả nhà cung cấp" (Sổ nhập xuất); "Đã trả NCC" (spec BR-LO-07) | Trùng chữ với Sổ nhập xuất. Trên màn viết đủ "nhà cung cấp", tài liệu vẫn được viết tắt NCC |
| C9 | `ConfirmationTask` | **Việc gọi xác nhận**. Màn: "Gọi xác nhận" | "Mục chờ gọi CSKH" (BE `delivery/models.py:136`); "Gọi xác nhận" (menu, quyền) | Bỏ "CSKH" khỏi tên chứng từ. Vai CSKH vẫn giữ tên |

Không lệch, giữ nguyên: Đơn hàng, Hoá đơn bán, Khách hàng, Lô hàng, Phiếu kiểm kê, Sổ nhập xuất, Hoá đơn mua, Chi phí mua hàng, Mặt hàng, Combo, Bảng giá, Ưu đãi, Tem giao, Kịch bản gọi.

### 4.2 Bảng 2: Trạng thái và lựa chọn đang lệch (T1–T66, cộng 18 nhãn thao tác Nhật ký ở T67–T76)

**Bán hàng và tiền**
| # | Trường | DB | Chuẩn (BE + ERP) | Shop (khách thấy) | Đang dùng | W |
|---|---|---|---|---|---|---|
| T1 | `SalesOrder.status` | BOOKED | Giữ chỗ | **Chờ thanh toán** | "Giữ chỗ" ở cả ba nơi | — |
| T2 | `SalesOrder.status` | AUTO_CANCELLED | **Hết giờ giữ chỗ** **[Q-2]** | **Đã huỷ vì quá giờ thanh toán** | BE/Shop "Tự huỷ (quá TTL)"; ERP chip "Đã huỷ", lý do "Hết giờ giữ chỗ"; Nhật ký "Tự huỷ đơn hết giờ giữ chỗ" | W1 |
| T3 | `PaymentTransaction.match_status` | MATCHED | Khớp đơn | | BE "Khớp — đã xác nhận"; ERP "Khớp" | W3 |
| T4 | 〃 | UNDERPAID | Chuyển thiếu | | BE "Thiếu tiền — chờ Chủ"; ERP "Thiếu tiền"; lý do đơn "Chuyển thiếu tiền" (`reasons.py`) | W3 |
| T5 | 〃 | ORPHAN | Về sau khi đơn đã huỷ | | BE "Đến sau khi đơn đã huỷ — chờ Chủ"; ERP "Về sau khi đơn tự huỷ". ERP **sai nghĩa**: code gán ORPHAN cho cả đơn huỷ tay (`sales/payments/services.py:273`) | W3 |
| T6 | 〃 | UNMATCHED | Không khớp đơn | | BE "Không khớp đơn — chờ Chủ" | W3 |
| T7 | 〃 | OVERPAID | Chuyển thừa | | BE "Chuyển thừa — đơn đã thanh toán, chờ Chủ" | W3 |
| T8 | `PaymentTransaction.resolution` | ATTACHED | Đã gắn vào đơn | | BE "Gắn vào đơn" | W5 |
| T9 | 〃 | CONFIRMED | Đã xác nhận đơn | | BE "Xác nhận đơn (khách đã bù)" | W5 |
| T10 | `PaymentTransaction.source` | WEBHOOK | Ngân hàng báo | | "Webhook SePay" (BE, ERP) | W4 |
| T11 | 〃 | MANUAL / GATEWAY | Xác nhận tay / Cổng SePay (giữ) | | khớp | W4 |
| T12 | `PaymentTransaction.environment` | SANDBOX | Chạy thử | | "Sandbox (thử)", ERP chưa có nhãn | W6 |
| T13 | 〃 | PRODUCTION | Chạy thật | | "Production (thật)" | W6 |
| T14 | Mã lý do huỷ (`reason_code`) | CUSTOMER_CHANGED_MIND | Khách đổi ý | | khớp | W7 |
| T15 | 〃 | DAMAGED_WHEN_PACKING | Hàng hư lúc soạn hàng | | BE "Hư hỏng khi soạn hàng"; hộp huỷ "Hư khi đóng hàng" | W7 |
| T16 | 〃 | GIVE_UP_AFTER_FAILED | Giao thất bại, không giao lại | | BE "Bỏ giao sau khi thất bại"; hộp huỷ "Bỏ sau khi giao thất bại" | W7 |
| T17 | 〃 | UNREACHABLE | Không liên lạc được khách | | khớp, `enums.ts` thiếu | W7 |
| T18 | 〃 | OTHER | Lý do khác | | BE và hộp huỷ "Khác"; dòng thời gian và hộp quyết định "Lý do khác" | W7 |
| T19 | 〃 | UNREACHABLE_AUTO | Hệ thống tự huỷ: không liên lạc được khách | | BE "Hệ thống tự huỷ — không liên lạc được"; `enums.ts` thiếu | W7 |
| T20 | `Refund.method` | GATEWAY | Qua cổng SePay (ẩn khỏi ô chọn khi chưa làm) | | BE "Qua cổng (chưa hiện thực)"; ERP "Qua cổng" | W8 |
| T21 | `Refund.status` | PENDING | Chờ hoàn tiền | Đang chờ hoàn tiền | BE/ERP "Chờ hoàn"; Shop "Đang chờ hoàn" | W9 |
| T22 | 〃 | REFUNDED | Đã hoàn tiền | | "Đã hoàn" | W9 |
| T23 | 〃 | FAILED | Hoàn thất bại | (Shop không hiện) | "Thất bại"; Nhật ký lấy nhầm chữ này cho phiếu giao | W11 |

Dòng thời gian khoản tiền: bỏ đuôi "— chờ Chủ" khỏi nhãn. Nếu cần báo còn việc thì ghép nhãn `resolution_status` ("Chờ xử lý" / "Đã xử lý") ra sau, để chip và dòng thời gian cùng một chữ.

**Giao hàng và gọi xác nhận**
| # | Trường | DB | Chuẩn (BE + ERP) | Shop (khách thấy) | Đang dùng | W |
|---|---|---|---|---|---|---|
| T24 | `DeliveryNote.status` | CONFIRMING | Chờ gọi xác nhận | Chờ vựa gọi xác nhận | BE/ERP "Chờ xác nhận" (lẫn với xác nhận tiền); Shop mã thô | W2, W10 |
| T25 | 〃 | PREPARING | Đang soạn hàng | Đang soạn hàng | BE/ERP "Soạn hàng"; Shop mã thô | W2 |
| T26 | 〃 | READY | Chờ lấy hàng | Đã soạn xong, chờ giao | Shop mã thô | W2 |
| T27 | 〃 | DELIVERING | Đang giao | Đang giao | Shop mã thô | W2 |
| T28 | 〃 | COMPLETED | **Đã giao** **[Q-4]** | Đã giao | BE/ERP "Hoàn tất"; Shop mã thô | W2 |
| T29 | 〃 | FAILED | Giao thất bại | Giao chưa thành công, vựa sẽ liên hệ lại | Nhật ký "Thất bại"; Shop mã thô | W2, W11 |
| T30 | 〃 | CANCELLED | Đã huỷ theo đơn | Đã huỷ | Nhật ký "Đã huỷ"; Shop mã thô | W2, W11 |
| T31 | `CustomerCall.result` | CONFIRMED_CHANGED | Đã xác nhận, có đổi thông tin | | BE "Xác nhận có đổi thông tin"; ERP "Đã xác nhận, có đổi" | W12 |
| T32 | 〃 | WRONG_NUMBER | Sai số điện thoại | | BE "Sai số" | W12 |
| T33 | 〃 | WANT_CHANGE | Khách muốn đổi món | | BE "Khách muốn đổi món/số lượng" | W12 |
| T34 | 〃 | WANT_CANCEL | Khách muốn huỷ đơn | | BE "Khách muốn huỷ" | W12 |
| T35 | `ConfirmationTask.escalation_reason` | WRONG_NUMBER | Sai số điện thoại | | "Sai số" | W13 |
| T36 | 〃 | WANT_CANCEL | Khách muốn huỷ đơn | | "Khách muốn huỷ" | W13 |
| T37 | 〃 | WANT_CHANGE | Khách muốn đổi món | | model "Khách muốn đổi"; serializer "Khách muốn đổi món – huỷ + hoàn + đặt lại" | W13 |
| T38 | `ConfirmationTask.state` | DONE | Đã xong | | "Hoàn tất" (trùng chữ với đơn và phiếu giao) | — |
| T39 | Tab hàng chờ gọi | DEFAULT | Đến giờ gọi | | "Cần gọi ngay", đứng cạnh tab "Chờ gọi" nên khó phân biệt | W14 |
| T40 | Quyết định đơn chưa xác nhận | DELIVER_WITHOUT_CONFIRM | Bỏ qua gọi xác nhận | | ERP "Giao không xác nhận"; Nhật ký "Bỏ qua bước gọi xác nhận"; BE không có nhãn | — |
| T41 | 〃 | EXTEND | Gia hạn gọi | | ERP "Gia hạn thêm"; Nhật ký "Gia hạn giao" (sai việc) | — |
| T42 | 〃 | CANCEL | Huỷ đơn | | khớp ERP, BE thêm nhãn | — |
| T43 | `auto_cancel_blocked` | "BR-LO-05" | Lô đã chốt, không tự huỷ được | | API trả mã thô | W40 |

Ghi chú T37: phần "huỷ, hoàn tiền, đặt lại" là hướng dẫn xử lý. Đưa vào dòng gợi ý dưới chip, không nhét vào nhãn.

**Kho và lô**
| # | Trường | DB | Chuẩn (BE + ERP) | Đang dùng | W |
|---|---|---|---|---|---|
| T44 | `StockLedgerEntry.movement_type` | WRITE_OFF | Huỷ hàng, ghi lỗ | BE "Hạch toán lỗ / huỷ"; ERP "Ghi lỗ, huỷ hàng" | W15 |
| T45 | `ReturnToStock.decision` | WRITE_OFF | Huỷ hàng, ghi lỗ | BE và dòng thời gian "Huỷ bỏ (hạch toán lỗ)"; ERP "Huỷ bỏ, ghi lỗ" | W16 |
| T46 | `ReturnToStock.decision` | RESTOCK / PENDING | Tái nhập / Chờ quyết định (giữ) | khớp | — |
| T47 | `ReturnToStock.status` | DRAFT | Chờ duyệt | Nhật ký "Nháp" | W11, W18 |

"Ghi lỗ" thay "hạch toán lỗ" ở mọi nhãn, gồm cả quyền "Huỷ lô quá hạn". Spec vẫn được dùng "hạch toán lỗ" vì đó là tài liệu.

**Danh mục, nhân sự, Nhật ký**
| # | Trường | DB | Chuẩn (BE + ERP) | Đang dùng | W |
|---|---|---|---|---|---|
| T48 | `StaffProfile.status` | INACTIVE | Đã nghỉ | BE "Nghỉ" | W19 |
| T49 | `AuditLog.actor_kind` | user | Người | BE "Người dùng"; ERP "Người". Giá trị `ai` để lô dọn AI xử lý | W20 |
| T50 | `Item.item_type` | BUNDLE | Combo | BE "Combo dạng gói (có công thức)" | W21 |
| T51 | `PricingRule.apply_on` | ITEM | Theo mặt hàng | BE "Theo mặt hàng (mua ≥ N kg)". Phần "≥ N kg" đưa thành chữ gợi ý ở form | W22 |
| T52 | 〃 | ORDER | Theo đơn | BE "Theo đơn (tổng ≥ M đồng)" | W22 |
| T53 | `PricingRule.is_active` | true | Đang áp dụng | BE "Đang áp dụng"; ERP "Đang bật" | W22 |

**Nội dung**
| # | Trường | DB | Chuẩn (BE + ERP) | Đang dùng | W |
|---|---|---|---|---|---|
| T54 | `Entry.page_role` | privacy | Chính sách bảo mật | BE/`enums.ts` "Bảo mật" | W23 |
| T55 | 〃 | terms | **Điều kiện giao dịch chung** **[Q-5]** | BE "Điều kiện giao dịch"; ô chọn "Điều khoản mua hàng" | W23 |
| T56 | 〃 | refund | Chính sách đổi trả và hoàn tiền | BE "Đổi trả hoàn tiền"; ô chọn "Chính sách đổi trả" | W23 |
| T57 | 〃 | seller_info | Thông tin người bán | khớp | W23 |
| T58 | Lý do trả về nháp | missing_info | Thiếu thông tin hoặc hình ảnh | `enums.ts` "Thiếu thông tin, hình ảnh" | W24 |
| T59 | 〃 | wrong_content | Nội dung chưa chuẩn | hộp thoại "Nội dung chưa chuẩn, cần sửa"; lý do gỡ bài cùng mã ghi "Nội dung chưa chuẩn" | W24 |
| T60 | 〃 | legal_risk | Rủi ro pháp lý hoặc bản quyền | `enums.ts` "Rủi ro pháp lý, bản quyền" | W24 |
| T61 | 〃 | other | Lý do khác | `enums.ts` "Khác" | W24 |
| T62 | Lý do gỡ bài | wrong_price | Giá chưa đúng | khớp | W25 |
| T63 | 〃 | complaint | Khiếu nại hoặc rủi ro pháp lý | `enums.ts` "Khiếu nại, rủi ro pháp lý" | W25 |
| T64 | 〃 | out_of_season | Hết mùa vụ | khớp | W25 |
| T65 | 〃 | wrong_content | Nội dung chưa chuẩn | khớp (trùng T59) | W25 |
| T66 | 〃 | other | Lý do khác | `enums.ts` "Khác" | W25 |

Quy ước chung cho mã `OTHER`/`other` ở lý do (huỷ đơn, trả về nháp, gỡ bài): dùng **"Lý do khác"**. Mã `OTHER` ở loại chi phí và lý do giao thất bại vẫn là "Khác", vì đó là loại, không phải lý do.

Nhãn Nhật ký cho 18 thao tác đang hiện "Thao tác khác" (W33, không gồm thao tác AI):
| # | `action` | Chuẩn |
|---|---|---|
| T67 | `batch_near_expiry` / `batch_expired` / `batch_sold_out` | Lô sang Cận hạn / Lô sang Quá hạn / Lô hết hàng |
| T68 | `batch_selling` / `batch_back_in_stock` | Lô sang Đang bán / Lô có hàng lại (hàng hoàn tái nhập) |
| T69 | `label_printed` / `label_reprinted` | In tem giao / In lại tem giao |
| T70 | `update_reconciliation_lines` | Sửa số đếm kiểm kê |
| T71 | `delete_returntostock` | Ẩn phiếu hàng hoàn |
| T72 | `change_group_capabilities` | Đổi phân quyền nhóm |
| T73 | `item_image_add` / `item_image_replace` | Thêm ảnh mặt hàng / Thay ảnh mặt hàng |
| T74 | `content_publish` / `content_republish` / `content_restore_version` | Đăng bài / Đăng lại bài / Khôi phục bản cũ |
| T75 | `create_callscript` / `update_callscript` | Thêm kịch bản gọi / Sửa kịch bản gọi |
| T76 | `admin_edit` | Sửa trong trang quản trị kỹ thuật |

T71 dùng "Ẩn" vì phiếu chỉ xoá mềm, chứng từ vẫn còn (bất biến 3).

### 4.3 Tên việc và quyền theo tên chuẩn (W30, W32 và các chỗ kéo theo)

Áp cho `Meta.permissions` (Admin), ma trận `/permissions/` (`registry.py`), "Tài khoản của tôi" (`auth/services.py`) và nhãn Nhật ký (`auditModel.ts`). `AuditLog.action` không đổi.

| # | Codename / action | Chuẩn | Đang dùng |
|---|---|---|---|
| P1 | `confirm_payment_manual` (quyền + Nhật ký) | Xác nhận đã nhận tiền | Meta và Nhật ký "Xác nhận thanh toán thủ công" (W30) |
| P2 | `publish_batch` | Mở bán lô | Meta "Publish lô ra Shop" (W32) |
| P3 | `cancel_expired_batch` | Huỷ lô quá hạn (ghi lỗ) | Nhật ký "Huỷ lô hết hạn"; Meta "(hạch toán lỗ)" |
| P4 | `approve_returntostock` | Duyệt hàng hoàn | Meta, ma trận "Duyệt hàng hoàn về kho"; Nhật ký "Duyệt phiếu trả về kho" |
| P5 | `return_to_warehouse` / `cancel_returntostock` | Mang hàng về kho / Huỷ phiếu hàng hoàn | Nhật ký "Trả hàng về kho" / "Huỷ phiếu trả về kho"; dòng thời gian "Huỷ phiếu hàng về kho" |
| P6 | `issue_credit_note` | Lập phiếu trừ doanh thu (theo Q-1) | Nhật ký "Lập hoá đơn điều chỉnh"; dòng thời gian "Lập chứng từ đảo doanh thu" |
| P7 | `create_refund` / `retry_refund` | Lập phiếu hoàn tiền / Thử hoàn tiền lại | "Lập phiếu hoàn", "Tạo phiếu hoàn tiền" / "Thử hoàn lại" |
| P8 | `return_batch_to_supplier` | Trả nhà cung cấp | Nhật ký "Trả lô về nhà cung cấp" |
| P9 | `assign_deliverynote` | Chọn người giao | Meta, ma trận "Giao phiếu cho người giao"; Tài khoản "Giao hoặc đổi người giao của phiếu giao"; Nhật ký "Gán phiếu giao" |
| P10 | `pack_deliverynote` | Soạn hàng | Meta "Đóng gói phiếu giao"; ma trận "Soạn hàng, in tem" |
| P11 | `delivery_confirm_skipped` / `delivery_extended` | Bỏ qua gọi xác nhận / Gia hạn gọi | Nhật ký "Bỏ qua bước gọi xác nhận" / "Gia hạn giao" |
| P12 | `view_profitreport` / `view_dashboard` | Xem báo cáo lãi lỗ / Xem Tổng quan | Meta "Xem báo cáo giá vốn / lãi lỗ" / "Xem Tổng quan vận hành" |
| P13 | `change_item_image` / `content.publish_entry` | Sửa ảnh mặt hàng / Đăng bài lên Shop | Meta "Thêm / thay / gỡ ảnh mặt hàng"; Tài khoản "Đăng bài viết và trang" |

### 4.4 Câu hỏi cần Duy chọn

| Mã | Câu hỏi | Phương án | PO đề xuất |
|---|---|---|---|
| Q-1 | Tên chứng từ `SalesCreditNote` (C2, P6) | (a) **Phiếu trừ doanh thu** · (b) giữ "Chứng từ đảo doanh thu" như spec BR-HT-10 · (c) "Phiếu giảm trừ doanh thu" | (a). Trùng chữ báo cáo, Lộc dễ hiểu. Chọn (a) hoặc (c) thì BA sửa chữ trong spec BR-HT-06/10. Chỉ đổi tên, nội dung quyết định 30/09 giữ nguyên |
| Q-2 | Đơn hết giờ giữ chỗ hiện thế nào ở ERP (T2) | (a) chip riêng **"Hết giờ giữ chỗ"** (xám) · (b) chip chung "Đã huỷ", cột lý do ghi "Hết giờ giữ chỗ" như hiện nay | (a). Một chữ ở chip, lý do, Nhật ký và Admin. Lọc "Đã huỷ" vẫn gộp được cả hai. Shop ghi "Đã huỷ vì quá giờ thanh toán" (cả hai phương án) |
| Q-3 | Tên menu và màn của C1 | (a) **"Hàng hoàn"** · (b) giữ "Hàng hoàn về kho" | (a). Menu nằm trong nhóm "Kho & lô" nên chữ "về kho" thừa |
| Q-4 | Phiếu giao COMPLETED (T28) | (a) **"Đã giao"** · (b) giữ "Hoàn tất" | (a). "Hoàn tất" đang dùng cho đơn, phiếu giao và việc gọi. W37 (đơn sang Hoàn tất) đang chạy luồng đầy đủ, nên tách chữ ngay để tránh lẫn |
| Q-5 | Vai trò trang `terms` (T55) | (a) **"Điều kiện giao dịch chung"** (tên trong Luật TMĐT 2025, NĐ 248) · (b) "Điều khoản mua hàng" (thân thiện) | (a) cho nhãn vai trò ở ERP, để Chủ đối chiếu checklist pháp lý mục 3. Tiêu đề trang khách đọc do người viết đặt, không phụ thuộc nhãn này |

Các nhãn còn lại PO tự chọn theo nguyên tắc. Duy chỉ cần nói "duyệt mục 4" và trả lời Q-1 đến Q-5. Nếu muốn sửa dòng nào thì ghi mã dòng (C, T, P).

### 4.5 Ngoài bảng này

- Phần AI (W26–W28, W31, W36, W39, giá trị `ai` của `actor_kind` và `Entry.source`): lô dọn chữ AI đang làm.
- W1 và W2 cũng nằm trong lô dọn chữ AI. Nếu Duy duyệt mục 4 trước khi lô đó xong thì lô dùng chữ T2 và T24–T30. Nếu chưa thì lô dùng tạm đề xuất ở "Top 10" và sửa lại theo bảng này sau.
- Lỗi cách vẽ, không phải chọn tên (W11 dò nhầm bảng, W34 và W35 code chết, W38 thanh bước, W41 chưa có màn): giữ cho lô sửa nhãn. Riêng W11 phải sửa cách dịch theo `model_name`, nếu không thì đổi chữ cũng không hết sai.
- W37 (đơn không sang Hoàn tất): đang chạy luồng đầy đủ BA → PO → Tech Lead.
- Cách áp dụng sau khi Duy duyệt: một lô NHANH. BE sửa nhãn `choices`, `verbose_name` và `Meta.permissions` (migration chỉ đổi metadata). ERP gom về `enums.ts`, xoá 6 bản chép (mục 2.10, khuyến nghị chung). Shop dùng `*_label` của BE hoặc bảng nhãn khách riêng. QA kiểm bằng cách so từng dòng C, T, P với màn thật.
