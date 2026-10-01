# Làm lại giao diện ERP (máy tính) theo bộ thiết kế — Thiết kế kỹ thuật
> Tech Lead · 2026-10-01 · Trạng thái: **ĐÃ DUYỆT** (Duy trả lời §6 ngày 01/10/2026)
> Nguồn: `01-analysis.md` (ĐÃ DUYỆT 01/10, B1–B6 duyệt), `doc/design/erp/UI-RULES.md`, `doc/design/erp/enum-map.md`,
> 105 board `doc/design/erp/screens/*.dc.html`. Code đọc trên `main` ngày 01/10. `02-stories.md` (mã `ED-xx`) viết song song,
> nên lô ở §5 gọi theo màn/đối tượng, điều phối viên tự ghép mã story.
> Mọi dữ liệu trong JSON mẫu là **giả** (`Khách Thử A`, `0900000123`, `[Địa chỉ giao]`).

## Mục lục
0. Tóm tắt quyết định · 0b. Mặc định 🟡 · 0c. Chỗ thiết kế lệch code (code thắng về dữ liệu)
1. Bản đồ màn
2. Khối FE dùng chung (làm trước)
3. Thay đổi backend (B1–B6, số điện thoại, API đọc bổ sung R1–R16)
4. Rủi ro và cơ chế chặn
5. Lô
6. Câu hỏi kỹ thuật 🔴
7. Review (Việc 3, để trống)

---

## 0. Tóm tắt quyết định

| # | Quyết định | Căn cứ |
|---|---|---|
| 1 | Chi tiết là **trang riêng**, route dạng `/<danh-sách>/detail/?id=<pk>` (static export, không route động). Query chỉ chứa id số hoặc mã nhóm, **không** chứa SĐT/tên. | 01 §3.8, skill nextjs (static export), bất biến 9 |
| 2 | Bỏ cột phải 3 cột (`RightRail`: Hoạt động + Trợ lý). AI nằm **trong trang**: thanh AI trên danh sách, khối "Trợ lý AI" trên trang chi tiết. Bỏ menu và trang **"Việc AI"** (`/ai/actions/`). | 01 §3.7 |
| 3 | Menu dựng từ **một bảng cấu hình theo quyền** (`shared/lib/nav.ts`), 6 nhóm theo UI-RULES §2.1. Mục hiện theo `me.permissions`. Giữ đúng 2 ngoại lệ đã nghiệm thu: ẩn mục đơn/giao với người **chỉ** thuộc `nv_giao` (S7-AC2), và "Việc giao của tôi" theo nhóm `nv_giao` (người nhận phiếu là thành viên nhóm, xem B6). | UI-RULES §8.1 |
| 4 | Nhãn và màu trạng thái lấy từ **một file** `shared/lib/enums.ts`, chép đúng cột "Nhãn dùng trên artboard" của `enum-map.md`. Không component nào tự viết nhãn trạng thái. | 01 §3.1, §3.12 |
| 5 | "Xem khách hàng" là quyền **Tầng 2 mới `sales.view_customer_list`**. Không dùng lại `sales.view_customer` vì quyền Tầng 1 này đang được cấp cho `nv_kho` và `nv_giao` (phạm vi dòng), và test S5 đang dựa vào nó. | 01 §3.13, B2 |
| 6 | Số điện thoại: ERP hiển thị **đủ** ở mọi chỗ API đã trả số (API chỉ trả cho người trong phạm vi). FE bỏ mọi chỗ tự cắt `…1234`. Giữ dạng che ở **tem in**, dòng CSKH **ngoài phạm vi**, và mọi đầu vào/đầu ra AI. | 01 §3.14, §3.7 dưới |
| 7 | Mốc trạng thái "Tiếp theo / Đã làm" + dòng thời gian: dùng `GET /api/guidance/<loại>/<id>/` sẵn có cho `order`, `payment`, `refund`, `batch`. Đối tượng khác thêm **provider chỉ có dòng thời gian** (R2). Câu "Tiếp theo" của các đối tượng này là bảng tĩnh theo trạng thái ở FE. | §3.8 R2 |
| 8 | Cột/trường tiền nhạy cảm mới đặt tên **trùng khoá có trong `COST_KEYS`** (`cogs`, `gross_profit`) hoặc thêm khoá mới vào `COST_KEYS` cùng lô. Serializer khai `sensitive_fields`. | Bất biến 1 |
| 9 | Mọi path mới có `/` cuối. Lỗi nghiệp vụ trả `{"detail", "code"}` qua `BusinessError`. Danh sách mới dùng `StandardPagination` (20 dòng, `?page=`). | Quy ước 02b trước |
| 10 | Migration **chỉ thêm**: 2 field + 1 quyền ở `delivery`, 1 quyền ở `sales`, 1 field ở `inventory`. Quyền Group cấp bằng data migration **trong app sở hữu quyền** (mẫu `sales/0010`), không thêm vào `accounts/migrations`, để các lô chạy song song không đụng số migration. | Bất biến 8 |

## 0b. Mặc định 🟡 đã áp (Duy lật được)

| # | Câu hỏi | Chọn | Hệ quả |
|---|---|---|---|
| 🟡 T1 | Tem in có hiện đủ SĐT? | **Giữ che** (`recipient_phone_masked`). Tem là giấy dán lên kiện hàng, đi ra ngoài vựa; quyết định 14 nói về màn ERP. Người giao gọi khách bằng nút "Gọi khách" trên màn Việc giao của tôi (số đủ). | Board W2e vẽ `…0412`: giữ nguyên. |
| 🟡 T2 | Bảng thao tác "…" của các đối tượng chưa có `available_actions` ở BE | FE suy ra từ trạng thái + `me.permissions` (bảng tĩnh trong `features/<x>/labels.ts`). BE vẫn chặn thật. | Không thêm field BE. |
| 🟡 T3 | Nút đổi sáng/tối | **Bỏ khỏi topbar** (thiết kế chỉ có tìm + avatar). Vẫn theo cài đặt máy qua `themeScript.ts`. | `ThemeToggle.tsx` xoá ở Lô 17. |
| 🟡 T4 | Điện thoại / màn < 1024 px | **Không thiết kế lại** (chưa duyệt). Giữ hành vi hiện có: menu trái thành ngăn kéo, menu đáy ≤ 5 mục. Nhân viên giao vẫn dùng được trên điện thoại. | Lô 1 không xoá menu đáy. |
| 🟡 T5 | Ô tìm ⌘K | Lô 1: nhảy tới **mục menu**. Lô 17: thêm nhảy theo **mã chứng từ khớp đúng** (`SO…`, `INV…`, `GH-…`, mã lô, `PR-n`, `KK-n`, `RT-n`). Không tìm theo tên/SĐT khách. | Chống dò dữ liệu khách. |
| 🟡 T6 | "Giao cho người giao" (B6) cho phiếu ở trạng thái nào? | `CONFIRMING`, `PREPARING`, `READY`. **Không** cho `DELIVERING`/`FAILED` (hàng đang trên xe của người cũ). | §3 B6 |
| 🟡 T7 | Số trên nhãn "Đang giao n phiếu" (F2o) | Số phiếu `DELIVERING` của người đó; trả kèm số `READY` đã gán. | §3 B6 |
| 🟡 T8 | B1: ai được sửa số đếm? | Ai có `change_stockreconciliation` khi phiếu `DRAFT`. **Người đã nhập hoặc sửa số đếm không được duyệt phiếu đó** (mở rộng BR-KK-02, đề xuất mã **BR-KK-08**). | §3 B1 |
| 🟡 T9 | Danh sách quyền "Chỉ Chủ" trong ma trận (B4) | Đúng các ô ❌ ở spec §1.5 + `ai.manage_ai_policy` + sửa giá bán/ưu đãi (spec §1.4: chỉ `chu` có CRU `ItemPrice`, `PricingRule`). | §3 B4 |
| 🟡 T10 | `Việc AI` bị bỏ thì việc AI `ESCALATED` cho nhóm xem ở đâu? | Thanh AI và khối Trợ lý AI của đúng trang chứng từ (lọc `target_model/target_id`, R1) + dòng "đề xuất AI chờ duyệt" ở Tổng quan. | §3 R1 |

## 0c. Chỗ thiết kế lệch code — code thắng về dữ liệu (01 §4)

| Board | Thiết kế vẽ | Code thật | Cách làm |
|---|---|---|---|
| D1, D2 mock | mã `DH-240924-011` | `SO<yymmdd>-<6 HEX>` | Dùng mã thật; dọn mã `DH-` khỏi `mock.ts` khi sửa màn. |
| W2c, F1f | cột/trường "Kho" của phiếu kiểm kê | `StockReconciliation` **không có** kho | List trả `warehouse_names` suy từ lô của các dòng (R8). Ô "Kho *" ở F1f chỉ là bộ lọc để nạp lô, không lưu. |
| W5k, F1j | "Điều chỉnh tồn" thay đổi tồn | `StockEntry` POST **chỉ lưu một dòng**, không đổi `qty_available`, không ghi sổ | **Điểm dừng D-1** (§6 Q1). Lô 7 chỉ làm tab danh sách đọc. |
| W2f | nút chính "Ngừng bán lô" | Không có action, `Batch.Status` không có trạng thái tạm ngừng | **Không làm** nút này; §6 Q2. |
| W2h | "Giá vốn ước tính / combo" | Không có API | Bỏ trường. Không tự tính giá vốn ở FE. |
| W2h, W5o | "Người đặt" giá | `ItemPrice` không lưu người đặt | Bỏ cột (enum-map đã ghi). |
| W3g | "Ngày đi làm 25", "Giao thất bại 2" trong tháng | Không có dữ liệu chấm công; thất bại không gắn người | Chỉ hiện "Phiếu đã giao" (đếm `COMPLETED` theo `assigned_to`). |
| W3i | "Phạm vi dữ liệu" bật/tắt | Tầng 3 viết trong code (`get_queryset`) | **Chỉ đọc**: BE trả mô tả cố định theo nhóm (B4). |
| F2o | "Tuyến Quận 7" | Không có field tuyến | Bỏ dòng. |
| F2l | ô "Mang hàng về kho" | Tạo hàng hoàn là chứng từ riêng (F2m) | Tick ô → sau khi báo thất bại thành công, mở F2m điền sẵn phiếu giao. |
| D2b | câu "Dữ liệu cá nhân chỉ hiện đủ trên trang khách…" | — | Bỏ câu (UI-RULES §3.3). Link "Mở trang khách" chỉ hiện khi có `view_customer_list`. |
| Guidance | `why.br` mang mã BR | UI cấm mã luật | FE **không** render `why.br`. |
| `enum-map.md` dòng `mark_failed` | "bỏ trường Lý do" | B5 thêm lý do (Duy duyệt 01/10) | Điều phối viên sửa dòng này trong `enum-map.md` khi Lô 4 xong. |
| 01 §4 | `doc/design/erp/README.md` | File không có trong repo | Bản đồ màn ở §1 thay thế. |
| `CAPABILITY_LABELS` (BE) | "Tạo phiếu hoàn", "Xác nhận thanh toán thủ công" | Vi phạm bảng "một việc một tên" | Đổi nhãn thành "Lập phiếu hoàn", "Xác nhận đã nhận tiền" (Lô 14). |
| `shared/lib/format.ts` | `dd/mm/yyyy hh:mm`, tiền "đ" | `dateTime` bỏ năm, `vnd` dùng "₫" | Sửa ở Lô 1 (§2.6). Chuỗi do BE dựng (vd nhãn chứng từ đảo) giữ nguyên. |

---

## 1. Bản đồ màn

Ký hiệu trạng thái: **SẴN** = CÓ SẴN, chỉ sửa giao diện · **MỘT PHẦN** = CÓ MỘT PHẦN · **MỚI**.
Cột API: ⚠ = thiếu, xem mục ở §3. Board `F*` nằm cùng dòng với trang cha (popup trên trang đó, hoặc trang form riêng nếu ghi "trang").
Component mới đặt trong `features/<module>/components/`; page mỏng trong `app/(console)/<route>/page.tsx` bọc `<ViewGuard>`.

