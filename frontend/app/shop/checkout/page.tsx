"use client";

import { Suspense } from "react";
import CheckoutScreen from "../../../features/checkout/components/CheckoutScreen";

export default function CheckoutPage() {
  return (
    <Suspense fallback={<p className="empty-state">Đang tải…</p>}>
      <CheckoutScreen />
    </Suspense>
  );
}
