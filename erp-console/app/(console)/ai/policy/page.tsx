import AiPolicyScreen from "@/features/ai/policy/components/AiPolicyScreen";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

export default function AiPolicyPage() {
  return (
    <AiFeatureGuard>
      <AiPolicyScreen />
    </AiFeatureGuard>
  );
}
