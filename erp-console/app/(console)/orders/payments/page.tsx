import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PaymentQueueScreen } from "@/features/orders/components/PaymentQueueScreen";

// S12: hàng chờ thanh toán lệch (menu con của "Đơn & tiền", chỉ Chủ — sales.confirm_payment_manual);
// S13: lập phiếu hoàn cho khoản không có hoá đơn, trong tấm chi tiết của từng khoản.
export default function Page() {
  return (
    <ViewGuard view="payments">
      <PaymentQueueScreen />
    </ViewGuard>
  );
}
