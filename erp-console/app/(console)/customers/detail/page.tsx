import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { CustomerDetailScreen } from "@/features/customers/components/CustomerDetailScreen";

// ED-14 / W5b: chi tiết khách (/customers/detail/?id=). Không ghép khối Trợ lý AI: dữ liệu cá nhân của khách không đưa cho AI.
export default function Page() {
  return (
    <ViewGuard view="customers">
      <CustomerDetailScreen />
    </ViewGuard>
  );
}
