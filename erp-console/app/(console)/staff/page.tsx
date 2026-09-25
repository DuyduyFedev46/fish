import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StaffScreen } from "@/features/staff/components/StaffScreen";

// S41/S42: Nhân viên. Cần accounts.manage_staff; thiếu quyền → ViewGuard chặn, không gọi /api/staff/ (S41-AC9).
export default function Page() {
  return (
    <ViewGuard view="staff">
      <StaffScreen />
    </ViewGuard>
  );
}
