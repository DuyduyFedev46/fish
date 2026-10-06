import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { TagLookupScreen } from "@/features/deliveries/components/TagLookupScreen";

// CS-17: quét hoặc gõ mã tem để mở phiếu soạn. Cần delivery.print_label (Chủ, Quản lý, NV kho).
export default function DeliveryLookupPage() {
  return (
    <ViewGuard view="delivery-lookup">
      <TagLookupScreen />
    </ViewGuard>
  );
}
