"use client";

// Công tắc bật/tắt một việc của nhóm. Là nút `role="switch"` (bàn phím: Space/Enter; trình đọc màn hình: "bật/tắt").
// `mixed` = nhóm có một phần quyền của việc: hiện nửa chừng, bấm = bật đủ. Vùng bấm >= 44px (token --tap).
// Đang gửi (`busy`) thì khoá và báo aria-busy: ô chỉ đổi khi BE đã nhận, nên không bao giờ hiện quyền chưa lưu.

import s from "../permissions.module.css";

type Props = {
  state: "on" | "off" | "partial";
  /** Tên đọc của công tắc, vd "Xem đơn hàng — Quản lý". */
  label: string;
  busy?: boolean;
  disabled?: boolean;
  onToggle: () => void;
  /** Lý do khoá (hiện khi rê chuột). */
  title?: string;
};

export function PermSwitch({ state, label, busy = false, disabled = false, onToggle, title }: Props) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={state === "partial" ? "mixed" : state === "on"}
      aria-label={label}
      aria-busy={busy || undefined}
      data-busy={busy || undefined}
      className={s.switch}
      disabled={disabled || busy}
      title={title}
      onClick={onToggle}
    >
      <span className={s.track} aria-hidden="true">
        <span className={s.thumb} />
      </span>
    </button>
  );
}
