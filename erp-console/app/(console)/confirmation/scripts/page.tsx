import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CallScriptsScreen } from "@/features/confirmation/components/CallScriptsScreen";

// CS-18: kịch bản gọi soạn sẵn. Chủ soạn; Quản lý và CSKH chỉ đọc.
export default function CallScriptsPage() {
  return (
    <ViewGuard view="call-scripts">
      <CallScriptsScreen />
    </ViewGuard>
  );
}
