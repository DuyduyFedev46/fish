// Khung thử (QA) vẽ ListPage/DataTable/FilterBar/Tabs/Chip/Toast/ErrorScreen/NotFoundScreen với dữ liệu giả.
// Build:  cd erp-console && node_modules/.bin/vite build --config e2e/qa_harness_ed_batch1/vite.config.mjs
// Phục vụ: (cd e2e/qa_harness_ed_batch1/dist && python3 -m http.server 3102)   rồi   python3 e2e/qa_ed_batch1_template.py
// Không thuộc sản phẩm: chỉ dùng cho QA; dist/ không commit.
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const app = path.resolve(here, "../..");
const nm = (p) => path.join(app, "node_modules", p);

export default {
  root: here,
  publicDir: path.join(app, "public"),
  resolve: {
    alias: [
      { find: "next/link", replacement: path.join(here, "stubs/link.tsx") },
      { find: "next/navigation", replacement: path.join(here, "stubs/navigation.ts") },
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
