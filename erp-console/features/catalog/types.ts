// Kiểu dữ liệu module catalog (A2, A3 — doc/features/2026-09-26-anh-mat-hang/02-stories.md).
// Màn Danh mục tối thiểu: danh sách mặt hàng có ảnh thu nhỏ + tải/thay ảnh. Phần sửa tên, nhóm,
// hạn dùng, ẩn/hiện vẫn thuộc S38 (chưa làm ở đây).
//
// Mẫu JSON rút gọn của A2 (02-stories.md) chỉ liệt `item_group` (ID số); BE thật (04-qa-report.md,
// đối chiếu qua e2e/a2_catalog_real.py) trả kèm `group_name` (chuỗi) — dùng field đó để hiện tên
// nhóm thay vì "Nhóm #<id>". Response còn nhiều field khác của `ItemSerializer` đầy đủ (stock_uom,
// shelf_life_in_days, has_batch_no, has_expiry_date, description, bundle_lines…) — TS bỏ qua field
// thừa không khai ở đây, an toàn vì FE chỉ đọc field mình cần.

export type ItemType = "SIMPLE" | "BUNDLE";

export type ItemImageUrls = { thumb: string; card: string; detail: string };

/** `image` trong danh sách/chi tiết mặt hàng (GET) — như response tải ảnh nhưng BỎ `uploaded_by`. */
export type CatalogItemImage = {
  id: string;
  alt: string;
  is_illustration: boolean;
  urls: ItemImageUrls;
  uploaded_at: string;
};

/** `image` trong response tải/thay ảnh (POST) — có thêm `uploaded_by`. */
export type UploadedItemImage = CatalogItemImage & { uploaded_by: string };

export type CatalogItem = {
  id: number;
  code: string;
  name: string;
  item_group: number;
  /** Tên nhóm hàng — BE thật trả kèm dù không có trong mẫu JSON rút gọn của 02-stories.md. */
  group_name: string;
  item_type: ItemType;
  is_active: boolean;
  image: CatalogItemImage | null;
};

export type ImageWarning = { code: string; message: string };

export type UploadImageResponse = {
  item_id: number;
  item_code: string;
  image: UploadedItemImage;
  warnings: ImageWarning[];
};

export type UploadImageInput = {
  file: File;
  /** Rỗng → BE dùng tên mặt hàng làm alt (A2-AC1). */
  altText: string;
  isIllustration: boolean;
  /** id ảnh FE đang thấy lúc mở form; rỗng = chưa có ảnh. Khác trên máy chủ → 409 (A2-AC13). */
  expectedImageId: string;
};

/** Bộ lọc màn Danh mục — UC-A5: "Chưa có ảnh" để Chủ gắn ảnh dần. */
export type ImageFilter = "all" | "with_image" | "without_image";
