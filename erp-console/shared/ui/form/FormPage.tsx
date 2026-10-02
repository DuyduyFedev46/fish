"use client";

// Form dài / nhiều dòng = TRANG RIÊNG (UI-RULES §6.1): tiêu đề + alert đầu form + nội dung + thanh nút dính đáy
// (cao `--action-bar-h`), nút canh PHẢI: [phụ] [chính] (board F1k), nhãn nói rõ việc ("Lập phiếu hoàn 380.000 đ").
// Gửi lỗi (`failed`) → nút chính đổi thành "Thử lại" (UI-RULES §6.6); đang gửi → nút khoá + chữ "Đang gửi…".
// Việc phá huỷ (huỷ đơn, gỡ bài) → `danger`: nút chính đỏ. Thanh nút dính trong vùng cuộn của khung app nên không che menu.

import Link from "next/link";
import { Icon } from "../Icon";
import { primaryLabel } from "./useSubmit";
import s from "./FormPage.module.css";

type Props = {
  title: string;
  /** "← tên danh sách". */
  back?: { href: string; label: string };
  /** Alert đầu form (FormAlert, ConflictBanner). */
  alert?: React.ReactNode;
  onSubmit: () => void;
  /** Nhãn nút chính khi chưa lỗi. */
  primaryText: string;
  submitting?: boolean;
  /** Lần gửi gần nhất lỗi → "Thử lại". */
  failed?: boolean;
  /** Khoá nút chính (form chưa hợp lệ). */
  primaryDisabled?: boolean;
  danger?: boolean;
  /** Nút phụ "Quay lại" / "Huỷ". */
  secondary?: { label: string; onClick: () => void };
  children: React.ReactNode;
};

export function FormPage({ title, back, alert, onSubmit, primaryText, submitting = false, failed = false, primaryDisabled = false, danger = false, secondary, children }: Props) {
  return (
    <form
      className={s.page}
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (!submitting) onSubmit();
      }}
      aria-busy={submitting || undefined}
    >
      <header className={s.head}>
        {back && (
          <Link href={back.href} className={s.back}>
            <Icon name="arrow_back" />
            <span>{back.label}</span>
          </Link>
        )}
        <h2 className={s.title}>{title}</h2>
      </header>
      {alert}
      <div className={s.body}>{children}</div>
      <div className={s.bar} data-action-bar>
        {secondary && (
          <button type="button" className="btn" onClick={secondary.onClick} disabled={submitting}>
            {secondary.label}
          </button>
        )}
        <button
          type="submit"
          className={`btn ${danger ? "danger solid" : "primary"}`}
          disabled={submitting || primaryDisabled}
          aria-disabled={submitting || primaryDisabled}
        >
          {submitting && <Icon name="progress_activity" className="spin" />}
          <span>{submitting ? "Đang gửi…" : primaryLabel(primaryText, failed)}</span>
        </button>
      </div>
    </form>
  );
}
