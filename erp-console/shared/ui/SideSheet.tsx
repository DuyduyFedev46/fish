"use client";

// Tấm bên / tấm trượt đáy dùng chung (UI4, lên shared/ui ở UI5). Bọc shared/ui/Sheet (giữ nguyên focus trap,
// Esc, bấm nền, `busy` chặn đóng), chỉ đổi cách hiện: điện thoại trượt từ đáy, ≥768px là tấm bên phải cao hết màn.
// Đóng có chuyển động ra (180ms) rồi mới gỡ khỏi DOM; máy bật "giảm chuyển động" thì đóng ngay.
// `children` có thể là hàm nhận `close()` để nội dung tự đóng tấm (vd lưu xong) mà vẫn có chuyển động ra.

import { useCallback, useEffect, useRef, useState } from "react";
import { Sheet } from "./Sheet";
import s from "./overlay.module.css";

/** Khớp --dur-base (180ms) trong tokens.css — thời lượng chuyển động ra. */
const EXIT_MS = 180;

type Props = {
  title: string;
  onClose: () => void;
  busy?: boolean;
  children: React.ReactNode | ((close: () => void) => React.ReactNode);
};

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function SideSheet({ title, onClose, busy = false, children }: Props) {
  const [closing, setClosing] = useState(false);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const close = useCallback(() => {
    if (timer.current) return; // đang đóng
    if (reducedMotion()) {
      closeRef.current();
      return;
    }
    setClosing(true);
    timer.current = setTimeout(() => closeRef.current(), EXIT_MS);
  }, []);

  return (
    <div className={s.side} data-closing={closing || undefined}>
      <Sheet title={title} onClose={close} busy={busy}>
        {typeof children === "function" ? children(close) : children}
      </Sheet>
    </div>
  );
}
