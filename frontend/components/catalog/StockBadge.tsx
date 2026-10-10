import type { StockLevel } from "@/lib/types";
import Icon from "../ui/Icon";
import { cx } from "../ui/cx";
import s from "./StockBadge.module.css";

export interface StockBadgeProps {
  /** Chỉ nhận mức tồn từ `stock_level`. Không có prop nào nhận số kg (BR-BH-23). */
  level: StockLevel;
  /** overlay: nhãn trên ảnh (chỉ "Sắp hết", "Hết hàng"). inline: dưới giá, hiện cả "Còn hàng". */
  placement?: "overlay" | "inline";
  size?: "sm" | "md";
}

const LABEL: Record<StockLevel, string> = {
  in: "Còn hàng",
  low: "Sắp hết",
  out: "Hết hàng",
};

/** Nhãn mức tồn: Còn hàng, Sắp hết, Hết hàng. Chữ luôn hiện (không chỉ màu). Không bấm được. */
export default function StockBadge({ level, placement = "overlay", size = "sm" }: StockBadgeProps) {
  if (placement === "overlay" && level === "in") return null;
  const icon = level === "in" ? "check" : level === "low" ? "hourglass" : "ban";
  return (
    <span className={cx(s.badge, s[placement], s[size], s[level])}>
      <Icon name={icon} size={placement === "inline" ? 14 : size === "md" ? 14 : 12} strokeWidth={2} />
      {LABEL[level]}
    </span>
  );
}
