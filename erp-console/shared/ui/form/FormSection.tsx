// Thẻ chia khối trong trang form (board F1a/F1d/F1f/F1k/F1m): nền trắng, viền, bo 10px, lề 20px, tiêu đề 14px đậm.
// `FormGrid` xếp ô thành 2 hoặc 3 cột (từ 640px; điện thoại một cột). `FormSpan` kéo một ô qua hết hàng.

import s from "./FormSection.module.css";

type SectionProps = {
  title?: string;
  /** Nút / liên kết cạnh tiêu đề (vd "Thêm dòng"). */
  action?: React.ReactNode;
  children: React.ReactNode;
};

export function FormSection({ title, action, children }: SectionProps) {
  return (
    <section className={s.section}>
      {(title || action) && (
        <div className={s.head}>
          {title && <h3 className={s.title}>{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function FormGrid({ cols = 2, children }: { cols?: 2 | 3; children: React.ReactNode }) {
  return <div className={`${s.grid} ${cols === 3 ? s.cols3 : s.cols2}`}>{children}</div>;
}

/** Bọc một ô để nó chiếm cả hàng trong FormGrid. */
export function FormSpan({ children }: { children: React.ReactNode }) {
  return <div className={s.span}>{children}</div>;
}
