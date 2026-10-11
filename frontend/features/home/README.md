# features/home

Trang chủ Shop `/` (SHOP-1-06, màn A1; banner và cam kết từ CMS ở SHOP-5-03).

- `components/HomeScreen.tsx`: banner, ô nhóm hàng (đếm từ `groups` của catalog), hàng "Đang có hàng" (ProductCard `rail`), "Combo nấu nhanh" (ProductCard `row`), Góc bếp (3 bài mới), dải cam kết (3 ô điện thoại, 2 ô máy tính).
- `homeBlocks.ts`: hàm thuần đọc thân bài CMS (02b §3.7.2). `home-banner`: mỗi slide = tiêu đề `##` + câu phụ + (tuỳ chọn) đoạn chỉ có một link nội bộ làm nút + (tuỳ chọn) ảnh; tối đa 3 slide; tóm tắt = dải chữ đầu trang. `home-commitments`: một danh sách, mỗi mục = **tiêu đề** + mô tả; điện thoại hiện 3 mục đầu, máy tính 2 mục đầu. Khối sai dạng thì bỏ qua.
- `homeContent.ts`: nạp hai trang trên (dùng chung với dải chữ của `ShopFrame`), cache khi có trang hoặc 404/410, bỏ cache khi lỗi mạng.
- Dữ liệu: `getCatalog()`, `getSiteInfo()` (hotline), `fetchPublicEntries()` (Góc bếp), `fetchPublicEntry("home-banner" | "home-commitments")`. Lỗi catalog hiện ErrorState với "Thử lại"; CMS chưa có banner/cam kết hoặc lỗi thì ẩn khối đó.
- Khẩu hiệu "Từ cảng về bếp nhà bạn" và ô phụ thanh toán là chữ giao diện, ở trong `HomeScreen.tsx`.
- Test: `node scripts/test-home-content.mjs`.
