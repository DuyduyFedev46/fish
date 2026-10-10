"use client";

import { useRouter } from "next/navigation";
import { useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./SearchBox.module.css";

export interface SearchBoxProps {
  /** brand: trên header nền accent (pill, máy tính có nút "Tìm"). page: trong trang danh mục. */
  variant?: "brand" | "page";
  defaultValue?: string;
  placeholder?: string;
  autoFocus?: boolean;
  /** Đường dẫn trang kết quả, mặc định "/shop/". */
  action?: string;
}

/**
 * Ô tìm sản phẩm (lô 1: chỉ gửi form, chưa có gợi ý). Enter hoặc "Tìm" đi tới `/shop/?q=<từ khoá>`;
 * ô rỗng thì không điều hướng. Chữ ô 16 px để iOS không tự phóng to.
 */
export default function SearchBox({
  variant = "page",
  defaultValue = "",
  placeholder = "Tìm cá, tôm, mực, combo…",
  autoFocus = false,
  action = "/shop/",
}: SearchBoxProps) {
  const router = useRouter();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState(defaultValue);

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = value.trim();
    if (!q) return;
    router.push(`${action}?q=${encodeURIComponent(q)}`);
  }

  return (
    <form role="search" className={cx(s.form, s[variant])} onSubmit={submit}>
      <label htmlFor={inputId} className="visually-hidden">
        Tìm sản phẩm
      </label>
      <span className={s.glass}>
        <Icon name="search" size={18} strokeWidth={1.8} />
      </span>
      <input
        ref={inputRef}
        id={inputId}
        type="search"
        name="q"
        className={s.input}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        enterKeyHint="search"
        autoFocus={autoFocus}
        onChange={(e) => setValue(e.target.value)}
      />
      {value ? (
        <button
          type="button"
          className={s.clear}
          aria-label="Xoá từ khoá"
          onClick={() => {
            setValue("");
            inputRef.current?.focus();
          }}
        >
          <Icon name="close" size={16} strokeWidth={2} />
        </button>
      ) : null}
      <button type="submit" className={s.submit}>
        Tìm
      </button>
    </form>
  );
}
