import { Suspense } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { VoucherEditScreen } from "@/features/catalog/components/VoucherForm";

// SHOP-3b-02: sửa mã giảm giá /vouchers/edit/?id=. Cần catalog.manage_voucher. URL chỉ có id số.
export default function Page() {
  return (
    <ViewGuard view="vouchers">
      <Suspense fallback={null}>
        <VoucherEditScreen />
      </Suspense>
    </ViewGuard>
  );
}
