"use client";

// Chặn lỗi runtime của MỘT màn trong console, để không sập toàn app (QA 04-qa-report.md, gợi ý sau B1:
// "Cân nhắc thêm error boundary tối thiểu cho route (console)"). Next.js: file error.tsx trong CÙNG
// thư mục với layout.tsx chỉ bọc {children} — Shell/menu ở layout.tsx (ConsoleGate) vẫn còn, người dùng
// đổi màn khác được ngay cả khi một màn đang lỗi. "Thử lại" gọi `reset()` để render lại đúng cây con đó.

import { useEffect } from "react";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";

export default function ConsoleError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[console] Lỗi màn:", error);
  }, [error]);

  return (
    <div className="empty" role="alert">
      <div className="big">
        <Icon name="error" />
      </div>
      <h2>Màn này gặp lỗi</h2>
      <p>
        Một phần của trang không tải được. Thử lại, hoặc quay về{" "}
        <Link href="/overview/">Tổng quan</Link>. Nếu còn lỗi, báo kỹ thuật kèm giờ xảy ra.
      </p>
      <button type="button" className="btn" onClick={() => reset()}>
        <Icon name="refresh" />
        Thử lại
      </button>
    </div>
  );
}