| Board | Route · component | Trạng thái | API (⚠ = thiếu) |
|---|---|---|---|
| **Khung** W6a/W6b/W6c (trống, không thấy, đang tải) | mọi danh sách · `shared/ui/list/*` | MỘT PHẦN | — |
| W6d Mất mạng · W6e Lưu thất bại · W6f Xung đột · W6i Thông báo | `shared/ui/states/*`, `shared/ui/overlay/Toast*` | MỘT PHẦN | W6f: `409`/`STALE_STATE` (B1, giao hàng, CSKH) |
| W6g 404 · W6h Lỗi chung | `app/not-found.tsx` (vẽ trong shell khi đã đăng nhập) · `app/(console)/error.tsx` | MỘT PHẦN | — |
| **Tổng quan** D1 | `/overview/` · `features/overview/components/OverviewScreen.tsx` | SẴN | `GET /api/dashboard/summary/`, `/api/dashboard/attention/`; đếm đề xuất AI theo màn ⚠R1 |
| **Bán hàng** D2 Đơn & tiền (tab Đơn hàng) | `/orders/` · `features/orders/components/OrdersScreen.tsx` | SẴN | `GET /api/sales/orders/` ⚠R3 (`reason`); ⚠R1 |
| D2b Chi tiết đơn · D2c (bảng thao tác theo trạng thái) · F2a Xác nhận đã nhận tiền · F2b Huỷ đơn · F2c Lập phiếu hoàn · F2e Xác nhận đơn đã đủ tiền · nút "Giao cho người giao" (W6i) | `/orders/detail/?id=` · `OrderDetailView.tsx` chuyển từ tấm trượt thành trang; form có sẵn `ConfirmPaymentForm`, `CancelOrderForm`, `RefundForm`, `ConfirmOrderForm` thành Modal | MỘT PHẦN | `GET /api/sales/orders/{id}/`, `GET /api/guidance/order/{id}/`, `POST …/confirm-payment`, `POST …/cancel/`, `POST /api/sales/refunds/create/`, `POST /api/sales/payments/{id}/resolve`; popup lô/mặt hàng/phiếu giao qua `shared/lib/lookups.ts`; giao người ⚠B6; ⚠R1 |
| W1a Hàng chờ thanh toán (tab) | `/orders/payments/` · `PaymentQueueScreen.tsx` | SẴN | `GET /api/sales/payments/?resolution_status=OPEN`; ⚠R1 |
| W1a2 Chi tiết khoản tiền · F2d Gắn khoản tiền vào đơn | `/orders/payments/detail/?id=` · `PaymentView.tsx`, `AttachOrderForm.tsx` | MỘT PHẦN | `GET /api/sales/payments/{id}/`, `/api/guidance/payment/{id}/`, `POST …/resolve`, `GET /api/sales/orders/?status=BOOKED&q=`; ⚠R1 |
| W1b Phiếu hoàn chờ chuyển (tab) | `/orders/refunds/` · `RefundQueueScreen.tsx` | SẴN | `GET /api/sales/refunds/`; dòng tổng theo tháng ⚠R3 (lọc `month`) |
| W1b2 Chi tiết phiếu hoàn · F2f Xác nhận đã hoàn tiền · F2g Báo chuyển thất bại | `/orders/refunds/detail/?id=` · `RefundView.tsx`, `ConfirmRefundForm`, `MarkRefundFailedForm`, `RetryRefundForm` | MỘT PHẦN | `GET /api/sales/refunds/{id}/`, `/api/guidance/refund/{id}/`, `POST …/confirm/`, `…/mark-failed/`, `…/retry/` |
| W5a Khách hàng | `/customers/` · **mới** `features/customers/components/CustomerListScreen.tsx` | MỚI | ⚠B2 `GET /api/sales/customer-directory/` |
| W5b Chi tiết khách hàng (**không** khối AI) | `/customers/detail/?id=` · `CustomerDetailScreen.tsx` | MỚI | ⚠B2 `GET/PATCH /api/sales/customer-directory/{id}/`; dòng thời gian ⚠R2 `customer` |
| W1c Gọi xác nhận · F2h Ghi kết quả gọi · F2i Hẹn gọi lại · F2j Đổi người nhận / địa chỉ | `/cskh/` · `features/cskh/CskhQueueView.tsx`, `CskhCallModal.tsx` | SẴN | `GET /api/cskh/queue/`, `POST …/claim/`, `…/calls/`, `…/recipient/`, `…/unconfirm/`, `POST /api/cskh/search/`; ⚠R1 |
| W1c2 Chi tiết gọi xác nhận · F2k Quyết định đơn chưa xác nhận | `/cskh/detail/?id=<note_id>` · **mới** `features/cskh/CskhDetailScreen.tsx` | MỘT PHẦN | `GET /api/cskh/queue/{id}/`, `POST …/decide/`; lịch sử cuộc gọi: `calls` đã có trong retrieve; ⚠R2 `delivery`; ⚠R1 |
| W1d Giao hàng | `/deliveries/` · `features/deliveries/components/DeliveriesView.tsx` | SẴN | `GET /api/delivery/notes/?status=`; ⚠R1 |
| W1d2 Chi tiết phiếu giao · F2o Giao cho người giao | `/deliveries/detail/?id=` · `DeliveryDetailModal.tsx` → `DeliveryDetailScreen.tsx` | MỘT PHẦN | `GET /api/delivery/notes/{id}/` ⚠R4 (`phone`, `assigned_to_name`), `POST …/status/`, `…/label/print/`, `…/label/void/`; ⚠B6 `GET /api/delivery/deliverers/`, `POST …/assign/`; ⚠R2 `delivery`; ⚠R1 |
| W2e In tem giao hàng | `/print/label/?note=&print_no=` · `app/print/label/page.tsx` | SẴN | `GET …/label/` (SĐT giữ che, 🟡 T1) |
| W1e Việc giao của tôi · F2l Báo giao thất bại · (mở F2m) | `/my-deliveries/` · **mới** `features/deliveries/components/MyDeliveriesScreen.tsx` | MỚI (đang Placeholder) | `GET /api/delivery/notes/?assigned_to=me&status=…` ⚠R4; `POST …/status/` ⚠B5; `POST /api/inventory/returns/` ⚠R9 |
| **Hàng hoá & kho** W2a Mua hàng (tab Phiếu nhập; tab Hoá đơn mua / Chi phí mua dùng lại component của W5g/W5g2) | `/purchasing/?tab=receipts\|invoices\|costs` · `PurchasingScreen.tsx` | MỘT PHẦN | `GET /api/purchasing/receipts/` ⚠R10; ⚠R1 |
| F1a Nhập lô tại cảng (trang) | `/purchasing/new/` · `NhapLoForm.tsx` | SẴN | `POST /api/purchasing/receipts/nhap-lo/`; "Lưu nháp" giữ `draftStorage` (không có dữ liệu khách) |
| W2b Chi tiết phiếu nhập · F1c Thêm hoá đơn mua · F1d Thêm chi phí phụ (trang) | `/purchasing/detail/?id=` · **mới** `ReceiptDetailScreen.tsx`; `/purchasing/costs/new/?receipt=` · **mới** `features/accounting/components/PurchaseCostForm.tsx` | MỚI | `GET /api/purchasing/receipts/{id}/` ⚠R10, `PATCH`, `POST …/submit/`, `…/cancel/`; `POST /api/purchasing/invoices/`; `POST /api/purchasing/costs/` (chỉ Chủ); ⚠R2 `receipt`; ⚠R1 |
| W5c Nhà cung cấp · F1b Thêm nhà cung cấp | `/suppliers/` · **mới** `features/suppliers/components/SupplierListScreen.tsx` | MỚI | ⚠B3 `GET /api/purchasing/suppliers/`, `POST` |
| W5d Chi tiết nhà cung cấp | `/suppliers/detail/?id=` · `SupplierDetailScreen.tsx` | MỚI | ⚠B3 `GET/PATCH …/suppliers/{id}/`; `GET receipts/?supplier=` ⚠R10; `GET batches/?supplier=&has_stock=1` ⚠R5; ⚠R2 `supplier` |
| D3 Kho & lô (tab Tồn theo lô) · F1e Mở bán lô | `/inventory/?tab=batches` · `InventoryScreen.tsx` | MỘT PHẦN (đang đọc tạm `dashboard/summary`) | `GET /api/inventory/batches/` ⚠R5; "Nhập xuất gần đây" `GET /api/inventory/ledger/` ⚠R6; `POST …/publish/`; ⚠R1 |
| W2f Chi tiết lô · F1g Trả nhà cung cấp · F1h Huỷ phần tồn, ghi lỗ · F1i Chốt lô · (F1m mở trang ưu đãi) | `/inventory/detail/?id=` · `BatchDetailSheet.tsx` → `BatchDetailScreen.tsx` | MỘT PHẦN | `GET /api/inventory/batches/{id}/` ⚠R5 (`receipt`), `/api/guidance/batch/{id}/`, `GET ledger/?batch=` ⚠R6, `GET /api/sales/orders/?batch=` ⚠R3, `POST …/return-to-supplier/`, `…/cancel-expired/`, `…/close/`; lãi lỗ trong F1i `GET /api/reports/batch/{batch_id}/` (chỉ `view_profitreport`); "Ngừng bán lô" ⚠ không có (§6 Q2); ⚠R1 |
| W5k Điều chỉnh tồn · F1j Điều chỉnh tồn | `/inventory/?tab=adjustments` · **mới** `StockEntryList.tsx` | MỚI | `GET /api/inventory/stock-entries/` ⚠R7b; **form F1j: điểm dừng D-1** |
| W5l Kho · F3m Thêm kho | `/inventory/?tab=warehouses` · **mới** `WarehouseList.tsx` | MỚI | `GET/POST /api/inventory/warehouses/` ⚠R7 |
| W5e Hàng hoàn về kho · F2m Nhập hàng hoàn về kho | `/returns/` · **mới** `features/returns/components/ReturnListScreen.tsx` | MỚI | `GET/POST /api/inventory/returns/` ⚠R9 |
| W5f Chi tiết hàng hoàn · F2n Duyệt hàng hoàn | `/returns/detail/?id=` · `ReturnDetailScreen.tsx` | MỚI | `GET /api/inventory/returns/{id}/` ⚠R9, `POST …/approve/`; ⚠R2 `return`; ⚠R1 |
| W2c Kiểm kê | `/stocktake/` · **mới** `features/stocktake/components/StocktakeListScreen.tsx` | MỚI (đang Placeholder) | `GET /api/inventory/reconciliations/` ⚠R8; ⚠R1 |
| F1f Nhập số kiểm kê (trang) | `/stocktake/new/`, `/stocktake/edit/?id=` · `StocktakeForm.tsx` | MỚI | ⚠B1 `POST /api/inventory/reconciliations/`, `POST …/{id}/lines/`; `GET batches/?warehouse=&has_stock=1` ⚠R5 |
| W2g Chi tiết phiếu kiểm kê · W6f Xung đột | `/stocktake/detail/?id=` · `StocktakeDetailScreen.tsx` | MỚI | `GET …/reconciliations/{id}/` ⚠B1/R8, `POST …/approve/`; ⚠R2 `stocktake`; ⚠R1 |
| W5i Sổ nhập xuất | `/ledger/` · **mới** `features/ledger/components/LedgerScreen.tsx` | MỚI | ⚠R6 `GET /api/inventory/ledger/` |
| W2d Danh mục & giá (tab Mặt hàng) | `/catalog/?tab=items` · `CatalogScreen.tsx` | MỘT PHẦN | `GET /api/catalog/items/` ⚠R14 (`current_price`); ⚠R1 |
| F1k Thêm mặt hàng (trang) | `/catalog/new/` · **mới** `ItemForm.tsx` | MỚI | `POST /api/catalog/items/`, `POST /api/catalog/bundle-lines/` (Tầng 1 `add_item`: chỉ Chủ) |
| W2h Chi tiết mặt hàng · F1l Đặt giá mới · F1n Ảnh mặt hàng | `/catalog/detail/?id=` · **mới** `ItemDetailScreen.tsx`; ảnh dùng lại `ImageUploadSheet.tsx` thành Modal | MỚI (ảnh SẴN) | `GET/PATCH /api/catalog/items/{id}/`, `GET item-prices/?item=` ⚠R14, `POST item-prices/`, `GET /api/inventory/batches/?item_code=&has_stock=1`, `POST/DELETE …/items/{id}/image/`; ⚠R2 `item`; ⚠R1 |
| W5o Bảng giá | `/catalog/?tab=prices` · **mới** `PriceList.tsx` | MỚI | `GET /api/catalog/item-prices/` ⚠R14, `GET price-lists/` |
| W5h Ưu đãi · F1m Tạo ưu đãi giảm giá (trang) | `/catalog/?tab=rules`, `/catalog/rules/new/?item=` · **mới** `PricingRuleList.tsx`, `PricingRuleForm.tsx` | MỚI | `GET/POST/PATCH /api/catalog/pricing-rules/` ⚠R14 |
| W5m Nhóm hàng · F1o Thêm nhóm hàng | `/catalog/?tab=groups` · **mới** `ItemGroupList.tsx` | MỚI | `GET/POST /api/catalog/item-groups/` ⚠R14 |
| **Kế toán** W3a Báo cáo lãi lỗ | `/reports/` · **mới** `features/reports/components/ProfitReportScreen.tsx` | MỚI (đang Placeholder) | `GET /api/reports/period/` ⚠R15, ⚠R15 `GET /api/reports/batches/`, `GET /api/reports/batch/{id}/` |
| W5j Hoá đơn bán | `/accounting/sales-invoices/` · **mới** `features/accounting/components/SalesInvoiceListScreen.tsx` | MỚI | ⚠R13 `GET /api/sales/invoices/` |
| W5g Hoá đơn mua · F1c Thêm hoá đơn mua | `/accounting/purchase-invoices/?tab=invoices` · **mới** `PurchaseInvoiceList.tsx`, `PurchaseInvoiceForm.tsx` | MỚI | `GET/POST/PATCH /api/purchasing/invoices/` ⚠R11 (🔴 Q3) |
| W5g2 Chi phí phụ · (F1d trang) | `/accounting/purchase-invoices/?tab=costs` · **mới** `PurchaseCostList.tsx` | MỚI | `GET/POST /api/purchasing/costs/` ⚠R12 |
| **Website** W3b Nội dung | `/content/` · `ContentListScreen.tsx` | SẴN | `/api/content/entries/`, `/golive-status/` |
| W3c Viết bài · F3i Trả về nháp · F3j Gỡ bài · F3k Kiểm tra trước khi đăng | `/content/edit/?id=` · `app/(console)/content/edit/page.tsx` | SẴN | `/api/content/entries/{id}/…` (submit, return, publish, unpublish, versions) |
| F3l Thiết lập bài viết (trang) | `/content/settings/?id=` · **mới** `features/content/components/EntrySettingsForm.tsx` | MỘT PHẦN (đang là khối trong trang viết) | `PATCH /api/content/entries/{id}/` |
| W3d Chuyên mục · F3h Thêm chuyên mục | `/content/categories/` · `CategoriesScreen.tsx` | SẴN | `/api/content/categories/` |
| **Quản trị** W3e Nhân sự · F3a Thêm nhân viên · F3b Tạo tài khoản nhóm Chủ | `/staff/` · `StaffScreen.tsx`, `StaffCreateForm.tsx` | SẴN | `GET/POST /api/staff/`; bảng "Nhóm quyền" ⚠B4 `GET /api/staff/groups/` |
| W3g Chi tiết nhân viên · F3c Sửa hồ sơ · F3d Đổi nhóm · F3e Đặt lại mật khẩu · F3f Cho nghỉ việc | `/staff/detail/?id=` · `StaffDetail.tsx` thành trang | MỘT PHẦN | `GET/PATCH /api/staff/{id}/`, `PUT …/groups/`, `POST …/deactivate/`, `…/reactivate/`, `…/reset-password/`; việc đang làm `GET delivery/notes/?assigned_to=<id>` ⚠R4; hoạt động `GET /api/audit-logs/?actor=<id>` ⚠R16; ⚠R2 `staff` |
| W3h Phân quyền | `/permissions/` · **mới** `features/permissions/components/PermissionMatrixScreen.tsx` | MỚI | ⚠B4 `GET /api/staff/groups/` |
| W3i Chi tiết nhóm quyền | `/permissions/detail/?group=<mã nhóm>` · `GroupDetailScreen.tsx` | MỚI | ⚠B4 `GET /api/staff/groups/{code}/`, `PUT …/capabilities/`; thêm người: `PUT /api/staff/{id}/groups/` |
| W3f Nhật ký hoạt động | `/audit-logs/` · `features/audit/components/AuditLogScreen.tsx` | SẴN | `GET /api/audit-logs/` ⚠R16 (`actor`) |
| W4c Chính sách AI | `/ai/policy/` · `AiPolicyScreen.tsx` | SẴN | `/api/ai/policy/…` |
| W4d Báo cáo AI | `/ai/report/` · `AiDailyReportScreen.tsx` | SẴN | `GET /api/ai/report/daily/` |
| **Menu avatar / ngoài shell** W4e Tài khoản của tôi · F3g Đổi mật khẩu | `/account/` · `AccountScreen.tsx`, `ChangePasswordForm.tsx` | SẴN | `/api/auth/me/`, `/api/auth/change-password/` |
| W4b AI của tôi | `/ai/settings/` · `MyConfigScreen.tsx` | SẴN | `/api/ai/my-config/…` |
| W4f Đăng nhập · W4g Đặt mật khẩu mới · W4h Không có quyền | `/login/`, `/set-password/`, `/no-role/` | SẴN | `/api/auth/token/`, `/api/auth/change-password/` |
| (bỏ) "Việc AI" | xoá `app/(console)/ai/actions/page.tsx` + mục menu; giữ `features/ai/actions/api.ts` cho khối AI | — | — |

