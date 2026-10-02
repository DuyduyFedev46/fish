import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ConfirmationQueueView } from "@/features/confirmation/components/ConfirmationQueueView";

export default function ConfirmationPage() {
  return (
    <ViewGuard view="confirmation">
      <ConfirmationQueueView />
    </ViewGuard>
  );
}
