import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { AuditLogScreen } from "@/features/audit/components/AuditLogScreen";

// S03: Nhật ký hoạt động. Cần accounts.view_auditlog (owner, manager); thiếu quyền → ViewGuard chặn,
// không gọi /api/audit-logs/ (S03-AC5).
export default function Page() {
  return (
    <ViewGuard view="audit-logs">
      <AuditLogScreen />
    </ViewGuard>
  );
}
