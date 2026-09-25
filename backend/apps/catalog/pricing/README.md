# catalog/pricing — Bảng giá & ưu đãi (P-01)

Giá niêm yết theo khoảng hiệu lực (BR-DM-02, `services.effective_price`); ưu đãi 1 tầng `PricingRule` (BR-DM-08 — áp ở `sales/orders`).
Endpoint: `/api/catalog/price-lists/`, `/api/catalog/item-prices/`, `/api/catalog/pricing-rules/`. Chưa có test riêng
(giá & ưu đãi được kiểm qua `sales/orders/tests`).
