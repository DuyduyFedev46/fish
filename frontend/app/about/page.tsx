import type { Metadata } from "next";
import AboutScreen from "./AboutScreen";

// SHOP-1-08, SHOP-1-09 AC2 (06-marketing C8). Chữ SEO trùng `seo_title`/`seo_description` của trang CMS `gioi-thieu`
// (nguồn: backend/apps/content/management/shop_content/pages.json). Trang tĩnh nên metadata phải có lúc build.
// Không ngoặc vuông, không "Lô mới", "miễn phí giao", "tươi sống" (UI-RULES §6.4).
const TITLE = "Giới thiệu Cá Về — Từ cảng về bếp nhà bạn";
const DESCRIPTION =
  "Cá Về mua hải sản theo từng lô tại cảng, bán hàng cấp đông theo kg và giao tận nhà ở Phan Thiết. Xem cách chúng tôi mua, bảo quản và giao hàng.";

export const metadata: Metadata = {
  title: { absolute: TITLE },
  description: DESCRIPTION,
  openGraph: { title: TITLE, description: DESCRIPTION, type: "website", locale: "vi_VN" },
};

export default function AboutPage() {
  return <AboutScreen />;
}
