// Thẻ khối của trang chi tiết (UI-RULES §5, board D2b): nền trắng, viền, bo góc, đầu thẻ 44px chứa tiêu đề
// (chữ thường, đậm) + bộ đếm + hành động bên phải. Tiêu đề NẰM TRONG thẻ, không bao giờ là chữ hoa ngoài thẻ.
// Mọi khối trên trang chi tiết (thông tin, bảng con, dòng thời gian, trợ lý AI, nhóm quyền…) dùng thành phần này.
// `flush` = thân thẻ không có lề trong (bảng DataTable chạy sát mép; viền riêng của bảng được bỏ để khỏi thành thẻ lồng thẻ).
import s from "./Section.module.css";

type Props = Omit<React.ComponentPropsWithoutRef<"section">, "title"> & {
  /** Tiêu đề trong đầu thẻ. Bỏ trống = thẻ không có đầu. */
  title?: React.ReactNode;
  /** Bộ đếm cạnh tiêu đề, vd 3 → "Hàng & phân bổ lô  3". */
  count?: number | string | null;
  /** Hành động bên phải đầu thẻ (nút, liên kết). */
  action?: React.ReactNode;
  /** Thân thẻ không lề trong: dành cho bảng. */
  flush?: boolean;
};

export function Section({ title, count, action, flush = false, className, children, ...rest }: Props) {
  const hasHead = title !== undefined && title !== null && title !== "";
  return (
    <section {...rest} className={`${s.card}${className ? ` ${className}` : ""}`}>
      {hasHead && (
        <div className={s.head}>
          <h3 className={s.title}>
            {title}
            {count !== undefined && count !== null && <span className={`${s.count} num`}>{count}</span>}
          </h3>
          {action && <div className={s.action}>{action}</div>}
        </div>
      )}
      <div className={flush ? s.flush : s.body}>{children}</div>
    </section>
  );
}
