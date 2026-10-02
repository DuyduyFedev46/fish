import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PurchaseAccountingScreen } from "@/features/accounting/components/PurchaseAccountingScreen";

export default function Page() {
  return (
    <ViewGuard view="purchase-invoices">
      <PurchaseAccountingScreen />
    </ViewGuard>
  );
}
