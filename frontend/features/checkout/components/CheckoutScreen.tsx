"use client";

// Màn checkout: giỏ hàng + form giao hàng → đặt đơn → thanh toán (P4). Tách khỏi
// app/shop/checkout/page.tsx theo cấu trúc module tính năng (features/checkout).

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useCart } from "../../../components/CartContext";
import { createOrder, getSiteInfo, ApiError } from "../../../lib/api";
import { formatVnd } from "../../../lib/format";
import type { CreateOrderPayload, CreateOrderResponse, SiteInfo } from "../../../lib/types";
import { getPrivacyPolicy } from "@/features/site/api";
import type { PrivacyPolicyResponse } from "@/features/site/types";
import PaymentPanel from "./PaymentPanel";
import { rememberOrderContact } from "../storage";

// Chỉ tồn tại ở chế độ mock: điều kiện literal `process.env.NEXT_PUBLIC_USE_MOCK === "1"` được
// bundler thay bằng hằng số, nên ở bản build thật cả lệnh dynamic import này bị cắt — chunk
// MockGatewayPanel (kéo theo lib/mock) không được sinh ra (M5-1b, kiểm bằng scripts/check-no-mock.mjs).
const MockGatewayPanel =
  process.env.NEXT_PUBLIC_USE_MOCK === "1"
    ? dynamic(() => import("./MockGatewayPanel"), { ssr: false })
    : null;

const PHONE_RE = /^(0|\+84)\d{9,10}$/;

