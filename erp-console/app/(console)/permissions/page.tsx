import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PermissionMatrixScreen } from "@/features/permissions/components/PermissionMatrixScreen";

// ED-40 / W3h: Phân quyền (/permissions/). Cần accounts.manage_staff (Chủ; Quản lý chỉ khi Chủ cấp). Chỉ Chủ bật/tắt; người khác chỉ xem.
export default function Page() {
  return (
    <ViewGuard view="permissions">
      <PermissionMatrixScreen />
    </ViewGuard>
  );
}
