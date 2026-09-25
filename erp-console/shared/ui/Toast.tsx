"use client";

// Thông báo nổi "đã xong" (UI4, lên shared/ui ở UI5): hiện ở đáy màn, tự ẩn sau vài giây, dừng đếm khi rê chuột / focus vào hoặc khi tab
// bị ẩn (người dùng chưa kịp đọc). Có nút đóng. Chỉ báo kết quả đã thấy được trên màn (danh sách đổi theo), không
// phải nơi duy nhất chứa thông tin quan trọng. Giữ lớp .alert-box.ok để e2e bám như trước.

import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";
import s from "./overlay.module.css";

type Props = {
  message: string;
  onClose: () => void;
  /** ms trước khi tự ẩn. */
  duration?: number;
};

export function Toast({ message, onClose, duration = 6000 }: Props) {
  const [hover, setHover] = useState(false);
  const [focus, setFocus] = useState(false);
  const [hidden, setHidden] = useState(false);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const onVis = () => setHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  const paused = hover || focus || hidden;
  useEffect(() => {
    if (paused) return;
    const t = setTimeout(() => closeRef.current(), duration);
    return () => clearTimeout(t);
  }, [paused, duration, message]);

  return (
    <div
      className={`alert-box ok ${s.toast}`}
      role="status"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
    >
      <Icon name="check_circle" />
      <span>{message}</span>
      <button type="button" className="iconbtn ghost" aria-label="Đóng thông báo" onClick={onClose}>
        <Icon name="close" />
      </button>
    </div>
  );
}
