/**
 * Cờ build bật/tắt toàn bộ giao diện AI (SR-HIDE-AI-01). Chỉ đúng "1" mới bật; vắng cờ hoặc giá trị khác là TẮT
 * (mặc định ở mọi môi trường, kể cả mock). Đặt cờ ở MỘT chỗ này; nơi khác import, không đọc process.env trực tiếp.
 * Tắt thì chỉ ẩn giao diện (menu, trang /ai/*, khối Trợ lý AI, nút AI), không xoá code AI.
 */
export const AI_FEATURES_ENABLED: boolean = process.env.NEXT_PUBLIC_AI_FEATURES === "1";
