"use client";

import { ViewGuard } from "@/features/auth/components/ViewGuard";
import AiPolicyScreen from "@/features/ai/policy/components/AiPolicyScreen";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

export default function AiPolicyPage() {
  return (
    <AiFeatureGuard>
      <ViewGuard view="ai-policy">
        <AiPolicyScreen />
      </ViewGuard>
    </AiFeatureGuard>
  );
}
