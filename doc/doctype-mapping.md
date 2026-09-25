# Level 2 — Mapping Doctype ERPNext → Hệ thống cảng cá Lộc

Nguồn: đọc trực tiếp schema JSON từ repo github.com/frappe/erpnext (branch develop), không suy đoán từ docs tóm tắt.

## Phát hiện quan trọng — ERPNext đã có sẵn cơ chế đơn giản hoá đúng cho use case này

- **Sales Invoice** có field `is_pos` (Include Payment - POS): bán + trừ kho + ghi nhận thanh toán trong 1 bước, không bắt buộc qua Sales Order → Delivery Note → Sales Invoice.
- **Customer** có 2 toggle: `so_required` (Allow sales invoice creation without sales order) và `dn_required` (Allow sales invoice creation without delivery note) — set false thì bỏ được cả Sales Order lẫn Delivery Note hợp lệ, đúng chuẩn ERPNext chứ không phải custom.
- **Supplier** có 2 toggle tương ứng: `allow_purchase_invoice_creation_without_purchase_order` / `..._without_purchase_receipt` — cho phép bỏ Purchase Order khi mua trực tiếp tại cảng.
- **Item**: `shelf_life_in_days` + `has_batch_no` + `has_expiry_date` → khi nhập kho, ERPNext tự tính `Batch.expiry_date` từ shelf_life_in_days. Đúng khớp quyết định "hạn dùng theo lô, mặc định 3 tháng" đã chốt trước đó — không cần build riêng.
- **Stock Reconciliation**: field `difference_amount`, purpose = "Stock Reconciliation" → chính là công cụ kiểm kê định kỳ, giải gap "đo hao hụt hàng đông lạnh" còn treo.

## Bảng mapping theo module

### KHO (Stock)
| Doctype ERPNext | Field chính dùng | Quyết định |
|---|---|---|
| Item | item_code, item_group, stock_uom=Kg, shelf_life_in_days=90, has_batch_no, has_expiry_date, standard_rate | **Giữ** — master chính |
| Item Group | tree structure | **Giữ** — phân loại cá/tôm/mực/cua |
| UOM | — | **Giữ**, chỉ cần "Kg", bỏ multi-UOM conversion |
| Batch | batch_id, item, expiry_date (auto), batch_qty, supplier | **Giữ** — trái tim vận hành, gắn cả nguồn cung theo mùa |
| Warehouse | warehouse_name, is_group=false | **Giữ**, đơn giản: 1 kho duy nhất |
| Price List + Item Price | price_list_rate, valid_from/valid_upto | **Giữ**, 1 price list "Bán lẻ"; valid_from/upto để đổi giá theo mùa mà không sửa Item gốc |
| Stock Entry | purpose=Material Receipt | **Giữ** — nhập kho ban đầu khi gom hàng |
| Stock Reconciliation | items, difference_amount | **Giữ** — kiểm kê định kỳ, giải gap hao hụt |
| Delivery Note | — | **Bỏ** — không giao hàng |

### MUA HÀNG (Buying)
| Doctype ERPNext | Quyết định |
|---|---|
| Supplier | **Giữ**, tối giản (supplier_name, supplier_type=Individual), set `allow_purchase_invoice_creation_without_purchase_order=true` |
| Purchase Order | **Cân nhắc bỏ** — mua trực tiếp tại cảng, không đặt trước |
| Purchase Receipt | **Giữ** — bước nhập kho theo lô thực tế, sinh Batch tự động |
| Purchase Invoice | **Giữ**, nhưng cân nhắc gộp chung bước với Purchase Receipt nếu trả tiền mặt ngay tại cảng (is_paid=true) |

### BÁN HÀNG (Selling)
| Doctype ERPNext | Quyết định |
|---|---|
| Customer | **Giữ** tối giản (customer_name, mobile_no), set `so_required=false`, `dn_required=false` |
| Quotation | **Bỏ** — giá niêm yết, không báo giá |
| Sales Order | **Bỏ** (nhờ toggle so_required) — trừ khi web shop cần trạng thái "chờ xác nhận" trước khi trừ kho (xem câu hỏi mở #1) |
| Sales Invoice | **Giữ**, `is_pos=true` — trung tâm bán hàng: bán + trừ kho (theo batch, FIFO) + thanh toán trong 1 bước |
| Payment Entry | Có thể không cần riêng — Sales Invoice is_pos đã có bảng payments tích hợp |
| Delivery Note | **Bỏ** — khớp quyết định không giao hàng |

## Câu hỏi mở cần chốt

1. Khi khách đặt trên shop online (giỏ hàng), đơn có cần trạng thái "chờ xác nhận/chờ lấy hàng" trước khi trừ kho + xuất hoá đơn luôn không? Nếu có → cần giữ 1 doctype dạng "Order" trung gian trước khi convert sang Sales Invoice, không thể bỏ hẳn Sales Order.
2. Mua hàng tại cảng trả tiền ngay hay gối đầu vài ngày với đầu mối quen? → quyết định Purchase Invoice tách khỏi Purchase Receipt hay gộp 1 bước.
3. Giá niêm yết đổi theo mùa (nguồn khan/nhiều) — có cần lưu lịch sử giá (Item Price với valid_from/valid_upto) hay chỉ cần giá hiện tại trên Item?

## Nguồn tham chiếu (schema đọc trực tiếp từ repo)

- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/item/item.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/batch/batch.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/warehouse/warehouse.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/price_list/price_list.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/item_price/item_price.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/stock_entry/stock_entry.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/stock_reconciliation/stock_reconciliation.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/purchase_receipt/purchase_receipt.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/stock/doctype/delivery_note/delivery_note.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/buying/doctype/supplier/supplier.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/buying/doctype/purchase_order/purchase_order.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/accounts/doctype/purchase_invoice/purchase_invoice.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/selling/doctype/customer/customer.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/selling/doctype/sales_order/sales_order.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/accounts/doctype/sales_invoice/sales_invoice.json
- https://github.com/frappe/erpnext/blob/develop/erpnext/accounts/doctype/payment_entry/payment_entry.json
