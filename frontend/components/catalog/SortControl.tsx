"use client";

import { useRef, useState } from "react";
import { BottomSheet } from "../ui/Sheet";
import SegmentedControl from "../ui/SegmentedControl";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./SortControl.module.css";

export type SortValue = "default" | "price_asc" | "price_desc";

export interface SortControlProps {
  value: SortValue;
  onChange: (v: SortValue) => void;
  /** Số sản phẩm đang hiện. */
  resultCount: number;
}

const OPTIONS: { value: SortValue; label: string; short: string }[] = [
  { value: "default", label: "Mặc định", short: "Mặc định" },
  { value: "price_asc", label: "Giá thấp đến cao", short: "Giá ↑" },
  { value: "price_desc", label: "Giá cao đến thấp", short: "Giá ↓" },
];

/** Đổi thứ tự danh sách. Điện thoại: nút mở bảng chọn. Máy tính: SegmentedControl. Món hết luôn ở cuối (do màn lo). */
export default function SortControl({ value, onChange, resultCount }: SortControlProps) {
  const [open, setOpen] = useState(false);
  const current = OPTIONS.find((o) => o.value === value) ?? OPTIONS[0];
  const listRef = useRef<HTMLFieldSetElement>(null);

  return (
    <>
      <div className={s.mobile}>
        <span className={cx(s.count, "num")}>{resultCount} sản phẩm</span>
        <button
          type="button"
          className={s.trigger}
          aria-haspopup="dialog"
          aria-expanded={open}
          aria-label={`Sắp xếp theo ${current.label.toLowerCase()}`}
          onClick={() => setOpen(true)}
        >
          Sắp xếp: {current.short}
          <Icon name="chevron-down" size={14} strokeWidth={2} />
        </button>
        <BottomSheet open={open} onClose={() => setOpen(false)} title="Sắp xếp">
          <fieldset ref={listRef} className={s.list}>
            <legend className="visually-hidden">Sắp xếp</legend>
            {OPTIONS.map((o) => (
              <label key={o.value} className={cx(s.row, o.value === value && s.selected)}>
                <input
                  type="radio"
                  name="sort-sheet"
                  value={o.value}
                  checked={o.value === value}
                  className={s.radio}
                  onChange={() => {
                    onChange(o.value);
                    setOpen(false);
                  }}
                />
                <span>{o.label}</span>
                {o.value === value ? <Icon name="check" size={18} strokeWidth={2.2} /> : null}
              </label>
            ))}
          </fieldset>
        </BottomSheet>
      </div>
      <div className={s.desktop}>
        <SegmentedControl
          legend="Sắp xếp"
          name="sort-segmented"
          options={OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
          value={value}
          onChange={onChange}
        />
      </div>
    </>
  );
}
