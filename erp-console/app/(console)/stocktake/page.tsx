import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { StocktakeListScreen } from "@/features/stocktake/components/StocktakeListScreen";

// Kiểm kê (ED-28 W2c): danh sách phiếu. Lập phiếu ở /stocktake/new/, chi tiết ở /stocktake/detail/?id=<số>.
export default function Page() {
  return (
    <ViewGuard view="stocktake">
      <StocktakeListScreen />
    </ViewGuard>
  );
}