---

## 2. Khối FE dùng chung (làm trước, Lô 1–2)

**Token:** chỉ dùng `erp-console/shared/ui/tokens.css` (bản chạy của `DESIGN.md`). Màu UI-RULES §9 đã khớp sẵn
(`--accent #1F66D1`, `--border #E4E4E9`, `--ink-2 #4E4E58`, `--ink-3 #686874`, `--canvas #FBFBFC`, tone chip `good/warn/crit/info/mute`).
Thêm đúng 2 token, ghi vào `DESIGN.md` trước: `--rail-left-w-collapsed: 60px`, `--action-bar-h: 64px`. Không hex/rgba ngoài `tokens.css`
(lệnh grep ở §5). Icon mới: thêm tên vào `scripts/subset-material-symbols.py` rồi chạy lại script.
Code nặng của AI không được vào chunk route nghiệp vụ (`scripts/check-ai-chunks.mjs`).

### 2.1 Khung (Lô 1)
| File | Việc | Thay / dùng lại |
|---|---|---|
| `shared/lib/nav.ts` | Viết lại `NAV`: `section` ∈ `"" \| "Bán hàng" \| "Hàng hoá & kho" \| "Kế toán" \| "Website" \| "Quản trị"`, thứ tự UI-RULES §2.1. Thêm `ViewKey`: `customers`, `suppliers`, `returns`, `ledger`, `sales-invoices`, `purchase-invoices`, `permissions`. Bỏ `ai-actions`; `payments`/`refunds` thành **tab** của Đơn & tiền (không còn mục menu); `content-categories` vào qua nút trong Nội dung; `ai-settings` vào menu avatar. Thêm `PERM.viewCustomerList`, `assignDelivery`, `viewSupplier`, `viewReturn`, `viewLedger`, `viewSalesInvoice`, `viewPurchaseInvoice`, `viewPurchaseCost`, `viewItemPrice`, `viewCostPrice`, `viewProfitReport`. Bỏ điều kiện tạm `viewDashboard` của Kho & lô ở Lô 7. | sửa file có sẵn |
| `shared/ui/shell/Shell.tsx` | Khung 2 cột: Sidebar + (Topbar + nội dung). Bỏ `RightRail`, `activity`, `assistant` props. | thay `shared/ui/Shell.tsx` |
| `shared/ui/shell/Sidebar.tsx` | 240 ↔ 60 px, nút thu gọn, tooltip khi thu gọn, nhớ trạng thái trong `localStorage` khoá `cave_ui_sidebar` (chỉ `"collapsed"\|"open"`). Mục đang chọn: khớp đường dẫn dài nhất (`navMatch`). | |
| `shared/ui/shell/Topbar.tsx` | Tên màn trái; ô tìm ⌘K + avatar phải. **Không** nút Làm mới, không đăng xuất rời. | |
| `shared/ui/shell/AvatarMenu.tsx` | Menu: Tài khoản của tôi · AI của tôi · Đăng xuất. Bàn phím: Enter/Space mở, Esc đóng, mũi tên di chuyển. | logout lấy từ `ConsoleGate` |
| `shared/ui/shell/CommandSearch.tsx` | ⌘K: lọc mục menu (🟡 T5). | |
| `features/auth/components/ConsoleGate.tsx`, `app/(console)/layout.tsx` | Bỏ ghép `ActivityFeed`/`AiAssistantGate` vào cột phải. | sửa |

### 2.2 Danh sách (Lô 1)
| File | Việc |
|---|---|
| `shared/ui/Tabs.tsx` | Tab dưới topbar, gạch dưới `--accent`, `role="tablist"`, đồng bộ `?tab=`, có số đếm tuỳ chọn ("Hàng chờ thanh toán 2"). |
| `shared/ui/list/ListPage.tsx` | Tiêu đề + nút tạo mới góc phải + `FilterBar` + `AiBar` + bảng + dòng "Đang hiện n / m". |
| `shared/ui/list/FilterBar.tsx` | Ô tìm, chọn trạng thái, chọn khoảng ngày. Không nút làm mới. |
| `shared/ui/list/DataTable.tsx` | Cột khai báo (`align`, `mono`, `num` = tabular-nums căn phải, `locked` = icon khoá ở tiêu đề); bấm dòng → `href` trang chi tiết; tự vẽ **skeleton** (W6c), **trống** (W6a: icon + tiêu đề + 1 câu), **không thấy** (W6b: "Không tìm thấy … khớp với <từ khoá>" + "Xoá tìm kiếm"). Thay `EmptyRow.tsx`, dùng lại `SkeletonTable` của `Skeleton.tsx`. |
| `shared/ui/Chip.tsx` + `shared/lib/enums.ts` | Chip một nhãn chuẩn, không chú thích. `enums.ts` khai mọi enum trong `enum-map.md`: `{ [value]: { label, tone } }` cho `SalesOrder.status`, `SalesInvoice.status`, `PaymentTransaction.match_status/resolution_status/resolution`, `Refund.status`, `DeliveryNote.status` (+ tem suy ra), `ConfirmTask.state`, `ConfirmCall.result`, `Batch.status`, `StockLedgerEntry.movement_type`, `StockEntry.purpose`, `StockReconciliation.status`, `ReturnToStock.status/decision`, `PurchaseReceipt.status`, `PurchaseCost.cost_type/allocation_method`, `PurchaseInvoice.is_paid`, `Supplier.supplier_type/is_active`, `Item.item_type/is_active`, `PricingRule.*`, `Entry.*`, `StaffProfile.status`, `AuditLog.actor_kind`, `AiAction.status`, `DeliveryNote.failure_reason` (B5). Thay `shared/ui/StatusChip.tsx`, `shared/lib/status.ts`, `features/orders/labels.ts` (phần nhãn), `STATUS_GROUP_TABS` trong `features/deliveries/types.ts`. |
| `shared/ui/AiBar.tsx` | Thanh mảnh "AI · Có n đề xuất: …  Xem" + `AiChip` "AI đề xuất" cho dòng. Nhận dữ liệu qua props (đếm do R1). Không import `features/ai`. |
| `shared/ui/states/OfflineBanner.tsx` + `shared/lib/useOnline.ts` | Banner "Mất kết nối. Đang thử lại…" + Thử lại; dữ liệu cũ mờ, ghi "Dữ liệu lúc dd/mm/yyyy hh:mm" (dùng mốc `asOf` của `useResource`/`usePagedList`). |
| `shared/ui/states/ErrorScreen.tsx`, `NotFoundScreen.tsx` (sửa), `NoPermission.tsx` | 404/lỗi chung nằm trong shell, nút "Về Tổng quan" / "Thử lại". `ViewGuard` vẽ `NoPermission`. |
| `shared/ui/overlay/Toast.tsx` + `ToastProvider` | Góc dưới phải; loại thành công/cảnh báo/lỗi; nút "Hoàn tác" tuỳ chọn; nút đóng; `aria-live="polite"`. Thay `shared/ui/Toast.tsx`. |
| `shared/lib/format.ts` | `dateTime` → `dd/mm/yyyy hh:mm` (thêm năm, `timeZone: "Asia/Ho_Chi_Minh"`); thêm `date` → `dd/mm/yyyy`; `vnd` → "540.000 đ"; thêm `money` (không đơn vị, cho ô bảng); `kg` dấu phẩy thập phân giữ; `remaining` → `mm:ss` cho đếm ngược. Sửa test/e2e đang khớp "₫" hoặc "dd/mm hh:mm". |
| `shared/ui/Toolbar.tsx` | Xoá nút "Làm mới" (UI-RULES §2.2). Màn cũ chuyển dần sang `FilterBar`. |

