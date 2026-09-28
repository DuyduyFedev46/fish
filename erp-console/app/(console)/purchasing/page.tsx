import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PurchasingScreen } from "@/features/purchasing/components/PurchasingScreen";

export default function Page() {
  return (
    <ViewGuard view="purchasing">
      <PurchasingScreen />
    </ViewGuard>
  );
}
