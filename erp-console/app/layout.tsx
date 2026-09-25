import type { Metadata, Viewport } from "next";
import "@/shared/ui/tokens.css";
import "@/shared/ui/globals.css";
import { AuthProvider } from "@/features/auth/components/AuthProvider";
import { THEME_INIT_SCRIPT } from "@/shared/ui/themeScript";

export const metadata: Metadata = {
  title: { default: "Vận hành Cá Về", template: "%s · Vận hành Cá Về" },
  description: "Bảng điều hành nội bộ Cá Về: đơn, tiền, giao hàng, kho theo lô.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  // theme-color: không khai ở đây — THEME_INIT_SCRIPT đọc token --canvas (tokens.css) để khớp cả khi bấm đổi giao diện.
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
        />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block"
        />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