### 2.3 Trang chi tiết (Lô 2)
| File | Việc |
|---|---|
| `shared/ui/detail/DetailPage.tsx` | Lưới: cột trái (StatusPath, InfoGrid, bảng con) + cột phải (khe `aiSlot`, rồi Timeline). `aiSlot` bỏ trống → không vẽ khối AI (trang khách hàng). |
| `shared/ui/detail/DetailHeader.tsx` | "← tên danh sách" · tiêu đề (mã mono nếu là chứng từ) · Chip · nút chính · nút "…" (`MoreMenu`). Không dòng xám dưới tiêu đề. |
| `shared/ui/detail/MoreMenu.tsx` | Mục bị chặn mờ, `aria-disabled`, **lý do ngắn nằm cạnh** ("Chốt lô · Lô còn 18,5 kg."). |
| `shared/ui/detail/StatusPath.tsx` | Dải bước mũi tên: đã qua nền `--accent-soft` có ✓, hiện tại nền `--accent` chữ `--on-accent`, kết thúc xấu tone `crit`. Cùng khối: "→ Tiếp theo: …" trái, "Đã làm: ✓ … ✓ …" phải. Props: `steps[]`, `current`, `badEnd?`, `next`, `done[]`. Dữ liệu `next/done`: từ guidance (order/payment/refund/batch) hoặc bảng tĩnh `features/<x>/labels.ts`. |
| `shared/ui/detail/InfoGrid.tsx` + `InfoField.tsx` | Lưới 2 cột, nhãn nhỏ trên, giá trị dưới, **một giá trị mỗi ô**. Biến thể: `text`; `editable` (rê chuột hiện bút chì → sửa tại chỗ, Lưu/Huỷ, lỗi dưới ô); `locked` (icon khoá — giá vốn, trường khoá nghiệp vụ); `link` (mở `LookupCard`). |
| `shared/ui/detail/LookupCard.tsx` + `shared/lib/lookups.ts` | Popup thẻ nhanh (lô, mặt hàng, phiếu giao, đơn) có "Đóng" và "Mở trang …". `lookups.ts` chứa hàm đọc theo id (`GET batches/{id}/`, `items/{id}/`, `delivery/notes/{id}/`) với kiểu tối thiểu, để module không import chéo nhau. **Không** có thẻ khách hàng lấy từ API khách. |
| `shared/ui/detail/Timeline.tsx` | Mỗi dòng: thời gian (`dd/mm/yyyy hh:mm`) \| việc (+ người làm). Dữ liệu = `timeline` của guidance. Bỏ `why.br`. |
| `shared/ui/detail/AiBlockFrame.tsx` | Khung tĩnh của khối "Trợ lý AI": người/giờ đề xuất, việc, bảng trước → sau, Từ chối / Đồng ý, chip câu hỏi nhanh, ô chat + nút gửi. Chỉ vẽ, nhận props. |
| `features/ai/components/AiDocBlock.tsx` (+ cổng mỏng `AiDocBlockGate.tsx`) | Nạp `GET /api/ai/actions/?target_model=&target_id=&status=PENDING,ESCALATED` (R1), `POST …/confirm/`, `…/reject/`; ô chat nạp động `AiAssistantPanel` (`ssr:false`) **chỉ khi** `ai_enabled` và đã đồng ý, như `AiAssistantGate`. Page (`app/…/page.tsx`) ghép vào `aiSlot`; feature screen không import `features/ai`. |
| `shared/ui/states/ConflictBanner.tsx` | Banner vàng dưới header "Phiếu vừa được <tên> sửa lúc …. Tải lại để xem bản mới." + Tải lại. Bật khi API trả `409` hoặc `code=STALE_STATE` (kèm `updated_by_name`, `updated_at` nếu có). |

### 2.4 Popup và form (Lô 2)
| File | Việc | Thay |
|---|---|---|
| `shared/ui/overlay/Modal.tsx` | Hộp thoại nổi trên đúng trang mở ra nó, nền cha mờ (`--scrim`), giữ focus, Esc đóng (khoá khi đang gửi), trả focus. ≤ 6 trường + xác nhận. | `shared/ui/Sheet.tsx`, `SideSheet.tsx`, `features/inventory/components/ModalDialog.tsx` (xoá ở Lô 17 khi hết chỗ dùng) |
| `shared/ui/form/FormPage.tsx` | Form dài là trang, thanh nút cố định đáy (`--action-bar-h`), [phụ … chính] chính bên phải. | |
| `shared/ui/form/Field.tsx` | Nhãn trên ô, `*` đỏ khi bắt buộc, đơn vị trong ô (`kg`, `đ`, `ngày`), lỗi = viền `--crit` + 1 dòng dưới ô, `aria-describedby`. Ô số `inputMode="decimal"`. Không chữ gợi ý xám dưới ô. Mật khẩu vẫn dùng `PasswordInput`. | |
| `shared/ui/form/SummaryBlock.tsx` | Khối tóm tắt cặp nhãn–giá trị (đơn nào, còn hoàn được bao nhiêu). | `features/orders/components/QueueFormParts.tsx` (phần tóm tắt) |
| `shared/ui/form/FormAlert.tsx` + `useSubmit.ts` | Alert vàng/đỏ đầu form. Gửi lỗi: giữ giá trị, alert đỏ, nút chính đổi thành "Thử lại" (W6e); chặn bấm đúp. | |

---

## 3. Thay đổi backend

### 3.0 Quy ước chung cho mọi thay đổi dưới đây
- Serializer khai `fields` tường minh; field tiền nhạy cảm vào `sensitive_fields` (`CostFieldSerializerMixin`) **và** tên khoá nằm trong `apps/common/cost_keys.py::COST_KEYS`.
- View chỉ parse + kiểm quyền + gọi service. Đổi trạng thái/tồn → service `@transaction.atomic` + `select_for_update` + `record_audit`.
- `AuditLog.changes` chỉ chứa mã/ID/trạng thái, **không** tên, SĐT, địa chỉ, ghi chú tự do.
- Endpoint trả dữ liệu cá nhân khách: `NoStoreMixin`.
- Mỗi endpoint mới: test happy path theo Group, 403 thiếu quyền + 401 chưa đăng nhập, không rò giá vốn bằng token `nv_kho`/`quan_ly`, lỗi nghiệp vụ 400.
- Quyền Tầng 2 mới: thêm vào `Meta.permissions`, data migration cấp Group **trong app sở hữu**, thêm nhãn vào `apps/accounts/auth/services.py::CAPABILITY_LABELS` (test `test_s47_moi_quyen_meta_permissions_deu_co_nhan` bắt).

### B1 — Kiểm kê: gửi được dòng số đếm (BR-KK, đề xuất **BR-KK-08**)
**Migration** `inventory/0005_stockreconciliation_updated_at`: `StockReconciliation.updated_at = DateTimeField(auto_now=True, null=True)`. Chỉ thêm. Lý do: phát hiện xung đột W6f.

**Tạo phiếu kèm dòng** — `POST /api/inventory/reconciliations/` · Tầng 1 `inventory.add_stockreconciliation` (chu, quan_ly, nv_kho — đã có).
```json
{"count_date": "2026-10-01", "note": "Đếm đầu ca",
 "lines": [{"batch": 12, "counted_qty": "18.100", "reason": ""},
           {"batch": 15, "counted_qty": "30.300", "reason": "Lần xuất 27/09 ghi dư"}]}
```
→ `201` body chi tiết (dưới). Service `stocktake.services.create_reconciliation(*, count_date, note, lines, actor)`: chụp `system_qty = batch.qty_available`, `difference_qty = counted_qty − system_qty` (Decimal), audit `create_stockreconciliation` `changes={"line_count": n}`.

**Thay toàn bộ dòng** — `POST /api/inventory/reconciliations/{id}/lines/` · `required_perms=("inventory.change_stockreconciliation",)`.
```json
{"expected_updated_at": "2026-10-01T07:30:12+07:00", "lines": [{"batch": 12, "counted_qty": "18.100", "reason": "Rút nước"}]}
```
→ `200` body chi tiết. Service `replace_lines(*, reconciliation, lines, expected_updated_at, actor)` khoá dòng phiếu. Audit `update_reconciliation_lines` `changes={"line_count": n}`.

Lỗi (400 trừ khi ghi khác):
| code | Khi |
|---|---|
| `RECON_NOT_DRAFT` | phiếu không ở `DRAFT` |
| `STALE_STATE` (**409**) | `expected_updated_at` ≠ `updated_at` hiện tại; body thêm `updated_at`, `updated_by_name` (lấy từ AuditLog mới nhất của phiếu) |
| `RECON_LINE_INVALID` | `counted_qty` < 0 / không phải số; lô trùng trong phiếu; lô `CANCELLED`/`CLOSED`; danh sách rỗng |
| `BR-KK-08` | (khi duyệt) người duyệt là `created_by` **hoặc** đã từng `update_reconciliation_lines` phiếu này |

`apply_reconciliation` giữ nguyên logic, chỉ mở rộng kiểm người duyệt (BR-KK-08). `PATCH` phiếu (`note`, `count_date`) giữ như cũ. `StockReconciliationLineSerializer` vẫn `read_only` ở serializer chính; dòng ghi qua serializer nhập riêng `ReconciliationLineInput` (batch, counted_qty, reason ≤ 500 ký tự).

**Body chi tiết/danh sách** (R8): `id, code ("KK-14"), count_date, status, status_label, note, created_by {id, display_name}, approved_by {..}|null, approved_at, updated_at, updated_by_name, warehouse_names [..], line_count, short_count, over_count, match_count, short_qty, over_qty, net_difference, available_actions ["edit_lines","approve"]`; chi tiết thêm `lines: [{id, batch, batch_code, item_name, warehouse_name, system_qty, counted_qty, difference_qty, reason}]`. Danh sách lọc `status`, `warehouse`, `date_from/date_to`; phân trang chuẩn.
Giá vốn: không có field nào. Dữ liệu cá nhân: không.

### B2 — Quyền "Xem khách hàng" + danh bạ khách (đề xuất **BR-PQ-31**)
**Quyền** `sales.view_customer_list` "Xem khách hàng" trên `Customer.Meta.permissions`. **Migration** `sales/0012_customer_view_customer_list` (AlterModelOptions) + `sales/0013_grant_view_customer_list` (data, mẫu `sales/0010`): cấp **chu, quan_ly**. Không đổi `sales.view_customer` và `/api/sales/customers/` (S5, CS-01 giữ nguyên; §6 Q4).

**ViewSet mới** `apps/sales/customers/directory_api.py::CustomerDirectoryViewSet` (`NoStoreMixin`, list + retrieve + partial_update), route `sales/customer-directory`. Mọi action `required_perms=("sales.view_customer_list",)`; `PATCH` thêm `sales.change_customer`. Không phạm vi dòng (quyền này = xem mọi khách).

`GET /api/sales/customer-directory/?q=&ordering=-last_order_at&page=` — `q` khớp tên (bỏ dấu, như `_customer_ids_by_name`) hoặc ≥ 4 chữ số của SĐT.
```json
{"count": 126, "next": "…?page=2", "previous": null, "results": [
 {"id": 41, "name": "Khách Thử A", "phone": "0900000123", "order_count": 6, "total_spent": "2140000",
  "cancelled_count": 1, "last_order_at": "2026-10-01T09:32:00+07:00", "note": "Giao trước 11 giờ"}]}
```
`total_spent` = Σ `SalesInvoice.amount` của hoá đơn `ISSUED` thuộc đơn **không** huỷ (`CANCELLED`/`AUTO_CANCELLED`), trừ Σ `Refund.amount` `REFUNDED` của chính các hoá đơn đó (theo ED-13-AC2; chốt lại ở review Lô 6 vì hoá đơn của đơn huỷ vẫn `ISSUED`). Doanh thu, không phải giá vốn. `cancelled_count` = đơn `CANCELLED` + `AUTO_CANCELLED`. Tính bằng `annotate` (Subquery/Count), không N+1.

`GET /api/sales/customer-directory/{id}/` — thêm `default_address`, `created_at`, `first_order_at`,
`orders: [{id, code, status, status_label, total_amount, created_at}]` (50 đơn mới nhất),
`refunds: [{id, order_code, status, status_label, amount, created_at}]`.

`PATCH /api/sales/customer-directory/{id}/` — chỉ nhận `name`, `default_address`, `note` (field khác → 400 `INPUT_NOT_ALLOWED`); `phone` khoá (khoá tự nhiên). Audit `update_customer` `changes={"fields": ["note"]}` — **không** chép giá trị.

**Chặn AI**: thêm `"/api/sales/customer-directory/"` và `"/api/sales/customers/"` vào `apps/ai/policy/rules.py::FORBIDDEN_PREFIXES`; thêm `"default_address"` vào khoá PII. Trang khách hàng không có khối AI.
Nhãn `CAPABILITY_LABELS["sales.view_customer_list"] = "Xem khách hàng"`. FE: `PERM.viewCustomerList`, mục menu "Khách hàng".

