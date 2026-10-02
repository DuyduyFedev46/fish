import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ProfitReportScreen } from "@/features/reports/components/ProfitReportScreen";

export default function Page() {
  return (
    <ViewGuard view="reports">
      <ProfitReportScreen />
    </ViewGuard>
  );
}
