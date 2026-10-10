# catalog/items — Mặt hàng & combo (P-01)

Nhóm hàng, mặt hàng (luôn Kg, BR-DM-01), combo = mặt hàng BUNDLE + công thức `BundleLine` (không lồng combo, BR-DM-05).
`services.sellable_qty`: tồn khả dụng NỘI BỘ (ERP, tạo đơn), không bao giờ ra API công khai; Shop chỉ nhận `stock_level` (`in`/`low`/`out`, BR-BH-23) từ `services.stock_level`; combo tính theo thành phần khan nhất (BR-DM-06), chỉ lô còn hạn (BR-LO-02).
Endpoint: `/api/catalog/item-groups/`, `/api/catalog/items/`, `/api/catalog/bundle-lines/`; Shop: `GET /api/shop/catalog/`, `GET /api/shop/catalog/{item_code}/` (không có giá vốn).
`ItemSerializer`/Shop API có thêm field `image` (null khi chưa có ảnh) — dữ liệu ảnh và endpoint tải/gỡ nằm ở module `apps/catalog/images/` (xem README ở đó). `?has_image=true|false` lọc theo có/chưa có ảnh (UC-A5).
R14 (ERP theo design, Lô 13): `items` có thêm `current_price` (giá bán đang hiệu lực, chỉ khi có `catalog.view_itemprice`, tức Chủ và Quản lý; `warehouse_staff` không thấy), lọc `item_group`, `is_active`, `item_type`; `item-groups` có `parent_name`, `item_count`. Bộ đọc tham số lọc ở `filters.py` (sai → 400 `INVALID_FILTER`). Test: `tests/test_r14_items.py`.
