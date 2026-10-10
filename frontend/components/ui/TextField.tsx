"use client";

import type { ReactNode } from "react";
import Icon from "./Icon";
import { cx } from "./cx";
import s from "./TextField.module.css";

export interface TextFieldProps {
  id: string;
  /** 'name' | 'phone' | 'delivery_address' | 'order_code' */
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  type?: "text" | "tel";
  multiline?: boolean;
  rows?: number;
  placeholder?: string;
  hint?: string;
  /** Có lỗi: aria-invalid, viền đỏ, dòng lỗi thay dòng gợi ý. */
  error?: string;
  required?: boolean;
  autoComplete?: string;
  inputMode?: "text" | "tel" | "numeric";
  /** Khi form đang gửi: dùng readOnly, không disabled, để dữ liệu vẫn đọc được. */
  readOnly?: boolean;
  /** Mã đơn: viết hoa, tắt kiểm chính tả. */
  autoCapitalize?: "off" | "characters";
  spellCheck?: boolean;
  /** Khe cuối ô (vd. nút Bản đồ). */
  endSlot?: ReactNode;
  /** id phần tử mô tả thêm (vd. dòng khu vực giao hàng), nối vào aria-describedby. */
  describedBy?: string;
  /** Viền xanh khi đã điền từ bản đồ. */
  tone?: "default" | "good";
  /** field: nhãn nhỏ 13/500. title: nhãn như tiêu đề khối 15/600 (ô địa chỉ). */
  labelStyle?: "field" | "title";
  /** Bỏ nhãn nhìn thấy (vẫn có nhãn cho trình đọc màn hình). */
  hideLabel?: boolean;
}

/**
 * Ô nhập có nhãn, gợi ý và lỗi (COMPONENTS #7). Ô cao 44, chữ 16 để iOS không tự phóng to. Nhãn là `<label for>` thật.
 * Giá trị không bao giờ ghi vào storage, URL hay console: giữ trong state của form để lỗi mạng không làm mất dữ liệu.
 */
export default function TextField({
  id,
  name,
  label,
  value,
  onChange,
  onBlur,
  type = "text",
  multiline = false,
  rows = 2,
  placeholder,
  hint,
  error,
  required = false,
  autoComplete,
  inputMode,
  readOnly = false,
  autoCapitalize,
  spellCheck,
  endSlot,
  describedBy,
  tone = "default",
  labelStyle = "field",
  hideLabel = false,
}: TextFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedIds = [error ? errorId : hint ? hintId : null, describedBy].filter(Boolean).join(" ") || undefined;
  const common = {
    id,
    name,
    value,
    placeholder,
    required,
    readOnly,
    autoComplete,
    inputMode,
    autoCapitalize,
    spellCheck,
    "aria-invalid": error ? (true as const) : undefined,
    "aria-describedby": describedIds,
    onBlur,
    className: s.control,
  };

  return (
    <div className={cx(s.field, error && s.hasError, tone === "good" && s.good)}>
      <label htmlFor={id} className={hideLabel ? "visually-hidden" : labelStyle === "title" ? s.labelTitle : s.label}>
        {label}
        {required ? <span className="visually-hidden"> (bắt buộc)</span> : null}
      </label>
      <div className={cx(s.box, multiline && s.multi)}>
        {multiline ? (
          <textarea {...common} rows={rows} onChange={(e) => onChange(e.target.value)} />
        ) : (
          <input {...common} type={type} onChange={(e) => onChange(e.target.value)} />
        )}
        {endSlot ? <div className={s.end}>{endSlot}</div> : null}
      </div>
      {error ? (
        <p id={errorId} className={s.error}>
          <Icon name="error" size={14} />
          <span>{error}</span>
        </p>
      ) : hint ? (
        <p id={hintId} className={s.hint}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}