### B3 — Số liệu nhà cung cấp
Không migration. `SupplierSerializer` thêm (đọc): `receipt_count` (chỉ phiếu `SUBMITTED`, theo Q4 mặc định Duy chốt 01/10, cập nhật theo Lô 11), `last_received_at` (max `PurchaseReceipt.created_at` của phiếu `SUBMITTED`), `supplier_type_label`, `purchase_total` (**nhạy cảm**: Σ `qty × rate` của dòng thuộc phiếu `SUBMITTED`). `sensitive_fields = ("purchase_total",)`; thêm `"purchase_total"` vào `COST_KEYS`.
`GET /api/purchasing/suppliers/?q=&supplier_type=&is_active=` (annotate, phân trang chuẩn) · Tầng 1 `purchasing.view_supplier` (chu, quan_ly, nv_kho). `POST`/`PATCH` như cũ (`add/change_supplier`: chu, quan_ly). "Ngừng hợp tác" = `PATCH {"is_active": false}`. FE **không** gọi `DELETE`.
```json
{"id": 3, "name": "Ghe Tư Hải", "supplier_type": "INDIVIDUAL", "supplier_type_label": "Cá nhân", "phone": "0900000907",
 "note": "…", "is_active": true, "receipt_count": 4, "last_received_at": "2026-09-29T05:40:00+07:00", "purchase_total": "14326000"}
```
(`purchase_total` không có trong JSON khi thiếu `inventory.view_costprice`.) Dòng thời gian: R2 `supplier`.

### B4 — Ma trận phân quyền (đọc/ghi) — chưa có, làm mới (đề xuất **BR-PQ-32**)
Không migration (dùng `auth.Group`/`Permission`). Module mới `apps/accounts/capabilities/` (`registry.py`, `services.py`, `api.py`, `tests/`).

**Registry** (một nguồn): mỗi "việc" = `key`, `label`, `section`, `perms` (codename đầy đủ), `chu_only`. Tập `perms` giữa các việc **rời nhau** (test kiểm). Bảng khởi tạo (theo W3h/W3i):

| Nhóm | key · nhãn | perms | Chỉ Chủ |
|---|---|---|---|
| Bán hàng | `view_orders` Xem đơn | `sales.view_salesorder`, `sales.view_salesorderline` | |
| | `view_customers` Xem khách hàng | `sales.view_customer_list` | |
| | `confirm_calls` Gọi xác nhận đơn | `delivery.confirm_with_customer`, `delivery.change_recipient` | |
| | `confirm_payment` Xác nhận đã nhận tiền | `sales.confirm_payment_manual` | ✓ |
| | `cancel_paid` Huỷ đơn đã thanh toán | `sales.cancel_paid_order` | |
| | `create_refund` Lập phiếu hoàn | `sales.create_refund` | |
| | `confirm_refund` Xác nhận đã hoàn tiền | `sales.confirm_refund` | ✓ |
| | `pack_print` Soạn hàng, in tem | `delivery.pack_deliverynote`, `delivery.print_label` | |
| | `assign_delivery` Giao phiếu cho người giao | `delivery.assign_deliverynote` (B6) | |
| | `deliver` Giao hàng, báo kết quả giao | `delivery.change_deliverynote` | |
| Hàng hoá & kho | `receive` Nhập lô tại cảng | `purchasing.add_purchasereceipt`, `purchasing.change_purchasereceipt` | |
| | `add_cost` Thêm chi phí phụ vào lô | `purchasing.add_purchasecost` | ✓ |
| | `publish_batch` Mở bán lô | `inventory.publish_batch` | |
| | `close_batch` Chốt lô | `inventory.close_batch` | ✓ |
| | `count_stock` Nhập số kiểm kê | `inventory.add_stockreconciliation`, `inventory.change_stockreconciliation` | |
| | `approve_count` Duyệt kiểm kê | `inventory.approve_stockreconciliation` | |
| | `approve_return` Duyệt hàng hoàn về kho | `inventory.approve_returntostock` | |
| | `set_price` Sửa giá bán | `catalog.add_itemprice`, `catalog.change_itemprice`, `catalog.add_pricingrule`, `catalog.change_pricingrule` | ✓ (🟡 T9) |
| Kế toán | `view_cost` Xem giá vốn | `inventory.view_costprice` | ✓ |
| | `view_profit` Xem báo cáo lãi lỗ | `reports.view_profitreport` | ✓ |
| Website | `write_content` Viết bài | `content.add_entry`, `content.change_entry` | |
| | `publish_content` Đăng bài lên Shop | `content.publish_entry` | |
| Quản trị | `manage_staff` Tạo tài khoản, đổi nhóm | `accounts.manage_staff` | ✓ |
| | `view_audit` Xem nhật ký hoạt động | `accounts.view_auditlog` | |
| | `ai_policy` Cài đặt chính sách AI | `ai.manage_ai_policy` | ✓ |

Codename trong bảng phải tồn tại (test `Permission.objects.filter(...)` đủ số); codename nào sai thì dev báo, không tự đổi việc.

**API** (route khai rõ trong `config/api_urls.py` **trước** `include(router.urls)` để không bị `StaffViewSet` bắt `pk="groups"`; nằm dưới `/api/staff/` nên đã thuộc danh sách cấm AI). Mọi view `required_perms=("accounts.manage_staff",)` (chỉ chu).
- `GET /api/staff/groups/` →
```json
[{"code": "quan_ly", "label": "Quản lý", "member_count": 2, "members": [{"id": 5, "display_name": "Chị Hạnh"}],
  "can_view_cost": false, "last_changed_at": "2026-09-22T09:00:00+07:00", "last_changed_by": "Lộc",
  "capabilities": {"view_orders": "on", "confirm_payment": "off", "set_price": "off"}}]
```
- `GET /api/staff/groups/{code}/` → như trên + `members` đủ (`id, display_name, username, other_groups, is_active, added_at`) + `registry` (`key, label, section, chu_only`) + `scopes` (chỉ đọc, chuỗi cố định theo nhóm, ví dụ `{"orders": "Được gán", "customers": "Không xem"}`) + `timeline` (AuditLog `change_group_capabilities`, `change_staff_groups`).
- `PUT /api/staff/groups/{code}/capabilities/` · body `{"capabilities": {"approve_return": true, "view_orders": true}}` (chỉ gửi việc muốn đổi) → `200` body chi tiết.
  Luật service `set_group_capabilities(*, group_code, changes, actor)` (atomic):
  1. `group_code` ∉ 5 nhóm có sẵn → 404. Nhóm `chu` → 400 `GROUP_LOCKED` (Chủ luôn đủ quyền).
  2. Bật việc `chu_only` cho nhóm khác `chu` → 400 `BR-PQ-32` ("Việc này chỉ nhóm Chủ được làm.").
  3. Key lạ → 400 `INPUT_NOT_ALLOWED`. Chỉ thêm/bớt đúng `perms` của việc; **không đụng** permission ngoài registry.
  4. Trạng thái việc: `on` khi nhóm có đủ perms, `off` khi không có cái nào, `partial` khi thiếu một phần (FE hiện như tắt + dấu cảnh báo; bật lại = cấp đủ).
  5. Audit `change_group_capabilities` `changes={"<key>": {"from": "off", "to": "on"}}`.
- "Thêm người vào nhóm" dùng `PUT /api/staff/{id}/groups/` có sẵn.

Rủi ro: tắt `view_orders` của `nv_giao` làm hỏng màn giao hàng của họ → FE hỏi xác nhận (Modal nêu hậu quả); BE không cấm (quyết định của Chủ).
Me endpoint không đổi; FE có nút "Tải lại quyền" ở Tài khoản (gọi lại `/api/auth/me/`).

### B5 — Lý do giao thất bại (đề xuất **BR-GH-22**)
**Migration** `delivery/0005_deliverynote_failure_reason_and_more` (gộp với quyền B6, xem dưới): thêm
`failure_reason = CharField("Lý do giao thất bại", max_length=16, choices=FailureReason.choices, blank=True, default="")`,
`failure_note = CharField("Ghi chú giao thất bại", max_length=200, blank=True, default="")`.
`FailureReason`: `NOT_MET` "Không gặp khách" · `REFUSED` "Khách từ chối nhận" · `WRONG_ADDRESS` "Sai địa chỉ" · `DAMAGED` "Hàng hư khi giao" · `OTHER` "Khác".
Hai field vào `DeliveryNoteViewSet.locked_fields` (chỉ đổi qua action).

**API** (mở rộng action có sẵn) `POST /api/delivery/notes/{id}/status/` · Tầng 2 như cũ `delivery.change_deliverynote` (nv_giao chỉ phiếu của mình — Tầng 3 trong `get_queryset`).
```json
{"to_status": "FAILED", "from_status": "DELIVERING", "failure_reason": "NOT_MET", "failure_note": "Gọi 3 lần không nghe máy"}
```
→ `200` body phiếu + `already` + `needs_decision` (như S19). Service `mark_failed(*, note, actor, reason, reason_note="")`:
| code (400) | Khi |
|---|---|
| `DELIVERY_FAILURE_REASON_REQUIRED` | `to_status=FAILED` mà thiếu/sai `failure_reason` |
| `DELIVERY_FAILURE_NOTE_REQUIRED` | `OTHER` mà `failure_note` rỗng |
| `DELIVERY_FAILURE_NOTE_PII` | `failure_note` có dãy ≥ 9 chữ số (`apps.common.pii.has_long_digit_run`, như BR-GH-19) |
`FAILED → DELIVERING` (giao lại) giữ lý do lần cuối; lịch sử từng lần nằm ở AuditLog.
Audit `delivery_mark_failed` `changes={"failed_attempts": {"to": n}, "failure_reason": {"to": "NOT_MET"}, "needs_decision": …}` — **không** chép `failure_note`.
Serializer list + detail thêm `failure_reason`, `failure_reason_label`; detail thêm `failure_note`. AI: thêm `"failure_note"` vào `SCRUB_FREE_TEXT_KEYS`.
Test hiện có gửi `FAILED` không lý do (S19) phải sửa theo contract mới trong cùng lô.

### B6 — Giao / đổi người giao (đề xuất **BR-GH-23**)
**Quyền** `delivery.assign_deliverynote` "Giao phiếu cho người giao" trên `DeliveryNote.Meta.permissions` (cùng migration `0005`). **Migration** `delivery/0006_grant_assign_deliverynote`: cấp **chu, quan_ly**. Thêm nhãn vào `CAPABILITY_LABELS`.

- `GET /api/delivery/deliverers/` · `required_perms=("delivery.assign_deliverynote",)` → người `is_active` thuộc nhóm `nv_giao`:
```json
[{"id": 7, "display_name": "Anh Phúc", "delivering_count": 0, "ready_count": 1},
 {"id": 8, "display_name": "Anh Lâm", "delivering_count": 2, "ready_count": 0}]
```
Không trả SĐT/username. Một truy vấn `annotate(Count(filter=Q(...)))`.
- `POST /api/delivery/notes/{id}/assign/` · `required_perms=("delivery.assign_deliverynote",)` · body `{"assigned_to": 7, "expected_assigned_to": null}` → `200` body phiếu + `already`.
  Service `assign_deliverer(*, note, assignee, expected_assignee_id, actor)` (atomic, `select_for_update`):
| code (400) | Khi |
|---|---|
| `DELIVERY_ASSIGN_STATE` | `status` ∉ {`CONFIRMING`, `PREPARING`, `READY`} (🟡 T6) |
| `DELIVERY_ASSIGNEE_INVALID` | người nhận không `is_active` hoặc không thuộc `nv_giao` |
| `STALE_STATE` | `expected_assigned_to` khác người đang gán (giữ 400 như các lỗi STALE_STATE của `delivery`) |
  Gán đúng người đang gán → `already: true`, không ghi audit. Audit `assign_deliverynote` `changes={"assigned_to": {"from": 8, "to": 7}}` (ID, không tên).
- `available_actions` thêm `"assign"` khi có quyền và trạng thái hợp lệ. Serializer list + detail thêm `assigned_to_name` (tên hiển thị nhân viên).

### 3.7 Số điện thoại hiển thị đủ trong ERP (quyết định Duy 01/10)
Hiện trạng đã rà:
| Chỗ | BE trả | FE hiện | Đổi |
|---|---|---|---|
| Danh sách đơn | `customer_phone` đủ (đã theo phạm vi đơn) | `OrdersScreen.tsx:59` cắt 4 số cuối | FE hiện đủ, cột riêng "Số điện thoại" |
| Gắn khoản tiền vào đơn | đủ | `AttachOrderForm.tsx:215` cắt 4 số | FE hiện đủ, cột riêng |
| Chi tiết đơn, phiếu hoàn | đủ | đủ | giữ |
| Phiếu giao chi tiết | **không trả** SĐT (FE khai `recipient_phone` nhưng BE không có) | trống | **BE** thêm `phone` = `recipient_phone` nếu có, ngược lại `SalesOrder.phone` (R4). Phạm vi: `get_queryset` (nv_giao chỉ phiếu của mình) |
| CSKH trong phạm vi | `phone`, `recipient_phone` đủ | đủ | giữ |
| CSKH ngoài phạm vi | `phone_masked` | che | **giữ che** (không có quyền) |
| Tem in | `recipient_phone_masked` | che | **giữ che** (🟡 T1) |
| Danh bạ khách (B2), nhà cung cấp, nhân viên | đủ | — | hiện đủ |
| AI (đầu vào/đầu ra) | khoá PII bị lọc | — | giữ; thêm khoá mới (B2, B5) |
Không có serializer ERP nào đang che số với người có quyền, nên BE chỉ thêm `phone` ở phiếu giao. Hiển thị dạng `0900 000 123` (nhóm 4-3-3) qua `shared/lib/format.ts::phone`, có `href="tel:"`. Không đưa SĐT vào URL, `localStorage`, `console`.

