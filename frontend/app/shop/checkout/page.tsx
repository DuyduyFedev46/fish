"use client";

import { useState } from "react";
import Link from "next/link";
import { useCart } from "../../../components/CartContext";
import { createOrder, type CreateOrderResponse } from "../../../lib/api";
import { formatVnd } from "../../../lib/format";
import QrCode from "../../../components/QrCode";
import CountdownTimer from "../../../components/CountdownTimer";

const PHONE_RE = /^(0|\+84)\d{9,10}$/;

export default function CheckoutPage() {
  const { lines, updateQty, removeItem, totalAmount, clear } = useCart();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [order, setOrder] = useState<CreateOrderResponse | null>(null);
  const [expired, setExpired] = useState(false);

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!name.trim()) next.name = "Vui lòng nhập tên người nhận";
    if (!PHONE_RE.test(phone.trim())) next.phone = "Số điện thoại không hợp lệ";
    if (!address.trim()) next.address = "Vui lòng nhập địa chỉ giao hàng";
    if (lines.length === 0) next.cart = "Giỏ hàng đang trống";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    if (!validate()) return;

    setSubmitting(true);
    try {
      const result = await createOrder({
        customer: { phone: phone.trim(), name: name.trim() },
        delivery_address: address.trim(),
        phone: phone.trim(),
        items: lines.map((l) => ({ item_code: l.item_code, qty: l.qty })),
      });
      setOrder(result);
      clear();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  if (order) {
    return (
      <div className="checkout-grid">
        <div className="panel order-result">
          <h2>Đặt hàng thành công</h2>
          <p>Mã đơn hàng của bạn:</p>
          <div className="order-code">{order.order_code}</div>

          <QrCode value={order.vietqr.payload} />

          <div className="vietqr-info">
            <div>
              <strong>Số tiền:</strong> {formatVnd(order.vietqr.amount)}
            </div>
            <div>
              <strong>Nội dung chuyển khoản:</strong> {order.vietqr.content}
            </div>
          </div>

          <CountdownTimer
            expiresAt={order.booked_expires_at}
            onExpire={() => setExpired(true)}
          />

          {expired && (
            <p className="form-banner-error">
              Đơn đã hết hạn giữ chỗ. Vui lòng đặt lại đơn mới.
            </p>
          )}

          <p style={{ fontSize: "0.85rem", color: "var(--color-muted)" }}>
            Sau khi chuyển khoản, hệ thống sẽ tự động xác nhận. Bạn có thể tra
            cứu trạng thái đơn bất cứ lúc nào.
          </p>
          <Link
            href={`/shop/orders?code=${encodeURIComponent(order.order_code)}`}
            className="btn btn-secondary btn-block"
          >
            Tra cứu trạng thái đơn này
          </Link>
        </div>
      </div>
    );
  }

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
                <th>Số kg</th>
                <th>Thành tiền</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.item_code}>
                  <td>
                    {l.name}
                    <div style={{ fontSize: "0.78rem", color: "var(--color-muted)" }}>
                      {formatVnd(l.price)} / kg
                    </div>
                  </td>
                  <td>
                    <input
                      className="cart-qty-input"
                      type="number"
                      min={0.1}
                      step={0.1}
                      value={l.qty}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        updateQty(l.item_code, Number.isFinite(v) ? v : 0);
                      }}
                      aria-label={`Số kg cho ${l.name}`}
                    />
                  </td>
                  <td>{formatVnd(l.qty * l.price)}</td>
                  <td>
                    <button
                      type="button"
                      className="cart-remove"
                      onClick={() => removeItem(l.item_code)}
                    >
                      Xoá
                    </button>
                  </td>
                </tr>
              ))}
              <tr className="cart-total-row">
                <td colSpan={2}>Tổng cộng</td>
                <td colSpan={2}>{formatVnd(totalAmount)}</td>
              </tr>
            </tbody>
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
          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? "Đang đặt hàng..." : `Đặt hàng — ${formatVnd(totalAmount)}`}
          </button>
        </form>
      </div>
    </div>
  );
}
