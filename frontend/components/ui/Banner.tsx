import type { ReactNode } from "react";
import Icon, { type IconName } from "./Icon";
import { cx } from "./cx";
import s from "./Banner.module.css";

export interface BannerProps {
  tone: "info" | "success" | "warn" | "crit";
  title?: string;
  children?: ReactNode;
  layout?: "inset" | "full-bleed" | "strip";
  /** null: không icon. Mặc định theo tone. */
  icon?: IconName | null;
  /** Banner hiện do thao tác: crit dùng "assertive" (role="alert"), còn lại "polite" (role="status"). */
  live?: "off" | "polite" | "assertive";
  action?: ReactNode;
}

const DEFAULT_ICON: Record<BannerProps["tone"], IconName> = {
  info: "info",
  success: "check",
  warn: "warning",
  crit: "error",
};

/** Khối thông báo trong trang. Không viền màu, không nút đóng. Nghĩa nằm ở chữ, không chỉ ở màu. */
export default function Banner({
  tone,
  title,
  children,
  layout = "inset",
  icon,
  live = "off",
  action,
}: BannerProps) {
  const iconName = icon === undefined ? DEFAULT_ICON[tone] : icon;
  const role = live === "assertive" ? "alert" : live === "polite" ? "status" : undefined;
  return (
    <div
      className={cx(s.banner, s[tone], s[layout === "full-bleed" ? "fullBleed" : layout])}
      role={role}
    >
      {iconName ? (
        <span className={s.icon}>
          <Icon name={iconName} size={layout === "strip" ? 14 : 18} />
        </span>
      ) : null}
      <div className={s.text}>
        {title ? <p className={s.title}>{title}</p> : null}
        {children ? <div className={s.body}>{children}</div> : null}
      </div>
      {action ? <div className={s.action}>{action}</div> : null}
    </div>
  );
}
