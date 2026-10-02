"use client";

// Một trường form (UI-RULES §6.2): nhãn nằm TRÊN ô, `*` đỏ khi bắt buộc, đơn vị nằm trong ô (`kg`, `đ`, `ngày`),
// lỗi = viền đỏ + MỘT dòng đỏ dưới ô, nối bằng aria-describedby / aria-invalid. KHÔNG có chữ gợi ý xám dưới ô.
// Ô số: `inputMode="decimal"`. Mật khẩu dùng PasswordInput riêng.

import { useId } from "react";
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
  /** `number` = ô số: inputMode decimal, vẫn là type=text để không bị trình duyệt đổi dấu thập phân. */
  type?: "text" | "number" | "tel" | "email" | "date" | "datetime-local";
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
  /** Hiện bộ đếm "n/max" dưới ô, bên phải (cần `maxLength`). Không phải chữ gợi ý: chỉ là số ký tự đã gõ. */
  counter?: boolean;
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
  const inputId = `${uid}-f`;
  const errId = `${uid}-e`;
  const { label, required, error, unit, name, disabled, autoFocus } = props;
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
    const isNumber = props.type === "number";
    control = (
      <input
        {...common}
        className={`${s.control} ${unit ? s.withUnit : ""} ${isNumber ? "num" : ""}`}
        type={isNumber ? "text" : props.type ?? "text"}
        inputMode={isNumber ? "decimal" : props.type === "tel" ? "tel" : undefined}
        autoComplete="off"
        maxLength={props.maxLength}
        placeholder={props.placeholder}
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
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
      {props.as === "textarea" && props.counter && props.maxLength ? (
        <p className={s.counter} data-field-counter>
          <span className="sr-only">Số ký tự đã nhập: </span>
          {props.value.length}/{props.maxLength}
        </p>
      ) : null}
      {invalid && (
        <p className={s.err} id={errId}>
          <Icon name="error" />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}
