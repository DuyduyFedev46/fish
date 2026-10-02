"use client";

// Cổng trạng thái của trang chi tiết: đang dựng · URL không có id · đang tải (khung xương) · 403 (Không có quyền) ·
// 404 (Không tìm thấy — cũng là câu cho NV giao mở đơn ngoài phiếu của mình, BR-PQ-12) · lỗi (Thử lại) · có dữ liệu.

import { useAuth } from "@/features/auth/components/AuthProvider";
import { homePath } from "@/shared/lib/nav";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import type { DetailState } from "./useDetail";
import s from "./orders.module.css";

type Props<T> = {
  /** Kết quả `useIdParam()`. */
  id: number | null | undefined;
  detail: DetailState<T>;
  noun: string;
  children: (data: T) => React.ReactNode;
};

export function DetailSkeleton({ noun }: { noun: string }) {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">{`Đang tải ${noun}…`}</span>
      <div aria-hidden="true">
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-s" />
      </div>
    </div>
  );
}

export function DetailGate<T>({ id, detail, noun, children }: Props<T>) {
  const { me } = useAuth();
  const home = me ? homePath(me) : undefined;
  if (id === undefined) return <DetailSkeleton noun={noun} />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton noun={noun} />;
  return <>{children(detail.data)}</>;
}
