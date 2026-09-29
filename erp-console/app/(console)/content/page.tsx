import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { ContentListScreen } from "@/features/content/components/ContentListScreen";

export default function ContentPage() {
  return (
    <ViewGuard view="content">
      <ContentListScreen />
    </ViewGuard>
  );
}
