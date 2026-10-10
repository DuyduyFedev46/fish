"use client";

import { Suspense } from "react";
import CheckoutScreen, { CheckoutFallback } from "@/features/checkout/components/CheckoutScreen";

export default function CheckoutPage() {
  return (
    <Suspense fallback={<CheckoutFallback />}>
      <CheckoutScreen />
    </Suspense>
  );
}
