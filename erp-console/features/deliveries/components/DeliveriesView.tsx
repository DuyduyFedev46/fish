"use client";

import React, { useState, useEffect, useCallback } from "react";
import { todayInVietnam } from "@/shared/lib/format";
import { fetchDeliveryNotes } from "../api";
import { DeliveryDetailModal } from "./DeliveryDetailModal";
import {
  DeliveryNoteItem,
  DeliveryStatusGroup,
  STATUS_GROUP_TABS,
} from "../types";
import s from "../deliveries.module.css";
import { PersonalText } from "@/shared/ui/PersonalText";
import { personalText } from "@/shared/lib/personalData";

export function DeliveriesView() {
  const [activeTab, setActiveTab] = useState<DeliveryStatusGroup>("PREPARING");
  const [notes, setNotes] = useState<DeliveryNoteItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<DeliveryNoteItem | null>(null);

  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);

    const params =
      activeTab === "COMPLETED"
        ? { status: "COMPLETED", completed_from: todayInVietnam() }
        : { status: activeTab };

    fetchDeliveryNotes(params)
      .then((res) => {
        setNotes(res.results || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message || "Không thể tải danh sách phiếu giao.");
        setLoading(false);
      });
  }, [activeTab]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const renderBadge = (status: string, label: string) => {
    let cls = s.badge;
    if (status === "CONFIRMING") cls += ` ${s.badgeConfirming}`;
    else if (status === "PREPARING") cls += ` ${s.badgePreparing}`;
    else if (status === "READY") cls += ` ${s.badgeReady}`;
    else if (status === "DELIVERING") cls += ` ${s.badgeDelivering}`;
    else if (status === "FAILED") cls += ` ${s.badgeFailed}`;
    else cls += ` ${s.badgeCompleted}`;

    return <span className={cls}>{label}</span>;
  };

  const renderLabelBadge = (item: DeliveryNoteItem) => {
    if (item.label.printed) {
      return (
        <span className={`${s.badge} ${s.badgeLabelPrinted}`}>
          Đã in {item.label.valid_print_no ? `(lần ${item.label.valid_print_no})` : ""}
        </span>
      );
    }
    return <span className={`${s.badge} ${s.badgeLabelUnprinted}`}>Chưa in tem</span>;
  };

  return (
    <div className={s.screen}>
      <div className={s.header}>
        <h1 className={s.title}>Giao hàng</h1>
        <p className={s.desc}>
          Bảng điều phối và theo dõi phiếu giao hàng theo trạng thái xử lý và đóng gói.
        </p>
      </div>

      <div className={s.tabs} role="tablist">
        {STATUS_GROUP_TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`${s.tab} ${isActive ? s.tabActive : ""}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <span>{tab.label}</span>
              {isActive && notes.length > 0 && (
                <span className={s.tabCount}>{notes.length}</span>
              )}
            </button>
          );
        })}
      </div>

      {error && <div className={`${s.alertBox} ${s.alertError}`}>{error}</div>}

      {loading ? (
        <div className={s.emptyState}>Đang tải danh sách phiếu giao...</div>
      ) : notes.length === 0 ? (
        <div className={s.emptyState}>Không có phiếu giao nào trong mục này.</div>
      ) : (
        <>
          {/* Bảng máy tính / Tablet */}
          <div className={s.tableWrapper}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th>Mã phiếu</th>
                  <th>Đơn / Hoá đơn</th>
                  <th>Người nhận & Địa chỉ</th>
                  <th>Tóm tắt hàng</th>
                  <th>Tổng kg</th>
                  <th>Tem</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {notes.map((item) => (
                  <tr
                    key={item.id}
                    className={s.rowClickable}
                    onClick={() => setSelectedNote(item)}
                  >
                    <td>
                      <div className={s.codeCell}>{item.code}</div>
                    </td>
                    <td>
                      <div>{item.order?.code || "—"}</div>
                      <div className={s.subCode}>{item.invoice_code || "—"}</div>
                    </td>
                    <td>
                      <div className={s.customerName}>
                        <PersonalText value={item.customer_name} whenEmpty="" />
                      </div>
                      {/* Cả tên và địa chỉ đã ẩn → chỉ hiện một dòng "Đã ẩn", khỏi lặp. */}
                      {!(item.customer_name === null && item.address === null) && (
                        <div className={s.customerAddress} title={personalText(item.address, "")}>
                          <PersonalText value={item.address} whenEmpty="" />
                        </div>
                      )}
                    </td>
                    <td>
                      <div className={s.linesSummary}>{item.lines_summary || "—"}</div>
                    </td>
                    <td>
                      <span className={s.totalKg}>{item.total_kg} kg</span>
                    </td>
                    <td>{renderLabelBadge(item)}</td>
                    <td>{renderBadge(item.status, item.status_label)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Dạng thẻ cho điện thoại (360x640) */}
          <div className={s.cardsContainer}>
            {notes.map((item) => (
              <div
                key={item.id}
                className={s.cardItem}
                onClick={() => setSelectedNote(item)}
              >
                <div className={s.cardTop}>
                  <div className={s.cardCodes}>
                    <div className={s.codeCell}>{item.code}</div>
                    <div className={s.subCode}>
                      Đơn: {item.order?.code || "—"} · HĐ: {item.invoice_code || "—"}
                    </div>
                  </div>
                  <div>{renderBadge(item.status, item.status_label)}</div>
                </div>

                <div className={s.cardMid}>
                  <div className={s.customerName}>
                    <PersonalText value={item.customer_name} whenEmpty="" />
                  </div>
                  {!(item.customer_name === null && item.address === null) && (
                    <div className={s.customerAddress}>
                      <PersonalText value={item.address} whenEmpty="" />
                    </div>
                  )}
                  <div className={s.linesSummary} style={{ marginTop: 4 }}>
                    {item.lines_summary}
                  </div>
                </div>

                <div className={s.cardBottom}>
                  <div>{renderLabelBadge(item)}</div>
                  <div>
                    <span className={s.totalKg}>{item.total_kg} kg</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {selectedNote && (
        <DeliveryDetailModal
          item={selectedNote}
          onClose={() => setSelectedNote(null)}
          onUpdated={() => {
            loadData();
          }}
        />
      )}
    </div>
  );
}
