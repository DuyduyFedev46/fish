/**
 * Cờ build bật/tắt toàn bộ giao diện AI (SR-HIDE-AI-01). Chỉ đúng "1" mới bật; vắng cờ hoặc giá trị khác là TẮT
 * (mặc định ở mọi môi trường, kể cả mock). Đặt cờ ở MỘT chỗ này; nơi khác import, không đọc process.env trực tiếp.
 * Tắt thì chỉ ẩn giao diện (menu, trang /ai/*, khối Trợ lý AI, nút AI), không xoá code AI.
 */
export const AI_FEATURES_ENABLED: boolean = process.env.NEXT_PUBLIC_AI_FEATURES === "1";

/** Kiểu tối thiểu của người dùng đang đăng nhập (không import `features/auth` để `shared/` không phụ thuộc module). */
export type AiVisibleMe = { ai_features_enabled?: boolean } | null | undefined;

/**
 * Giao diện AI chỉ hiện khi cờ build BẬT và BE báo bật (`/api/auth/me/` → `ai_features_enabled`, W39).
 * `me` chưa tải xong coi như tắt (không nháy giao diện AI). Cờ build PHẢI đứng đầu biểu thức `&&`
 * để bundler gấp hằng `false` và bỏ chunk AI (scripts/check-ai-chunks.mjs).
 */
export function aiVisible(me: AiVisibleMe): boolean {
  return AI_FEATURES_ENABLED && me?.ai_features_enabled === true;
}
