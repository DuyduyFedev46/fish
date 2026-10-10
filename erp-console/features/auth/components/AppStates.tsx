"use client";

// 404 và lỗi chung nằm trong khung app: nút "về trang chính" đi theo `homePath(me)` (người chỉ có vai giao hàng
// về "Việc giao của tôi", không phải Tổng quan mà họ không có quyền xem — G9). Cần `me` nên nằm ở features/auth.
import Link from "next/link";
import { MSG } from "@/shared/lib/messages";
import { homePath } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { useAuth } from "./AuthProvider";

export function NotFoundInApp() {
  const { me } = useAuth();
  return <NotFoundScreen homeHref={me ? homePath(me) : undefined} />;
}

export function ErrorInApp({ onRetry }: { onRetry?: () => void }) {
  const { me } = useAuth();
  return <ErrorScreen onRetry={onRetry} homeHref={me ? homePath(me) : undefined} />;
}

/**
 * PV-13: màn chi tiết đã có dữ liệu, tải lại thì BE trả 404 (phạm vi của người xem vừa hẹp lại). Không vẽ gì của mục cũ.
 * `listHref` = đường quay lại danh sách của màn; `extra` = câu phụ (vd phiếu nhập tạo từ hôm trước, PV-13-AC2).
 */
export function ScopeLostInApp({ listHref, extra }: { listHref: string; extra?: string | null }) {
  return (
    <div className="page-state" data-testid="scope-lost">
      <span className="state-ic">
        <Icon name="lock" />
      </span>
      <h2 className="state-title" role="alert">
        {MSG.scopeLostTitle}
      </h2>
      <p>{MSG.scopeLostHint}</p>
      {extra ? <p data-testid="scope-lost-extra">{extra}</p> : null}
      <div className="page-state-actions">
        <Link href={listHref} className="btn primary">
          {MSG.backToList}
        </Link>
      </div>
    </div>
  );
}
