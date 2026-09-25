"use client";

// S11 — Chủ xác nhận "đã nhận tiền" cho đơn Giữ chỗ (hoặc đơn đã tự huỷ mà tiền về muộn) khi webhook không về.
// Nêu rõ hậu quả (mã đơn, số tiền, việc hệ thống sẽ làm), nút gửi ghi đúng số tiền; chống bấm đúp (khoá theo ref + nút
// tắt khi đang gửi, tấm không đóng được khi đang gửi); lỗi BE (BR-TT-08, 403…) hiện NGUYÊN VĂN ngay trên thanh nút.
// Nút gửi không tắt vì thiếu ô: bấm khi trống → báo tại ô + focus (quy ước UI5).
// B13 (QA L7): FE chặn trước tại ô số tiền — âm, 0 (kể cả 0,004), chữ, quá 12 chữ số phần nguyên → báo tại ô, KHÔNG gửi.
// Phần lẻ dưới 1 ₫ bị bỏ (VND không số lẻ). Mã GD tự trim, tối đa 100 ký tự. BE vẫn là lớp chặn chính (S11-AC6, BR-TT-08).
// BE chạy cùng service với webhook → kết quả PAID / UNDERPAID / ORPHAN / duplicate do BE quyết, FE chỉ báo lại.

import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { vnd } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { confirmPayment } from "../api";
import { ORDERS_MSG } from "../messages";
import type { ConfirmPaymentResult, OrderDetail } from "../types";
import s from "../orders.module.css";

type Props = {
  order: OrderDetail;
  /** Tổng đơn từ dòng danh sách nếu chi tiết thiếu `total_amount`. */
  fallbackTotal: string;
  onBusy: (busy: boolean) => void;
  onCancel: () => void;
  onDone: (r: ConfirmPaymentResult) => void;
};

/** Chỉ giữ chữ số (tiền VND không số lẻ). "540.000" / "540,000 ₫" → "540000". */
function digits(v: string): string {
  return v.replace(/\D+/g, "").replace(/^0+(?=\d)/, "");
}

/** Tối đa 12 chữ số phần nguyên (999.999.999.999 ₫) — cột `amount` của BE là 14 chữ số, 2 lẻ (B13). */
export const AMOUNT_MAX_DIGITS = 12;
export const TXN_MAX_LENGTH = 100;

type AmountProblem = "missing" | "negative" | "zero" | "tooBig" | "notNumber";
type AmountCheck = { value: string; problem: null } | { value: null; problem: AmountProblem };

/**
 * Đọc ô số tiền theo cách người Việt gõ: "." / "," / khoảng trắng là dấu nghìn ("540.000", "540,000 ₫").
 * Dấu cuối theo sau 1–2 chữ số ("540000,5") hoặc "0," / "0." ở đầu ("0,004") là phần lẻ → bỏ, chỉ giữ đồng.
 */
export function parseAmount(raw: string): AmountCheck {
  const s = raw.replace(/vnd|₫|đ/gi, "").replace(/\s+/g, "");
  if (/[-−]/.test(s)) return { value: null, problem: "negative" };
  if (/[^\d.,]/.test(s)) return { value: null, problem: "notNumber" };
  if (!/\d/.test(s)) return { value: null, problem: "missing" };
  let int = s;
  const frac = s.match(/^(.*?)[.,](\d{1,2})$/);
  if (frac) int = frac[1];
  else if (/^0*[.,]\d/.test(s) || /^0+[.,]/.test(s)) int = "0";
  const d = int.replace(/\D+/g, "").replace(/^0+/, "");
  if (!d) return { value: null, problem: "zero" };
  if (d.length > AMOUNT_MAX_DIGITS) return { value: null, problem: "tooBig" };
  return { value: d, problem: null };
}

const AMOUNT_MSG: Record<AmountProblem, string> = {
  missing: ORDERS_MSG.amountMissing,
  negative: ORDERS_MSG.amountNegative,
  zero: ORDERS_MSG.amountZero,
  tooBig: ORDERS_MSG.amountTooBig,
  notNumber: ORDERS_MSG.amountNotNumber,
};

