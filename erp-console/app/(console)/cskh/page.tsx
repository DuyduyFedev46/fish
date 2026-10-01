"use client";

import { useEffect } from "react";

/**
 * Đường dẫn cũ `/cskh/` (P8b Lô 3): giữ vĩnh viễn để dấu trang, liên kết trong thông báo và lịch sử trình duyệt
 * không gãy. Chuyển sang `/confirmation/`, giữ nguyên query (vd `?state=CALLBACK`) và hash.
 * Không có server nên chuyển ở phía trình duyệt; `replace` để nút Back không quay lại trang cũ.
 */
export default function LegacyConfirmationRedirect() {
  useEffect(() => {
    window.location.replace(`/confirmation/${window.location.search}${window.location.hash}`);
  }, []);
  return <p className="p-6 text-sm text-gray-500">Đang chuyển sang màn Gọi xác nhận…</p>;
}
