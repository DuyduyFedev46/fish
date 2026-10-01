// Hiện một trường dữ liệu khách có thể bị ẩn theo thời hạn (SR-PII-02): null → chữ mờ "Đã ẩn (quá 7 ngày)".
// Rỗng/thiếu → `whenEmpty` (giữ cách hiện cũ của từng màn). Không đoán, không gọi thêm API.
import { personalText } from "@/shared/lib/personalData";

type Props = {
  value: string | null | undefined;
  /** Chữ khi trường rỗng thật (không phải đã ẩn). Mặc định "—". */
  whenEmpty?: string;
  /** true → chữ `whenEmpty` cũng hiện mờ (vd "Chưa có địa chỉ"). */
  mutedWhenEmpty?: boolean;
};

export function PersonalText({ value, whenEmpty = "—", mutedWhenEmpty = false }: Props) {
  if (value === null) return <span className="muted">{personalText(null)}</span>;
  if (!value && mutedWhenEmpty) return <span className="muted">{whenEmpty}</span>;
  return <>{personalText(value, whenEmpty)}</>;
}
