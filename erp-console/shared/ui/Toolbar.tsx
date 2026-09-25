"use client";

// Thanh công cụ đầu màn dữ liệu: ô tìm (lọc phía máy) + nút Làm mới + mốc "cập nhật lúc".
// Bản HTML cũ để ô tìm và nút làm mới trên topbar; console mới đặt ngay đầu màn để dùng được trên điện thoại.

import { useId } from "react";
import { Icon } from "./Icon";
import { timeHM } from "@/shared/lib/format";

type Props = {
  query: string;
  onQuery: (q: string) => void;
  placeholder: string;
  onRefresh: () => void;
  refreshing: boolean;
  /** Mốc dữ liệu (as_of của BE). */
  asOf?: string;
};

export function Toolbar({ query, onQuery, placeholder, onRefresh, refreshing, asOf }: Props) {
  const id = useId();
  return (
    <div className="toolbar">
      <div className="search">
        <label htmlFor={id} className="sr-only">
          Tìm kiếm
        </label>
        <Icon name="search" />
        <input
          id={id}
          name="q"
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          enterKeyHint="search"
        />
        {query && (
          <button type="button" className="clr" onClick={() => onQuery("")} aria-label="Xoá tìm">
            <Icon name="close" />
          </button>
        )}
      </div>
      <button
        type="button"
        className="iconbtn"
        onClick={onRefresh}
        disabled={refreshing}
        aria-label="Làm mới"
        title="Làm mới"
      >
        <Icon name="refresh" className={refreshing ? "spin" : undefined} />
      </button>
      {asOf && (
        <span className="asof muted" aria-live="polite">
          {refreshing ? "Đang tải…" : `Cập nhật ${timeHM(asOf)}`}
        </span>
      )}
    </div>
  );
}
