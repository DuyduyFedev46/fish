// Alert đầu form (UI-RULES §6.3): vàng = cảnh báo quan trọng (chỉ khi thật cần), đỏ = gửi lỗi. Một câu, nói cách sửa.
// `role="alert"` cho lỗi để trình đọc màn hình đọc ngay; cảnh báo dùng role="status".
import { Icon } from "../Icon";

type Props = {
  kind?: "error" | "warn";
  children: React.ReactNode;
  id?: string;
};

export function FormAlert({ kind = "error", children, id }: Props) {
  return (
    <div className={`alert-box ${kind === "error" ? "err" : "warn"}`} role={kind === "error" ? "alert" : "status"} id={id} data-form-alert={kind}>
      <Icon name={kind === "error" ? "error" : "warning"} />
      <span>{children}</span>
    </div>
  );
}
