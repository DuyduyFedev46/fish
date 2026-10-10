// Vai trò trang bắt buộc go-live (BR-ND-16) + 3 vai trò SHOP-5-02 (BR-ND-20), khớp `Entry.PAGE_ROLE_CHOICES` backend.
// Nhãn lấy từ `shared/lib/enums.ts`.
import { ENUMS } from "@/shared/lib/enums";
import { CONTENT_MSG as M } from "./messages";
import type { ContentPageRole } from "./types";

type PageRole = NonNullable<ContentPageRole>;

const PAGE_ROLE_LABELS: Record<PageRole, string> = {
  privacy: ENUMS.entryPageRole.privacy.label,
  terms: ENUMS.entryPageRole.terms.label,
  refund: ENUMS.entryPageRole.refund.label,
  seller_info: ENUMS.entryPageRole.seller_info.label,
  shipping: ENUMS.entryPageRole.shipping.label,
  payment: ENUMS.entryPageRole.payment.label,
  complaints: ENUMS.entryPageRole.complaints.label,
};

export const REQUIRED_PAGE_ROLES: PageRole[] = [
  "privacy",
  "terms",
  "refund",
  "seller_info",
  "shipping",
  "payment",
  "complaints",
];

export function pageRoleLabel(role: string): string {
  return (PAGE_ROLE_LABELS as Record<string, string>)[role] ?? role;
}

export const PAGE_ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: M.fieldPageRoleNone },
  ...REQUIRED_PAGE_ROLES.map((value) => ({ value, label: PAGE_ROLE_LABELS[value] })),
];
