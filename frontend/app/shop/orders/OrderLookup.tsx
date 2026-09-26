"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getOrderStatus, type OrderStatus } from "../../../lib/api";
import { formatVnd, formatKg } from "../../../lib/format";
import OrderPaymentPanel, {
  type PaymentReturn,
} from "../../../features/checkout/components/OrderPaymentPanel";
import { recallOrderContact } from "../../../features/checkout/storage";

const POLL_MS = 5000;

export default function OrderLookup({
  initialCode,
  paymentReturn = null,
}: {
  initialCode: string;
  paymentReturn?: PaymentReturn;
}) {
  const [orderCode, setOrderCode] = useState(initialCode);
  const [phoneLast4, setPhoneLast4] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [result, setResult] = useState<OrderStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const performLookup = useCallback(async (code: string, last4: string, opts?: { silent?: boolean }) => {
    if (!opts?.silent) {
      setError(null);
      setNotFound(false);
      setLoading(true);
    }
    try {
      const status = await getOrderStatus(code, last4);
      if (!status) {
        if (!opts?.silent) setNotFound(true);
      } else {
        setResult(status);
        setNotFound(false);
      }
    } catch (err) {
      if (!opts?.silent) {
        setError(err instanceof Error ? err.message : "Có lỗi xảy ra, vui lòng thử lại.");
      }
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, []);

  // Khách quay về từ cổng thanh toán (?payment=...): nếu Shop còn nhớ 4 số cuối SĐT
  // trong phiên này (đã lưu lúc đặt hàng/thanh toán), tự tra cứu luôn — khách không phải
  // gõ lại gì (P4-AC7, PA spec §7.1). Không nhớ được thì vẫn có ô nhập bình thường.
  useEffect(() => {
    if (!initialCode || !paymentReturn) return;
    const recalled = recallOrderContact(initialCode);
    if (recalled) {
      setPhoneLast4(recalled);
      performLookup(initialCode, recalled);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCode, paymentReturn]);

  // Tự cập nhật khi đơn còn chờ (chưa thanh toán, chưa hết hạn): bắt IPN đến mà khách
  // không cần bấm gì (BR-TT-12, P4-AC3).
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!result || result.is_paid || result.is_expired || !phoneLast4) return;
    pollRef.current = setInterval(() => {
      performLookup(result.order_code, phoneLast4, { silent: true });
    }, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [result, phoneLast4, performLookup]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
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
    setResult(null);
    await performLookup(code, last4);
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

          <OrderPaymentPanel
            order={result}
            paymentReturn={paymentReturn}
            phoneLast4={phoneLast4}
            onRefresh={() => performLookup(result.order_code, phoneLast4)}
          />

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
