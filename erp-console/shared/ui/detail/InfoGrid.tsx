// Thẻ thông tin (UI-RULES §5.4, board D2b): thẻ có đầu 44px (tiêu đề chữ thường nằm trong thẻ), thân là lưới 2 cột; mỗi ô
// MỘT giá trị, nhãn nhỏ trên, giá trị dưới, ngăn các ô bằng đường kẻ mảnh. Mobile = 1 cột.
// Các ô là <InfoField>; đặt trong <dl> để trình đọc màn hình hiểu cặp nhãn–giá trị.
// `groups` = chia thẻ thành các cột có tiêu đề chữ HOA nhỏ ("THANH TOÁN" | "GIAO HÀNG" ở D2b); khi đó bỏ `children`.
import { Section } from "./Section";
import s from "./InfoGrid.module.css";

export type InfoGroup = { title: string; children: React.ReactNode };

type Props = {
  children?: React.ReactNode;
  label?: string;
  title?: string;
  count?: number | string | null;
  action?: React.ReactNode;
  groups?: InfoGroup[];
};

export function InfoGrid({ children, label, title, count, action, groups }: Props) {
  return (
    <Section title={title} count={count} action={action} flush aria-label={label ?? title}>
      {groups ? (
        <div className={s.groups}>
          {groups.map((g) => (
            <div key={g.title} className={s.group}>
              <div className={s.groupH}>{g.title}</div>
              <dl className={s.list}>{g.children}</dl>
            </div>
          ))}
        </div>
      ) : (
        <dl className={s.grid}>{children}</dl>
      )}
    </Section>
  );
}
