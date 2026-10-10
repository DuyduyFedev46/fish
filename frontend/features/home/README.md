# features/home

Trang chủ Shop `/` (SHOP-1-06, màn A1).

- `components/HomeScreen.tsx`: banner, ô nhóm hàng (đếm từ `groups` của catalog), hàng "Đang có hàng" (ProductCard `rail`), "Combo nấu nhanh" (ProductCard `row`), Góc bếp (3 bài mới), dải cam kết (3 ô điện thoại, 2 ô máy tính).
- `content.ts`: chữ banner và cam kết lấy từ 06-marketing C5, chỉ dòng "ĐÃ ĐỐI CHIẾU". Không có "Cân đúng" (S-18). SHOP-5-03 chuyển sang CMS rồi xoá file.
- Dữ liệu: `getCatalog()` (`GET /api/shop/catalog/`), `getSiteInfo()` (hotline), `fetchPublicEntries()` (bài Góc bếp). Lỗi catalog hiện ErrorState với "Thử lại"; lỗi bài viết ẩn khối.
