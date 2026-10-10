import { personalText, type CustomerHiddenReason } from "@/shared/lib/personalData";
import { PersonalText } from "@/shared/ui/PersonalText";

/** §2.7: ô khách đã bị che (`null`) ghi lý do (quá 7 ngày / không có quyền xem thông tin khách); còn lại như PersonalText. */
export function CustomerCell({ value, reason }: { value: string | null | undefined; reason?: CustomerHiddenReason | null }) {
  if (value === null) return <span className="muted">{personalText(null, "—", reason)}</span>;
  return <PersonalText value={value} />;
}
