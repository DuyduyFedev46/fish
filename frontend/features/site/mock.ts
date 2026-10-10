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
    zalo: "0900000000",
    working_hours: "7:00 – 20:00, thứ Hai đến Chủ nhật",
    registration_issued_by: "Sở Thử Nghiệm",
    registration_issued_on: "2026-01-01",
    // Chưa có link thông báo website -> khối biểu tượng ẩn (05-phap-ly §4).
    website_notice_url: null,
    website_notice_image: null,
  },
  seller_complete: true,
  privacy_consent_required: true,
  confirm_call_notice: false,
  confirm_call_hours: "7:00–20:00",
  confirmation_policy: {
    enabled: true,
    working_hours: "07:00-21:00",
    max_attempts: 3,
    window_minutes: 30,
    decision_minutes: 30,
    auto_cancel_enabled: false,
    refund_deadline_days: 30,
    hotline: "1900 xxxx",
  },
  policies: { return_report_hours: null, min_qty_kg: "1", qty_step_kg: "0.5", hold_minutes: 30 },
};

// Khớp 6 trang chính sách do lệnh `load_shop_content` nạp (06-marketing B4, thứ tự footer 1→6).
export const MOCK_FOOTER_LINKS: FooterLinkItem[] = [
  { title: "Chính sách đổi trả và hoàn tiền", slug: "doi-tra" },
  { title: "Chính sách giao hàng", slug: "giao-hang" },
  { title: "Chính sách thanh toán", slug: "thanh-toan" },
  { title: "Chính sách quyền riêng tư", slug: "quyen-rieng-tu" },
  { title: "Điều kiện giao dịch chung", slug: "dieu-khoan" },
  { title: "Cơ chế giải quyết khiếu nại", slug: "khieu-nai" },
];

export const MOCK_PRIVACY_POLICY: PrivacyPolicyResponse = {
  slug: "quyen-rieng-tu",
  title: "Chính sách quyền riêng tư",
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
