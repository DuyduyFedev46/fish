import type { Metadata } from "next";
import "./globals.css";
import SiteLegalFooter from "@/features/site/components/SiteLegalFooter";

export const metadata: Metadata = {
  title: {
    default: "Cá Về — Vựa hải sản đông lạnh",
    template: "%s | Cá Về",
  },
  description:
    "Cá Về — vựa hải sản đông lạnh tươi ngon, giao tận nhà. Cá, tôm, mực, cua ghẹ và combo hải sản giá tốt.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>
        {children}
        <SiteLegalFooter />
      </body>
    </html>
  );
}
