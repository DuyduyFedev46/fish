"use client";

// Thanh công cụ đầu màn dữ liệu CŨ: ô tìm (lọc phía máy) + mốc "cập nhật lúc". UI-RULES §2.2: KHÔNG có nút Làm mới.
// Màn mới dùng shared/ui/list/FilterBar; màn cũ còn gọi Toolbar tới khi được làm lại (Lô 17 xoá).
// `onRefresh` / `refreshing` còn nhận để các màn cũ build được nhưng không vẽ gì; dữ liệu tự nạp lại khi vào màn / sau thao tác.

import { useId } from "react";
import { Icon } from "./Icon";
import { timeHM } from "@/shared/lib/format";

type Props = {
  query: string;
  onQuery: (q: string) => void;
  placeholder: string;
  /** @deprecated Không còn nút Làm mới (UI-RULES §2.2). Giữ để màn cũ build được. */
  onRefresh?: () => void;
  /** Dùng để hiện "Đang tải…" cạnh mốc cập nhật. */
  refreshing?: boolean;
  /** Mốc dữ liệu (as_of của BE). */
  asOf?: string;
};

export function Toolbar({ query, onQuery, placeholder, refreshing, asOf }: Props) {
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
      {asOf && (
        <span className="asof muted" aria-live="polite">
          {refreshing ? "Đang tải…" : `Cập nhật ${timeHM(asOf)}`}
        </span>
      )}
    </div>
  );
}
