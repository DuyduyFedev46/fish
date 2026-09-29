import type { FooterLinkItem, PrivacyPolicyResponse, SiteInfoResponse } from "./types";

export const MOCK_SELLER_INFO: SiteInfoResponse = {
  seller: {
    name: "Vựa Thử Nghiệm",
    business_type: "Hộ kinh doanh",
    registration_no: "0000000000",
    tax_code: "0000000000",
    address: "1 Đường Thử, Phường Thử, Tỉnh Thử",
    phone: "0900000000",
    email: "lienhe@example.com",
  },
  seller_complete: true,
  privacy_consent_required: true,
  confirm_call_notice: false,
  confirm_call_hours: "7:00–20:00",
  cskh_notice: {
    enabled: true,
    working_hours: "07:00-21:00",
    max_attempts: 3,
    window_minutes: 30,
    decision_minutes: 30,
    auto_cancel_enabled: false,
    refund_deadline_days: 30,
    hotline: "1900 xxxx",
  },
};

export const MOCK_FOOTER_LINKS: FooterLinkItem[] = [
  { title: "Chính sách bảo mật", slug: "chinh-sach-bao-mat" },
  { title: "Chính sách kiểm hàng và đổi trả", slug: "chinh-sach-kiem-hang-va-doi-tra" },
  { title: "Chính sách thanh toán", slug: "chinh-sach-thanh-toan" },
  { title: "Chính sách giao hàng", slug: "chinh-sach-giao-hang" },
];

export const MOCK_PRIVACY_POLICY: PrivacyPolicyResponse = {
  slug: "chinh-sach-bao-mat",
  title: "Chính sách bảo mật thông tin",
  version: 1,
  version_id: 918,
  effective_from: "2026-09-28T00:00:00Z",
};

export async function mockSiteInfo(): Promise<SiteInfoResponse> {
  return Promise.resolve(MOCK_SELLER_INFO);
}

export async function mockFooterLinks(): Promise<FooterLinkItem[]> {
  return Promise.resolve(MOCK_FOOTER_LINKS);
}

export async function mockPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  return Promise.resolve(MOCK_PRIVACY_POLICY);
}
