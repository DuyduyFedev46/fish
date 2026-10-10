// Kiểu dữ liệu module catalog: A2 (ảnh mặt hàng) và Lô 13 (ED-30, ED-31: mặt hàng, bảng giá, ưu đãi, nhóm hàng).
// Hình dạng theo contract BE R14 (backend/apps/catalog/items, pricing). Tiền là chuỗi thập phân ("215000.00");
// ngày hiệu lực là NGÀY THUẦN ("2026-10-05"), không phải ngày giờ. Không có field giá vốn nào ở module này.

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

/** Giá BÁN đang hiệu lực. BE chỉ trả cho người có `catalog.view_itemprice` (Chủ, Quản lý); NV kho không có key. */
export type CurrentPrice = { rate: string; valid_from: string; valid_upto: string | null };

/** Một thành phần của combo: định mức kg cho MỘT combo. */
export type BundleLine = {
  id: number;
  bundle: number;
  component: number;
  component_code: string;
  component_name: string;
  qty_per_bundle: string;
};

export type CatalogItem = {
  id: number;
  code: string;
  name: string;
  item_group: number;
  /** Tên nhóm hàng — BE trả kèm. */
  group_name: string;
  item_type: ItemType;
  stock_uom: string;
  shelf_life_in_days: number;
  has_batch_no: boolean;
  has_expiry_date: boolean;
  is_active: boolean;
  description: string;
  /** Thông tin hiển thị trên Shop (SHOP-2b-01). Chỉ Chủ ghi được; BE kiểm: không SĐT, giá, mã lô. */
  short_note: string;
  spec: string;
  storage: string;
  origin: string;
  bundle_lines: BundleLine[];
  image: CatalogItemImage | null;
  /** Không có key với người thiếu `catalog.view_itemprice`; `null` = chưa có giá hiệu lực. */
  current_price?: CurrentPrice | null;
};

/** Thân POST /api/catalog/items/. Combo: công thức gửi riêng qua `bundle-lines`. */
export type ItemInput = {
  code: string;
  name: string;
  item_group: number;
  item_type: ItemType;
  stock_uom: string;
  shelf_life_in_days: number;
  has_batch_no: boolean;
  has_expiry_date: boolean;
  is_active: boolean;
  description: string;
  short_note?: string;
  spec?: string;
  storage?: string;
  origin?: string;
};

/** PATCH một phần: chỉ trường đổi. Chủ mới được (catalog.change_item). */
export type ItemPatch = Partial<Pick<ItemInput, "name" | "description" | "is_active" | "short_note" | "spec" | "storage" | "origin">>;

export type BundleLineInput = { bundle: number; component: number; qty_per_bundle: string };

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

/** Bộ lọc ảnh cũ của A2 — `listItems("all")` vẫn dùng ở form Nhập lô (features/purchasing). */
export type ImageFilter = "all" | "with_image" | "without_image";

/** Tham số danh sách mặt hàng. Rỗng = không lọc (BE: rỗng hoặc khoảng trắng không lọc, sai giá trị → 400 INVALID_FILTER). */
export type ItemListParams = {
  group: string;
  type: "" | ItemType;
  /** "" | "1" | "0". */
  active: string;
  /** "" | "1" (có ảnh) | "0" (chưa có ảnh). */
  hasImage: string;
};

export const EMPTY_ITEM_PARAMS: ItemListParams = { group: "", type: "", active: "", hasImage: "" };

export type ItemGroup = {
  id: number;
  name: string;
  parent: number | null;
  parent_name: string | null;
  /** Đường dẫn của nhóm trên Shop (`/shop/?group=<slug>`). */
  slug: string;
  /** Số mặt hàng thuộc nhóm, kể cả đang ẩn. */
  item_count: number;
};

export type ItemGroupInput = { name: string; parent: number | null; /** Bỏ trống khi tạo thì BE tự sinh từ tên. */ slug?: string };

/** PATCH nhóm hàng: hiện chỉ đổi đường dẫn (slug). */
export type ItemGroupPatch = { slug: string };

export type PriceList = { id: number; name: string; currency: string; is_default: boolean };

export type ItemPrice = {
  id: number;
  price_list: number;
  item: number;
  item_name: string;
  item_code: string;
  rate: string;
  valid_from: string;
  valid_upto: string | null;
};

export type ItemPriceInput = { price_list: number; item: number; rate: string; valid_from: string; valid_upto: string | null };

export type RuleApplyOn = "ITEM" | "ORDER";
export type RuleDiscountType = "AMOUNT" | "PERCENT";

export type PricingRule = {
  id: number;
  name: string;
  is_active: boolean;
  apply_on: RuleApplyOn;
  item: number | null;
  item_name: string | null;
  min_qty: string | null;
  min_amount: string | null;
  discount_type: RuleDiscountType;
  discount_value: string;
  valid_from: string | null;
  valid_upto: string | null;
};

export type PricingRuleInput = {
  name: string;
  is_active: boolean;
  apply_on: RuleApplyOn;
  item: number | null;
  min_qty: string | null;
  min_amount: string | null;
  discount_type: RuleDiscountType;
  discount_value: string;
  valid_from: string | null;
  valid_upto: string | null;
};

export type PricingRuleListParams = {
  /** "" | "1" | "0". */
  active: string;
  applyOn: "" | RuleApplyOn;
};

export type ItemPriceListParams = { item: number | null };
