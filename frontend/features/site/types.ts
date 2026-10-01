export interface SellerInfo {
  name: string | null;
  business_type: string | null;
  registration_no: string | null;
  tax_code: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
}

/** Cấu hình thông báo xác nhận đơn (BE: `settings.CONFIRMATION_*`). `working_hours` = `CONFIRMATION_WORKING_HOURS`: nguồn duy nhất của khung giờ gọi. */
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
  confirmation_policy?: ConfirmationPolicyConfig | null;
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
