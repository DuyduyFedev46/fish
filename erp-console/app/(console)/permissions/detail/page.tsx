"use client";

import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { GroupDetailScreen } from "@/features/permissions/components/GroupDetailScreen";

// ED-40 / W3i: chi tiết nhóm quyền (/permissions/detail/?group=<mã>). Cần accounts.manage_staff. Không có khối Trợ lý AI.
export default function Page() {
  return (
    <ViewGuard view="permissions">
      <Suspense fallback={null}>
        <GroupDetailScreen />
      </Suspense>
    </ViewGuard>
  );
}
