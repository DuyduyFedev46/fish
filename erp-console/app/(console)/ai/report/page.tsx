"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { AiDailyReportScreen } from "@/features/ai/report/components/AiDailyReportScreen";

export default function AiDailyReportPage() {
  return (
    <ViewGuard view="ai-report">
      <AiDailyReportScreen />
    </ViewGuard>
  );
}
