"use client";

// Ô tìm ⌘K / Ctrl+K (🟡 T5): ở Lô 1 chỉ NHẢY TỚI MỤC MENU theo tên. Không tìm khách, không gọi API, không ghi
// từ khoá đi đâu (không localStorage, URL, log). Lô 17 thêm nhảy theo mã chứng từ khớp đúng.
// Hai dạng: ô gõ trên topbar (≥768 px) và nút kính lúp (điện thoại) — cùng mở một bảng kết quả.

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Icon } from "../Icon";
import type { NavItem } from "@/shared/lib/nav";
import { fold } from "@/shared/lib/search";

type Props = {
  items: NavItem[];
  /** Mở/đóng từ Shell (phím tắt ở Shell, nút kính lúp ở topbar hẹp). */
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function CommandSearch({ items, open, onOpenChange }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const listId = useId();

  const results = useMemo(() => {
    const q = fold(query);
    if (!q) return items;
    return items.filter((i) => fold(i.label).includes(q) || fold(i.short).includes(q));
  }, [items, query]);

  useEffect(() => {
    if (open) {
      openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setQuery("");
      setActive(0);
      const frame = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(frame);
    }
  }, [open]);

  useEffect(() => setActive(0), [query]);

  // Đóng bằng Esc / bấm nền: trả focus về nút đã mở (hoặc nút tìm đang hiện nếu mở bằng phím tắt), không để rơi về body.
  const dismiss = useCallback(() => {
    const opener = openerRef.current;
    // Trả focus ngay (đồng bộ) trước khi hộp thoại gỡ khỏi cây, để không có khoảnh khắc focus rơi về body.
    const target =
      opener && opener !== document.body && opener.isConnected
        ? opener
        : Array.from(document.querySelectorAll<HTMLElement>("button[aria-label='Tìm màn hình']")).find((b) => b.offsetParent !== null);
    target?.focus();
    onOpenChange(false);
  }, [onOpenChange]);

  // Esc nghe ở cấp tài liệu: bấm Esc ngay sau khi mở (lúc ô nhập chưa kịp nhận focus) vẫn đóng được.
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        dismiss();
      }
    };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [open, dismiss]);

  if (!open) return null;

  const go = (item: NavItem | undefined) => {
    if (!item) return;
    onOpenChange(false);
    router.push(item.href);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (results.length ? (a + 1) % results.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (results.length ? (a - 1 + results.length) % results.length : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      go(results[active]);
    }
  };

  return (
    <div className="cmd-layer" role="presentation">
      <button type="button" className="cmd-scrim" tabIndex={-1} aria-label="Đóng tìm kiếm" onClick={dismiss} />
      <div className="cmd" role="dialog" aria-modal="true" aria-label="Tìm màn hình" onKeyDown={onKey}>
        <label className="cmd-input">
          <Icon name="search" />
          <input
            ref={inputRef}
            type="search"
            name="cmd"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm màn hình…"
            aria-label="Tìm màn hình"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={results[active] ? `${listId}-${results[active].key}` : undefined}
            autoComplete="off"
            enterKeyHint="go"
          />
        </label>
        <ul id={listId} className="cmd-list" role="listbox" aria-label="Màn hình">
          {results.length === 0 && <li className="cmd-empty">Không có màn nào khớp.</li>}
          {results.map((i, idx) => (
            <li
              key={i.key}
              id={`${listId}-${i.key}`}
              role="option"
              aria-selected={idx === active}
              className={idx === active ? "on" : undefined}
              onMouseEnter={() => setActive(idx)}
              onClick={() => go(i)}
            >
              <Icon name={i.icon} />
              <span>{i.label}</span>
              {i.section && <small>{i.section}</small>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
