"use client";

import { useEffect, useState } from "react";
import { getSiteInfo } from "../api";
import type { SiteInfoResponse } from "../types";

export interface ConfirmCallNoticeProps {
  last4: string;
}

/**
 * GL-04: Thông báo "vựa sẽ gọi xác nhận" sau khi đặt.
 * - Chỉ hiện khi site-info có `confirm_call_notice === true`.
 * - Lấy khung giờ từ `confirm_call_hours` (mặc định "7:00–20:00").
 * - Chỉ nhận và render 4 số cuối SĐT (`last4`), tuyệt đối không render SĐT đầy đủ (bất biến 9).
 * - Lỗi site-info hoặc cờ tắt -> ẩn hoàn toàn, không chặn luồng (GL-04-AC4, GL-04-AC5).
 */
export function ConfirmCallNotice({ last4 }: ConfirmCallNoticeProps) {
  const [siteInfo, setSiteInfo] = useState<SiteInfoResponse | null>(null);

  useEffect(() => {
    let active = true;
    getSiteInfo()
      .then((info) => {
        if (active) setSiteInfo(info);
      })
      .catch(() => {
        // Lỗi site-info: không làm gì, an toàn ẩn component (GL-04-AC5)
      });
    return () => {
      active = false;
    };
  }, []);

  const cleanLast4 = (last4 || "").trim().slice(-4);
  if (!siteInfo?.confirm_call_notice || !cleanLast4 || cleanLast4.length !== 4) {
    return null;
  }

  const hours = siteInfo.confirm_call_hours || "7:00–20:00";

  return (
    <div
      className="confirm-call-notice"
      data-testid="confirm-call-notice"
      style={{
        background: "#eff6ff",
        border: "1px solid #bfdbfe",
        borderRadius: "6px",
        padding: "10px 14px",
        margin: "12px 0",
        fontSize: "0.875rem",
        color: "#1e40af",
        lineHeight: "1.45",
        textAlign: "left",
      }}
    >
      Cá Về sẽ gọi số đuôi <strong>{cleanLast4}</strong> trong khung {hours} để xác nhận trước khi giao.
    </div>
  );
}

export default ConfirmCallNotice;
