import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ConfirmationDetailScreen } from "@/features/confirmation/components/ConfirmationDetailScreen";

// Chi tiết một việc gọi xác nhận: /confirmation/detail/?id=<số>. useSearchParams cần Suspense khi xuất tĩnh.
// Phiếu ngoài phạm vi của người xem: BE trả 404 → màn hiện "Không tìm thấy trang này".
export default function ConfirmationDetailPage() {
  return (
    <ViewGuard view="confirmation">
      <Suspense fallback={null}>
        <ConfirmationDetailScreen />
      </Suspense>
    </ViewGuard>
  );
}
