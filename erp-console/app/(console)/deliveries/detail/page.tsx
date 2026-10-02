import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { DeliveryDetailScreen } from "@/features/deliveries/components/DeliveryDetailScreen";

// Chi tiết phiếu giao: /deliveries/detail/?id=<số>. useSearchParams cần Suspense khi xuất tĩnh.
// Dùng chung hai vai: Chủ/Quản lý/NV kho (menu Giao hàng) và Nhân viên giao mở phiếu CỦA MÌNH (menu Việc giao của tôi).
// Phiếu của người khác: BE trả 404 → màn hiện "Không tìm thấy trang này" (ED-19-AC6). Danh sách /deliveries/ vẫn chỉ cho vai có menu Giao hàng.
export default function DeliveryDetailPage() {
  return (
    <ViewGuard view={["deliveries", "my-deliveries"]}>
      <Suspense fallback={null}>
        <DeliveryDetailScreen />
      </Suspense>
    </ViewGuard>
  );
}
