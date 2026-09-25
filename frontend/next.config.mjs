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
};

export default nextConfig;
