"use client";

// Thanh lọc trên bảng (UI-RULES §4.2): ô tìm, chọn trạng thái, khoảng ngày; bên phải "Đang hiện n / m <noun>".
// Không nút Làm mới. Ô tìm KHÔNG ghi từ khoá đi đâu (không localStorage/URL/log) — màn tự debounce rồi gọi API.
// Mọi lựa chọn là ô chọn thật (select/input date) để dùng được bằng bàn phím và trên điện thoại.

import { useId, useRef } from "react";
import { Icon } from "../Icon";

export type FilterSelect = {
  key: string;
  /** Nhãn đọc cho trình đọc màn hình (không hiện chữ). */
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
};

export type DateRange = {
  from: string;
  to: string;
  onFrom: (value: string) => void;
  onTo: (value: string) => void;
};

type Props = {
  query: string;
  onQuery: (q: string) => void;
  placeholder: string;
  /** Nhãn đọc của ô tìm. */
  searchLabel: string;
  selects?: FilterSelect[];
  dateRange?: DateRange;
  /** "Đang hiện 10 / 45 đơn". Bỏ trống = không hiện. */
  summary?: string;
  /** Chỗ thêm (nút lọc riêng của màn). */
  children?: React.ReactNode;
};

// Ô ngày như board (W5i): khung 32px có icon lịch bên trái; vẫn là input date thật (bàn phím, điện thoại).
// Chạm icon mở bảng chọn ngày (nút chỉ chuột; bàn phím dùng ô nhập như cũ).
function DateBox({ label, value, min, max, onChange }: { label: string; value: string; min?: string; max?: string; onChange: (v: string) => void }) {
  const ref = useRef<HTMLInputElement>(null);
  const openPicker = () => {
    try {
      ref.current?.showPicker?.();
    } catch {
      ref.current?.focus();
    }
  };
  return (
    <label className="fb-date">
      <span className="sr-only">{label}</span>
      <span className="fb-date-ic" aria-hidden="true" onClick={openPicker}>
        <Icon name="calendar_today" />
      </span>
      <input ref={ref} type="date" value={value} min={min} max={max} onChange={(e) => onChange(e.target.value)} aria-label={label} />
    </label>
  );
}

export function FilterBar({ query, onQuery, placeholder, searchLabel, selects, dateRange, summary, children }: Props) {
  const id = useId();
  return (
    <div className="fb" role="search" aria-label={searchLabel}>
      <div className="fb-search search">
        <label htmlFor={`${id}-q`} className="sr-only">
          {searchLabel}
        </label>
        <Icon name="search" />
        <input
          id={`${id}-q`}
          name="q"
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          enterKeyHint="search"
        />
        {query && (
          <button type="button" className="clr" onClick={() => onQuery("")} aria-label="Xoá tìm kiếm">
            <Icon name="close" />
          </button>
        )}
      </div>
      {selects?.map((s) => (
        <label key={s.key} className="fb-select">
          <span className="sr-only">{s.label}</span>
          <select value={s.value} onChange={(e) => s.onChange(e.target.value)} aria-label={s.label}>
            {s.options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <Icon name="expand_more" />
        </label>
      ))}
      {dateRange && (
        <div className="fb-dates">
          <DateBox label="Từ ngày" value={dateRange.from} max={dateRange.to || undefined} onChange={dateRange.onFrom} />
          <span aria-hidden="true">–</span>
          <DateBox label="Đến ngày" value={dateRange.to} min={dateRange.from || undefined} onChange={dateRange.onTo} />
        </div>
      )}
      {children}
      {summary && (
        <span className="fb-summary" aria-live="polite">
          {summary}
        </span>
      )}
    </div>
  );
}