### 3.8 API đọc bổ sung cho màn mới (không đổi nghiệp vụ, không migration)
| # | Endpoint | Thêm | Quyền | Giá vốn / cá nhân |
|---|---|---|---|---|
| R1 | `GET /api/ai/actions/` | lọc `target_model`, `target_id` (nhiều id cách phẩy), `status` có sẵn; `GET /api/ai/actions/counts/?status=PENDING,ESCALATED` → `{"by_target_model": {"purchasing.purchasereceipt": 1}}` (đếm theo phạm vi "mine" hiện có) | như hiện tại (owner hoặc nhóm nhận việc) | không đổi lọc đầu ra AI |
| R2 | `GET /api/guidance/<loại>/<id>/` | provider **chỉ dòng thời gian** (`next_steps: []`, `warnings: []`) cho `receipt`, `stocktake`, `delivery`, `return`, `item`, `supplier`, `customer`, `staff`, `group`. Hàm chung `apps/common/guidance/audit_timeline.py::make_audit_timeline_provider(model, view_perm, scope_fn=None)` đọc `AuditLog` theo `model_name/object_id`, format bằng `format_guidance_timeline`. Quyền: `view_<model>` + phạm vi giống API chi tiết; `customer` đòi `sales.view_customer_list`; `staff`/`group` đòi `accounts.manage_staff`. | như cột trái | `changes` thô không trả; nhãn dòng không chứa tên/SĐT/địa chỉ khách |
| R3 | `GET /api/sales/orders/` | field `reason: {"code","label"}\|null` (AUTO_CANCELLED → "Hết giờ giữ chỗ"; CANCELLED → nhãn `SalesCreditNote.reason_code`; giao dịch mở `UNDERPAID` → "Chuyển thiếu tiền"; phiếu `FAILED` → nhãn `failure_reason`); lọc `customer=<id>` (đòi thêm `view_customer_list`), `batch=<pk>` (qua `lines__batch_allocations__batch`). `GET /api/sales/refunds/` thêm lọc `month=YYYY-MM` (lọc `status` đã có). | `sales.view_salesorder` + `scope_orders_for` | không thêm |
| R4 | `GET /api/delivery/notes/` | lọc `assigned_to=me\|<id>` (`<id>` chỉ người full scope), `order=<id>`; field `assigned_to_name`, `failure_reason(_label)`; detail thêm `phone` (§3.7), `failure_note`. (`GET /api/cskh/queue/{id}/` đã trả `calls`, không đổi) | như hiện tại | `phone` chỉ trong detail, đã qua phạm vi |
| R5 | `GET /api/inventory/batches/` | lọc `supplier`, `warehouse`; field `receipt: {"id","code"}\|null` | `inventory.view_batch` | giữ `sensitive_fields` |
| R6 | `GET /api/inventory/ledger/` | lọc `batch`, `movement_type` (nhiều), `warehouse`, `item`, `date_from/date_to`; field `batch_code`, `item_name`, `warehouse_name`, `type_label` (WRITE_OFF → "Ghi lỗ, huỷ hàng"), `balance_after` (truy vấn con tương quan theo lô, thứ tự `created_at, id` — không dùng `Window` vì chạy sau WHERE nên sai khi lọc; sửa theo Lô 7), `reference_display` + `reference_link {kind, id}` (phân tích `reference`: `reconciliation N`→KK-N, `return N`→RT-N, `INV…`, `cancel SO…`, `create_batch`→PR của lô, `supplier_return SR-N`), `created_by_name` ("Hệ thống" khi null); `StandardPagination` | `inventory.view_stockledgerentry` | không có tiền |
| R7 | `GET /api/inventory/warehouses/` | `active_batch_count`, `total_qty` (lô còn tồn); `is_group_label` | `inventory.view_warehouse` | không |
| R7b | `GET /api/inventory/stock-entries/` | `code` "SE-n", `purpose_label`, `batch_code`, `item_name`, `created_by_name`; lọc `purpose`, `date_from/date_to` | `inventory.view_stockentry` | không |
| R8 | kiểm kê | xem B1 | | |
| R9 | `GET/POST /api/inventory/returns/` | đọc: `code` "RT-n", `delivery_note_code`, `order_code`, `batch_code`, `item_name`, `outside_minutes` (`returned_at − left_warehouse_at`), `status_label`, `decision_label` ("Huỷ bỏ, ghi lỗ"), `created_by_name`; lọc `status`, `month`. **Tạo** (sửa lỗ hổng): `validate` buộc `delivery_note` ở `FAILED`/`DELIVERING`, `batch` thuộc phân bổ của phiếu, `qty` ≤ số kg đã giao của lô đó (`RETURN_QTY_EXCEEDS`), người không full scope chỉ tạo cho phiếu gán cho mình (403/404); `perform_create` ghi audit `return_to_warehouse` | Tầng 1 như cũ | không |
| R10 | `GET /api/purchasing/receipts/` | `code` "PR-n", `supplier_name`, `warehouse_name`, `created_by_name`, `items_summary`, `total_qty`, `batch_codes`, `invoice: {"id"}\|null`, `status_label`, `purchase_amount` (**nhạy cảm**, thêm vào `sensitive_fields` + `COST_KEYS`); lọc `status`, `supplier`, `month`, `has_invoice` | `purchasing.view_purchasereceipt` | `rate` dòng đã ẩn; `purchase_amount` ẩn khi thiếu `view_costprice` |
| R11 | `GET /api/purchasing/invoices/` | `code` "#n", `supplier_name`, `receipt_code`, `is_paid_label`; lọc `is_paid`, `supplier`, `month`. `amount`: **🔴 Q3** | `purchasing.view_purchaseinvoice` (chu, quan_ly) | xem Q3 |
| R12 | `GET /api/purchasing/costs/` | `cost_type_label`, `allocation_method_label`, `batch_count`; lọc `cost_type`, `month` | `purchasing.view_purchasecost` (chỉ chu) | cả chứng từ là giá vốn |
| R13 | `GET /api/sales/invoices/` | serializer list mới `SalesInvoiceListSerializer`: `id, code, sales_order, order_code, customer_name, issued_at, amount, status, status_label, cogs, gross_profit` (`cogs` = Σ `qty × unit_cost` của `SalesInvoiceLineBatch`; `gross_profit = amount − cogs`); `sensitive_fields=("cogs","gross_profit")`; response thêm `totals: {"amount", "gross_profit"}` (bỏ hoá đơn `CANCELLED`; `gross_profit` chỉ khi có `view_costprice`); lọc `status`, `date_from/date_to`, `q` (mã); `StandardPagination`; detail giữ serializer cũ | `sales.view_salesinvoice` (chu, quan_ly, nv_kho) | **ẩn** `cogs`, `gross_profit` khi thiếu `view_costprice` (khoá đã có trong `COST_KEYS`) |
| R14 | catalog | `items`: `current_price {"rate","valid_from","valid_upto"}\|null` chỉ khi có `catalog.view_itemprice` (pop trong `to_representation`), lọc `item_group`, `is_active`, `item_type`; `item-prices`: `item_name`, `item_code`, lọc `item`; `pricing-rules`: `item_name`, lọc `is_active`, `apply_on`; `item-groups`: `parent_name`, `item_count` | Tầng 1 có sẵn | giá bán không phải giá vốn |
| R15 | `GET /api/reports/batches/?month=YYYY-MM&state=closed\|provisional` (mới) → danh sách `batch_pnl` của lô có phát sinh trong kỳ + `item_name`, `status`, `status_label`; `GET /api/reports/period/` thêm `invoice_count`, `refund_count` | `reports.view_profitreport` (chỉ chu) | toàn bộ là lãi lỗ; không mở cho quyền khác |
| R16 | `GET /api/audit-logs/` | lọc `actor=<user id>` | `accounts.view_auditlog` | như hiện tại |

### 3.9 Tổng hợp migration (đều chỉ thêm)
| App | File | Nội dung | Lô |
|---|---|---|---|
| inventory | `0005_stockreconciliation_updated_at` | 1 field | 8 |
| sales | `0012_customer_view_customer_list` | Meta.permissions | 6 |
| sales | `0013_grant_view_customer_list` | data: chu, quan_ly | 6 |
| delivery | `0005_deliverynote_failure_reason_and_more` | 2 field + Meta.permissions `assign_deliverynote` | 4 |
| delivery | `0006_grant_assign_deliverynote` | data: chu, quan_ly | 4 |
Mỗi lô BE chạy `makemigrations --check --dry-run` sạch, đọc file sinh ra, `reverse` chạy được (`migrate <app> <số trước>` trên DB test).

---

## 4. Rủi ro và cơ chế chặn

| Rủi ro | Cơ chế chặn | Test bắt lỗi |
|---|---|---|
| **Rò giá vốn** ở Hoá đơn bán (`cogs`, `gross_profit`, `totals.gross_profit`) | `sensitive_fields` + khoá trong `COST_KEYS`; `totals` tính trong view theo `can_view_cost` | `apps/sales/payments/tests/test_invoice_list.py`: token `quan_ly`, `nv_kho` → JSON không có `cogs`/`gross_profit` ở `results[]` và `totals`; token `chu` có |
| Rò giá vốn ở Nhà cung cấp (`purchase_total`), phiếu nhập (`purchase_amount`) | như trên | `apps/purchasing/receipts/tests/test_supplier_aggregates.py`, `test_receipt_list.py`: `quan_ly`, `nv_kho` không có khoá |
| Rò giá vốn ở Hoá đơn mua (`amount` suy ra giá mua khi phiếu 1 dòng) | 🔴 Q3; mặc định đề xuất ẩn với người thiếu `view_costprice` | `apps/purchasing/invoices/tests/test_api.py` theo kết quả Q3 |
| Rò giá vốn ở Sổ nhập xuất / Kho / Kiểm kê / Hàng hoàn | Không có field tiền (chỉ kg) | test liệt kê khoá JSON = tập cho phép (assert `set(keys) == EXPECTED`) |
| Rò lãi lỗ ở Báo cáo (R15), F1i | `required_perms=("reports.view_profitreport",)` | 403 với `quan_ly`, `nv_kho`; FE ẩn dòng "Lãi/lỗ lô" trong F1i khi `!can_view_profit` |
| FE vô tình hiện giá vốn khi BE trả thiếu | Cột `locked` chỉ render khi khoá có trong JSON **và** `me.can_view_cost` | vitest `DataTable` + e2e đăng nhập `kho1`: không thấy cột "Giá vốn", "Lãi gộp" |
| **Rò dữ liệu cá nhân**: màn Khách hàng | `required_perms=("sales.view_customer_list",)` cả list/detail/patch; `NoStoreMixin`; mặc định chỉ chu, quan_ly | `apps/sales/customers/tests/test_directory_api.py`: `nv_kho`, `nv_giao`, `cskh` → 403; 401 khi chưa đăng nhập; header `Cache-Control: no-store`; PATCH với `phone` → 400 |
| Dữ liệu khách tới AI | Trang khách không có `aiSlot`; `/api/sales/customer-directory/` + `/api/sales/customers/` vào `FORBIDDEN_PREFIXES`; `default_address`, `failure_note` vào bộ lọc; bỏ `RightRail` (trợ lý toàn cục) | `apps/ai/tests`: `is_url_forbidden` True cho 2 tiền tố; registry index không có lệnh nào trỏ tới 2 tiền tố; e2e: trang `/customers/detail/` không có phần tử `[data-ai-block]` |
| Dữ liệu khách vào AuditLog / log | `changes` chỉ chứa mã/ID; không log `request.data` | test `update_customer`, `delivery_mark_failed`, `assign_deliverynote`: `AuditLog.changes` không chứa chuỗi tên/SĐT/địa chỉ/ghi chú của fixture |
| Dữ liệu khách vào URL / localStorage | Route chi tiết chỉ nhận `id`; nháp form chỉ cho form không có dữ liệu khách; ⌘K không tìm theo tên/SĐT | e2e `ra_soat_x_ac4_storage.py` mở rộng: sau khi xem trang khách, `localStorage` + `location.href` không chứa SĐT/tên fixture |
| SĐT bị che với người có quyền | FE `format.phone` hiện đủ; BE thêm `phone` ở phiếu giao | vitest `format.phone`; e2e mock: cột "Số điện thoại" danh sách đơn = số đủ |
| **Leo quyền** qua ma trận (B4) | Chỉ `manage_staff`; nhóm `chu` khoá; `chu_only` không cấp cho nhóm khác; chỉ đụng perms trong registry | `apps/accounts/capabilities/tests/test_api.py`: `quan_ly` → 403; bật `view_cost` cho `quan_ly` → 400 `BR-PQ-32`; sửa nhóm `chu` → 400; perm ngoài registry của nhóm không đổi sau PUT; registry rời nhau + codename tồn tại |
| Leo quyền giao phiếu (B6) | `assign_deliverynote` chỉ chu, quan_ly; người nhận phải `nv_giao` đang làm | `test_assign.py`: `nv_kho`, `nv_giao` → 403; gán cho `nv_kho` → 400; phiếu `DELIVERING` → 400; hai yêu cầu cùng lúc với `expected_assigned_to` cũ → một thành công, một `STALE_STATE` |
| `nv_giao` tạo hàng hoàn cho phiếu người khác / vượt số kg (R9) | `validate` + kiểm phạm vi | `apps/inventory/returns/tests/test_create_validation.py` |
| Người nhập số tự duyệt kiểm kê sau khi lines sửa được (B1) | BR-KK-08 | `apps/inventory/stocktake/tests/test_lines.py`: người sửa dòng duyệt → 400; người khác duyệt → 200 và tồn đổi đúng |
| Hai người sửa cùng phiếu kiểm kê | `expected_updated_at` → 409 | test 409 + body có `updated_by_name` |
| **Xoá chứng từ** | Không thêm DELETE; `DocumentViewSet` giữ; FE không có nút xoá cho chứng từ. Master data (`Warehouse`, `ItemPrice`, `PricingRule`) còn DELETE ở BE với `chu`; `Supplier` DELETE/PUT → 405 từ Lô 11 → FE **không** gọi DELETE ngoài ảnh mặt hàng và bài nháp (đã có) | test 405 DELETE cho `reconciliations`, `returns`, `delivery/notes`, `sales/invoices`; `grep -rn '"DELETE"' erp-console/features` chỉ ra `catalog` ảnh + `content` |
| Migration phá dữ liệu | Chỉ `AddField` có default/null + `AlterModelOptions` + data migration có `revoke` | `makemigrations --check --dry-run`; đọc file; test chạy migrate từ đầu (Django test runner) |
| AI tải vào route nghiệp vụ | Khối AI qua cổng mỏng + `next/dynamic` `ssr:false` | `node scripts/check-ai-chunks.mjs` phải exit 0 sau build |
| Mock lọt vào bản build thật | Biểu thức `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockX : undefined` tại chỗ | `NEXT_PUBLIC_USE_MOCK=0 npm run build && node scripts/check-no-mock.mjs` |

