import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PricingRuleForm } from "@/features/catalog/components/PricingRuleForm";

// ED-31 (W5o, F1n): tạo ưu đãi giảm giá /catalog/rules/new/. Cần catalog.add_pricingrule (PricingRuleForm tự chặn người thiếu quyền).
export default function Page() {
  return (
    <ViewGuard view="catalog">
      <PricingRuleForm />
    </ViewGuard>
  );
}
