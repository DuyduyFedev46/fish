"use client";

import { useEffect, useRef } from "react";
import Icon from "./Icon";
import s from "./FormErrorSummary.module.css";

export interface FormErrorSummaryProps {
  /** Rỗng thì không render. Thứ tự theo thứ tự ô trên form. */
  errors: { fieldId: string; label: string }[];
  /** Mỗi lần bấm gửi mà còn lỗi, đổi số này để đưa tiêu điểm vào khối (lần đầu hiện cũng vậy). */
  focusToken?: number;
}

/**
 * Khối "Còn N chỗ cần sửa" (COMPONENTS #11). Mỗi mục là link nhảy tới ô và đưa tiêu điểm vào đó.
 * `role="alert"`. Không dùng cho form tra đơn (không được chỉ ra ô nào sai). Không chép chữ khách đã nhập.
 */
export default function FormErrorSummary({ errors, focusToken = 0 }: FormErrorSummaryProps) {
  const ref = useRef<HTMLDivElement>(null);
  const hasErrors = errors.length > 0;

  useEffect(() => {
    if (!hasErrors || focusToken === 0) return;
    ref.current?.focus();
    ref.current?.scrollIntoView({ block: "center", behavior: "auto" });
  }, [hasErrors, focusToken]);

  if (!hasErrors) return null;

  return (
    <div ref={ref} tabIndex={-1} role="alert" aria-labelledby="form-errors-title" className={s.summary}>
      <p id="form-errors-title" className={s.title}>
        <Icon name="error" size={18} />
        <span>Còn {errors.length} chỗ cần sửa</span>
      </p>
      <ul className={s.list}>
        {errors.map((e) => (
          <li key={e.fieldId}>
            <a
              href={`#${e.fieldId}`}
              className={s.link}
              onClick={(ev) => {
                ev.preventDefault();
                const el = document.getElementById(e.fieldId);
                if (el) {
                  el.focus();
                  el.scrollIntoView({ block: "center", behavior: "auto" });
                }
              }}
            >
              {e.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
