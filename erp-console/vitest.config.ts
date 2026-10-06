import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
    },
  },
  // tsconfig đặt jsx=preserve cho Next; test dựng component (react-dom/server) cần biến đổi JSX tự động.
  oxc: { jsx: { runtime: "automatic" } },
  test: {
    environment: "node",
    // Các test AI có sẵn kiểm giao diện AI đang bật; test của trạng thái tắt mock `@/shared/lib/features` (SR-HIDE-AI-01).
    env: { NEXT_PUBLIC_AI_FEATURES: "1" },
  },
});