---

## 5. Lô

### 5.0 Lệnh kiểm chứng dùng chung
**BE** (`<apps>` = app của lô, luôn kèm `apps.common apps.ai apps.accounts`):
```bash
cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test <apps>
cd backend && .venv/bin/python manage.py test          # lô có migration hoặc đụng apps/common, apps/ai
```
**FE**:
```bash
cd erp-console && rm -rf node_modules && npm ci
cd erp-console && npx tsc --noEmit && npx vitest run
cd erp-console && NEXT_PUBLIC_USE_MOCK=0 npm run build && node scripts/check-no-mock.mjs && node scripts/check-ai-chunks.mjs
cd erp-console && grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' app features shared --include=*.ts --include=*.tsx --include=*.css | grep -v 'shared/ui/tokens.css'   # phải rỗng
cd erp-console && NEXT_PUBLIC_USE_MOCK=1 npm run build && (cd out && python3 -m http.server 3101 &) && python3 e2e/<file>.py   # tắt server sau khi xong
```
E2E mới đặt tên `erp-console/e2e/ed_lo<N>_<màn>.py`, theo quy ước `s7_shell.py` (không `wait_for_timeout`). Lô có BE thật: thêm 1 kịch bản trên backend thật (mẫu `s41_s47_real.py`).
**Không được đụng (mọi lô):** `doc/decisions.md`, `02-stories.md`, `01-analysis.md`, migration đã có, `frontend/`, `adapter/`, `.env*`, `firebase*.json`.

### 5.1 Bảng lô

| Lô | Nội dung | Kiểu | Phụ thuộc | Chạy song song được với |
|---|---|---|---|---|
| 1 | Khung + mẫu danh sách (§2.1, §2.2) | FE | — | BE của 2–14 |
| 2 | Mẫu trang chi tiết + popup/form (§2.3, §2.4) ∥ R1, R2 | BE ∥ FE | FE: 1 | BE của 3–14 |
| 3 | Đơn & tiền (D2, D2b, D2c, W1a, W1a2, W1b, W1b2, F2a–F2g) ∥ R3 + SĐT đủ | BE ∥ FE | FE: 1, 2 | 6–14 (BE khác app) |
| 4 | Giao hàng + Việc giao của tôi (W1d, W1d2, W1e, W2e, F2l, F2o) ∥ B5, B6, R4 | BE ∥ FE | FE: 1, 2 | 6–13 |
| 5 | Gọi xác nhận (W1c, W1c2, F2h–F2k) | FE | 1, 2 | 6–13 |
| 6 | Khách hàng (W5a, W5b) ∥ B2 | BE ∥ FE | FE: 1, 2; FE link từ đơn: 3 | 4, 7–13 |
| 7 | Kho & lô, chi tiết lô, Sổ nhập xuất, Kho (D3, W2f, W5i, W5l, W5k chỉ danh sách, F1e, F1g, F1h, F1i, F3m) ∥ R5, R6, R7, R7b | BE ∥ FE | FE: 1, 2 | 4, 6, 10–13 (BE `inventory` đụng 8, 9) |
| 8 | Kiểm kê (W2c, W2g, F1f, W6f) ∥ B1 | BE ∥ FE | FE: 1, 2; BE sau 7 (cùng `inventory/`) | 4, 6, 10–13 |
| 9 | Hàng hoàn về kho (W5e, W5f, F2m, F2n) ∥ R9 | BE ∥ FE | FE: 1, 2, 4 (F2m mở từ W1e); BE sau 8 | 6, 10–13 |
| 10 | Mua hàng + phiếu nhập (W2a, W2b, F1a, F1c, F1d) ∥ R10 | BE ∥ FE | FE: 1, 2 | 3–9, 13 (BE `purchasing` đụng 11, 12) |
| 11 | Nhà cung cấp (W5c, W5d, F1b) ∥ B3 | BE ∥ FE | FE: 1, 2; BE sau 10; FE dùng R5 của 7 | 3–9, 13 |
| 12 | Kế toán (W3a, W5j, W5g, W5g2) ∥ R11–R13, R15 | BE ∥ FE | FE: 1, 2, 10 (form F1c/F1d dùng chung); BE sau 11 | 13, 14 |
| 13 | Danh mục & giá (W2d, W2h, W5o, W5h, W5m, F1k–F1o) ∥ R14 | BE ∥ FE | FE: 1, 2 | 3–12 |
| 14 | Nhân sự + Phân quyền (W3e, W3g, W3h, W3i, F3a–F3f) ∥ B4, R16, nhãn `CAPABILITY_LABELS` | BE ∥ FE | FE: 1, 2; BE sau 4 và 6 (registry dùng quyền mới) | 12, 13, 15, 16 |
| 15 | Tổng quan, Nhật ký, Tài khoản, Đăng nhập/Đặt mật khẩu/Không có quyền, AI của tôi, Chính sách AI, Báo cáo AI (D1, W3f, W4b–W4h, F3g) | FE | 1, 2; W3f lọc người dùng R16 của 14 | 13, 14, 16 |
| 16 | Nội dung (W3b, W3c, W3d, F3h–F3l) | FE | 1, 2 | 13–15 |
| 17 | Dọn dẹp + ⌘K theo mã + e2e hồi quy toàn bộ | FE | 1–16 | — |

**File chung dễ đụng nhau khi chạy song song** (điều phối viên ghép tuần tự khi commit): `backend/config/api_urls.py`, `apps/accounts/auth/services.py` (`CAPABILITY_LABELS`), `apps/ai/policy/rules.py`, `apps/common/cost_keys.py`, `erp-console/shared/lib/nav.ts`, `shared/lib/enums.ts`, `scripts/subset-material-symbols.py`. Mỗi lô chỉ **thêm dòng** vào các file này.

### 5.2 Chi tiết từng lô

**Lô 1 — Khung và mẫu danh sách (FE)**
- Được sửa: `erp-console/shared/**`, `features/auth/components/ConsoleGate.tsx`, `features/auth/components/ViewGuard.tsx`, `app/(console)/layout.tsx`, `app/not-found.tsx`, `app/(console)/error.tsx`, `DESIGN.md` (2 token), `scripts/subset-material-symbols.py`, `public/fonts/ms/*`, `e2e/s7_shell.py` (cập nhật nhãn menu), `e2e/ed_lo1_shell.py` (mới), test vitest liên quan `format`/`nav`.
- Không được đụng: `features/*/components/*Screen*` (ngoài sửa import tối thiểu để build qua khi đổi `Shell`/`Toolbar`), `backend/`.
- Kiểm: §5.0 FE; e2e: menu theo 4 vai mock (`chu`, `ql1`, `kho1`, `giao1`) đúng nhóm/mục; thu gọn sidebar nhớ sau tải lại; avatar menu có 3 mục, không có nút Làm mới/đăng xuất rời; URL lạ → 404 trong shell; vitest `format.dateTime` ra `01/10/2026 09:32`.

**Lô 2 — Mẫu chi tiết, popup, form (FE) ∥ R1, R2 (BE)**
- BE được sửa: `backend/apps/ai/actions/` (lọc + `counts`), `backend/apps/common/guidance/` (`audit_timeline.py` + test), đăng ký provider trong `next_steps.py`/module tương ứng của `purchasing/receipts`, `inventory/stocktake`, `inventory/returns`, `delivery`, `catalog/items`, `sales/customers`, `accounts/staff`, `accounts/capabilities` (đăng ký `group` để ở Lô 14), `config/api_urls.py`.
- FE được sửa: `shared/ui/detail/**`, `shared/ui/overlay/**`, `shared/ui/form/**`, `shared/ui/states/ConflictBanner.tsx`, `shared/lib/lookups.ts`, `features/ai/components/AiDocBlock*.tsx`, `features/ai/actions/api.ts` (+ mock), `features/guidance/**` (dùng lại cho StatusPath/Timeline), `e2e/ed_lo2_patterns.py`.
- Không được đụng: các màn nghiệp vụ, `apps/ai/policy/rules.py`.
- Kiểm: §5.0 BE (`apps.ai apps.common apps.purchasing apps.inventory apps.delivery apps.catalog apps.sales apps.accounts`), FE + `check-ai-chunks`; test BE: timeline `customer` với `quan_ly` 200, `nv_kho` 403; timeline không chứa SĐT/địa chỉ fixture; lọc `target_model` không lộ việc AI của người khác.

**Lô 3 — Đơn & tiền ∥ R3**
- BE: `backend/apps/sales/orders/` (serializer list `reason`, lọc `customer`, `batch`), `backend/apps/sales/refunds/api.py` (lọc), test.
- FE: `features/orders/**`, `app/(console)/orders/**` (thêm `detail/`, `payments/detail/`, `refunds/detail/`), `e2e/s10_s11_orders.py`, `s12_s13_queue.py`, `s14_s16_cancel_refund.py` (sửa theo trang mới), `e2e/ed_lo3_orders.py`.
- Không: `apps/sales/payments/services.py`, `apps/sales/refunds/services.py` (logic tiền không đổi).
- Kiểm: §5.0 (`apps.sales`); e2e: SĐT đủ; Quản lý không thấy "Xác nhận đã nhận tiền"; huỷ đơn đang giao bị chặn trong "…" kèm lý do; toast "Hoàn tác" chỉ hiện khi thao tác có hoàn tác.
- **Điểm dừng:** không có.

**Lô 4 — Giao hàng + Việc giao của tôi ∥ B5, B6, R4**
- BE: `backend/apps/delivery/` (models, migrations `0005`, `0006`, services, api, serializers, tests), `apps/accounts/auth/services.py` (1 nhãn), `apps/ai/policy/rules.py` (`failure_note`), `config/api_urls.py`.
- FE: `features/deliveries/**`, `app/(console)/deliveries/**`, `app/(console)/my-deliveries/page.tsx`, `app/print/label/page.tsx` (chỉ giao diện), `e2e/ed_lo4_delivery.py`, e2e cũ của giao hàng/in tem nếu vỡ do đổi giao diện.
- Không: `apps/delivery/cskh/services.py`, `apps/sales/**`.
- Kiểm: §5.0 (`apps.delivery apps.sales`) + full `manage.py test`; test B5/B6 ở §4; e2e: `giao1` chỉ thấy phiếu của mình, báo thất bại bắt buộc chọn lý do, "Khác" bắt buộc ghi chú; `ql1` giao phiếu thấy số "Đang giao n phiếu".
- **Điểm dừng:** không có.

