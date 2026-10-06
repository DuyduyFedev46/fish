// Khung thử (QA) cho mẫu trang chi tiết, popup, form, khối Trợ lý AI. Dữ liệu giả. Không thuộc sản phẩm.
// Build:  cd erp-console && node_modules/.bin/vite build --config e2e/qa_harness_ed_batch2/vite.config.mjs
// Phục vụ: (cd e2e/qa_harness_ed_batch2/dist && python3 -m http.server 3103)   rồi   python3 e2e/qa_ed_batch2_harness.py
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const app = path.resolve(here, "../..");
const nm = (p) => path.join(app, "node_modules", p);
const b1 = path.join(here, "../qa_harness_ed_batch1/stubs");

export default {
  root: here,
  publicDir: path.join(app, "public"),
  define: {
    "process.env.NEXT_PUBLIC_USE_MOCK": '"0"',
    "process.env.NEXT_PUBLIC_API_BASE": '"http://api.qa.test"',
    "process.env.NODE_ENV": '"production"',
  },
  resolve: {
    alias: [
      { find: "next/link", replacement: path.join(b1, "link.tsx") },
      { find: "next/navigation", replacement: path.join(b1, "navigation.ts") },
      { find: "next/dynamic", replacement: path.join(here, "stubs/dynamic.tsx") },
      { find: /^\.\/AiAssistantPanel$/, replacement: path.join(here, "stubs/AiAssistantPanel.tsx") },
      { find: "@/features/auth/components/AuthProvider", replacement: path.join(here, "stubs/AuthProvider.tsx") },
      { find: /^@\//, replacement: app + "/" },
      { find: "react/jsx-runtime", replacement: nm("react/jsx-runtime.js") },
      { find: /^react-dom\/client$/, replacement: nm("react-dom/client.js") },
      { find: /^react$/, replacement: nm("react/index.js") },
      { find: /^react-dom$/, replacement: nm("react-dom/index.js") },
    ],
  },
  oxc: { jsx: { runtime: "automatic" } },
  server: { fs: { strict: false } },
  build: { outDir: path.join(here, "dist"), emptyOutDir: true, minify: false },
};
