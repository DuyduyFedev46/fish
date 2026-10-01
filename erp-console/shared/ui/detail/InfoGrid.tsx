// Lưới thông tin 2 cột (UI-RULES §5.4): mỗi ô MỘT giá trị, nhãn nhỏ trên, giá trị dưới. Mobile = 1 cột.
// Các ô là <InfoField>; đặt trong <dl> để trình đọc màn hình hiểu cặp nhãn–giá trị.
import s from "./InfoGrid.module.css";

export function InfoGrid({ children, label, title }: { children: React.ReactNode; label?: string; title?: string }) {
  return (
    <section className={s.wrap} aria-label={label ?? title}>
      {title && <h3 className={s.title}>{title}</h3>}
      <dl className={s.grid}>{children}</dl>
    </section>
  );
}
