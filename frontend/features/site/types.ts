export interface SellerInfo {
  name: string | null;
  business_type: string | null;
  registration_no: string | null;
  tax_code: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  // 02b §3.6 (BR-ND-18): khoá mới, BE trả thật ở lô 5. Tuỳ chọn để FE lô 1 đọc được cả backend cũ;
  // vắng hoặc `null` = chưa cấu hình -> ẩn phần tương ứng (khối biểu tượng thông báo ẩn hẳn khi chưa có link, 05-phap-ly §4).
  zalo?: string | null;
  working_hours?: string | null;
  registration_issued_by?: string | null;
  registration_issued_on?: string | null;
  website_notice_url?: string | null;
  website_notice_image?: string | null;
}

/** Số liệu cho trang Cách mua (5-04 AC3) và E3, đọc từ settings BE (02b §3.6). Tiền/số lượng là chuỗi thập phân. */
export interface ShopPolicies {
  /** `null` khi env `SHOP_RETURN_REPORT_HOURS` rỗng. */
  return_report_hours: number | null;
  min_qty_kg: string;
  qty_step_kg: string;
  hold_minutes: number;
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
  // 02b §3.6: vắng = backend chưa có (lô 5) -> FE dùng mặc định của mình hoặc ẩn câu có số.
  policies?: ShopPolicies | null;
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
