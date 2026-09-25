"use client";

import { useState } from "react";
import { getOrderStatus, type OrderStatus } from "../../../lib/api";
import { formatVnd, formatKg } from "../../../lib/format";

export default function OrderLookup({ initialCode }: { initialCode: string }) {
  const [orderCode, setOrderCode] = useState(initialCode);
  const [phoneLast4, setPhoneLast4] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [result, setResult] = useState<OrderStatus | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setNotFound(false);
    setResult(null);

    const code = orderCode.trim();
    const last4 = phoneLast4.trim();

    if (!code) {
      setError("Vui lòng nhập mã đơn hàng");
      return;
    }
    if (!/^\d{4}$/.test(last4)) {
      setError("Vui lòng nhập đúng 4 số cuối số điện thoại");
      return;
    }

    setLoading(true);
    try {
      const status = await getOrderStatus(code, last4);
      if (!status) {
        setNotFound(true);
      } else {
        setResult(status);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <form className="lookup-form panel" onSubmit={handleSubmit} noValidate>
        <div className="lookup-form-row">
          <div className="form-field">
            <label htmlFor="orderCode">Mã đơn hàng</label>
            <input
              id="orderCode"
              type="text"
              value={orderCode}
              onChange={(e) => setOrderCode(e.target.value)}
              placeholder="DH-260913-1234"
            />
          </div>
          <div className="form-field">
            <label htmlFor="phoneLast4">4 số cuối SĐT</label>
            <input
              id="phoneLast4"
              type="text"
              inputMode="numeric"
              maxLength={4}
              value={phoneLast4}
              onChange={(e) => setPhoneLast4(e.target.value.replace(/\D/g, ""))}
              placeholder="6789"
            />
          </div>
        </div>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? "Đang tra cứu..." : "Tra cứu"}
        </button>
      </form>

      {notFound && (
        <p className="lookup-not-found">
          Không tìm thấy đơn hàng phù hợp. Vui lòng kiểm tra lại mã đơn và số điện thoại.
        </p>
      )}

      {result && (
        <div className="lookup-result panel">
          <p style={{ margin: "0 0 6px", fontWeight: 700 }}>{result.order_code}</p>
          <span className="status-badge">{result.status_label}</span>

          <table className="order-lines-table">
            <thead>
              <tr>
                <th>Mặt hàng</th>
                <th>Số kg</th>
                <th>Thành tiền</th>
              </tr>
            </thead>
            <tbody>
              {result.lines.map((l) => (
                <tr key={l.item_code}>
                  <td>{l.name}</td>
                  <td>{formatKg(l.qty)}</td>
                  <td>{l.line_total != null ? formatVnd(l.line_total) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {result.delivery && (
            <p className="delivery-status">
              Trạng thái giao hàng: <strong>{result.delivery.status}</strong>
            </p>
          )}
        </div>
      )}
    </>
  );
}
