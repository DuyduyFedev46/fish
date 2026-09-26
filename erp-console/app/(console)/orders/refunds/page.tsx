import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { RefundQueueScreen } from "@/features/orders/components/RefundQueueScreen";

// S16: phiếu hoàn chờ chuyển (menu con của "Đơn & tiền") — xác nhận đã chuyển, báo thất bại, thử lại.
// Xem được với sales.view_refund (Chủ, Quản lý); nút thao tác theo `available_actions` của từng phiếu
// (chỉ Chủ có sales.confirm_refund, S16-AC7).
export default function Page() {
  return (
    <ViewGuard view="refunds">
      <RefundQueueScreen />
    </ViewGuard>
  );
}