**Lô 5 — Gọi xác nhận (FE)**
- FE: `features/cskh/**`, `app/(console)/cskh/**`, `e2e/ra_soat_cs02_cs05_mobile_360.py` (giữ xanh), `e2e/ed_lo5_cskh.py`.
- Không: `apps/delivery/cskh/scope.py`, `services.py`.
- Kiểm: §5.0; e2e: dòng ngoài phạm vi vẫn che số, dòng trong phạm vi số đủ.

**Lô 6 — Khách hàng ∥ B2**
- BE: `backend/apps/sales/models/customers.py` (Meta), `apps/sales/migrations/0012`, `0013`, `apps/sales/customers/` (`directory_api.py`, serializers, tests), `apps/accounts/auth/services.py` (1 nhãn), `apps/ai/policy/rules.py`, `config/api_urls.py`.
- FE: **mới** `features/customers/**`, `app/(console)/customers/**`, `shared/lib/nav.ts` (bật mục), `features/auth/mock.ts` (thêm quyền cho `chu`, `ql1`), `e2e/ed_lo6_customers.py`.
- Không: `apps/sales/customers/api.py` (endpoint cũ), test S5/CS-01 hiện có.
- Kiểm: §5.0 (`apps.sales apps.delivery`) + full; test §4 dòng Khách hàng + AI; e2e: `kho1` không thấy menu, vào URL → "Không có quyền"; trang chi tiết không có khối AI.
- Q4 (Duy chốt): giữ nguyên endpoint cũ `/api/sales/customers/`.

**Lô 7 — Kho & lô, Sổ nhập xuất, Kho ∥ R5, R6, R7, R7b**
- BE: `backend/apps/inventory/batches/` (lọc, `receipt`), `apps/inventory/stock/` (ledger, warehouses, stock-entries đọc), test.
- FE: `features/inventory/**`, **mới** `features/ledger/**`, `app/(console)/inventory/**`, `app/(console)/ledger/`, `shared/lib/nav.ts` (bỏ điều kiện `viewDashboard`), e2e cũ `p8_lo5_*`, `p8_lo7_fe_erp.py` giữ xanh, `e2e/ed_lo7_inventory.py`.
- Không: `apps/inventory/batches/services.py`, `apps/inventory/stock/services.py`.
- Kiểm: §5.0 (`apps.inventory apps.reports`); test `balance_after` đúng qua chuỗi nhập–bán–kiểm kê; `nv_kho` không có `purchase_rate`/`landed_unit_cost`.
- D-1 (Duy chốt): W5k chỉ danh sách đọc, không làm F1j. D-2 (Duy chốt): không có nút "Ngừng bán lô".

**Lô 8 — Kiểm kê ∥ B1**
- BE: `backend/apps/inventory/models/stocktake.py`, `apps/inventory/migrations/0005`, `apps/inventory/stocktake/` (services, api, serializers, tests).
- FE: **mới** `features/stocktake/**`, `app/(console)/stocktake/**`, `e2e/ed_lo8_stocktake.py`.
- Không: `apps/inventory/stock/services.py::record_movement`.
- Kiểm: §5.0 (`apps.inventory`) + full; test §4 (BR-KK-08, 409, đếm âm, lô trùng); e2e: lưu nháp → gửi duyệt; người nhập không thấy nút duyệt hoạt động (mờ + lý do).

**Lô 9 — Hàng hoàn về kho ∥ R9**
- BE: `backend/apps/inventory/returns/` (serializers, api, tests).
- FE: **mới** `features/returns/**`, `app/(console)/returns/**`, `features/deliveries/components/MyDeliveriesScreen.tsx` (nối nút "Mang hàng về kho" tới F2m), `e2e/ed_lo9_returns.py`.
- Không: `apps/inventory/returns/services.py::apply_return`.
- Kiểm: §5.0 (`apps.inventory apps.delivery`); test tạo vượt số kg, phiếu người khác.

**Lô 10 — Mua hàng ∥ R10**
- BE: `backend/apps/purchasing/receipts/` (serializers, api lọc, tests), `apps/common/cost_keys.py` (`purchase_amount`).
- FE: `features/purchasing/**`, `app/(console)/purchasing/**`, **mới** `features/accounting/components/PurchaseInvoiceForm.tsx`, `PurchaseCostForm.tsx` (dùng lại ở Lô 12), `e2e/sr07_*.py` giữ xanh, `e2e/ed_lo10_purchasing.py`.
- Không: `apps/purchasing/receipts/services.py`, `apps/purchasing/costs/services.py`.
- Kiểm: §5.0 (`apps.purchasing apps.inventory`); `quan_ly`, `nv_kho` không có `purchase_amount`, `rate`.

**Lô 11 — Nhà cung cấp ∥ B3**
- BE: `backend/apps/purchasing/receipts/` (SupplierSerializer, SupplierViewSet), `apps/common/cost_keys.py` (`purchase_total`).
- FE: **mới** `features/suppliers/**`, `app/(console)/suppliers/**`, `e2e/ed_lo11_suppliers.py`.
- Kiểm: §5.0 (`apps.purchasing`); test §4.

**Lô 12 — Kế toán ∥ R11, R12, R13, R15**
- BE: `backend/apps/sales/payments/` (list serializer + view list), `apps/purchasing/invoices/`, `apps/purchasing/costs/` (đọc), `apps/reports/` (`batches` list, period counts), `config/api_urls.py`.
- FE: **mới** `features/accounting/**`, **mới** `features/reports/**`, `app/(console)/accounting/**`, `app/(console)/reports/page.tsx`, `e2e/ed_lo12_accounting.py`.
- Không: `apps/reports/services.py::batch_pnl/period_pnl` (chỉ gọi lại, không sửa công thức), `apps/sales/payments/services.py`.
- Kiểm: §5.0 (`apps.sales apps.purchasing apps.reports`); test §4 rò giá vốn hoá đơn bán; e2e `kho1`: Hoá đơn bán không có cột Giá vốn/Lãi gộp.
- D-3 (Duy chốt): Quản lý vẫn thấy `PurchaseInvoice.amount`; không thêm khoá.

**Lô 13 — Danh mục & giá ∥ R14**
- BE: `backend/apps/catalog/items/`, `apps/catalog/pricing/` (serializers, lọc, tests).
- FE: `features/catalog/**`, `app/(console)/catalog/**`, `e2e/a2_catalog_real.py` giữ xanh, `e2e/ed_lo13_catalog.py`.
- Không: `apps/catalog/images/`, `apps/sales/**` (giá chốt vào đơn).
- Kiểm: §5.0 (`apps.catalog apps.sales`); `nv_kho` không có `current_price`.

**Lô 14 — Nhân sự + Phân quyền ∥ B4, R16**
- BE: **mới** `backend/apps/accounts/capabilities/`, `apps/accounts/audit/api.py` (lọc `actor`), `apps/accounts/auth/services.py` (đổi 2 nhãn sai wording), `config/api_urls.py`.
- FE: `features/staff/**`, **mới** `features/permissions/**`, `app/(console)/staff/**`, `app/(console)/permissions/**`, `e2e/s41_s47_*.py`, `s48_password.py` giữ xanh, `e2e/ed_lo14_permissions.py`.
- Không: `apps/accounts/staff/services.py` (đổi nhóm người dùng), migration `accounts/*`.
- Kiểm: §5.0 (`apps.accounts`) + full; test §4 leo quyền.
- **Điểm dừng:** nếu codename nào trong registry B4 không tồn tại hoặc `nv_giao` mất quyền cần cho Lô 4 khi chạy test → dừng, báo.

**Lô 15 — Tổng quan, Nhật ký, Tài khoản, màn ngoài shell, AI (FE)**
- Được sửa: `features/overview/**`, `features/audit/**`, `features/auth/components/{AccountScreen,ChangePasswordForm,LoginScreen,SetPasswordScreen,NoRoleScreen}.tsx`, `features/ai/{settings,policy,report}/**`, `app/(console)/{overview,audit-logs,account,ai}/**`, `app/{login,set-password,no-role}/**`, e2e `s48_password.py`, `qa_lo7_*.py`, `l7_1_open_redirect.py` giữ xanh, `e2e/ed_lo15_misc.py`.
- Không: `features/ai/runtime/**`, `features/ai/commands/**`.
- Kiểm: §5.0 FE + `check-ai-chunks`.

**Lô 16 — Nội dung (FE)**
- Được sửa: `features/content/**`, `app/(console)/content/**`, e2e `ra_soat_cms*.py` giữ xanh, `e2e/ed_lo16_content.py`.
- Không: `features/content/editor/convert.ts`, `safeHref.ts` (logic an toàn).
- Kiểm: §5.0 FE.

**Lô 17 — Dọn dẹp, ⌘K theo mã, hồi quy (FE)**
- Xoá: `shared/ui/{RightRail,SideSheet,Sheet,Placeholder,StatusChip,EmptyRow,ThemeToggle}.tsx`, `shared/lib/status.ts`, `features/inventory/components/{ActivityFeed,ModalDialog,BatchDetailSheet}.tsx`, `features/orders/components/*Sheet.tsx`, `features/deliveries/components/DeliveryDetailModal.tsx`, `app/(console)/ai/actions/`, code mock `DH-…` — chỉ khi `grep` không còn chỗ dùng.
- ⌘K tra mã chứng từ khớp đúng (🟡 T5) qua endpoint list có sẵn với `q`.
- Kiểm: §5.0 FE + chạy **toàn bộ** `e2e/*.py` trên bản mock; `grep -rn "Làm mới\|NCC\|SĐT\|FEFO\|TTL\|hạch toán\|BR-" erp-console/app erp-console/features erp-console/shared --include=*.tsx` chỉ còn trong comment.

---

## 6. Câu hỏi kỹ thuật 🔴 (điều phối viên hỏi Duy)

| # | Câu hỏi | Vì sao | Đề xuất của Tech Lead |
|---|---|---|---|
| 🔴 Q1 (D-1) | "Điều chỉnh tồn" (W5k, F1j): bấm "Lưu điều chỉnh" có đổi tồn lô không? | Code hiện tại `StockEntry` chỉ lưu dòng, **không** đổi `qty_available`, không ghi Sổ nhập xuất. Cho đổi tồn = quy tắc kho mới (đụng giá vốn lô và lãi lỗ), ngoài phạm vi 01. | Đợt này chỉ làm **danh sách đọc**; ẩn nút "Điều chỉnh tồn". Muốn đổi tồn thì làm hồ sơ riêng (P-09). |
| 🔴 Q2 (D-2) | "Ngừng bán lô" (W2f) | Không có action, `Batch.Status` không có trạng thái tạm ngừng; thêm = đổi enum DB (01 §2 ngoài phạm vi). | Không hiện nút. Cách hiện có: ẩn mặt hàng khỏi Shop (W2h). |
| 🔴 Q3 (D-3) | Tiền hoá đơn mua (`PurchaseInvoice.amount`) với Quản lý | Spec §1.4 cho Quản lý xem hoá đơn mua; nhưng UI-RULES §1.7 coi "tiền nhà cung cấp" là khoá, và phiếu 1 dòng thì chia ra được giá mua/kg (giá vốn). 01 §6 ghi Hoá đơn mua là chỗ có thể rò. | Ẩn `amount` với người thiếu `view_costprice` (Quản lý vẫn thấy dòng hoá đơn, trạng thái đã trả). |
| 🔴 Q4 | Đóng danh sách cũ `GET /api/sales/customers/` với `nv_kho`? | `nv_kho` đang có `sales.view_customer` và đọc được toàn bộ khách qua endpoint cũ (FE không dùng). Quyết định 13: xem khách mặc định Chủ + Quản lý. Đóng lại sẽ đổi test S5 đã nghiệm thu. | Đóng `list` của endpoint cũ cho người không có `view_customer_list` (giữ `retrieve` có phạm vi cho `nv_giao`), sửa test S5 tương ứng. Làm như lô phụ sau Lô 6. |

### Duy trả lời (01/10/2026)
- **Q1:** chỉ làm danh sách Điều chỉnh tồn (đọc), ẩn nút "Điều chỉnh tồn". Không đổi tồn.
- **Q2:** bỏ nút "Ngừng bán lô".
- **Q3:** **Quản lý cũng thấy** tiền hoá đơn mua (`PurchaseInvoice.amount`) — giữ như hiện tại, không khoá.
- **Q4:** **giữ nguyên** endpoint cũ `/api/sales/customers/`, không đóng, không sửa test S5.
- Câu hỏi Q1–Q7 trong `02-stories.md`: dùng giá trị mặc định đã ghi ở đó.

---

## 7. Review (Việc 3 — để trống)
