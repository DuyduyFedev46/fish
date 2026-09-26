"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import OrderLookup from "./OrderLookup";

function OrderLookupInner() {
  const searchParams = useSearchParams();
  const initialCode = searchParams.get("code") || "";
  const paymentParam = searchParams.get("payment");
  const paymentReturn =
    paymentParam === "success" || paymentParam === "cancel" || paymentParam === "error"
      ? paymentParam
      : null;
  return (
    <>
      <h1 className="page-title">Tra cứu đơn hàng</h1>
      <p className="page-subtitle">
        Nhập mã đơn hàng và 4 số cuối số điện thoại đã dùng khi đặt hàng.
      </p>
      <OrderLookup initialCode={initialCode} paymentReturn={paymentReturn} />
    </>
  );
}

export default function OrderLookupPage() {
  return (
    <Suspense fallback={<p className="empty-state">Đang tải…</p>}>
      <OrderLookupInner />
    </Suspense>
  );
}
