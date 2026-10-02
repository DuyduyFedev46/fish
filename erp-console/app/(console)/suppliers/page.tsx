import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { SupplierListScreen } from "@/features/suppliers/components/SupplierListScreen";

// ED-22 / W5c: danh sách nhà cung cấp (/suppliers/). Cần purchasing.view_supplier (Chủ, Quản lý, NV kho). Không có thanh AI trên danh sách.
export default function Page() {
  return (
    <ViewGuard view="suppliers">
      <SupplierListScreen />
    </ViewGuard>
  );
}
