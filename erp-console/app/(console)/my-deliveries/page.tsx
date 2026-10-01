import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { MyDeliveriesScreen } from "@/features/deliveries/components/MyDeliveriesScreen";

// ED-19: Việc giao của tôi (nhân viên giao). ViewGuard chặn người không thuộc nhóm giao hàng trước khi gọi API.
export default function Page() {
  return (
    <ViewGuard view="my-deliveries">
      <MyDeliveriesScreen />
    </ViewGuard>
  );
}
