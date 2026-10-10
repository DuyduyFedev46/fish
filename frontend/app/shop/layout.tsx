import type { Metadata } from "next";

// Khung trang (header, footer, thanh đáy) do từng màn tự bọc bằng <ShopFrame>; CartProvider đã ở app/layout.tsx.
export const metadata: Metadata = {
  // Gốc đã có template "%s | Cá Về"; nhóm /shop/ ghi trọn tiêu đề mặc định, không để lặp tên.
  title: {
    default: "Shop hải sản cấp đông | Cá Về",
    template: "%s | Cá Về",
  },
  description: "Đặt mua hải sản đông lạnh: cá, tôm, mực, cua ghẹ và combo — giao tận nhà.",
};

export default function ShopLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
