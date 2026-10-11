# catalog — Danh mục & giá (P-01)

Master data: mặt hàng (bán theo Kg), combo (BUNDLE + công thức), bảng giá theo hiệu lực, ưu đãi 1 tầng.
BR chính: BR-DM-01 (Kg), BR-DM-02 (giá theo hiệu lực), BR-DM-05/06 (combo), BR-DM-08 (ưu đãi không cộng dồn).
Model: `models/` (items, pricing, images, vouchers).

| Module | Làm gì |
|---|---|
| `items/` | nhóm hàng, mặt hàng, công thức combo; Shop API danh mục (giá + tồn khả dụng) |
| `pricing/` | bảng giá, giá niêm yết, ưu đãi (PricingRule); hàm giá hiệu lực |
| `vouchers/` | mã giảm giá công khai (BR-DM-17…24): model `Voucher`, API ERP (`manage_voucher`), kiểm mã Shop, `evaluate_voucher` dùng chung với tạo đơn |
| `images/` | ảnh mặt hàng (1 ảnh/mặt hàng, BR-DM-09..16): kiểm tệp, xử lý (Pillow), lưu trữ (local/GCS), quyền `catalog.change_item_image` |
