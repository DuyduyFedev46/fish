"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import MyConfigScreen from "@/features/ai/settings/components/MyConfigScreen";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

export default function AiSettingsPage() {
  return (
    <AiFeatureGuard>
      <ViewGuard view="ai-settings">
        <MyConfigScreen />
      </ViewGuard>
    </AiFeatureGuard>
  );
}
