# catalog/items — Mặt hàng & combo (P-01)

Nhóm hàng, mặt hàng (luôn Kg, BR-DM-01), combo = mặt hàng BUNDLE + công thức `BundleLine` (không lồng combo, BR-DM-05).
`services.sellable_qty`: tồn khả dụng Shop; combo tính theo thành phần khan nhất (BR-DM-06), chỉ lô còn hạn (BR-LO-02).
Endpoint: `/api/catalog/item-groups/`, `/api/catalog/items/`, `/api/catalog/bundle-lines/`; Shop: `GET /api/shop/catalog/`, `GET /api/shop/catalog/{item_code}/` (không có giá vốn).
