"use client";

// Trang "cổng thanh toán" giả lập — CHỈ hiện khi NEXT_PUBLIC_USE_MOCK=1 và URL có `?mock_gateway=1` (do lib/mock.ts sinh ra).
// Cho phép QA/E2E đi hết luồng đặt → thanh toán → quay về mà không cần mạng thật hay khoá thật.
// Guard theo USE_MOCK (hằng số biên dịch) để bản build thật loại hẳn nhánh này.

import { useSearchParams } from "next/navigation";
import Button from "@/components/ui/Button";
import { formatPriceVnd } from "@/lib/format";
import { mockMarkPaymentPending } from "@/lib/mock";
import s from "./MockGatewayPanel.module.css";

export default function MockGatewayPanel() {
  const searchParams = useSearchParams();
  const orderCode = searchParams.get("order") || "";
  const amount = Number(searchParams.get("amount") || 0);
  const successUrl = searchParams.get("success_url") || "";
  const cancelUrl = searchParams.get("cancel_url") || "";
  const errorUrl = searchParams.get("error_url") || "";

  function go(url: string) {
    if (url) window.location.href = url;
  }

  function paidThenGo(delayMs: number | null) {
    mockMarkPaymentPending(orderCode, delayMs);
    go(successUrl);
  }

  return (
    <div className={s.panel}>
      <span className={s.tag}>Giả lập — chỉ hiện ở chế độ mock</span>
      <h1 className={s.title}>Trang thanh toán (giả lập)</h1>
      <p>
        Đơn <strong>{orderCode || "—"}</strong> — số tiền {formatPriceVnd(amount)}
      </p>
      <p className={s.note}>Trang thật hiện mã QR để quét. Ở đây chỉ giả lập các kết quả có thể xảy ra khi khách rời trang này.</p>
      <div className={s.actions}>
        <Button fullWidth onClick={() => paidThenGo(0)}>
          Giả lập đã chuyển khoản (tiền về ngay)
        </Button>
        <Button fullWidth onClick={() => paidThenGo(4000)}>
          Giả lập đã chuyển khoản (tiền về sau 4 giây)
        </Button>
        <Button fullWidth variant="outline" onClick={() => paidThenGo(null)}>
          Giả lập tiền chưa về
        </Button>
        <Button fullWidth variant="secondary" onClick={() => go(cancelUrl)}>
          Huỷ thanh toán
        </Button>
        <Button fullWidth variant="secondary" onClick={() => go(errorUrl)}>
          Báo lỗi thanh toán
        </Button>
      </div>
    </div>
  );
}
