import { cx } from "./cx";
import s from "./SegmentedControl.module.css";

export interface SegmentedControlProps<T extends string> {
  /** Nhãn nhóm, ví dụ "Sắp xếp". */
  legend: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  /** Tên nhóm radio (duy nhất trên trang). */
  name: string;
  className?: string;
}

/**
 * Chọn một trong vài giá trị ngang hàng, hiện tất cả cùng lúc (máy tính: sắp xếp danh mục).
 * Dựng bằng fieldset + radio gốc: trình duyệt lo phím ← → và đọc "đã chọn".
 */
export default function SegmentedControl<T extends string>({
  legend,
  options,
  value,
  onChange,
  name,
  className,
}: SegmentedControlProps<T>) {
  return (
    <fieldset className={cx(s.group, className)}>
      <legend className="visually-hidden">{legend}</legend>
      <span className={s.legend} aria-hidden="true">
        {legend}
      </span>
      {options.map((o) => (
        <label key={o.value} className={s.option}>
          <input
            type="radio"
            name={name}
            value={o.value}
            checked={o.value === value}
            onChange={() => onChange(o.value)}
            className={s.input}
          />
          <span className={s.pill}>{o.label}</span>
        </label>
      ))}
    </fieldset>
  );
}
