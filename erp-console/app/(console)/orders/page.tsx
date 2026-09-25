import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { OrdersScreen } from "@/features/orders/components/OrdersScreen";

// S10: danh sách + chi tiết đơn (GET /api/sales/orders/); S11: Chủ xác nhận đã nhận tiền trong chi tiết.
export default function Page() {
  return (
    <ViewGuard view="orders">
      <OrdersScreen />
    </ViewGuard>
  );
}
