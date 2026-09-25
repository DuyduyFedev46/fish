"use client";

// Bọc nội dung một màn: thiếu quyền → hiện thông báo và KHÔNG mount children,
// nên không có request API nào của màn đó được gọi (S7-AC3, S8-AC5).
// Backend vẫn là lớp chặn thật (BR-PQ-12); đây chỉ là ẩn cho gọn.

import { Empty } from "@/shared/ui/StateBox";
import { canView, type ViewKey } from "@/shared/lib/nav";
import { useAuth } from "./AuthProvider";
import { MSG } from "@/shared/lib/messages";

export function ViewGuard({ view, children }: { view: ViewKey; children: React.ReactNode }) {
  const { me } = useAuth();
  if (!canView(me, view)) {
    return (
      <Empty icon="lock" title={MSG.noViewPermission}>
        {MSG.noViewPermissionHint}
      </Empty>
    );
  }
  return <>{children}</>;
}
