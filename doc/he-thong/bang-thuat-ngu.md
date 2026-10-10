# Bảng thuật ngữ

> Cập nhật 11/10/2026. Tên chuẩn chứng từ và trạng thái (Duy duyệt 07/10): `doc/thuat-ngu-va-trang-thai.md` mục 2–4; khi lệch thì file đó đúng.
> Quy tắc đặt tên đầy đủ: skill `caveve-domain` mục "Đặt tên" và `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1.
> Kiểm bằng máy: `python3 scripts/check_naming.py`.

## Người và vai

| Tiếng Việt | Trong code | Ghi chú |
|---|---|---|
| Chủ (Lộc) | Group `owner` | Toàn quyền, giữ việc đụng tiền và giá vốn |
| Quản lý | Group `manager` | |
| Nhân viên kho (NV kho) | Group `warehouse_staff` | |
| Nhân viên giao (NV giao) | Group `delivery_staff` | |
| Nhân viên gọi xác nhận | Group `customer_service` | Gọi xác nhận đơn. Nhãn cũ "CSKH" đổi ngày 08/10, mã nhóm giữ nguyên |
| Người giao trên một phiếu | `courier` / `DeliveryNote.assigned_to` | |
| Hệ thống | `actor=None`, `actor_kind="system"` | Job, signal |
| AI | `actor_kind="ai"`, `AiAction` | |
| Khách | `Customer` | Không phải `User`, không đăng nhập |
| Nhân viên | `User` + `StaffProfile` | |

## Hàng, giá, mua

| Tiếng Việt | Trong code |
|---|---|
| Mặt hàng | `Item` |
| Nhóm hàng | `ItemGroup` |
| Combo | `Item` có `item_type = BUNDLE` + `BundleLine` (công thức thành phần). Mặt hàng thường là `SIMPLE` |
| Bảng giá / giá niêm yết | `PriceList` / `ItemPrice` |
| Ưu đãi | `PricingRule` |
| Mã giảm giá | Voucher (quyết định 10/10; model và API thêm ở Shop lô 3b, 02b §3.8–3.9, §4). Khác `PricingRule` |
| Ảnh mặt hàng | `ItemImage` |
| Nhà cung cấp (NCC) | `Supplier` |
| Phiếu nhập (mua tại cảng) | `PurchaseReceipt`, `PurchaseReceiptLine` |
| Nhập lô | `receive_batches` (route `purchasing/receipts/receive-batches/`) |
| Hoá đơn mua | `PurchaseInvoice` |
| Chi phí phụ, chi phí mua | `PurchaseCost`, phân bổ `PurchaseCostAllocation` |
| Giá vốn lô (đã gồm chi phí phụ) | `Batch.landed_unit_cost` (landed cost) |
| Giá mua | `Batch.purchase_rate`, `PurchaseReceiptLine.rate` |
| Trả nhà cung cấp | `BatchSupplierReturn`, action `return-to-supplier` |

## Kho

| Tiếng Việt | Trong code |
|---|---|
| Lô | `Batch` |
| Mở bán lô | `publish_batch` (`DRAFT` → `SELLING`) |
| Chốt lô | `close_batch` (`CLOSED`) |
| Cận hạn / quá hạn | `NEAR_EXPIRY` / `EXPIRED` |
| Huỷ lô quá hạn | `cancel_expired_batch`, action `cancel-expired` |
| Hết hạn trước xuất trước | FEFO, `sellable_batches` |
| Kho | `Warehouse` |
| Sổ kho (thẻ kho) | `StockLedgerEntry` (append-only) |
| Phiếu điều chỉnh kho | `StockEntry` |
| Kiểm kê | `StockReconciliation`, `StockReconciliationLine` |
| Hao hụt | chênh lệch âm khi kiểm kê |
| Hàng hoàn về kho | `ReturnToStock` |
| Tái nhập / huỷ bỏ (hàng hoàn) | `RESTOCK` / `WRITE_OFF` |
| Chuỗi lạnh | `COLD_CHAIN_MAX_HOURS` |

## Bán, tiền

| Tiếng Việt | Trong code |
|---|---|
| Đơn hàng | `SalesOrder`, `SalesOrderLine` |
| Giữ chỗ | trạng thái `BOOKED`, TTL `SALES_ORDER_TTL_MINUTES` |
| Hết giờ giữ chỗ | `AUTO_CANCELLED`, job `cancel_expired_orders` |
| Phân bổ lô của dòng đơn | `SalesOrderLineBatch` |
| Hoá đơn bán | `SalesInvoice`, `SalesInvoiceLine`, `SalesInvoiceLineBatch` |
| Giao dịch thanh toán | `PaymentTransaction` |
| Hàng chờ thanh toán lệch | `PaymentTransaction.match_status` ≠ `MATCHED`, action `resolve` |
| Thiếu tiền / tiền mồ côi / không khớp / chuyển thừa | `UNDERPAID` / `ORPHAN` / `UNMATCHED` / `OVERPAID` |
| Xác nhận thanh toán tay | `confirm_payment_manual`, action `confirm-payment` |
| Huỷ đơn đã thanh toán | `cancel_paid_order` |
| Phiếu hoàn tiền | `Refund` (`PENDING` → `REFUNDED` / `FAILED`) |
| Phiếu trừ doanh thu | `SalesCreditNote`, `SalesCreditNoteLine` |
| Cổng thanh toán | SePay, `checkout`, IPN (`/ipn/sepay` ở adapter) |
| Mã giao dịch ngân hàng | `bank_txn_id` (mã FT...) |
| Đồng ý xử lý dữ liệu | `PRIVACY_CONSENT_REQUIRED`, quyền `view_privacy_consent` |

## Giao hàng

| Tiếng Việt | Trong code |
|---|---|
| Phiếu giao | `DeliveryNote` |
| Chờ xác nhận / soạn hàng / chờ lấy hàng / đang giao / hoàn tất / giao thất bại / huỷ theo đơn | `CONFIRMING` / `PREPARING` / `READY` / `DELIVERING` / `COMPLETED` / `FAILED` / `CANCELLED` |
| Gọi xác nhận đơn | `confirmation` (module `delivery/confirmation`, route `/api/confirmation/`) |
| Việc gọi | `ConfirmationTask` |
| Một cuộc gọi | `CustomerCall` |
| Đổi thông tin nhận hàng | `change_recipient`, action `recipient` |
| Đóng gói | `pack_deliverynote` |
| In tem | `print_label`, `LabelPrint` |

## Báo cáo, hệ thống

| Tiếng Việt | Trong code |
|---|---|
| Lãi lỗ theo lô / theo kỳ | `reports/batch/{id}/` / `reports/period/` (`pnl`) |
| Bảng điều hành (Tổng quan) | `dashboard/summary/`, quyền `view_dashboard` |
| Xem giá vốn | `view_costprice` |
| Xem lãi lỗ | `view_profitreport` |
| Nhật ký hoạt động | `AuditLog`, route `audit-logs/` |
| Tiếp theo · Đã làm | `guidance` |
| Bài viết / trang / chuyên mục | `Entry` (`kind` = `post` / `page`) / `Category` |
| Lệnh AI | `CommandSpec`, `ai/commands/` |
| Việc AI | `AiAction` |
| AI của tôi / Chính sách AI | `AiConfigVersion` / `AiPolicyVersion` |
| Nhóm lệnh AI: thu mua / bán hàng / gọi xác nhận | `purchasing` / `sales` / `customer_service` |
| Mức nhạy cảm: cao / trung bình / thấp | `high` / `medium` / `low` |
| Giờ Việt Nam | `todayInVietnam()` (TS), `TIME_ZONE = "Asia/Ho_Chi_Minh"` (Django) |
| Dữ liệu demo | `seed_demo`, `DemoRecord` |

## Tên giữ nguyên (không đổi sang tiếng Anh)

Migration đã chạy, giá trị `AuditLog.action` đã ghi, phiên bản cấu hình AI cũ, slug nội dung CMS (vd `cach-mua-hang`; URL Shop đã đổi sang tiếng Anh `/about/`, `/blog/`, `/pages/` ngày 11/10),
dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca` trong tên hạ tầng.
