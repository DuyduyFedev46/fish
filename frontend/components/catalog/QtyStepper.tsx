"use client";

import type { SaleUnit } from "@/lib/types";
import { formatQty, parseQtyRule, stepDown, stepUp } from "@/lib/quantity";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./QtyStepper.module.css";

export interface QtyStepperProps {
  value: number;
  /** `min_qty` từ API. */
  min: number;
  /** `qty_step` từ API. */
  step: number;
  unit: SaleUnit;
  /** Cho nhãn đọc: "Thêm 0,5 kg Mực ống". */
  itemName: string;
  /**
   * select: trang chi tiết, số chưa vào giỏ; ở mức tối thiểu nút trừ tắt.
   * cart: thẻ và dòng giỏ; ở mức tối thiểu nút trừ thành thùng rác và gọi `onRequestRemove`.
   */
  mode?: "select" | "cart";
  variant?: "outline" | "filled";
  size?: "md" | "sm";
  onChange: (next: number) => void;
  /** Bắt buộc khi mode="cart": container mở hộp thoại xác nhận bỏ món, không xoá ngay. */
  onRequestRemove?: () => void;
  /** id của dòng "Tối thiểu 1 kg": nút trừ tắt trỏ tới đó để người dùng trình đọc nghe lý do. */
  describedBy?: string;
  className?: string;
}

/**
 * Tăng giảm số lượng theo luật bán (BR-BH-22): kg tối thiểu 1, bước 0,5; combo tối thiểu 1, bước 1.
 * Không bao giờ xuống dưới mức tối thiểu hay ra số ngoài bước; không có trần (FE không biết tồn kho).
 */
export default function QtyStepper({
  value,
  min,
  step,
  unit,
  itemName,
  mode = "cart",
  variant = "outline",
  size = "md",
  onChange,
  onRequestRemove,
  describedBy,
  className,
}: QtyStepperProps) {
  const rule = parseQtyRule(min, step, unit);
  const stepText = `${formatQty(rule.step)} ${unit}`;
  const atMin = stepDown(value, rule) === null;
  const asTrash = atMin && mode === "cart";
  const disabledMinus = atMin && mode === "select";

  function onMinus() {
    const next = stepDown(value, rule);
    if (next === null) {
      if (mode === "cart") onRequestRemove?.();
      return; // select: tắt, không làm gì
    }
    onChange(next);
  }

  return (
    <div
      role="group"
      aria-label={`Số lượng ${itemName}`}
      className={cx(s.stepper, s[variant], s[size], className)}
    >
      <button
        type="button"
        className={s.btn}
        aria-label={asTrash ? `Bỏ ${itemName} khỏi giỏ` : `Bớt ${stepText} ${itemName}`}
        aria-disabled={disabledMinus || undefined}
        aria-describedby={disabledMinus ? describedBy : undefined}
        data-qty-minus=""
        onClick={onMinus}
      >
        <span key={asTrash ? "trash" : "minus"} className={s.icon}>
          <Icon name={asTrash ? "trash" : "minus"} size={18} strokeWidth={2} />
        </span>
      </button>
      <span className={cx(s.value, "num")} aria-live={mode === "select" ? "polite" : undefined}>
        {formatQty(value)} {unit}
      </span>
      <button
        type="button"
        className={s.btn}
        aria-label={`Thêm ${stepText} ${itemName}`}
        data-qty-plus=""
        onClick={() => onChange(stepUp(value, rule))}
      >
        <span className={s.icon}>
          <Icon name="plus" size={18} strokeWidth={2} />
        </span>
      </button>
    </div>
  );
}
