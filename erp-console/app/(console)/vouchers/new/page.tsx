import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { VoucherCreateScreen } from "@/features/catalog/components/VoucherForm";

// SHOP-3b-02: tạo mã giảm giá /vouchers/new/. Cần catalog.manage_voucher.
export default function Page() {
  return (
    <ViewGuard view="vouchers">
      <VoucherCreateScreen />
    </ViewGuard>
  );
}
