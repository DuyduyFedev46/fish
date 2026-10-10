"use client";

import { Suspense } from "react";
import OrderScreen, { OrderFallback } from "@/features/checkout/components/OrderScreen";

export default function OrdersPage() {
  return (
    <Suspense fallback={<OrderFallback />}>
      <OrderScreen />
    </Suspense>
  );
}
