"use client";

// Lỗi chung của một màn (UI-RULES §7, board W6h): nằm TRONG khung app (có menu). Icon lỗi đỏ nhạt, "Có lỗi xảy ra",
// câu hướng dẫn kèm giờ để báo kỹ thuật, rồi hai nút: "Về <trang chính>" (phụ) và "Thử lại" (chính, bên phải).
// `homeHref` = `homePath(me)` để người chỉ có vai giao hàng về "Việc giao của tôi". Không in nội dung lỗi kỹ thuật ra màn.
import Link from "next/link";
import { useState } from "react";
import { Icon } from "../Icon";
import { dateTime } from "@/shared/lib/format";
import { homeLabel } from "@/shared/lib/nav";

export function ErrorScreen({ onRetry, homeHref = "/overview/" }: { onRetry?: () => void; homeHref?: string }) {
  // Giờ lỗi xảy ra (giờ Việt Nam): cố định theo lần màn lỗi hiện ra, để người dùng đọc cho kỹ thuật.
  const [at] = useState(() => dateTime(new Date().toISOString()));
  return (
    <div className="page-state" role="alert">
      <span className="state-ic state-ic-err">
        <Icon name="error" />
      </span>
      <h2 className="state-title">Có lỗi xảy ra</h2>
      <p>
        Màn này chưa tải được. Nếu vẫn lỗi, báo kỹ thuật kèm giờ <span className="num">{at}</span>.
      </p>
      <div className="page-state-actions">
        <Link href={homeHref} className="btn">
          {homeLabel(homeHref)}
        </Link>
        {onRetry && (
          <button type="button" className="btn primary" onClick={onRetry}>
            <Icon name="refresh" />
            Thử lại
          </button>
        )}
      </div>
    </div>
  );
}
