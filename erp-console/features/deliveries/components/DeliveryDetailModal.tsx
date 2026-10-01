"use client";

import React, { useState, useEffect } from "react";
import { dateOnly } from "@/shared/lib/format";
import { fetchDeliveryNoteDetail, packDeliveryNote, printDeliveryLabel, voidDeliveryLabel } from "../api";
import type { DeliveryNoteDetail, DeliveryNoteItem } from "../types";
import s from "../deliveries.module.css";
import { PersonalText } from "@/shared/ui/PersonalText";

type Props = {
  item: DeliveryNoteItem;
  onClose: () => void;
  onUpdated: () => void;
};

export function DeliveryDetailModal({ item, onClose, onUpdated }: Props) {
  const [detail, setDetail] = useState<DeliveryNoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [packing, setPacking] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [voidingNo, setVoidingNo] = useState<number | null>(null);
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

  const handleVoidLabel = async (printNo: number) => {
    setVoidingNo(printNo);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await voidDeliveryLabel(current.id, printNo);
      if (res.already) {
        setSuccessMsg(`Tem lần ${printNo} đã được xác nhận huỷ trước đó.`);
      } else {
        setSuccessMsg(`Đã xác nhận huỷ tem giấy lần ${printNo}.`);
      }
      if (detail) {
        const updatedToVoid = (detail.label?.to_void || []).filter((p) => p !== printNo);
        setDetail({
          ...detail,
          label: {
            ...detail.label,
            to_void: updatedToVoid,
            needs_void: updatedToVoid.length,
          },
        });
      }
      onUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể huỷ tem.";
      setError(msg);
    } finally {
      setVoidingNo(null);
    }
  };

  const current = detail || item;
  const canPack =
    current.status === "PREPARING" &&
    current.available_actions.includes("set_status:READY");
  const canPrint =
    (current.status === "PREPARING" || current.status === "READY") &&
    (current.available_actions.includes("print_label") ||
      current.available_actions.includes("reprint_label"));

  const handlePrint = async () => {
    if (!current) return;
    setPrinting(true);
    setError(null);
    try {
      const res = await printDeliveryLabel(current.id);
      window.open(`/print/label/?note=${current.id}&print_no=${res.print_no}`, "_blank");
      if (detail) {
        const oldPrintNo = detail.label.valid_print_no;
        const toVoidList = [...(detail.label.to_void || [])];
        if (detail.label.printed && oldPrintNo && !toVoidList.includes(oldPrintNo)) {
          toVoidList.push(oldPrintNo);
        }
        setDetail({
          ...detail,
          label: {
            ...detail.label,
            printed: true,
            valid_print_no: res.print_no,
            to_void: toVoidList,
            needs_void: toVoidList.length,
          },
          available_actions: detail.available_actions.includes("reprint_label")
            ? detail.available_actions
            : [...detail.available_actions.filter((a) => a !== "print_label"), "reprint_label"],
        });
      }
      onUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể in tem.";
      setError(msg);
    } finally {
      setPrinting(false);
    }
  };

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

          {/* Cảnh báo tem cần huỷ theo CS-14 */}
          {current.label?.to_void && current.label.to_void.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {current.label.to_void.map((pNo) => (
                <div
                  key={pNo}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "6px",
                    fontSize: "0.875rem",
                    background: current.status === "CANCELLED" ? "#fef2f2" : "#fffbeb",
                    border: `1px solid ${current.status === "CANCELLED" ? "#fecaca" : "#fde68a"}`,
                    color: current.status === "CANCELLED" ? "#991b1b" : "#92400e",
                  }}
                >
                  <div style={{ fontWeight: 500 }}>
                    {current.status === "CANCELLED"
                      ? `🚨 Đơn đã huỷ – xé tem lần ${pNo}`
                      : `⚠️ Tem cũ lần ${pNo} hết hiệu lực – in tem mới, huỷ tem cũ`}
                  </div>
                  <button
                    type="button"
                    className={s.btnSecondary}
                    onClick={() => handleVoidLabel(pNo)}
                    disabled={voidingNo === pNo}
                    style={{
                      fontSize: "0.8125rem",
                      padding: "4px 10px",
                      background: "#ffffff",
                      borderColor: current.status === "CANCELLED" ? "#fca5a5" : "#fcd34d",
                      color: current.status === "CANCELLED" ? "#991b1b" : "#92400e",
                      fontWeight: 600,
                      cursor: voidingNo === pNo ? "not-allowed" : "pointer",
                    }}
                  >
                    {voidingNo === pNo ? "Đang xử lý..." : "Đã huỷ tem"}
                  </button>
                </div>
              ))}
            </div>
          )}

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
                {current.customer_name === null ? (
                  <PersonalText value={null} />
                ) : (
                  detail?.recipient_name || current.customer_name || "—"
                )}
              </div>
            </div>
            <div>
              <div className={s.infoItemLabel}>Địa chỉ giao</div>
              <div className={s.infoItemValue}>
                <PersonalText value={current.address} />
              </div>
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
            {(current.note || current.note === null) && (
              <div>
                <div className={s.infoItemLabel}>Ghi chú đơn</div>
                <div className={s.infoItemValue}>
                  <PersonalText value={current.note} />
                </div>
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
                        Lô: {line.batch_id} · HSD: {dateOnly(line.expiry_date)}
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
          {canPrint && (
            <button
              type="button"
              className={s.btnSecondary}
              onClick={handlePrint}
              disabled={printing}
            >
              {printing
                ? "Đang xử lý..."
                : current.label.printed
                ? "In lại tem"
                : "In tem"}
            </button>
          )}
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
