"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import MyConfigScreen from "@/features/ai/settings/components/MyConfigScreen";

export default function AiSettingsPage() {
  return (
    <ViewGuard view="ai-settings">
      <MyConfigScreen />
    </ViewGuard>
  );
}
