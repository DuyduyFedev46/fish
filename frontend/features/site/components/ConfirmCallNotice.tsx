"use client";

import { useEffect, useState } from "react";
import { getSiteInfo } from "../api";
import type { SiteInfoResponse } from "../types";
import { CallNoticeBox, callHours } from "./CskhNotice";

export interface ConfirmCallNoticeProps {
  last4: string;
  /**
   * `site-info` đã tải sẵn ở màn cha (màn thanh toán truyền xuống để cả màn chỉ gọi 1 lần).
   * `null` = cha tải xong nhưng lỗi/không có -> ẩn, KHÔNG gọi lại. Bỏ trống (`undefined`) = tự tải
   * (trang tra đơn, quay về từ cổng thanh toán).
   */
  info?: SiteInfoResponse | null;
}

/**
 * GL-04: Thông báo "vựa sẽ gọi xác nhận" sau khi đặt.
 * - Chỉ hiện khi site-info có `confirm_call_notice === true`.
 * - Khung giờ lấy từ `callHours()` (một nguồn với khối CSKH, SR-23 F10).
 * - Chỉ nhận và render 4 số cuối SĐT (`last4`), tuyệt đối không render SĐT đầy đủ (bất biến 9).
 * - Lỗi site-info hoặc cờ tắt -> ẩn hoàn toàn, không chặn luồng (GL-04-AC4, GL-04-AC5).
 */
export function ConfirmCallNotice({ last4, info }: ConfirmCallNoticeProps) {
  const [fetched, setFetched] = useState<SiteInfoResponse | null>(null);
  const selfFetch = info === undefined;

  useEffect(() => {
    if (!selfFetch) return;
    let active = true;
    getSiteInfo()
      .then((res) => {
        if (active) setFetched(res);
      })
      .catch(() => {
        // Lỗi site-info: không làm gì, an toàn ẩn component (GL-04-AC5)
      });
    return () => {
      active = false;
    };
  }, [selfFetch]);

  const siteInfo = selfFetch ? fetched : info;
  const cleanLast4 = (last4 || "").trim().slice(-4);
  if (!siteInfo?.confirm_call_notice || !cleanLast4 || cleanLast4.length !== 4) {
    return null;
  }

  return <CallNoticeBox last4={cleanLast4} hours={callHours(siteInfo)} />;
}

export default ConfirmCallNotice;
