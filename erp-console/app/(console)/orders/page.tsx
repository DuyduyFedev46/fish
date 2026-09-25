import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { OrdersScreen } from "@/features/orders/components/OrdersScreen";

// S8: Đơn (8 đơn gần nhất). S10 mở rộng thành danh sách đầy đủ + thao tác tiền.
export default function Page() {
  return (
    <ViewGuard view="orders">
      <OrdersScreen />
    </ViewGuard>
  );
}
