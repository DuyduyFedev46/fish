/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export để deploy lên Firebase Hosting (phục vụ tĩnh, không cần Cloud Functions).
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Trang xem thử component `/ui-preview/` (file `page.preview.tsx`) chỉ được dựng khi build có cờ
  // NEXT_PUBLIC_UI_PREVIEW=1. Không cờ thì Next không thấy route, bản production không có trang này (SHOP-1-02 AC2).
  pageExtensions:
    process.env.NEXT_PUBLIC_UI_PREVIEW === "1"
      ? ["tsx", "ts", "preview.tsx"]
      : ["tsx", "ts"],
};

export default nextConfig;
