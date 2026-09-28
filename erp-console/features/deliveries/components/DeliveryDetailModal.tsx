"use client";

import React, { useState, useEffect } from "react";
import { fetchDeliveryNoteDetail, packDeliveryNote } from "../api";
import type { DeliveryNoteDetail, DeliveryNoteItem } from "../types";
import s from "../deliveries.module.css";

type Props = {
  item: DeliveryNoteItem;
  onClose: () => void;
  onUpdated: () => void;
};

export function DeliveryDetailModal({ item, onClose, onUpdated }: Props) {
  const [detail, setDetail] = useState<DeliveryNoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [packing, setPacking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    fetchDeliveryNoteDetail(item.id)
      .then((data) => {
        if (active) {
          setDetail(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err?.message || "Không thể tải chi tiết phiếu giao.");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [item.id]);

  const handlePack = async () => {
    if (!detail) return;
    setPacking(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const res = await packDeliveryNote(detail.id, detail.status);
      setDetail(res);
      if (res.already) {
        setSuccessMsg("Phiếu đã ở trạng thái Chờ lấy.");
      } else {
        setSuccessMsg("Đã đóng gói thành công. Phiếu chuyển sang Chờ lấy.");
      }
      onUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra.";
      setError(msg);
    } finally {
      setPacking(false);
    }
  };

  const current = detail || item;
  const canPack =
    current.status === "PREPARING" &&
    current.available_actions.includes("set_status:READY");

  return (
    <div className={s.modalBackdrop} onClick={onClose} role="dialog" aria-modal="true">
      <div className={s.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={s.modalHeader}>
          <h2 className={s.modalTitle}>
            <span>Phiếu giao {current.code}</span>
            <span
              className={`${s.badge} ${
                current.status === "CONFIRMING"
                  ? s.badgeConfirming
                  : current.status === "PREPARING"
                  ? s.badgePreparing
                  : current.status === "READY"
                  ? s.badgeReady
                  : current.status === "DELIVERING"
                  ? s.badgeDelivering
                  : current.status === "FAILED"
                  ? s.badgeFailed
                  : s.badgeCompleted
              }`}
            >
              {current.status_label}
            </span>
          </h2>
          <button type="button" className={s.closeBtn} onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </div>

        <div className={s.modalBody}>
          {error && <div className={`${s.alertBox} ${s.alertError}`}>{error}</div>}
          {successMsg && <div className={`${s.alertBox} ${s.alertSuccess}`}>{successMsg}</div>}

          <div className={s.infoSection}>
            <div>
              <div className={s.infoItemLabel}>Mã đơn hàng / Hoá đơn</div>
              <div className={s.infoItemValue}>
                {current.order?.code || "—"} · {current.invoice_code || "—"}
              </div>
            </div>
            <div>
              <div className={s.infoItemLabel}>Người nhận</div>
              <div className={s.infoItemValue}>
                {detail?.recipient_name || current.customer_name || "—"}
              </div>
            </div>
            <div>
              <div className={s.infoItemLabel}>Địa chỉ giao</div>
              <div className={s.infoItemValue}>{current.address || "—"}</div>
            </div>
            <div>
              <div className={s.infoItemLabel}>Tổng khối lượng</div>
              <div className={s.infoItemValue}>{current.total_kg} kg</div>
            </div>
            <div>
              <div className={s.infoItemLabel}>Tình trạng tem</div>
              <div className={s.infoItemValue}>
                {current.label.printed ? (
                  <span className={`${s.badge} ${s.badgeLabelPrinted}`}>
                    Đã in {current.label.valid_print_no ? `(lần ${current.label.valid_print_no})` : ""}
                  </span>
                ) : (
                  <span className={`${s.badge} ${s.badgeLabelUnprinted}`}>Chưa in tem</span>
                )}
              </div>
            </div>
            {current.note && (
              <div>
                <div className={s.infoItemLabel}>Ghi chú đơn</div>
                <div className={s.infoItemValue}>{current.note}</div>
              </div>
            )}
          </div>

          <div>
            <h3 className={s.linesTitle}>Dòng hàng soạn theo lô</h3>
            {loading ? (
              <div className={s.emptyState}>Đang tải chi tiết dòng hàng...</div>
            ) : detail?.lines && detail.lines.length > 0 ? (
              <div className={s.linesList}>
                {detail.lines.map((line, idx) => (
                  <div key={idx} className={s.lineItem}>
                    <div>
                      <div className={s.lineItemName}>{line.item_name}</div>
                      <div className={s.lineItemSub}>
                        Lô: {line.batch_id} · HSD: {line.expiry_date}
                      </div>
                    </div>
                    <div className={s.lineItemQty}>{line.qty_kg} kg</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={s.emptyState}>Không có thông tin dòng hàng</div>
            )}
          </div>
        </div>

        <div className={s.modalFooter}>
          <button type="button" className={s.btnSecondary} onClick={onClose}>
            Đóng
          </button>
          {canPack && (
            <button
              type="button"
              className={s.btnPrimary}
              onClick={handlePack}
              disabled={packing}
            >
              {packing ? "Đang xử lý..." : "Đã đóng gói"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
