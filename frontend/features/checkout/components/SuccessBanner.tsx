"use client";

import Icon from "@/components/ui/Icon";
import IconButton from "@/components/ui/IconButton";
import s from "./SuccessBanner.module.css";

export interface SuccessBannerProps {
  onDismiss: () => void;
  message?: string;
}

/**
 * Banner "Thanh toán thành công" trên đầu trang đơn (COMPONENTS #29). Chỉ hiện khi về từ cổng với `result=success` VÀ máy chủ
 * đã ghi nhận tiền (state ≠ chờ trả). `role="status"`, không lấy tiêu điểm.
 */
export default function SuccessBanner({ onDismiss, message = "Cá Về sẽ gọi xác nhận trước khi giao." }: SuccessBannerProps) {
  return (
    <div className={s.banner} role="status">
      <span className={s.circle} aria-hidden="true">
        <Icon name="check" size={20} strokeWidth={2.6} />
      </span>
      <span className={s.text}>
        <span className={s.title}>Thanh toán thành công</span>
        <span className={s.message}>{message}</span>
      </span>
      <IconButton
        label="Đóng thông báo thanh toán thành công"
        icon="close"
        iconSize={18}
        variant="ghost"
        onClick={onDismiss}
        className={s.close}
      />
    </div>
  );
}
