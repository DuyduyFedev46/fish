"use client";

import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StaffDetailScreen } from "@/features/staff/components/StaffDetailScreen";

// ED-37 / W3g: hồ sơ nhân viên (/staff/detail/?id=<số>). Cần accounts.manage_staff; thiếu quyền → ViewGuard chặn, không gọi API. Không có khối Trợ lý AI.
export default function Page() {
  return (
    <ViewGuard view="staff">
      <Suspense fallback={null}>
        <StaffDetailScreen />
      </Suspense>
    </ViewGuard>
  );
}
