import type { ReactNode } from "react";
import Button from "./Button";
import Chip from "./Chip";
import Icon, { type IconName } from "./Icon";
import { cx } from "./cx";
import s from "./EmptyState.module.css";

export interface EmptyStateProps {
  icon: IconName;
  title: string;
  description?: string;
  /** Một nút chính. */
  primaryAction?: { label: string; href: string };
  /** Chip nhóm gợi ý. */
  suggestions?: { label: string; href: string }[];
  /** tel:… thì có nút phụ "Liên hệ chúng tôi để hỏi hàng". */
  contactHref?: string;
  contactLabel?: string;
  /** false: không khung (giỏ trống). */
  framed?: boolean;
  /** Mức tiêu đề, mặc định h2. */
  headingLevel?: 1 | 2;
  children?: ReactNode;
}

/** Trạng thái rỗng có một hướng đi tiếp: một nút chính, hoặc gợi ý nhóm kèm liên hệ. */
export default function EmptyState({
  icon,
  title,
  description,
  primaryAction,
  suggestions,
  contactHref,
  contactLabel = "Liên hệ chúng tôi để hỏi hàng",
  framed = true,
  headingLevel = 2,
  children,
}: EmptyStateProps) {
  const Heading = headingLevel === 1 ? "h1" : "h2";
  return (
    <section className={cx(s.empty, framed && s.framed)} aria-labelledby="empty-title">
      <span className={framed ? s.iconBox : s.iconBare} aria-hidden="true">
        <Icon name={icon} size={framed ? 30 : 40} />
      </span>
      <Heading id="empty-title" className={s.title}>
        {title}
      </Heading>
      {description ? <p className={s.description}>{description}</p> : null}
      {children}
      {primaryAction ? (
        <Button href={primaryAction.href} size="md" shape="pill" className={s.action}>
          {primaryAction.label}
        </Button>
      ) : null}
      {suggestions && suggestions.length > 0 ? (
        <ul className={s.chips} aria-label="Nhóm hàng gợi ý">
          {suggestions.map((x) => (
            <li key={x.href}>
              <Chip variant="link" label={x.label} href={x.href} />
            </li>
          ))}
        </ul>
      ) : null}
      {contactHref ? (
        <div className={s.contact}>
          <Button
            href={contactHref}
            variant="secondary"
            fullWidth
            iconStart={<Icon name="phone" size={18} />}
          >
            {contactLabel}
          </Button>
        </div>
      ) : null}
    </section>
  );
}
