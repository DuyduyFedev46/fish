import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { Placeholder } from "@/shared/ui/Placeholder";

// Màn chưa làm (xem plannedIn trong shared/lib/nav.ts). Khi làm: thay <Placeholder> bằng màn của features/<module>.
export default function Page() {
  return (
    <ViewGuard view="deliveries">
      <Placeholder view="deliveries" />
    </ViewGuard>
  );
}
