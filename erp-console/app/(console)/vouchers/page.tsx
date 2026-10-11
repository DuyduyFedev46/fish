import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { VoucherList } from "@/features/catalog/components/VoucherList";

// SHOP-3b-02: Mã giảm giá /vouchers/. Chỉ người có catalog.manage_voucher (Chủ, hoặc người Chủ uỷ quyền) thấy menu và vào được;
// người khác vào thẳng đường dẫn nhận màn "không có quyền" và không có request API nào được gọi.
export default function Page() {
  return (
    <ViewGuard view="vouchers">
      <VoucherList />
    </ViewGuard>
  );
}
