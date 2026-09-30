import type { SiteInfoResponse } from "../types";
import s from "./ConfirmationPolicyNotice.module.css";

/** Khung giờ gọi mặc định khi backend chưa trả gì (giữ đúng mặc định `SHOP_CONFIRM_CALL_HOURS` cũ). */
export const DEFAULT_CALL_HOURS = "7:00–20:00";

/**
 * MỘT nguồn khung giờ gọi cho mọi câu thông báo (SR-23 F10).
 * Ưu tiên `cskh_notice.working_hours` (= `settings.CSKH_WORKING_HOURS`, giờ thật CSKH làm việc);
 * chỉ khi khối CSKH tắt/vắng (backend cũ) mới dùng `confirm_call_hours` (`SHOP_CONFIRM_CALL_HOURS`).
 * Trước đây hai câu trên cùng một màn dùng hai nguồn nên có thể hiện hai khung giờ khác nhau.
 */
export function callHours(info: SiteInfoResponse | null | undefined): string {
  const policy = info?.cskh_notice;
  if (policy?.enabled && policy.working_hours) return policy.working_hours;
  return info?.confirm_call_hours || DEFAULT_CALL_HOURS;
}

/**
 * Khối "Lưu ý xác nhận đơn" dùng chung cho form đặt hàng (`variant="form"`) và màn thanh toán
 * (`variant="paid"`). Chỉ nhận dữ liệu đã tải (`info`), KHÔNG tự gọi API: người dùng component
 * truyền `site-info` đã có để cả màn chỉ tốn 1 request. Không có SĐT/địa chỉ ở đây (bất biến 9).
 */
export function ConfirmationPolicyNotice({
  info,
  variant,
}: {
  info: SiteInfoResponse | null | undefined;
  variant: "form" | "paid";
}) {
  const policy = info?.cskh_notice;
  if (!policy?.enabled) return null;

  return (
    <div className={s.box} data-testid="confirmation-policy-notice">
      <strong>Lưu ý xác nhận đơn:</strong>{" "}
      {variant === "paid" ? "Sau khi thanh toán, Cá Về" : "Cá Về"} sẽ gọi xác nhận trong khung giờ{" "}
      {callHours(info)} (tối đa {policy.max_attempts} lần trong {policy.window_minutes} phút).
      {policy.auto_cancel_enabled && (
        <span>
          {" "}
          Sau thời gian trên nếu không liên lạc được, đơn hàng có thể bị huỷ và hoàn đủ tiền trong vòng{" "}
          {policy.refund_deadline_days} ngày.
          {policy.hotline ? ` Hotline: ${policy.hotline}.` : ""}
        </span>
      )}
      {/* # CHỜ legal-vn */}
    </div>
  );
}

/** Câu "gọi số đuôi ####" (GL-04) — bọc riêng để `ConfirmCallNotice` dùng cùng kiểu dáng và cùng khung giờ. */
export function CallNoticeBox({
  last4,
  hours,
}: {
  last4: string;
  hours: string;
}) {
  return (
    <div className={s.callNotice} data-testid="confirm-call-notice">
      Cá Về sẽ gọi số đuôi <strong>{last4}</strong> trong khung {hours} để xác nhận trước khi giao.
    </div>
  );
}

export default ConfirmationPolicyNotice;
