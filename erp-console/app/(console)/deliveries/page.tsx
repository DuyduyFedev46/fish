import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { DeliveriesView } from "@/features/deliveries/components/DeliveriesView";

export default function DeliveriesPage() {
  return (
    <ViewGuard view="deliveries">
      <DeliveriesView />
    </ViewGuard>
  );
}
