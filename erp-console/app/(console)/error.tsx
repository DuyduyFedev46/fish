"use client";

// Chặn lỗi runtime của MỘT màn trong console để không sập toàn app. Next.js: error.tsx cùng thư mục với layout.tsx chỉ
// bọc {children} — Shell/menu (ConsoleGate) vẫn còn, người dùng đổi màn khác được ngay cả khi một màn đang lỗi.
// "Thử lại" gọi `reset()` để vẽ lại đúng cây con đó. Code ở đây KHÔNG ghi nội dung lỗi ra console/log.
// Lưu ý: React tự ghi thông điệp lỗi gốc ra console, nên quy ước: không đặt dữ liệu khách (tên, SĐT, địa chỉ) vào thông điệp của `Error`.
import { ErrorInApp } from "@/features/auth/components/AppStates";

export default function ConsoleError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <ErrorInApp onRetry={reset} />;
}
