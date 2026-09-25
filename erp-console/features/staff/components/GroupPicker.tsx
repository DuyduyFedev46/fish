"use client";

// Chọn nhiều nhóm (cộng dồn, BR-PQ-09) bằng thẻ ô chọn. Chỉ là ô chọn: luật ai được gán nhóm nào do BE quyết (BR-PQ-17).
// `.check-row` giữ lại để e2e đo vùng bấm ≥44px; kiểu riêng ở staff.module.css.
import { GROUP_CODES, GROUP_HINT, groupLabel } from "@/shared/lib/groups";
import s from "../staff.module.css";

type Props = {
  value: string[];
  onChange: (groups: string[]) => void;
  disabled?: boolean;
  legend?: string;
  /** Mô tả thêm dưới nhóm ô chọn (gắn aria-describedby). */
  describedBy?: string;
  /** Focus vào ô đầu khi chế độ "Đổi nhóm" mở (data-autofocus, xem useFocusOnSwap). */
  autoFocus?: boolean;
};

export function GroupPicker({ value, onChange, disabled, legend = "Nhóm quyền", describedBy, autoFocus }: Props) {
  const toggle = (code: string, on: boolean) => {
    const next = on ? [...value, code] : value.filter((g) => g !== code);
    onChange(GROUP_CODES.filter((g) => next.includes(g)));
  };
  return (
    <fieldset className={s.groups} disabled={disabled} aria-describedby={describedBy}>
      <legend>{legend}</legend>
      {GROUP_CODES.map((code, i) => (
        <label key={code} className="check-row">
          <input
            data-autofocus={autoFocus && i === 0 ? true : undefined}
            type="checkbox"
            name="groups"
            value={code}
            checked={value.includes(code)}
            onChange={(e) => toggle(code, e.target.checked)}
          />
          <span>
            <b>{groupLabel(code)}</b>
            <small>{GROUP_HINT[code]}</small>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
