import MyConfigScreen from "@/features/ai/settings/components/MyConfigScreen";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

export default function AiSettingsPage() {
  return (
    <AiFeatureGuard>
      <MyConfigScreen />
    </AiFeatureGuard>
  );
}
