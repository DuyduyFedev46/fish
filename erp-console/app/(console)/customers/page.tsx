import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CustomerListScreen } from "@/features/customers/components/CustomerListScreen";

// ED-14 / W5a: danh bạ khách (GET /api/sales/customer-directory/). Chủ + Quản lý mặc định (sales.view_customer_list).
export default function Page() {
  return (
    <ViewGuard view="customers">
      <CustomerListScreen />
    </ViewGuard>
  );
}
