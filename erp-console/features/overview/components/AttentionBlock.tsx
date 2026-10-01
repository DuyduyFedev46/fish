"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { getDashboardAttention, readConfirmationCounts } from "../api";
import type { DashboardAttentionData } from "../types";

export function AttentionBlock() {
  const [data, setData] = useState<DashboardAttentionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    getDashboardAttention()
      .then((res) => {
        if (active) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          // CS-15-AC6: Lỗi riêng khối, hiển thị "Chưa tải được", phần còn lại vẫn hiện
          setError("Chưa tải được");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "8px 12px", fontSize: "0.8125rem", color: "var(--ink-3)" }}>
        Đang kiểm tra đầu việc…
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "10px 14px",
          borderRadius: "6px",
          background: "var(--crit-soft)",
          border: "1px solid var(--crit)",
          color: "var(--crit)",
          fontSize: "0.8125rem",
          margin: "8px 0",
        }}
        role="alert"
      >
        <Icon name="error" />
        <span>Chưa tải được thông tin việc cần chú ý.</span>
      </div>
    );
  }

  if (!data) return null;

  const items: Array<{
    key: string;
    count: number;
    label: string;
    href: string;
    crit: boolean;
    /** Ghi đè cả dòng chữ (mặc định "{count} {label}"). */
    text?: string;
  }> = [];

  // P8 Lô 5 (BR-LO-07): lô Quá hạn còn tồn — chỉ Chủ có khoá này. Bấm → danh sách lô lọc theo Quá hạn.
  if (typeof data.expired_batches_open === "number" && data.expired_batches_open > 0) {
    items.push({
      key: "expired_batches_open",
      count: data.expired_batches_open,
      label: "lô quá hạn còn tồn",
      text: `Lô quá hạn còn tồn: ${data.expired_batches_open}`,
      href: "/inventory/?status=EXPIRED",
      crit: true,
    });
  }

  const { queueWaiting, escalated, autoCancelBlocked } = readConfirmationCounts(data);

  if (typeof queueWaiting === "number" && queueWaiting > 0) {
    items.push({
      key: "confirmation_queue_waiting",
      count: queueWaiting,
      label: "đơn chờ gọi xác nhận quá hạn",
      href: "/confirmation/",
      crit: true,
    });
  }

  if (typeof escalated === "number" && escalated > 0) {
    items.push({
      key: "confirmation_escalated",
      count: escalated,
      label: "đơn cần Quản lý quyết định",
      href: "/confirmation/",
      crit: true,
    });
  }

  if (typeof autoCancelBlocked === "number" && autoCancelBlocked > 0) {
    items.push({
      key: "confirmation_auto_cancel_blocked",
      count: autoCancelBlocked,
      label: "đơn quá hạn bị hoãn tự huỷ",
      href: "/confirmation/",
      crit: true,
    });
  }

  if (typeof data.refund_calls_open === "number" && data.refund_calls_open > 0) {
    items.push({
      key: "refund_calls_open",
      count: data.refund_calls_open,
      label: "cuộc gọi cần nhắc báo hoàn/huỷ",
      href: "/confirmation/",
      crit: false,
    });
  }

  if (typeof data.labels_not_printed === "number" && data.labels_not_printed > 0) {
    items.push({
      key: "labels_not_printed",
      count: data.labels_not_printed,
      label: "phiếu soạn chưa in tem quá hạn",
      href: "/deliveries/",
      crit: false,
    });
  }

  if (typeof data.labels_to_void === "number" && data.labels_to_void > 0) {
    items.push({
      key: "labels_to_void",
      count: data.labels_to_void,
      label: "tem giấy cần huỷ (xé)",
      href: "/deliveries/",
      crit: true,
    });
  }

  if (items.length === 0) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 12px",
          color: "var(--ink-2)",
          fontSize: "0.8125rem",
        }}
      >
        <span style={{ color: "var(--good)", display: "inline-flex" }}>
          <Icon name="check_circle" />
        </span>
        <span>Không có việc gọi hoặc tem bị quá hạn.</span>
      </div>
    );
  }

  return (
    <ul className="alerts" style={{ borderTop: "none" }}>
      {items.map((it) => (
        <li key={it.key} className={`alert${it.crit ? " crit" : ""}`} data-attention={it.key}>
          <Icon name={it.crit ? "error" : "schedule"} />
          <div className="tx" style={{ flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <b style={{ color: it.crit ? "var(--crit)" : "inherit" }}>
                {it.text ?? `${it.count} ${it.label}`}
              </b>
            </div>
            <Link
              href={it.href}
              className="link"
              style={{ fontSize: "0.8125rem", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "2px" }}
            >
              Xử lý <span style={{ fontSize: "14px", display: "inline-flex" }}><Icon name="arrow_forward" /></span>
            </Link>
          </div>
        </li>
      ))}
    </ul>
  );
}
