# catalog — Danh mục & giá (P-01)

Master data: mặt hàng (bán theo Kg), combo (BUNDLE + công thức), bảng giá theo hiệu lực, ưu đãi 1 tầng.
BR chính: BR-DM-01 (Kg), BR-DM-02 (giá theo hiệu lực), BR-DM-05/06 (combo), BR-DM-08 (ưu đãi không cộng dồn).
Model: `models/` (items, pricing).

| Module | Làm gì |
|---|---|
| `items/` | nhóm hàng, mặt hàng, công thức combo; Shop API danh mục (giá + tồn khả dụng) |
| `pricing/` | bảng giá, giá niêm yết, ưu đãi (PricingRule); hàm giá hiệu lực |
