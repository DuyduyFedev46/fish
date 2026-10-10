// PV-13-AC2: khi phiếu nhập vừa mất quyền xem mà chính mình là người lập và phiếu tạo từ hôm trước (giờ VN), màn nói thêm
// một câu để người dùng biết vì sao (phạm vi D6 chỉ còn "do tôi tạo hôm nay"). Hàm thuần để test mốc nửa đêm.
import { dateKeyInVietnam, todayInVietnam } from "@/shared/lib/format";
import type { ReceiptDetail } from "./types";

export function isOwnReceiptFromEarlierDay(
  row: Pick<ReceiptDetail, "created_by" | "created_at">,
  meId: number | null | undefined,
  now: Date = new Date(),
): boolean {
  if (!meId || row.created_by !== meId) return false;
  const created = dateKeyInVietnam(row.created_at);
  const today = todayInVietnam(now);
  return !!created && !!today && created < today;
}
