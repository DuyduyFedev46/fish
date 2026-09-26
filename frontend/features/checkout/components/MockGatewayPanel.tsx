"use client";

// Trang "cổng SePay" giả lập — CHỈ hiện khi NEXT_PUBLIC_USE_MOCK=1 và URL có
// `?mock_gateway=1` (do lib/mock.ts sinh ra). Cho phép QA/E2E đi hết luồng đặt →
// thanh toán → quay về mà không cần mạng thật hay khoá SePay thật.
// Guard theo USE_MOCK (hằng số biên dịch) để khi build thật (NEXT_PUBLIC_USE_MOCK khác
// "1") Next.js loại hẳn nhánh này — build thật không hiện được màn giả lập này.

import { useSearchParams } from "next/navigation";
import { formatVnd } from "../../../lib/format";
import { mockMarkPaymentPending } from "../../../lib/mock";

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

  function paidThenGo(delayMs: number) {
    mockMarkPaymentPending(orderCode, delayMs);
    go(successUrl);
  }

  return (
    <div className="checkout-grid">
      <div className="panel mock-gateway">
        <span className="mock-gateway-tag">Giả lập — chỉ hiện ở chế độ mock</span>
        <h2>Trang thanh toán SePay (giả lập)</h2>
        <p>
          Đơn <strong>{orderCode || "—"}</strong> — số tiền {formatVnd(amount)}
        </p>
        <p className="pay-note">
          Trang thật do SePay host và hiện VietQR để quét. Ở đây chỉ để giả lập các kết
          quả có thể xảy ra khi khách rời trang này.
        </p>
        <div className="mock-gateway-actions">
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={() => paidThenGo(0)}
          >
            Giả lập đã chuyển khoản (IPN báo ngay)
          </button>
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={() => paidThenGo(4000)}
          >
            Giả lập đã chuyển khoản (IPN đến sau 4 giây)
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            onClick={() => go(cancelUrl)}
          >
            Huỷ thanh toán
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            onClick={() => go(errorUrl)}
          >
            Báo lỗi thanh toán
          </button>
        </div>
      </div>
    </div>
  );
}
