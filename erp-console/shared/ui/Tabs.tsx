"use client";

// Tab dưới topbar (UI-RULES §2.3): gạch dưới màu nhấn ở tab đang chọn, số đếm tuỳ chọn ("Hàng chờ thanh toán 2").
// role="tablist"; mũi tên trái/phải đổi tab (roving tabindex). `useTabParam` đồng bộ `?tab=` để tải lại / chia sẻ link
// vẫn đúng tab, và Back về tab trước. Chỉ ghi KHOÁ tab vào URL, không bao giờ ghi gì khác (không dữ liệu cá nhân).

import { useCallback, useEffect, useId, useRef, useState } from "react";

export type TabItem = {
  key: string;
  label: string;
  /** Số hiện cạnh nhãn (vd số việc chờ). Bỏ trống = không hiện. 0 = không hiện. */
  count?: number | null;
};

type Props = {
  tabs: TabItem[];
  value: string;
  onChange: (key: string) => void;
  /** Nhãn đọc cho trình đọc màn hình. */
  label: string;
  /** Nếu màn dùng `id` riêng cho vùng nội dung của tab, truyền để nối aria-controls. */
  panelId?: string;
};

export function Tabs({ tabs, value, onChange, label, panelId }: Props) {
  const base = useId();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKey = (e: React.KeyboardEvent, idx: number) => {
    let next = -1;
    if (e.key === "ArrowRight") next = (idx + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    if (next < 0) return;
    e.preventDefault();
    const k = tabs[next].key;
    onChange(k);
    refs.current[k]?.focus();
  };

  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {tabs.map((t, i) => {
        const selected = t.key === value;
        return (
          <button
            key={t.key}
            ref={(el) => {
              refs.current[t.key] = el;
            }}
            id={`${base}-${t.key}`}
            type="button"
            role="tab"
            className="tab"
            aria-selected={selected}
            aria-controls={panelId}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.key)}
            onKeyDown={(e) => onKey(e, i)}
          >
            {t.label}
            {t.count ? <span className="tab-count">{t.count}</span> : null}
          </button>
        );
      })}
    </div>
  );
}

/** Đọc khoá tab từ `?tab=`; khoá lạ hoặc thiếu → `fallback`. */
export function tabFromSearch(search: string, keys: readonly string[], fallback: string): string {
  const q = new URLSearchParams(search).get("tab");
  return q && keys.includes(q) ? q : fallback;
}

/** Địa chỉ mới khi chọn tab: giữ nguyên các tham số khác; tab mặc định thì bỏ `?tab=`. */
export function tabHref(loc: { pathname: string; search: string; hash: string }, key: string, fallback: string): string {
  const params = new URLSearchParams(loc.search);
  if (key === fallback) params.delete("tab");
  else params.set("tab", key);
  const qs = params.toString();
  return loc.pathname + (qs ? `?${qs}` : "") + loc.hash;
}

/**
 * Tab đang chọn, đồng bộ với `?tab=` (không dùng useSearchParams để khỏi cần Suspense ở trang tĩnh).
 * Lần vẽ đầu luôn là `fallback` (khớp HTML tĩnh), rồi đọc URL ngay sau khi mount. Khoá lạ → về `fallback`.
 * Đổi tab = `pushState` (ED-01-AC4: Back quay về tab trước); Back/Forward bắn `popstate` thì đọc lại URL.
 */
export function useTabParam(keys: readonly string[], fallback: string): [string, (key: string) => void] {
  const [tab, setTab] = useState(fallback);
  const keyList = keys.join("|");
  const current = useRef(fallback);

  useEffect(() => {
    const valid = keyList.split("|");
    const sync = () => {
      const next = tabFromSearch(window.location.search, valid, fallback);
      current.current = next;
      setTab(next);
    };
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, [keyList, fallback]);

  const select = useCallback(
    (key: string) => {
      if (key === current.current) return; // bấm lại tab đang chọn: không thêm mục lịch sử
      current.current = key;
      setTab(key);
      window.history.pushState(window.history.state, "", tabHref(window.location, key, fallback));
    },
    [fallback],
  );

  return [tab, select];
}
