/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export lên Firebase Hosting site cangca-erp (không có server lúc chạy).
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  // Luôn định nghĩa cờ mock lúc build (mặc định "0") để bản build thật loại bỏ hẳn code mock.
  env: {
    NEXT_PUBLIC_USE_MOCK: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? "1" : "0",
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
