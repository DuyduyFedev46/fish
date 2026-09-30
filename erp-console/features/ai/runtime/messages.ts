// Chuỗi tiếng Việt CHỈ dùng trong runtime AI (chạy trên máy). Tách khỏi `../messages.ts` vì file đó được layout
// nạp tĩnh: để chuỗi này ở đó thì tên thư viện AI (wllama) lọt vào chunk ban đầu của mọi màn (SR-20, F13, BR-AI-17).
// Chỉ các file trong `features/ai/runtime/` được import file này.

export const AI_RUNTIME_MSG = {
  /** Lô 1–3: @wllama/wllama chưa cài (chờ S17 chốt model) — fail-closed, vẫn nhập tay được. */
  wllamaMissing: "Thư viện chạy AI chưa được cài (đang chờ chốt model). Bạn vẫn nhập tay như bình thường.",
} as const;
