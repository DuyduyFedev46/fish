"use client";

import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { PaymentDetailScreen } from "@/features/orders/components/PaymentDetailScreen";

// ED-11: chi tiết khoản tiền (/orders/payments/detail/?id=). Xem được với quyền của hàng chờ thanh toán.
// Khối Trợ lý AI ghép ở đây (feature màn hình không import features/ai); targetId = pk khoản tiền (BE lưu str(payment.id)).
export default function Page() {
  return (
    <ViewGuard view="payments">
      <PaymentDetailScreen
        renderAi={(t, onApplied) => <AiDocBlockGate targetModel="sales.paymenttransaction" targetId={t.id} onApplied={onApplied} />}
      />
    </ViewGuard>
  );
}
