import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "@/shared/ui/tokens.css";
import "@/shared/ui/globals.css";
import { AuthProvider } from "@/features/auth/components/AuthProvider";
import { THEME_INIT_SCRIPT } from "@/shared/ui/themeScript";

// Tự host font (C.6/K8 — QA baseline 27/09: LCP mobile 2829ms do 2 stylesheet Google Fonts
// render-blocking + preconnect):
// - Inter + JetBrains Mono: next/font/google tải font LÚC BUILD → tự host, không request runtime.
//   (tokens.css: --font-sans/--font-mono trỏ tới var(--font-inter)/var(--font-jetmono).)
// - Material Symbols (font icon biến trục — next/font không tự host được): tập con tự cắt ở
//   public/fonts/ms/ (scripts/subset-material-symbols.py) + css local, KHÔNG còn request Google.
// KHÔNG được thêm lại <link> font Google vào đây; KHÔNG preload model AI/wasm vào metadata (C.2).

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-inter",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  variable: "--font-jetmono",
});

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
    <html lang="vi" suppressHydrationWarning className={`${inter.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <link rel="stylesheet" href="/fonts/material-symbols.css" />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
