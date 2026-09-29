"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Icon } from "@/shared/ui/Icon";
import { getDashboardAttention } from "../api";
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
      <div style={{ padding: "8px 12px", fontSize: "0.8125rem", color: "var(--ink-3, #6b7280)" }}>
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
          background: "#fef2f2",
          border: "1px solid #fecaca",
          color: "#991b1b",
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
  }> = [];

  if (typeof data.cskh_queue_waiting === "number" && data.cskh_queue_waiting > 0) {
    items.push({
      key: "cskh_queue_waiting",
      count: data.cskh_queue_waiting,
      label: "đơn chờ gọi xác nhận quá hạn",
      href: "/cskh/",
      crit: true,
    });
  }

  if (typeof data.cskh_escalated === "number" && data.cskh_escalated > 0) {
    items.push({
      key: "cskh_escalated",
      count: data.cskh_escalated,
      label: "đơn cần Quản lý quyết định",
      href: "/cskh/",
      crit: true,
    });
  }

  if (typeof data.cskh_auto_cancel_blocked === "number" && data.cskh_auto_cancel_blocked > 0) {
    items.push({
      key: "cskh_auto_cancel_blocked",
      count: data.cskh_auto_cancel_blocked,
      label: "đơn quá hạn bị hoãn tự huỷ",
      href: "/cskh/",
      crit: true,
    });
  }

  if (typeof data.refund_calls_open === "number" && data.refund_calls_open > 0) {
    items.push({
      key: "refund_calls_open",
      count: data.refund_calls_open,
      label: "cuộc gọi cần nhắc báo hoàn/huỷ",
      href: "/cskh/",
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
          color: "var(--ink-2, #4b5563)",
          fontSize: "0.8125rem",
        }}
      >
        <span style={{ color: "var(--good, #16a34a)", display: "inline-flex" }}>
          <Icon name="check_circle" />
        </span>
        <span>Không có việc gọi hoặc tem bị quá hạn.</span>
      </div>
    );
  }

  return (
    <ul className="alerts" style={{ borderTop: "none" }}>
      {items.map((it) => (
        <li key={it.key} className={`alert${it.crit ? " crit" : ""}`}>
          <Icon name={it.crit ? "error" : "schedule"} />
          <div className="tx" style={{ flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <b style={{ color: it.crit ? "#b91c1c" : "inherit" }}>
                {it.count} {it.label}
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
