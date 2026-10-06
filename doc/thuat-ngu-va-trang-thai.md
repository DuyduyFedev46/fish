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
