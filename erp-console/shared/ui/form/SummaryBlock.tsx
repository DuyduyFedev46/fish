// Khối tóm tắt ngữ cảnh trong form (UI-RULES §6.3): mỗi dòng MỘT cặp nhãn – giá trị (đơn nào, còn hoàn được bao nhiêu).
// Dùng thay cho chữ gợi ý xám dưới ô. Giá trị nhạy cảm (SĐT, địa chỉ khách) do màn truyền vào đã che sẵn; khối này không tự lấy dữ liệu.
import s from "./SummaryBlock.module.css";

export type SummaryRow = {
  label: string;
  value: React.ReactNode;
  /** Mã chứng từ → chữ mono. */
  mono?: boolean;
  /** Số tiền / số lượng → căn số thẳng hàng. */
  num?: boolean;
  /** Dòng nhấn mạnh (tổng cần thu, số hoàn…). */
  strong?: boolean;
};

export function SummaryBlock({ rows, label }: { rows: SummaryRow[]; label?: string }) {
  if (rows.length === 0) return null;
  return (
    <dl className={s.block} aria-label={label}>
      {rows.map((r) => (
        <div key={r.label} className={s.row}>
          <dt className={s.k}>{r.label}</dt>
          <dd className={`${s.v} ${r.mono ? s.mono : ""} ${r.num ? "num" : ""} ${r.strong ? s.strong : ""}`}>{r.value}</dd>
        </div>
      ))}
    </dl>
  );
}