export default function CheckoutScreen() {
  const searchParams = useSearchParams();
  const { lines, updateQty, removeItem, totalAmount, clear } = useCart();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [order, setOrder] = useState<CreateOrderResponse | null>(null);
  const [orderPhone, setOrderPhone] = useState("");
  const [siteInfo, setSiteInfo] = useState<SiteInfo | null>(null);

  // Khung go-live pháp lý (GL-03)
  const [policyInfo, setPolicyInfo] = useState<PrivacyPolicyResponse | null>(null);
  const [consentAccepted, setConsentAccepted] = useState(false);
  const [consentRequired, setConsentRequired] = useState<boolean | null>(null);
  const [shopClosed, setShopClosed] = useState(false);

  useEffect(() => {
    let active = true;

    Promise.allSettled([getSiteInfo(), getPrivacyPolicy()]).then(([siteRes, policyRes]) => {
      if (!active) return;

      let isRequired = true;
      if (siteRes.status === "fulfilled" && siteRes.value) {
        setSiteInfo(siteRes.value);
        if (siteRes.value.privacy_consent_required === false) {
          isRequired = false;
        }
      }
      setConsentRequired(isRequired);

      if (policyRes.status === "fulfilled" && policyRes.value) {
        setPolicyInfo(policyRes.value);
      } else {
        // Chưa có chính sách bảo mật Đã đăng (GL-03-AC5)
        if (isRequired) {
          setShopClosed(true);
        }
      }
    });

    return () => {
      active = false;
    };
  }, []);

  // Trang "cổng SePay" giả lập chỉ tồn tại ở chế độ mock (xem lib/mock.ts,
  // mockStartCheckoutSession) — build thật (USE_MOCK=false) loại hẳn nhánh này.
  if (MockGatewayPanel && searchParams.get("mock_gateway") === "1") {
    return <MockGatewayPanel />;
  }

  if (shopClosed) {
    return (
      <div className="checkout-grid">
        <div className="panel" style={{ textAlign: "center", padding: "3rem 1.5rem" }}>
          <h2>Shop tạm chưa nhận đơn</h2>
          <p style={{ color: "#6b7280", marginTop: "0.5rem", marginBottom: "1.5rem" }}>
            Hệ thống đang hoàn thiện chuẩn bị điều kiện phục vụ tốt nhất. Quý khách vui lòng quay lại sau.
          </p>
          <Link href="/shop" className="btn btn-secondary">
            Quay lại cửa hàng
          </Link>
        </div>
      </div>
    );
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Vui lòng nhập tên người nhận";
    if (!PHONE_RE.test(phone.trim())) next.phone = "Số điện thoại không hợp lệ";
    if (!address.trim()) next.address = "Vui lòng nhập địa chỉ giao hàng";
    if (lines.length === 0) next.cart = "Giỏ hàng đang trống";
    if (consentRequired && policyInfo && !consentAccepted) {
      next.consent = "Vui lòng đồng ý chính sách xử lý dữ liệu cá nhân";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const payload: CreateOrderPayload = {
        customer: { phone: phone.trim(), name: name.trim() },
        delivery_address: address.trim(),
        phone: phone.trim(),
        items: lines.map((l) => ({ item_code: l.item_code, qty: l.qty })),
      };

      if (consentRequired && policyInfo) {
        payload.privacy_consent = {
          accepted: consentAccepted,
          policy_version_id: policyInfo.version_id,
        };
      }

      const result = await createOrder(payload);
      rememberOrderContact(result.order_code, phone.trim().slice(-4));
      setOrderPhone(phone.trim());
      setOrder(result);
      clear();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409 || err.code === "POLICY_CHANGED") {
          setConsentAccepted(false);
          if (err.data?.current) {
            setPolicyInfo({
              slug: err.data.current.slug,
              title: policyInfo?.title || "Chính sách bảo mật",
              version: err.data.current.version,
              version_id: err.data.current.version_id,
              effective_from: null,
            });
          }
          setSubmitError("Chính sách vừa cập nhật, vui lòng xem và đồng ý lại.");
          return;
        }
        if (err.status === 503) {
          setShopClosed(true);
          setSubmitError("Shop tạm chưa nhận đơn.");
          return;
        }
        setSubmitError(err.message);
      } else {
        setSubmitError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (order) {
    return <PaymentPanel order={order} phone={orderPhone} />;
  }

  const isConsentLocked = consentRequired === true && policyInfo !== null && !consentAccepted;

  return (
    <div className="checkout-grid">
      <div className="panel">
        <h2>Giỏ hàng của bạn</h2>
        {lines.length === 0 ? (
          <p className="cart-empty">
            Giỏ hàng đang trống. <Link href="/shop">Xem bảng giá</Link>
          </p>
        ) : (
          <table className="cart-table">
            <thead>
              <tr>
                <th>Mặt hàng</th>
                <th>Số lượng</th>
                <th>Đơn giá</th>
                <th>Thành tiền</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.item_code}>
                  <td>
                    <strong>{l.name}</strong>
                    <div className="item-unit">({l.unit})</div>
                  </td>
                  <td>
                    <div className="qty-control">
                      <button
                        type="button"
                        onClick={() => updateQty(l.item_code, l.qty - 1)}
                        className="btn-qty"
                      >
                        -
                      </button>
                      <span className="qty-value">{l.qty}</span>
                      <button
                        type="button"
                        onClick={() => updateQty(l.item_code, l.qty + 1)}
                        className="btn-qty"
                      >
                        +
                      </button>
                    </div>
                  </td>
                  <td>{formatVnd(l.price)}</td>
                  <td>
                    <strong>{formatVnd(l.price * l.qty)}</strong>
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => removeItem(l.item_code)}
                      className="btn-remove"
                      aria-label="Xoá khỏi giỏ"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}>
                  <strong>Tổng cộng</strong>
                </td>
                <td colSpan={2}>
                  <strong className="cart-total">{formatVnd(totalAmount)}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        )}
      </div>

      <div className="panel">
        <h2>Thông tin giao hàng</h2>
        {errors.cart && <p className="form-banner-error">{errors.cart}</p>}
        {submitError && <p className="form-banner-error">{submitError}</p>}
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-field">
            <label htmlFor="name">Tên người nhận</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nguyễn Văn A"
            />
            {errors.name && <span className="form-error">{errors.name}</span>}
          </div>
          <div className="form-field">
            <label htmlFor="phone">Số điện thoại</label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0909xxxxxx"
            />
            {errors.phone && <span className="form-error">{errors.phone}</span>}
          </div>
          <div className="form-field">
            <label htmlFor="address">Địa chỉ giao hàng</label>
            <textarea
              id="address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành"
            />
            {errors.address && <span className="form-error">{errors.address}</span>}
          </div>

          {siteInfo?.cskh_notice?.enabled && (
            <div
              className="cskh-notice-box"
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "6px",
                padding: "10px 14px",
                marginBottom: "16px",
                fontSize: "0.8125rem",
                color: "#166534",
                lineHeight: "1.45",
              }}
            >
              <strong>Lưu ý xác nhận đơn:</strong> Cá Về sẽ gọi xác nhận trong khung giờ{" "}
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

          {consentRequired && policyInfo && (
            <div className="form-field form-field-checkbox" style={{ marginBottom: "16px" }}>
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  fontSize: "0.875rem",
                  lineHeight: "1.45",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={consentAccepted}
                  onChange={(e) => setConsentAccepted(e.target.checked)}
                  style={{ marginTop: "3px" }}
                />
                <span>
                  Tôi đồng ý để Cá Về dùng họ tên, số điện thoại và địa chỉ của tôi để giao hàng và liên hệ
                  xác nhận đơn, theo{" "}
                  <Link
                    href={{ pathname: "/trang/", query: { slug: policyInfo.slug } }}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "#2563eb", textDecoration: "underline" }}
                  >
                    Chính sách bảo mật
                  </Link>
                  .
                </span>
              </label>
              {errors.consent && <span className="form-error">{errors.consent}</span>}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary btn-block"
            disabled={submitting || isConsentLocked}
          >
            {submitting ? "Đang đặt hàng..." : `Đặt hàng — ${formatVnd(totalAmount)}`}
          </button>
        </form>
      </div>
    </div>
  );
}
