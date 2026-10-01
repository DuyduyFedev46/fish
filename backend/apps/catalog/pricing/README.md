# catalog/pricing — Bảng giá & ưu đãi (P-01)

Giá niêm yết theo khoảng hiệu lực (BR-DM-02, `services.effective_price`); ưu đãi 1 tầng `PricingRule` (BR-DM-08 — áp ở `sales/orders`).
Endpoint: `/api/catalog/price-lists/`, `/api/catalog/item-prices/`, `/api/catalog/pricing-rules/`. Test: `tests/test_r14_pricing.py`
(R14) và `sales/orders/tests` (áp giá, ưu đãi).
R14 (Lô 13): `item-prices` có `item_name`, `item_code`, lọc `?item=`; `pricing-rules` có `item_name`, lọc `is_active`, `apply_on`.
T9: ghi giá bán và ưu đãi chỉ Chủ; Quản lý chỉ xem. `serializers.py` kiểm ngày kết thúc ≥ ngày bắt đầu, phần trăm ≤ 100, điều kiện theo `apply_on` (ED-31-AC3).
`services.current_item_price` / `prefetch_current_prices`: giá hiệu lực dùng chung cho Shop và danh sách ERP.
`services.set_item_price` (POST `item-prices/`): đóng giá cũ bằng `valid_from mới − 1 ngày`, chặn chồng lấn BR-DM-03 (400 mã `BR-DM-03`), audit `create_itemprice`/`close_itemprice`; PATCH qua `update_item_price`.
Không xoá cứng: `DELETE` ba endpoint này trả 405 cho mọi người đã đăng nhập (`NoHardDeleteMixin`); tắt ưu đãi bằng `is_active=false`, đóng giá bằng `valid_upto`.
`rate`, `min_qty`, `discount_value` phải > 0 (400 tiếng Việt). Nhóm hàng chống vòng ở `items/serializers.py::validate_parent`.
