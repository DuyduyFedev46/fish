"use client";

// Công tắc bật/tắt và nhóm radio của form (board F1k, F1m). Vẫn là <input type="checkbox"> / <input type="radio"> thật
// (bàn phím, đọc màn hình, e2e giữ nguyên); chỉ đổi cách vẽ. KHÔNG thêm role="switch" để getByRole("checkbox") còn trúng.

import { useId } from "react";
import s from "./Choice.module.css";

type SwitchProps = {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  name?: string;
  disabled?: boolean;
};

/** Hàng "nhãn … công tắc" như board: nhãn bên trái, công tắc 34×20 bên phải. */
export function Switch({ label, checked, onChange, name, disabled }: SwitchProps) {
  return (
    <label className={s.switchRow} data-disabled={disabled || undefined}>
      <span>{label}</span>
      <input className={s.switch} type="checkbox" name={name} checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

type RadioProps = {
  label: string;
  name: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
  error?: string | null;
};

/** Nhóm radio ngang (2–3 lựa chọn ngắn); nhãn nhóm nằm trên, như board. Từ 4 lựa chọn trở lên dùng Field as="select". */
export function RadioGroup({ label, name, value, options, onChange, required, disabled, error }: RadioProps) {
  const uid = useId();
  return (
    <div className={s.group} role="radiogroup" aria-labelledby={`${uid}-l`} aria-required={required || undefined} aria-invalid={error ? true : undefined}>
      <span className={s.groupLabel} id={`${uid}-l`}>
        {label}
        {required && (
          <span className={s.req} aria-hidden="true">
            {" "}
            *
          </span>
        )}
      </span>
      <div className={s.options}>
        {options.map((o) => (
          <label key={o.value} className={s.option} data-disabled={disabled || undefined}>
            <input className={s.radio} type="radio" name={name} value={o.value} checked={value === o.value} disabled={disabled} onChange={() => onChange(o.value)} />
            <span>{o.label}</span>
          </label>
        ))}
      </div>
      {error && <p className={s.err}>{error}</p>}
    </div>
  );
}
