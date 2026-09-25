import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { OverviewScreen } from "@/features/overview/components/OverviewScreen";

// S8: Tổng quan. Thiếu quyền → ViewGuard chặn, màn không mount nên không gọi API (S8-AC5).
export default function Page() {
  return (
    <ViewGuard view="overview">
      <OverviewScreen />
    </ViewGuard>
  );
}
