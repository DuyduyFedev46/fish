"use client";

// Bọc nội dung một màn: thiếu quyền → hiện thông báo và KHÔNG mount children,
// nên không có request API nào của màn đó được gọi (S7-AC3, S8-AC5).
// Backend vẫn là lớp chặn thật (BR-PQ-12); đây chỉ là ẩn cho gọn.

import { NoPermission } from "@/shared/ui/states/NoPermission";
import { canView, homePath, type ViewKey } from "@/shared/lib/nav";
import { useAuth } from "./AuthProvider";

/** `view` là một màn, hoặc nhiều màn (qua được nếu thấy ÍT NHẤT một): trang dùng chung giữa hai vai, vd chi tiết phiếu giao. */
export function ViewGuard({ view, children }: { view: ViewKey | ViewKey[]; children: React.ReactNode }) {
  const { me } = useAuth();
  const views = Array.isArray(view) ? view : [view];
  if (!me || !views.some((v) => canView(me, v))) {
    return <NoPermission homeHref={me ? homePath(me) : undefined} />;
  }
  return <>{children}</>;
}
