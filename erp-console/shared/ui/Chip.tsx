// Chip trạng thái chuẩn (UI-RULES §1.2, §9): MỘT nhãn, không chú thích bên trong. Nhãn + tông màu lấy từ
// shared/lib/enums.ts: <Chip table={ENUMS.salesOrderStatus} value={order.status} />. Giá trị lạ → chip xám ghi đúng mã gốc (ED-02-AC4); giá trị trống → "—" (không chip).
// Chip KHÔNG tự đặt nhãn; muốn chip riêng (vd số lần in tem) truyền thẳng `entry`.
import { enumOf, isEmptyEnumValue, type EnumEntry, type EnumTable } from "@/shared/lib/enums";

type Props =
  | { table: EnumTable; value: string | number | boolean | null | undefined; entry?: never }
  | { entry: EnumEntry; table?: never; value?: never };

export function Chip(props: Props) {
  if (!props.entry && isEmptyEnumValue(props.value)) return <span className="muted">—</span>;
  const e = props.entry ?? enumOf(props.table, props.value);
  return <span className={`stat-chip ${e.tone}`}>{e.label}</span>;
}