export function ConfirmPaymentForm({ order, fallbackTotal, onBusy, onCancel, onDone }: Props) {
  const id = useId();
  const total = digits(order.total_amount ?? fallbackTotal);
  const [txn, setTxn] = useState("");
  const [amountRaw, setAmountRaw] = useState(total);
  const [missing, setMissing] = useState<"txn" | AmountProblem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const txnRef = useRef<HTMLInputElement>(null);
  const amountRef = useRef<HTMLInputElement>(null);
  const errRef = useRef<HTMLDivElement>(null);
  const cancelled = order.status === "AUTO_CANCELLED";
  const check = parseAmount(amountRaw);
  const amount = check.value ?? ""; // chỉ số hợp lệ mới lên tiêu đề / nút / đọc lại
  const amountErr = missing && missing !== "txn" ? AMOUNT_MSG[missing] : null;
  const diff = amount && total ? Number(amount) - Number(total) : 0;

  // Mở bước xác nhận (đổi chế độ trong tấm) → focus vào ô mã giao dịch (Sheet chỉ tự focus lúc mở tấm).
  useEffect(() => {
    txnRef.current?.focus();
  }, []);

  const submit = async () => {
    if (lock.current) return; // chống bấm đúp: lần bấm thứ hai trong lúc đang gửi bị bỏ
    const t = txn.trim();
    if (t !== txn) setTxn(t);
    setError(null); // lần bấm mới: bỏ câu BE của lần trước, lỗi tại ô (nếu có) thay chỗ
    if (!t) {
      setMissing("txn");
      txnRef.current?.focus();
      return;
    }
    if (check.problem) {
      setMissing(check.problem);
      amountRef.current?.focus();
      return;
    }
    lock.current = true;
    setBusy(true);
    onBusy(true);
    setError(null);
    try {
      const r = await confirmPayment(order.id, { bank_txn_id: t.slice(0, TXN_MAX_LENGTH), amount: check.value });
      lock.current = false;
      setBusy(false);
      onBusy(false);
      onDone(r);
    } catch (err) {
      lock.current = false;
      setBusy(false);
      onBusy(false);
      if (err instanceof ApiError && err.status === 401) return;
      setError(errorText(err));
      requestAnimationFrame(() => errRef.current?.scrollIntoView({ block: "nearest" }));
    }
  };

  return (
    <form
      className={`${s.pane} confirm-payment`}
      noValidate
      aria-labelledby={`${id}-q`}
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div className={s.confirmHead}>
        <span className={`${s.confirmIcon}${cancelled ? ` ${s.confirmIconWarn}` : ""}`} aria-hidden="true">
          <Icon name={cancelled ? "warning" : "payments"} />
        </span>
        <h3 id={`${id}-q`}>
          {amount ? ORDERS_MSG.confirmQuestion(amount, order.code) : ORDERS_MSG.confirmAction}
        </h3>
        <p className={`${s.confirmSum} num`}>
          {order.customer.name} · Tổng đơn {vnd(total)}
        </p>
      </div>

      <div className="field">
        <label htmlFor={`${id}-txn`}>
          {ORDERS_MSG.txnLabel}
          <span className={s.req} aria-hidden="true">
            *
          </span>
        </label>
        <input
          ref={txnRef}
          id={`${id}-txn`}
          name="bank_txn_id"
          className="mono-input"
          value={txn}
          onChange={(e) => {
            setTxn(e.target.value);
            if (missing === "txn") setMissing(null);
          }}
          onBlur={() => setTxn((v) => v.trim())}
          maxLength={TXN_MAX_LENGTH}
          placeholder={ORDERS_MSG.txnPlaceholder}
          autoComplete="off"
          autoCapitalize="characters"
          spellCheck={false}
          required
          disabled={busy}
          data-autofocus
          aria-invalid={missing === "txn" || undefined}
          aria-describedby={`${missing === "txn" ? `${id}-txn-err ` : ""}${id}-txn-help`}
        />
        {missing === "txn" && (
          <p className="field-err" id={`${id}-txn-err`}>
            <Icon name="error" />
            {ORDERS_MSG.txnMissing}
          </p>
        )}
        <p className="help" id={`${id}-txn-help`}>
          {ORDERS_MSG.txnHelp}
        </p>
      </div>

      <div className="field">
        <label htmlFor={`${id}-amt`}>
          {ORDERS_MSG.amountLabel}
          <span className={s.req} aria-hidden="true">
            *
          </span>
        </label>
        <div className={s.money}>
          <input
            ref={amountRef}
            id={`${id}-amt`}
            name="amount"
            className="num"
            inputMode="numeric"
            value={check.value ?? amountRaw}
            onChange={(e) => {
              setAmountRaw(e.target.value);
              if (missing && missing !== "txn") setMissing(null);
            }}
            autoComplete="off"
            required
            disabled={busy}
            aria-invalid={amountErr ? true : undefined}
            aria-describedby={`${amountErr ? `${id}-amt-err ` : ""}${id}-amt-help`}
          />
          <span className={s.moneyUnit} aria-hidden="true">
            ₫
          </span>
        </div>
        {amountErr && (
          <p className="field-err" id={`${id}-amt-err`}>
            <Icon name="error" />
            {amountErr}
          </p>
        )}
        <p className="help num" id={`${id}-amt-help`} aria-live="polite">
          {amount ? <b className={s.moneyRead}>{vnd(amount)}</b> : null}
          {amount ? " · " : ""}
          {diff < 0 ? (
            <span className={s.warnText}>{ORDERS_MSG.amountLess(String(-diff))}</span>
          ) : diff > 0 ? (
            <span className={s.warnText}>{ORDERS_MSG.amountMore(String(diff))}</span>
          ) : (
            ORDERS_MSG.amountHelp
          )}
        </p>
      </div>

      <ul className={s.consequences} aria-label="Điều sẽ xảy ra">
        {cancelled ? (
          <li>
            <Icon name="undo" />
            <span>{ORDERS_MSG.consequenceOrphan}</span>
          </li>
        ) : (
          <>
            <li>
              <Icon name="local_shipping" />
              <span>{ORDERS_MSG.consequencePaid}</span>
            </li>
            <li>
              <Icon name="pending" />
              <span>{ORDERS_MSG.consequenceUnder}</span>
            </li>
          </>
        )}
        <li>
          <Icon name="block" />
          <span>{ORDERS_MSG.consequenceFinal}</span>
        </li>
        <li>
          <Icon name="history" />
          <span>{ORDERS_MSG.consequenceAudit}</span>
        </li>
      </ul>

      {error && (
        <div className="alert-box err confirm-error" role="alert" ref={errRef}>
          <Icon name="error" />
          <span>{error}</span>
        </div>
      )}

      <div className={`form-actions ${s.footer} ${s.stack}`}>
        <button type="button" className="btn" onClick={onCancel} disabled={busy}>
          {ORDERS_MSG.back}
        </button>
        <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
          {busy ? <Icon name="progress_activity" className="spin" /> : <Icon name="check" />}
          {busy ? ORDERS_MSG.confirming : amount ? ORDERS_MSG.confirmSubmit(amount) : ORDERS_MSG.confirmSubmitNoAmount}
        </button>
      </div>
    </form>
  );
}
