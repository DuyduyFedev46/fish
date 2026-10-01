"use client";

// 404 và lỗi chung nằm trong khung app: nút "về trang chính" đi theo `homePath(me)` (người chỉ có vai giao hàng
// về "Việc giao của tôi", không phải Tổng quan mà họ không có quyền xem — G9). Cần `me` nên nằm ở features/auth.
import { homePath } from "@/shared/lib/nav";
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
