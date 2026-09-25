"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import OrderLookup from "./OrderLookup";

function OrderLookupInner() {
  const initialCode = useSearchParams().get("code") || "";
  return (
    <>
      <h1 className="page-title">Tra cứu đơn hàng</h1>
      <p className="page-subtitle">
        Nhập mã đơn hàng và 4 số cuối số điện thoại đã dùng khi đặt hàng.
      </p>
      <OrderLookup initialCode={initialCode} />
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
