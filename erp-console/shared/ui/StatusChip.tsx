// Trạng thái đơn / lô dạng CHẤM MÀU + CHỮ (UI3, thay viên thuốc đậm): chấm chỉ là tín hiệu phụ, chữ `status_label`
// của BE luôn hiện nên không chỉ dựa vào màu. Tông màu ở shared/lib/status.ts. Tên giữ "StatusChip" để không đổi chỗ gọi.
// Viên thuốc `.chip` vẫn còn cho nhãn nhóm/Đang làm ở Nhân sự, Tài khoản.
import { UNKNOWN_STATUS, type StatusLook } from "@/shared/lib/status";

export function StatusChip({ map, status, label }: { map: Record<string, StatusLook>; status: string; label: string }) {
  const look = map[status] || UNKNOWN_STATUS;
  return (
    <span className={`status ${look.tone}`}>
      <span className="dot" aria-hidden="true" />
      {label}
    </span>
  );
}
