"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import AiPolicyScreen from "@/features/ai/policy/components/AiPolicyScreen";

export default function AiPolicyPage() {
  return (
    <ViewGuard view="ai-policy">
      <AiPolicyScreen />
    </ViewGuard>
  );
}
