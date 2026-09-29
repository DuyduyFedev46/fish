import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CskhQueueView } from "@/features/cskh/CskhQueueView";

export default function CskhPage() {
  return (
    <ViewGuard view="cskh">
      <CskhQueueView />
    </ViewGuard>
  );
}
