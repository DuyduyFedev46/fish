import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { SalesInvoiceListScreen } from "@/features/accounting/components/SalesInvoiceListScreen";

export default function Page() {
  return (
    <ViewGuard view="sales-invoices">
      <SalesInvoiceListScreen />
    </ViewGuard>
  );
}
