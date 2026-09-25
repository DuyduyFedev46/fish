import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { InventoryScreen } from "@/features/inventory/components/InventoryScreen";

// S8: Kho & lô. S25 thêm mở bán / chốt lô.
export default function Page() {
  return (
    <ViewGuard view="inventory">
      <InventoryScreen />
    </ViewGuard>
  );
}
