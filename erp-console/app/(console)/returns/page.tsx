import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ReturnListScreen } from "@/features/returns/components/ReturnListScreen";

// ED-26 / W5e: hàng hoàn về kho (GET /api/inventory/returns/). Chủ, Quản lý, NV kho, NV giao (chỉ phiếu của mình) có inventory.view_returntostock.
export default function Page() {
  return (
    <ViewGuard view="returns">
      <ReturnListScreen />
    </ViewGuard>
  );
}
