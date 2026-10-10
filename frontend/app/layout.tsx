import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "./legacy.css";
import { CartProvider } from "@/components/CartContext";
import { ToastProvider } from "@/components/ui/Toast";

// Inter tải lúc build và tự host trong out/_next/static/media: lúc chạy không có request nào tới
// fonts.googleapis.com hay fonts.gstatic.com (SHOP-1-01 AC2).
const inter = Inter({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "Cá Về — Hải sản cấp đông theo lô, giao tận nhà",
    template: "%s | Cá Về",
  },
  description:
    "Hải sản cấp đông theo kg, từ 1 kg: cá, tôm, mực, cua ghẹ và combo nấu nhanh. Thanh toán quét mã QR, giao tận nhà.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi" className={inter.variable}>
      <body>
        <CartProvider>
          <ToastProvider>{children}</ToastProvider>
        </CartProvider>
      </body>
    </html>
  );
}
