"use client";

// Màn "đặt hàng thành công" của trang checkout: tóm tắt đơn, đồng hồ giữ chỗ, nút
// "Thanh toán bằng VietQR" chuyển khách sang cổng SePay (P4-AC1/AC2, BR-TT-01/13).

import { useState, useEffect } from "react";
import Link from "next/link";
import { formatVnd } from "../../../lib/format";
import { getSiteInfo, startCheckoutSession } from "../../../lib/api";
import type { CreateOrderResponse, SiteInfo } from "../../../lib/types";
import CountdownTimer from "../../../components/CountdownTimer";
import { goToMockGateway, redirectToGateway } from "../gateway";
import { rememberOrderContact } from "../storage";
import { ConfirmCallNotice } from "../../site/components/ConfirmCallNotice";

export default function PaymentPanel({
  order,
  phone,
}: {
  order: CreateOrderResponse;
  phone: string;
}) {
  const [expired, setExpired] = useState(false);
  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState<string | null>(null);
  const [siteInfo, setSiteInfo] = useState<SiteInfo | null>(null);

  useEffect(() => {
    getSiteInfo()
      .then(setSiteInfo)
      .catch(() => {});
  }, []);

  async function handlePay() {
    setPayError(null);
    setPaying(true);
    try {
      const session = await startCheckoutSession(order.order_code);
      rememberOrderContact(order.order_code, phone.slice(-4));
      if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
        goToMockGateway(order.order_code, order.total_amount);
      } else {
        redirectToGateway(session);
      }
      // Không tắt trạng thái "đang chuyển" ở đây: trình duyệt sắp điều hướng đi.
    } catch (err) {
      setPayError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
      setPaying(false);
    }
  }

  return (
    <div className="checkout-grid">
      <div className="panel order-result">
        <h2>Đặt hàng thành công</h2>
        <p>Mã đơn hàng của bạn:</p>
        <div className="order-code">{order.order_code}</div>

        <div className="pay-amount">
          <span className="pay-amount-label">Số tiền cần thanh toán</span>
          <span className="pay-amount-value">{formatVnd(order.total_amount)}</span>
        </div>

        <CountdownTimer expiresAt={order.booked_expires_at} onExpire={() => setExpired(true)} />

        {expired ? (
          <p className="form-banner-error">
            Đơn đã hết hạn giữ chỗ. Vui lòng đặt lại đơn mới.
          </p>
        ) : (
          <>
            <p className="pay-note">
              Thanh toán 100% trước khi giao, bằng VietQR qua cổng SePay.
            </p>
            <ConfirmCallNotice last4={phone.slice(-4)} />
            {siteInfo?.cskh_notice?.enabled && (
              <div
                className="cskh-notice-box"
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  borderRadius: "6px",
                  padding: "10px 14px",
                  marginBottom: "12px",
                  fontSize: "0.8125rem",
                  color: "#166534",
                  lineHeight: "1.45",
                  textAlign: "left",
                }}
              >
                <strong>Lưu ý xác nhận đơn:</strong> Sau khi thanh toán, Cá Về sẽ gọi xác nhận trong khung giờ{" "}
                {siteInfo.cskh_notice.working_hours} (tối đa {siteInfo.cskh_notice.max_attempts} lần trong{" "}
                {siteInfo.cskh_notice.window_minutes} phút).
                {siteInfo.cskh_notice.auto_cancel_enabled && (
                  <span>
                    {" "}
                    Sau thời gian trên nếu không liên lạc được, đơn hàng có thể bị huỷ và hoàn đủ tiền trong vòng{" "}
                    {siteInfo.cskh_notice.refund_deadline_days} ngày. Hotline: {siteInfo.cskh_notice.hotline}.
                  </span>
                )}{" "}
                {/* # CHỜ legal-vn */}
              </div>
            )}
            {payError && <p className="form-banner-error">{payError}</p>}
            <button
              type="button"
              className="btn btn-primary btn-block"
              onClick={handlePay}
              disabled={paying}
            >
              {paying ? "Đang chuyển sang cổng thanh toán..." : "Thanh toán bằng VietQR"}
            </button>
          </>
        )}

        <Link
          href={`/shop/orders?code=${encodeURIComponent(order.order_code)}`}
          className="btn btn-secondary btn-block"
          style={{ marginTop: 10 }}
        >
          Tra cứu trạng thái đơn này
        </Link>
      </div>
    </div>
  );
}
