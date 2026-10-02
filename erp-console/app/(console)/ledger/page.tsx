import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { LedgerScreen } from "@/features/ledger/components/LedgerScreen";

// Sổ nhập xuất (W5i, ED-29): chỉ đọc. Cần inventory.view_stockledgerentry.
export default function Page() {
  return (
    <ViewGuard view="ledger">
      <LedgerScreen />
    </ViewGuard>
  );
}
