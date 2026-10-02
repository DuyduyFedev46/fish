"use client";

// Một trường form (UI-RULES §6.2): nhãn nằm TRÊN ô, `*` đỏ khi bắt buộc, đơn vị nằm trong ô (`kg`, `đ`, `ngày`),
// lỗi = viền đỏ + MỘT dòng đỏ dưới ô, nối bằng aria-describedby / aria-invalid. KHÔNG có chữ gợi ý xám dưới ô.
// Ô số: `inputMode="decimal"`. Mật khẩu dùng PasswordInput riêng.

import { useId, useLayoutEffect, useRef, useState } from "react";
import { MONEY_FRACTION_MESSAGE, editMoneyInput } from "../../lib/moneyInput";
import { Icon } from "../Icon";
import s from "./Field.module.css";

type Common = {
  label: string;
  /** Bắt buộc → hiện `*` đỏ + aria-required. */
  required?: boolean;
  /** Lỗi của ô; có giá trị → viền đỏ + một dòng dưới ô. */
  error?: string | null;
  /** Đơn vị nằm trong ô, bên phải (kg, đ, ngày). */
  unit?: string;
  name?: string;
  disabled?: boolean;
  autoFocus?: boolean;
};

type InputProps = Common & {
  as?: "input";
  /** `number` = ô số: inputMode decimal, vẫn là type=text để không bị trình duyệt đổi dấu thập phân.
   *  `money` = ô tiền VNĐ (số nguyên): giá trị chỉ gồm chữ số nhóm nghìn "1.500.000", giữ con trỏ khi gõ/xoá/dán (shared/lib/moneyInput). */
  type?: "text" | "number" | "money" | "tel" | "email" | "date" | "datetime-local";
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
};

type TextareaProps = Common & {
  as: "textarea";
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  maxLength?: number;
  placeholder?: string;
};

type SelectProps = Common & {
  as: "select";
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
};

export function Field(props: InputProps | TextareaProps | SelectProps) {
  const uid = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const pendingCaret = useRef<number | null>(null);
  // Đặt lại con trỏ sau khi React ghi giá trị đã nhóm nghìn (ghi giá trị làm con trỏ nhảy về cuối). Chạy cả khi giá trị không đổi.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (el && pendingCaret.current != null && document.activeElement === el) el.setSelectionRange(pendingCaret.current, pendingCaret.current);
  });
  const inputId = `${uid}-f`;
  const errId = `${uid}-e`;
  const [rejected, setRejected] = useState(false);
  const { label, required, unit, name, disabled, autoFocus } = props;
  // Ô tiền từ chối chuỗi có phần lẻ: giữ giá trị cũ, báo ngay dưới ô cho tới lần sửa hợp lệ kế tiếp.
  const error = props.error || (rejected ? MONEY_FRACTION_MESSAGE : null);
  const invalid = Boolean(error);
  const common = {
    id: inputId,
    name,
    disabled,
    autoFocus,
    "aria-invalid": invalid || undefined,
    "aria-describedby": invalid ? errId : undefined,
    "aria-required": required || undefined,
    "data-autofocus": autoFocus ? "" : undefined,
  };

  let control: React.ReactNode;
  if (props.as === "textarea") {
    control = (
      <textarea
        {...common}
        className={s.control}
        rows={props.rows ?? 3}
        maxLength={props.maxLength}
        placeholder={props.placeholder}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    );
  } else if (props.as === "select") {
    control = (
      <select {...common} className={`${s.control} ${s.select}`} value={props.value} onChange={(e) => props.onChange(e.target.value)}>
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    );
  } else {
    const isMoney = props.type === "money";
    const isNumber = props.type === "number" || isMoney;
    control = (
      <input
        {...common}
        ref={inputRef}
        className={`${s.control} ${unit ? s.withUnit : ""} ${isNumber ? "num" : ""}`}
        type={isNumber ? "text" : props.type ?? "text"}
        inputMode={isMoney ? "numeric" : isNumber ? "decimal" : props.type === "tel" ? "tel" : undefined}
        autoComplete="off"
        maxLength={props.maxLength}
        placeholder={props.placeholder}
        value={props.value}
        onChange={(e) => {
          if (!isMoney) {
            props.onChange(e.target.value);
            return;
          }
          const el = e.target;
          const inputType = (e.nativeEvent as InputEvent).inputType ?? "";
          const edit = editMoneyInput(props.value, el.value, el.selectionStart ?? el.value.length, inputType);
          pendingCaret.current = edit.caret;
          setRejected(edit.rejected === "fraction");
          if (!edit.rejected) props.onChange(edit.value);
          // Nếu giá trị không đổi (vd gõ chữ bị bỏ) thì React không vẽ lại; đặt con trỏ ngay sau sự kiện.
          queueMicrotask(() => {
            if (document.activeElement === el) el.setSelectionRange(edit.caret, edit.caret);
            pendingCaret.current = null;
          });
        }}
      />
    );
  }

  return (
    <div className={s.field} data-invalid={invalid || undefined}>
      <label htmlFor={inputId} className={s.label}>
        {label}
        {required && (
          <span className={s.req} aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </label>
      <div className={s.box}>
        {control}
        {unit && props.as !== "textarea" && props.as !== "select" && <span className={s.unit}>{unit}</span>}
      </div>
      {invalid && (
        <p className={s.err} id={errId}>
          <Icon name="error" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
