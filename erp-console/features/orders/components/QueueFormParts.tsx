"use client";

// Mảnh dùng chung cho ba bước xử lý khoản lệch (gắn đơn · xác nhận đơn · lập phiếu hoàn): đầu câu hỏi, ô ghi chú, danh sách
// hậu quả, thanh nút có câu lỗi BE nguyên văn, và khoá gửi chống bấm đúp (theo ref — lần bấm thứ hai trong lúc gửi bị bỏ).

import { useCallback, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { QUEUE_MSG } from "../messages";
import s from "../orders.module.css";

export function FormHead({ id, icon, tone, question, sub }: { id: string; icon: string; tone?: "warn"; question: string; sub: React.ReactNode }) {
  return (
    <div className={s.confirmHead}>
      <span className={`${s.confirmIcon}${tone === "warn" ? ` ${s.confirmIconWarn}` : ""}`} aria-hidden="true">
        <Icon name={icon} />
      </span>
      <h3 id={id}>{question}</h3>
      <p className={`${s.confirmSum} num`}>{sub}</p>
    </div>
  );
}

export function NoteField({
  id,
  label,
  value,
  onChange,
  help,
  required,
  error,
  disabled,
  inputRef,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  help: string;
  required?: boolean;
  error?: string | null;
  disabled?: boolean;
  inputRef?: React.RefObject<HTMLTextAreaElement>;
}) {
  return (
    <div className={`field ${s.noteField}`}>
      <label htmlFor={id}>
        {label}
        {required ? (
          <span className={s.req} aria-hidden="true">
            *
          </span>
        ) : (
          <span className={s.optional}> {QUEUE_MSG.noteOptional}</span>
        )}
      </label>
      <textarea
        ref={inputRef}
        id={id}
        name="note"
        rows={2}
        value={value}
        maxLength={500}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={`${error ? `${id}-err ` : ""}${id}-help`}
      />
      {error && (
        <p className="field-err" id={`${id}-err`}>
          <Icon name="error" />
          {error}
        </p>
      )}
      <p className="help" id={`${id}-help`}>
        {help}
      </p>
    </div>
  );
}

export function Consequences({ items }: { items: { icon: string; text: string }[] }) {
  return (
    <ul className={s.consequences} aria-label="Điều sẽ xảy ra">
      {items.map((c) => (
        <li key={c.text}>
          <Icon name={c.icon} />
          <span>{c.text}</span>
        </li>
      ))}
    </ul>
  );
}

export function FormFooter({
  error,
  errRef,
  busy,
  onCancel,
  submitIcon,
  submitLabel,
  busyLabel,
}: {
  error: string | null;
  errRef: React.RefObject<HTMLDivElement>;
  busy: boolean;
  onCancel: () => void;
  submitIcon: string;
  submitLabel: string;
  busyLabel: string;
}) {
  return (
    <>
      {error && (
        <div className="alert-box err queue-error" role="alert" ref={errRef}>
          <Icon name="error" />
          <span>{error}</span>
        </div>
      )}
      <div className={`form-actions ${s.footer} ${s.stack}`}>
        <button type="button" className="btn" onClick={onCancel} disabled={busy}>
          {QUEUE_MSG.back}
        </button>
        <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
          {busy ? <Icon name="progress_activity" className="spin" /> : <Icon name={submitIcon} />}
          {busy ? busyLabel : submitLabel}
        </button>
      </div>
    </>
  );
}

/**
 * Gửi một lần: khoá theo ref (bấm đúp → 1 request), báo `onBusy` cho tấm (tấm không đóng khi đang gửi), lỗi BE → câu
 * nguyên văn + cuộn tới dòng lỗi. 401 thì im (đã về màn đăng nhập).
 */
export function useSubmit(onBusy: (b: boolean) => void) {
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errRef = useRef<HTMLDivElement>(null);

  const run = useCallback(
    async <T,>(send: () => Promise<T>, onOk: (r: T) => void) => {
      if (lock.current) return;
      lock.current = true;
      setBusy(true);
      onBusy(true);
      setError(null);
      try {
        const r = await send();
        lock.current = false;
        setBusy(false);
        onBusy(false);
        onOk(r);
      } catch (err) {
        lock.current = false;
        setBusy(false);
        onBusy(false);
        if (err instanceof ApiError && err.status === 401) return;
        setError(errorText(err));
        requestAnimationFrame(() => errRef.current?.scrollIntoView({ block: "nearest" }));
      }
    },
    [onBusy],
  );

  return { busy, error, setError, errRef, run, locked: () => lock.current };
}
