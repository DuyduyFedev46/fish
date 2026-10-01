"use client";

// Bọc nội dung một màn: thiếu quyền → hiện thông báo và KHÔNG mount children,
// nên không có request API nào của màn đó được gọi (S7-AC3, S8-AC5).
// Backend vẫn là lớp chặn thật (BR-PQ-12); đây chỉ là ẩn cho gọn.

import { NoPermission } from "@/shared/ui/states/NoPermission";
import { canView, homePath, type ViewKey } from "@/shared/lib/nav";
import { useAuth } from "./AuthProvider";

export function ViewGuard({ view, children }: { view: ViewKey; children: React.ReactNode }) {
  const { me } = useAuth();
  if (!me || !canView(me, view)) {
    return <NoPermission homeHref={me ? homePath(me) : undefined} />;
  }
  return <>{children}</>;
}
