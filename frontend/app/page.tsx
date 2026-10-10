import type { Metadata } from "next";
import HomeScreen from "@/features/home/components/HomeScreen";

// SHOP-1-09 AC2, AC3 (06-marketing C8; S-08 khu vực Phan Thiết). Title <= 60, description <= 160 ký tự,
// không ngoặc vuông, không "Lô mới", "miễn phí giao", "tươi sống" (UI-RULES §6.4).
const TITLE = "Cá Về — Hải sản cấp đông theo lô, giao tận nhà";
const DESCRIPTION =
  "Mua hải sản cấp đông theo kg, từ 1 kg: cá, tôm, mực, cua ghẹ và combo nấu nhanh. Thanh toán quét mã QR, giao tận nhà ở Phan Thiết.";

export const metadata: Metadata = {
  title: { absolute: TITLE },
  description: DESCRIPTION,
  openGraph: { title: TITLE, description: DESCRIPTION, type: "website", locale: "vi_VN" },
};

export default function HomePage() {
  return <HomeScreen />;
}
