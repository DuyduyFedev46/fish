"use client";

import { useEffect, useState } from "react";
import { pickHotline, zaloUrlOf } from "@/lib/phone";
import { getSiteInfo } from "@/features/site/api";

/** Hotline hợp lệ (ưu tiên số người bán) và link Zalo từ site-info; lỗi hoặc chưa có thì để trống, nút dẫn tới trang Liên hệ. */
export function useHotline(): { hotline?: string; zaloUrl?: string } {
  const [state, setState] = useState<{ hotline?: string; zaloUrl?: string }>({});
  useEffect(() => {
    let active = true;
    getSiteInfo()
      .then((info) => {
        if (!active) return;
        setState({
          hotline: pickHotline(info.seller?.phone, info.confirmation_policy?.hotline),
          zaloUrl: zaloUrlOf(info.seller?.zalo),
        });
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return state;
}
