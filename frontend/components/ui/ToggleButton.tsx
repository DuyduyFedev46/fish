import { cx } from "./cx";
import s from "./ToggleButton.module.css";

export interface ToggleButtonProps {
  pressed: boolean;
  onPressedChange: (pressed: boolean) => void;
  /** preset: "1,5 kg". thumb: "Ảnh 2 trên 3". */
  label: string;
  variant?: "preset" | "thumb";
  /** thumb: ảnh nhỏ. */
  imageSrc?: string;
}

/** Nút bật/tắt dạng ô: chọn nhanh số kg ở trang chi tiết. Không phải công tắc (switch). */
export default function ToggleButton({
  pressed,
  onPressedChange,
  label,
  variant = "preset",
  imageSrc,
}: ToggleButtonProps) {
  return (
    <button
      type="button"
      className={cx(s.toggle, s[variant], pressed && s.pressed)}
      aria-pressed={pressed}
      aria-label={variant === "thumb" ? label : undefined}
      onClick={() => onPressedChange(!pressed)}
    >
      {variant === "thumb" && imageSrc ? <img src={imageSrc} alt="" /> : variant === "preset" ? label : null}
    </button>
  );
}
