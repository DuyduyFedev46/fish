import type { Metadata } from "next";
import { CartProvider } from "../../components/CartContext";
import ShopHeader from "../../components/ShopHeader";
import ShopFooter from "../../components/ShopFooter";

export const metadata: Metadata = {
  title: {
    default: "Shop — Cá Về",
    template: "%s | Shop Cá Về",
  },
  description: "Đặt mua hải sản đông lạnh: cá, tôm, mực, cua ghẹ và combo — giao tận nhà.",
};

export default function ShopLayout({ children }: { children: React.ReactNode }) {
  return (
    <CartProvider>
      <ShopHeader />
      <main className="shop-main">{children}</main>
      <ShopFooter />
    </CartProvider>
  );
}
