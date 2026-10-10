"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { looksLikePhone } from "@/lib/text";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import SearchSuggest, { type SuggestItem } from "./SearchSuggest";
import s from "./SearchBox.module.css";

export interface SearchBoxProps {
  /** brand: trên header nền accent (pill, máy tính có nút "Tìm"). page: trong trang danh mục. */
  variant?: "brand" | "page";
  defaultValue?: string;
  placeholder?: string;
  autoFocus?: boolean;
  /** Đường dẫn trang kết quả, mặc định "/shop/". */
  action?: string;
  /** Container lọc sẵn từ catalog đã tải, tối đa 5 món. */
  suggestions?: SuggestItem[];
  recentQueries?: string[];
  onQueryChange?: (q: string) => void;
  onClearRecent?: () => void;
  /** Gọi khi gửi từ khoá (Enter, "Tìm", chọn "Xem tất cả") để container lưu "Tìm gần đây". */
  onRemember?: (q: string) => void;
}

const MIN_CHARS = 2;

/**
 * Ô tìm sản phẩm kèm gợi ý (combobox + listbox). Gõ từ 2 ký tự mới gợi ý. Enter hoặc "Tìm" đi tới
 * `/shop/?q=<từ khoá>`; ô rỗng thì không điều hướng. Chữ ô 16 px để iOS không tự phóng to.
 */
export default function SearchBox({
  variant = "page",
  defaultValue = "",
  placeholder = "Tìm cá, tôm, mực, combo…",
  autoFocus = false,
  action = "/shop/",
  suggestions = [],
  recentQueries = [],
  onQueryChange,
  onClearRecent,
  onRemember,
}: SearchBoxProps) {
  const router = useRouter();
  const inputId = useId();
  const listboxId = `${inputId}-list`;
  const optionPrefix = `${inputId}-opt`;
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState(defaultValue);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const q = value.trim();
  const hasQuery = q.length >= MIN_CHARS;
  const items = hasQuery ? suggestions.slice(0, 5) : [];
  const showPanel = open && (hasQuery || (q === "" && recentQueries.length > 0));
  const optionCount = hasQuery ? items.length + 1 : 0;

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  function go(query: string) {
    // Chuỗi giống số điện thoại không được đưa lên URL hay vào "Tìm gần đây" (bất biến 9).
    if (looksLikePhone(query)) {
      setOpen(false);
      return;
    }
    setOpen(false);
    setActive(-1);
    onRemember?.(query);
    router.push(`${action}?q=${encodeURIComponent(query)}`);
  }

  function pickItem(it: SuggestItem) {
    setOpen(false);
    setActive(-1);
    router.push(`/shop/item/?code=${encodeURIComponent(it.itemCode)}`);
  }

  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (active >= 0 && active < items.length) return pickItem(items[active]);
    if (!q) return;
    go(q);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      if (showPanel) {
        e.preventDefault();
        setOpen(false);
        setActive(-1);
      }
      return;
    }
    if ((e.key === "ArrowDown" || e.key === "ArrowUp") && optionCount > 0) {
      e.preventDefault();
      setOpen(true);
      setActive((cur) => {
        if (e.key === "ArrowDown") return cur >= optionCount - 1 ? 0 : cur + 1;
        return cur <= 0 ? optionCount - 1 : cur - 1;
      });
    }
  }

  return (
    <div ref={rootRef} className={s.root}>
      {showPanel ? <div className={s.scrim} aria-hidden="true" onClick={() => setOpen(false)} /> : null}
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
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showPanel}
          aria-controls={showPanel && hasQuery ? listboxId : undefined}
          aria-activedescendant={showPanel && active >= 0 ? `${optionPrefix}-${active}` : undefined}
          className={s.input}
          value={value}
          placeholder={placeholder}
          autoComplete="off"
          enterKeyHint="search"
          autoFocus={autoFocus}
          onChange={(e) => {
            setValue(e.target.value);
            setActive(-1);
            setOpen(true);
            onQueryChange?.(e.target.value);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {value ? (
          <button
            type="button"
            className={s.clear}
            aria-label="Xoá từ khoá"
            onClick={() => {
              setValue("");
              setActive(-1);
              onQueryChange?.("");
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
      <span role="status" className="visually-hidden">
        {showPanel && hasQuery ? `${items.length} gợi ý cho “${q}”` : ""}
      </span>
      {showPanel ? (
        <div className={s.panelWrap}>
          <SearchSuggest
            listboxId={listboxId}
            optionIdPrefix={optionPrefix}
            query={value}
            items={items}
            showViewAll={hasQuery}
            activeIndex={active}
            recent={recentQueries}
            onPickItem={pickItem}
            onViewAll={() => go(q)}
            onPickRecent={() => setOpen(false)}
            onClearRecent={() => onClearRecent?.()}
          />
        </div>
      ) : null}
    </div>
  );
}
