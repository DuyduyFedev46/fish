"use client";

import type { ReactNode } from "react";
import { cx } from "./cx";
import s from "./Checkbox.module.css";

export interface CheckboxProps {
  id: string;
  /** 'privacy_consent' */
  name: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** Câu đồng ý kèm link. */
  children: ReactNode;
  error?: string;
  disabled?: boolean;
}

/**
 * Ô đồng ý xử lý dữ liệu (COMPONENTS #9). KHÔNG BAO GIỜ tick sẵn (NĐ 356/2025, BR-BH-17): trạng thái đầu do
 * chỗ dùng quyết định và phải là `false`. Cả hàng là `<label>` để vùng chạm đủ 44; link trong nhãn vẫn bấm riêng được.
 */
export default function Checkbox({ id, name, checked, onChange, children, error, disabled = false }: CheckboxProps) {
  const errorId = `${id}-error`;
  return (
    <div className={cx(s.wrap, error && s.hasError)}>
      <label className={s.row} htmlFor={id}>
        <input
          id={id}
          name={name}
          type="checkbox"
          className={s.box}
          checked={checked}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className={s.text}>{children}</span>
      </label>
      {error ? (
        <p id={errorId} className={s.error}>
          {error}
        </p>
      ) : null}
    </div>
  );
}
