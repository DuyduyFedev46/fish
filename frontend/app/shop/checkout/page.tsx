"use client";

import { Suspense } from "react";
import CheckoutScreen from "../../../features/checkout/components/CheckoutScreen";
import ShopFrame from "../../../components/ShopFrame";

export default function CheckoutPage() {
  return (
    <ShopFrame header="checkout" title="Thông tin nhận hàng" footer="compact" bottomNav={false}>
      <div className="shop-main">
        <Suspense fallback={<p className="empty-state">Đang tải…</p>}>
          <CheckoutScreen />
        </Suspense>
      </div>
    </ShopFrame>
  );
}
