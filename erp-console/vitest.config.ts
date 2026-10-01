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
  },
});


