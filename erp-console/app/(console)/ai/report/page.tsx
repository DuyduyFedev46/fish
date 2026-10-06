"use client";

import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { AiDailyReportScreen } from "@/features/ai/report/components/AiDailyReportScreen";

export default function AiDailyReportPage() {
  return (
    <AiFeatureGuard>
      <ViewGuard view="ai-report">
        <AiDailyReportScreen />
      </ViewGuard>
    </AiFeatureGuard>
  );
}
