"use client";

// Ô tìm ⌘K / Ctrl+K (🟡 T5): nhảy tới MỤC MENU theo tên. Không tìm khách, không ghi từ khoá đi đâu (không localStorage, URL, log).
// Lô 17b (ED-07): gõ đúng MẪU MÃ chứng từ (SO…, GH-…, mã lô, PR-n, KK-n, RT-n, #n) thì thêm dòng "Mở <mã>" và Enter sẽ tra bằng endpoint có
// phạm vi rồi mở trang chi tiết. Chuỗi không đúng mẫu mã giữ hành vi cũ và KHÔNG gọi API (chống dò tên/SĐT, 02b T5).
// Hai dạng: ô gõ trên topbar (≥768 px) và nút kính lúp (điện thoại) — cùng mở một bảng kết quả.

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Icon } from "../Icon";
import type { NavItem } from "@/shared/lib/nav";
import { CODE_NOT_FOUND, parseCodeRef, resolveCodeRef } from "@/shared/lib/codeLookup";
import { fold } from "@/shared/lib/search";
import { loadErrorText } from "@/shared/lib/http";
import { useCodeFinder } from "./CodeFinderContext";

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
  const finder = useCodeFinder();
  const codeRef = useMemo(() => (finder ? parseCodeRef(query) : null), [finder, query]);
  // Kết quả tra mã: "đang tìm" · "không có" · "lỗi" (kèm câu của BE). Chỉ gắn với mã đang gõ; gõ tiếp thì bỏ.
  const [lookup, setLookup] = useState<{ state: "busy" | "none" | "error"; text?: string } | null>(null);
  const lookupAbort = useRef<AbortController | null>(null);

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

  useEffect(() => {
    setActive(0);
    setLookup(null);
    lookupAbort.current?.abort();
  }, [query]);
  useEffect(() => () => lookupAbort.current?.abort(), []);

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

  const openCode = async () => {
    if (!codeRef || !finder || lookup?.state === "busy") return;
    lookupAbort.current?.abort();
    const ac = new AbortController();
    lookupAbort.current = ac;
    setLookup({ state: "busy" });
    try {
      const r = await resolveCodeRef(codeRef, finder, ac.signal);
      if (ac.signal.aborted) return;
      if (r.status === "found") {
        onOpenChange(false);
        router.push(r.href);
      } else setLookup({ state: "none", text: CODE_NOT_FOUND(r.code) });
    } catch (err) {
      if (ac.signal.aborted) return;
      setLookup({ state: "error", text: loadErrorText(err) });
    }
  };

  const offset = codeRef ? 1 : 0; // dòng "Mở <mã>" nằm trước các mục menu
  const total = results.length + offset;

  const go = (item: NavItem | undefined) => {
    if (!item) return;
    onOpenChange(false);
    router.push(item.href);
  };

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (total ? (a + 1) % total : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (total ? (a - 1 + total) % total : 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Có mã đúng mẫu: Enter mở chứng từ, trừ khi người dùng đã chọn xuống một mục menu khớp tên.
      if (codeRef && active === 0) void openCode();
      else go(results[active - offset]);
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
            placeholder="Tìm màn hình hoặc mã chứng từ…"
            aria-label="Tìm màn hình"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={codeRef && active === 0 ? `${listId}-code` : results[active - offset] ? `${listId}-${results[active - offset].key}` : undefined}
            autoComplete="off"
            enterKeyHint="go"
          />
        </label>
        <ul id={listId} className="cmd-list" role="listbox" aria-label="Màn hình">
          {codeRef && (
            <li
              id={`${listId}-code`}
              role="option"
              aria-selected={active === 0}
              className={active === 0 ? "on" : undefined}
              data-cmd-code
              onMouseEnter={() => setActive(0)}
              onClick={() => void openCode()}
            >
              <Icon name={lookup?.state === "busy" ? "progress_activity" : "search"} className={lookup?.state === "busy" ? "spin" : undefined} />
              <span>{codeRef.code}</span>
              <small>{lookup?.state === "busy" ? "Đang tìm…" : "Mở chứng từ"}</small>
            </li>
          )}
          {lookup && lookup.state !== "busy" && (
            <li className="cmd-empty" role="status" data-cmd-code-result={lookup.state}>
              {lookup.text}
            </li>
          )}
          {results.length === 0 && !codeRef && <li className="cmd-empty">Không có màn nào khớp.</li>}
          {results.map((i, idx0) => {
            const idx = idx0 + offset;
            return (
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
            );
          })}
        </ul>
      </div>
    </div>
  );
}
