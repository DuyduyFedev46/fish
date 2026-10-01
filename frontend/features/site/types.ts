export interface SellerInfo {
  name: string | null;
  business_type: string | null;
  registration_no: string | null;
  tax_code: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
}

/** Cấu hình thông báo xác nhận đơn (BE: `settings.CONFIRMATION_*`). `working_hours` = `CONFIRMATION_WORKING_HOURS` (env cũ `CSKH_WORKING_HOURS` còn là fallback): nguồn duy nhất của khung giờ gọi. */
export interface ConfirmationPolicyConfig {
  enabled: boolean;
  working_hours: string;
  max_attempts: number;
  window_minutes: number;
  decision_minutes: number;
  auto_cancel_enabled: boolean;
  refund_deadline_days: number;
  hotline: string;
}

export interface SiteInfoResponse {
  seller: SellerInfo;
  seller_complete: boolean;
  privacy_consent_required: boolean;
  confirm_call_notice: boolean;
  confirm_call_hours: string;
  // `null`/vắng = backend cũ hoặc chưa cấu hình -> không hiện khối thông báo.
  /** Khoá mới (P8b Lô 3). Đọc khoá này trước: `confirmation_policy ?? cskh_notice` (xem `confirmationPolicy()`). */
  confirmation_policy?: ConfirmationPolicyConfig | null;
  /** Khoá cũ, BE còn trả song song tới Lô 5 (có thể vắng nếu BE đã gỡ). */
  cskh_notice?: ConfirmationPolicyConfig | null; // naming: allow - khoá JSON cũ BE còn trả song song tới Lô 5, FE chỉ đọc làm dự phòng
}

export interface FooterLinkItem {
  title: string;
  slug: string;
}

export interface PrivacyPolicyResponse {
  slug: string;
  title: string;
  version: number;
  version_id: number;
  effective_from: string | null;
}
