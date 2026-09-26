"use client";

// Phần "thanh toán" trên trang tra đơn: đã thanh toán / đang chờ IPN / hết hạn / chưa
// thanh toán + nút thanh toán lại (P4-AC3…AC6, BR-TT-12/17). Chỉ hiện khi đơn còn liên
// quan tới việc thanh toán; các trạng thái khác (đang giao, đã huỷ tay…) dùng badge sẵn có.

import { useState } from "react";
import Link from "next/link";
import type { OrderStatus } from "../../../lib/types";
import { startCheckoutSession, USE_MOCK } from "../../../lib/api";
import CountdownTimer from "../../../components/CountdownTimer";
import { goToMockGateway, redirectToGateway } from "../gateway";
import { rememberOrderContact } from "../storage";

export type PaymentReturn = "success" | "cancel" | "error" | null;

export default function OrderPaymentPanel({
  order,
  paymentReturn,
  phoneLast4,
  onRefresh,
}: {
  order: OrderStatus;
  paymentReturn: PaymentReturn;
  phoneLast4: string;
  onRefresh: () => void;
}) {
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  async function handleRetryPay() {
    setRetryError(null);
    setRetrying(true);
    try {
      const session = await startCheckoutSession(order.order_code);
      rememberOrderContact(order.order_code, phoneLast4);
      if (USE_MOCK) {
        goToMockGateway(order.order_code, order.total_amount);
      } else {
        redirectToGateway(session);
      }
    } catch (err) {
      setRetryError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
      setRetrying(false);
    }
  }

  if (order.is_paid) {
    return (
      <div className="pay-status">
        <p className="pay-status-paid">
          <span aria-hidden>✓</span> Đã thanh toán, đang soạn hàng
        </p>
      </div>
    );
  }

  if (order.is_expired) {
    return (
      <div className="pay-status">
        <p className="pay-status-expired-text">Đơn đã hết hạn giữ hàng, vui lòng đặt lại.</p>
        <Link href="/shop" className="btn btn-primary btn-block">
          Đặt đơn mới
        </Link>
      </div>
    );
  }

  const waiting = paymentReturn === "success";

  return (
    <div className="pay-status">
      {waiting && <p className="pay-status-waiting">Đang chờ xác nhận thanh toán…</p>}
      {!waiting && paymentReturn === "error" && (
        <p className="form-banner-error">Thanh toán chưa thành công, bạn có thể thử lại.</p>
      )}
      {!waiting && paymentReturn === "cancel" && (
        <p className="pay-status-note">Bạn đã huỷ thanh toán. Đơn vẫn được giữ chỗ.</p>
      )}
      {!waiting && paymentReturn === null && <p className="pay-status-note">Chưa thanh toán.</p>}

      {/* API tra đơn hôm nay chưa trả `booked_expires_at` (xem lib/types.ts) — thiếu thì ẩn
          đồng hồ thay vì suy đoán, nút "Thanh toán lại" vẫn dùng được (BE tự chặn nếu hết hạn). */}
      {order.booked_expires_at && (
        <CountdownTimer expiresAt={order.booked_expires_at} onExpire={onRefresh} />
      )}

      {waiting ? (
        <p className="pay-status-hint">
          Nếu bạn đã chuyển khoản, vui lòng đợi trong giây lát — trang sẽ tự cập nhật.
        </p>
      ) : (
        <>
          {retryError && <p className="form-banner-error">{retryError}</p>}
          <button
            type="button"
            className="btn btn-primary btn-block"
            onClick={handleRetryPay}
            disabled={retrying}
          >
            {retrying ? "Đang chuyển sang cổng thanh toán..." : "Thanh toán lại"}
          </button>
        </>
      )}

      <button type="button" className="btn btn-secondary btn-block" onClick={onRefresh}>
        Kiểm tra lại trạng thái
      </button>
    </div>
  );
}
