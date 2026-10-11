"use client";

import { useEffect, useId, useState } from "react";
import type { KeyboardEvent } from "react";
import Button from "../ui/Button";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import { isInfoKind, normalizeVoucherInput, voucherMessage, VOUCHER_CODE_MAX, type VoucherErrorKind } from "@/features/cart/voucherView";
import s from "./VoucherField.module.css";

export interface VoucherFieldProps {
  /**
   * trigger-row: điện thoại, dòng "Mã giảm giá · Nhập mã ›" (hoặc chip khi đã áp).
   * sheet: nội dung bottom sheet (ô nhập + "Áp dụng").
   * inline: máy tính, ô nhập + "Áp dụng" ngay trong tóm tắt (hoặc chip + "Bỏ mã").
   */
  variant: "trigger-row" | "sheet" | "inline";
  /** Có thì hiện chip mã đã áp. */
  appliedCode?: string;
  checking?: boolean;
  error?: VoucherErrorKind;
  /** Đơn tối thiểu của mã (đồng), cho câu MIN_ORDER. */
  minOrderAmount?: string | null;
  /** Số ưu đãi tự động đang áp (đồng) cho câu BETTER_PROMO. */
  promoAmount?: string | null;
  onApply: (code: string) => void;
  onRemove: () => void;
  /** Gõ lại thì báo cha ẩn lỗi. */
  onEdit?: () => void;
  onRetry?: () => void;
  /** trigger-row: mở bottom sheet. */
  onOpenSheet?: () => void;
}

/**
 * Ô mã giảm giá (COMPONENTS #48, UI-RULES §2b). Mỗi đơn 1 mã; số tiền giảm không hiện ở đây mà ở dòng "Giảm giá −…"
 * của CartSummary (số do máy chủ trả). Không tự tính giảm, không log mã.
 */
export default function VoucherField({
  variant,
  appliedCode,
  checking = false,
  error,
  minOrderAmount,
  promoAmount,
  onApply,
  onRemove,
  onEdit,
  onRetry,
  onOpenSheet,
}: VoucherFieldProps) {
  const uid = useId();
  const inputId = `${uid}-code`;
  const errId = `${uid}-err`;
  const hintId = `${uid}-hint`;
  const [value, setValue] = useState("");

  // Áp xong thì xoá ô để lần sau nhập mã khác.
  useEffect(() => {
    if (appliedCode) setValue("");
  }, [appliedCode]);

  function submit() {
    if (!value || checking) return;
    onApply(value);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  const errorNode = error ? (
    <p id={errId} role={isInfoKind(error) ? "status" : "alert"} className={cx(s.error, isInfoKind(error) && s.errorInfo)}>
      <Icon name={isInfoKind(error) ? "info" : "error"} size={14} />
      <span>
        {voucherMessage(error, minOrderAmount, promoAmount)}
        {error === "NETWORK" && onRetry ? (
          <>
            {" "}
            <button type="button" className={s.retry} onClick={onRetry}>
              Thử lại
            </button>
          </>
        ) : null}
      </span>
    </p>
  ) : null;

  const chip = appliedCode ? (
    <span className={s.chip}>
      <Icon name="check" size={14} />
      <span className={s.chipCode}>{appliedCode}</span>
      <button type="button" className={s.chipRemove} data-voucher-remove aria-label={`Bỏ mã ${appliedCode}`} onClick={onRemove}>
        <span className={s.chipRemoveDot}>
          <Icon name="close" size={12} />
        </span>
      </button>
    </span>
  ) : null;

  if (variant === "trigger-row") {
    if (appliedCode) {
      return (
        <div className={cx(s.row, s.onlyMobile)}>
          <span className={s.rowLabel}>Mã giảm giá</span>
          {chip}
        </div>
      );
    }
    return (
      <div className={s.onlyMobile}>
        <div className={s.row}>
          <span className={s.rowLabel}>Mã giảm giá</span>
          <button type="button" className={s.openBtn} aria-haspopup="dialog" aria-describedby={error ? errId : undefined} onClick={onOpenSheet}>
            Nhập mã
            <Icon name="chevron-right" size={16} />
          </button>
        </div>
        {errorNode}
      </div>
    );
  }

  const applyDisabled = !value || checking;
  const input = (
    <input
      id={inputId}
      className={cx(s.input, error && !isInfoKind(error) && s.inputBad)}
      type="text"
      value={value}
      onChange={(e) => {
        if (checking) return;
        setValue(normalizeVoucherInput(e.target.value));
        onEdit?.();
      }}
      onKeyDown={onKeyDown}
      readOnly={checking}
      autoCapitalize="characters"
      autoComplete="off"
      autoCorrect="off"
      spellCheck={false}
      enterKeyHint="done"
      maxLength={VOUCHER_CODE_MAX}
      placeholder="Nhập mã"
      aria-invalid={error && !isInfoKind(error) ? true : undefined}
      aria-describedby={error ? errId : hintId}
      data-autofocus={variant === "sheet" ? true : undefined}
    />
  );

  if (variant === "sheet") {
    return (
      <div className={s.sheetBody}>
        <label htmlFor={inputId} className="visually-hidden">
          Mã giảm giá
        </label>
        <div className={s.inputRow}>
          {input}
          <Button className={s.sheetBtn} loading={checking} loadingText="Đang kiểm" disabled={applyDisabled} onClick={submit} aria-label={checking ? "Đang kiểm mã" : undefined}>
            Áp dụng
          </Button>
        </div>
        {errorNode}
        {error ? null : (
          <p id={hintId} className={s.hint}>
            Mỗi đơn dùng 1 mã.
          </p>
        )}
      </div>
    );
  }

  // inline (máy tính)
  if (appliedCode) {
    return (
      <div className={cx(s.inline, s.onlyDesktop)}>
        <span className={s.inlineLabel}>Mã giảm giá</span>
        <div className={s.appliedRow}>
          {chip}
          <button type="button" className={s.removeText} data-voucher-remove aria-label={`Bỏ mã ${appliedCode}`} onClick={onRemove}>
            <Icon name="close" size={14} />
            Bỏ mã
          </button>
        </div>
      </div>
    );
  }
  return (
    <div className={cx(s.inline, s.onlyDesktop)}>
      <label htmlFor={inputId} className={s.inlineLabel}>
        Mã giảm giá
      </label>
      <div className={s.inputRow}>
        {input}
        <Button variant="outline" loading={checking} loadingText="Đang kiểm" disabled={applyDisabled} onClick={submit}>
          Áp dụng
        </Button>
      </div>
      {errorNode}
      {error ? null : (
        <p id={hintId} className={s.hint}>
          Mỗi đơn dùng 1 mã.
        </p>
      )}
    </div>
  );
}
