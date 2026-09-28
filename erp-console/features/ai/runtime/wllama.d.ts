// @wllama/wllama chưa cài (Lô 4 — S17 chốt model mới cài). Shim kiểu để TypeScript
// qua được `import(/* webpackIgnore: true */ "@wllama/wllama")`; lúc chạy thiếu gói
// thì wllama.ts bắt lỗi và trả thông báo fail-closed. Xoá file này khi cài thật.
declare module "@wllama/wllama";
