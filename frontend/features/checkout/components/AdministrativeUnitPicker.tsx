"use client";

// Ô chọn một cấp địa giới (tỉnh, quận/huyện, phường/xã) của form nhận hàng, STA-02 (BR-BH-29). Bấm nút thì mở bảng chọn có ô
// tìm không dấu: điện thoại là tấm trượt từ đáy, máy tính là hộp thoại giữa màn (BottomSheet). Danh sách tải từ
// `getAdministrativeUnits` khi có cấp cha; đang tải, lỗi (Thử lại), rỗng đều có trạng thái. Không lưu gì vào storage/URL/console.

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { getAdministrativeUnits } from "@/lib/api";
import { foldVietnamese } from "@/lib/text";
import type { AddressScheme, AdministrativeLevel, AdministrativeUnit } from "@/lib/types";
import BottomSheet from "@/components/ui/Sheet";
import Button from "@/components/ui/Button";
import Icon from "@/components/ui/Icon";
import Spinner from "@/components/ui/Spinner";
import { cx } from "@/components/ui/cx";
import { filterUnits } from "../formRules";
import s from "./AdministrativeUnitPicker.module.css";

export interface AdministrativeUnitPickerProps {
  /** Id nút mở (id ô trên form: f-addr-province, f-addr-district, f-addr-ward). */
  id: string;
  label: string;
  scheme: AddressScheme;
  level: AdministrativeLevel;
  /** Mã cấp trên; chưa có thì ô bị tắt và hiện `disabledHint`. */
  parentCode?: string;
  value: string;
  onChange: (code: string) => void;
  placeholder: string;
  disabledHint?: string;
  error?: string;
  /** Form đang gửi: không mở bảng. */
  readOnly?: boolean;
  /** Dòng giải thích cho ô tìm, ví dụ "Gõ tên phường/xã, không cần dấu". */
  searchLabel: string;
}

type LoadState = { status: "idle" | "loading" | "error" } | { status: "ready"; items: AdministrativeUnit[] };

export default function AdministrativeUnitPicker({
  id,
  label,
  scheme,
  level,
  parentCode,
  value,
  onChange,
  placeholder,
  disabledHint,
  error,
  readOnly = false,
  searchLabel,
}: AdministrativeUnitPickerProps) {
  const needsParent = level !== "province";
  const enabled = !needsParent || !!parentCode;
  const [load, setLoad] = useState<LoadState>({ status: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const listId = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const listRef = useRef<HTMLUListElement>(null);

  // Tải danh sách khi có cấp cha; đổi kiểu hay cấp cha thì tải lại từ đầu (cấp con đã bị form xoá).
  useEffect(() => {
    if (!enabled) {
      setLoad({ status: "idle" });
      return;
    }
    let live = true;
    setLoad({ status: "loading" });
    getAdministrativeUnits(scheme, level, parentCode)
      .then((res) => live && setLoad({ status: "ready", items: res.items }))
      .catch(() => live && setLoad({ status: "error" }));
    return () => {
      live = false;
    };
  }, [enabled, scheme, level, parentCode, attempt]);

  const items = load.status === "ready" ? load.items : [];
  const shown = useMemo(() => filterUnits(items, query, foldVietnamese), [items, query]);
  const selected = items.find((u) => u.code === value);

  // Đang mở mà cấp cha đổi: đóng bảng.
  useEffect(() => {
    if (!enabled) setOpen(false);
  }, [enabled]);

  useEffect(() => {
    setActive(0);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.querySelector<HTMLElement>('[data-active="true"]')?.scrollIntoView?.({ block: "nearest" });
  }, [active, open, shown.length]);

  function openSheet() {
    if (!enabled || readOnly) return;
    setQuery("");
    setOpen(true);
    if (load.status === "error") setAttempt((n) => n + 1);
  }

  function pick(code: string) {
    onChange(code);
    setOpen(false);
  }

  function onSearchKey(e: KeyboardEvent<HTMLInputElement>) {
    // Bảng nằm trong <form> của màn đặt hàng: Enter không bao giờ được gửi form.
    if (e.key === "Enter") e.preventDefault();
    if (shown.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, shown.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Home" && e.ctrlKey) {
      e.preventDefault();
      setActive(0);
    } else if (e.key === "End" && e.ctrlKey) {
      e.preventDefault();
      setActive(shown.length - 1);
    } else if (e.key === "Enter") {
      const u = shown[Math.min(active, shown.length - 1)];
      if (u) pick(u.code);
    }
  }

  const buttonText = selected?.name ?? (enabled ? placeholder : (disabledHint ?? placeholder));
  const describedBy = error ? errorId : !enabled && disabledHint ? hintId : undefined;

  return (
    <div className={cx(s.field, error && s.hasError)}>
      <label htmlFor={id} className={s.label}>
        {label}
        <span className="visually-hidden"> (bắt buộc)</span>
      </label>
      <button
        type="button"
        id={id}
        className={cx(s.trigger, !selected && s.placeholder)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        disabled={!enabled || readOnly}
        onClick={openSheet}
      >
        <span className={s.triggerText}>
          {enabled && load.status === "loading" && !selected && value ? "Đang tải…" : buttonText}
        </span>
        <Icon name="chevron-down" size={18} />
      </button>
      {error ? (
        <p id={errorId} className={s.error}>
          <Icon name="error" size={14} />
          <span>{error}</span>
        </p>
      ) : null}
      <BottomSheet open={open} onClose={() => setOpen(false)} title={label} initialFocus="first-action">
        <div className={s.panel}>
          <input
            type="search"
            className={s.search}
            data-autofocus
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={shown.length > 0 ? `${listId}-${Math.min(active, shown.length - 1)}` : undefined}
            aria-autocomplete="list"
            aria-label={searchLabel}
            placeholder="Gõ tên, không cần dấu"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="done"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onSearchKey}
          />
          {load.status === "loading" ? (
            <div className={s.state} role="status" aria-busy="true">
              <Spinner size={18} />
              <span>Đang tải danh sách…</span>
            </div>
          ) : load.status === "error" ? (
            <div className={s.state} role="alert">
              <p>Chưa tải được danh sách. Kiểm tra mạng rồi thử lại.</p>
              <Button variant="secondary" onClick={() => setAttempt((n) => n + 1)}>
                Thử lại
              </Button>
            </div>
          ) : shown.length === 0 ? (
            <div className={s.state} role="status">
              <p>{query ? "Không thấy kết quả phù hợp. Thử gõ ngắn hơn." : "Chưa có mục nào để chọn."}</p>
            </div>
          ) : (
            <>
              <p className="visually-hidden" role="status">
                {shown.length} kết quả
              </p>
              <ul id={listId} ref={listRef} role="listbox" aria-label={label} className={s.list}>
                {shown.map((u, i) => (
                  <li
                    key={u.code}
                    id={`${listId}-${i}`}
                    role="option"
                    aria-selected={u.code === value}
                    data-active={i === Math.min(active, shown.length - 1)}
                    className={cx(s.option, u.code === value && s.selected)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pick(u.code)}
                  >
                    <span>{u.name}</span>
                    {u.code === value ? <Icon name="check" size={18} /> : null}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </BottomSheet>
    </div>
  );
}
