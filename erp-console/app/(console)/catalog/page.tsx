import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CatalogScreen } from "@/features/catalog/components/CatalogScreen";

// A2 (doc/features/2026-09-26-anh-mat-hang/02-stories.md): màn Danh mục tối thiểu — danh sách mặt
// hàng có ảnh thu nhỏ + tải/thay ảnh. Cần catalog.view_item; nút ảnh riêng cần catalog.change_item_image
// (CatalogScreen tự ẩn nút, không phải ViewGuard — Tầng 2 chỉ khoá MỘT hành động, không khoá cả màn).
// Sửa tên, nhóm, hạn dùng, ẩn/hiện vẫn thuộc S38 (chưa làm ở đây).
export default function Page() {
  return (
    <ViewGuard view="catalog">
      <CatalogScreen />
    </ViewGuard>
  );
}
