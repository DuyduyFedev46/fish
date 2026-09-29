"use client";

import React, { useState, useEffect, useId } from "react";
import { useRouter } from "next/navigation";
import {
  claimCskhTask,
  fetchCskhDetail,
  recordCskhCall,
  unconfirmDelivery,
  changeRecipient,
  decideCskh,
} from "./api";
import type {
  CallResult,
  CskhDecision,
  CskhQueueDetail,
  CskhQueueItem,
  RecordCallPayload,
} from "./types";
import { CALL_RESULT_OPTIONS } from "./types";
import s from "./cskh.module.css";

type Props = {
  noteId: number;
  initialItem?: CskhQueueItem;
  onClose: () => void;
  onUpdated: () => void;
};

export function CskhCallModal({ noteId, initialItem, onClose, onUpdated }: Props) {
  const router = useRouter();
  const [detail, setDetail] = useState<CskhQueueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockWarning, setLockWarning] = useState<string | null>(null);
  const [isLockedByOther, setIsLockedByOther] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Form states
  const [selectedResult, setSelectedResult] = useState<CallResult | null>(null);
  const [callNote, setCallNote] = useState("");
  const [callbackTime, setCallbackTime] = useState("");

  // Manager Decision state (for ESCALATED)
  const [decisionType, setDecisionType] = useState<CskhDecision>("DELIVER_WITHOUT_CONFIRM");
  const [deliverReason, setDeliverReason] = useState("");
  const [extendUntil, setExtendUntil] = useState("");
  const [extendReason, setExtendReason] = useState("");
  const [cancelReasonCode, setCancelReasonCode] = useState<"UNREACHABLE" | "CUSTOMER_CHANGED_MIND" | "OTHER">("UNREACHABLE");
  const [cancelNote, setCancelNote] = useState("");

  // Subform toggles
  const [showChangeRecipient, setShowChangeRecipient] = useState(false);
  const [recipientName, setRecipientName] = useState("");
  const [recipientPhone, setRecipientPhone] = useState("");
  const [deliveryAddress, setDeliveryAddress] = useState("");

  const [showUnconfirm, setShowUnconfirm] = useState(false);
  const [unconfirmReason, setUnconfirmReason] = useState("");

  // Generate request_id once per modal session
  const [requestId] = useState(() => {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return `req-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
  });

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    // First, attempt to claim soft lock
    claimCskhTask(noteId)
      .then((res) => {
        if (!active) return;
        setLockWarning(null);
        setIsLockedByOther(false);
      })
      .catch((err) => {
        if (!active) return;
        if (err?.code === "CLAIMED") {
          setLockWarning(err.message || "Đơn đang được nhân viên khác xử lý.");
          setIsLockedByOther(true);
        }
      });

    // Then load detail
    fetchCskhDetail(noteId)
      .then((data) => {
        if (active) {
          setDetail(data);
          setRecipientName(data.recipient_name || "");
          setRecipientPhone(data.recipient_phone || "");
          setDeliveryAddress(data.address || "");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err?.message || "Không thể tải chi tiết phiếu CSKH.");
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [noteId]);

  // BR-GH-19 Validation: no >= 9 digits in note
  const cleanDigits = callNote.replace(/[\s.\-]/g, "");
  const hasForbiddenPii = /\d{9,}/.test(cleanDigits);

  const handleRecordCall = async (result: CallResult) => {
    if (isLockedByOther) return;
    if (hasForbiddenPii) {
      setError("BR-GH-19: Không được ghi SĐT hoặc số tài khoản vào ghi chú.");
      return;
    }

    if (result === "CALLBACK" && !callbackTime) {
      setSelectedResult("CALLBACK");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload: RecordCallPayload = {
        result,
        note: callNote.trim(),
        callback_at: result === "CALLBACK" ? new Date(callbackTime).toISOString() : null,
        request_id: requestId,
      };

      await recordCskhCall(noteId, payload);
      onUpdated();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra.";
      setError(msg);
      setSubmitting(false);
    }
  };

  const handleChangeRecipientSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const res = await changeRecipient(noteId, {
        recipient_name: recipientName.trim(),
        recipient_phone: recipientPhone.trim(),
        delivery_address: deliveryAddress.trim(),
      });
      setShowChangeRecipient(false);
      if (res.label_invalidated) {
        setNotice("Tem cũ đã hết hiệu lực – cần in lại tem mới và huỷ tem cũ.");
      }
      // Reload detail
      const refreshed = await fetchCskhDetail(noteId);
      setDetail(refreshed);
      onUpdated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể đổi người nhận.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleUnconfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!unconfirmReason.trim()) {
      setError("Vui lòng nhập lý do huỷ xác nhận.");
      return;
    }
    setSubmitting(true);
    setError(null);

    try {
      await unconfirmDelivery(noteId, { reason: unconfirmReason.trim() });
      setShowUnconfirm(false);
      onUpdated();
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể huỷ xác nhận.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleManagerDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      if (decisionType === "DELIVER_WITHOUT_CONFIRM") {
        if (!deliverReason.trim()) {
          setError("Vui lòng nhập lý do giao không xác nhận.");
          setSubmitting(false);
          return;
        }
        await decideCskh(noteId, {
          decision: "DELIVER_WITHOUT_CONFIRM",
          reason: deliverReason.trim(),
        });
        onUpdated();
        onClose();
      } else if (decisionType === "EXTEND") {
        if (!extendUntil) {
          setError("Vui lòng chọn thời gian gia hạn.");
          setSubmitting(false);
          return;
        }
        if (!extendReason.trim()) {
          setError("Vui lòng nhập lý do gia hạn.");
          setSubmitting(false);
          return;
        }
        await decideCskh(noteId, {
          decision: "EXTEND",
          until: new Date(extendUntil).toISOString(),
          reason: extendReason.trim(),
        });
        onUpdated();
        onClose();
      } else if (decisionType === "CANCEL") {
        const res = await decideCskh(noteId, {
          decision: "CANCEL",
          reason_code: cancelReasonCode,
          note: cancelNote.trim(),
        });
        onUpdated();
        onClose();
        if (res.order_id) {
          router.push(`/orders/?order=${res.order_id}&open=refund`);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể thực hiện quyết định Quản lý.";
      setError(msg);
      setSubmitting(false);
    }
  };

  const item = detail || initialItem;

  return (
    <div className={s.modalBackdrop} onClick={onClose} role="dialog" aria-modal="true">
      <div className={s.modalContent} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={s.modalHeader}>
          <h2 className={s.modalTitle}>
            <span>Gọi xác nhận đơn</span>
            {item && (
              <span style={{ fontFamily: "var(--font-mono, monospace)", color: "#2563eb" }}>
                {item.order_code}
              </span>
            )}
          </h2>
          <button type="button" className={s.closeBtn} onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </div>

        {/* Body */}
        <div className={s.modalBody}>
          {lockWarning && (
            <div className={`${s.alertBox} ${s.alertWarn}`}>
              ⚠️ {lockWarning}
            </div>
          )}

          {notice && (
            <div className={`${s.alertBox} ${s.alertWarn}`} style={{ background: "#fffbeb", borderColor: "#fde68a", color: "#92400e" }}>
              ⚠️ {notice}
            </div>
          )}

          {error && (
            <div className={`${s.alertBox} ${s.alertError}`}>
              {error}
            </div>
          )}

          {loading ? (
            <div className={s.emptyState}>Đang tải chi tiết cuộc gọi...</div>
          ) : !item ? (
            <div className={s.emptyState}>Không tìm thấy thông tin đơn.</div>
          ) : (
            <>
              {/* Customer Hero Block with tel: link */}
              <div className={s.customerHero}>
                <div className={s.heroLeft}>
                  <div className={s.heroName}>
                    {item.recipient_name ? (
                      <span>
                        {item.recipient_name}{" "}
                        <span style={{ fontSize: "0.8125rem", color: "#64748b" }}>
                          (Người nhận hộ)
                        </span>
                      </span>
                    ) : (
                      item.customer_name
                    )}
                  </div>
                  <div className={s.heroAddress}>{item.address}</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>
                    {item.lines_summary} · <strong>{item.total_kg} kg</strong>
                  </div>
                </div>

                {/* CS-05-AC8: Phone is clickable tel: link with touch target >= 44px */}
                <a
                  href={`tel:${item.recipient_phone || item.phone}`}
                  className={s.callNowBtn}
                >
                  <span style={{ fontSize: "1.25rem" }}>📞</span>
                  <span>{item.recipient_phone || item.phone}</span>
                </a>
              </div>

              {/* Action buttons: Change Recipient & Unconfirm */}
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className={s.btnSecondary}
                  onClick={() => setShowChangeRecipient(!showChangeRecipient)}
                >
                  {showChangeRecipient ? "Đóng đổi người nhận" : "Đổi người nhận / địa chỉ"}
                </button>
                {item.note_status === "PREPARING" && (
                  <button
                    type="button"
                    className={s.btnSecondary}
                    onClick={() => setShowUnconfirm(!showUnconfirm)}
                  >
                    {showUnconfirm ? "Đóng huỷ xác nhận" : "Huỷ xác nhận đơn"}
                  </button>
                )}
              </div>

              {/* Form Change Recipient (CS-12) */}
              {showChangeRecipient && (
                <form onSubmit={handleChangeRecipientSubmit} className={s.subformSection}>
                  <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                    Cập nhật thông tin nhận hàng
                  </div>
                  <div>
                    <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                      Tên người nhận hộ (để trống nếu là khách đặt)
                    </label>
                    <input
                      type="text"
                      className={s.searchInput}
                      value={recipientName}
                      onChange={(e) => setRecipientName(e.target.value)}
                      placeholder="VD: Anh Minh (nhận hộ)"
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                      SĐT người nhận hộ
                    </label>
                    <input
                      type="tel"
                      className={s.searchInput}
                      value={recipientPhone}
                      onChange={(e) => setRecipientPhone(e.target.value)}
                      placeholder="VD: 0900000456"
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                      Địa chỉ giao mới
                    </label>
                    <input
                      type="text"
                      className={s.searchInput}
                      value={deliveryAddress}
                      onChange={(e) => setDeliveryAddress(e.target.value)}
                      placeholder="Số nhà, đường, phường/xã..."
                      required
                    />
                  </div>
                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className={s.btnSecondary}
                      onClick={() => setShowChangeRecipient(false)}
                    >
                      Huỷ
                    </button>
                    <button
                      type="submit"
                      className={s.btnPrimary}
                      disabled={submitting}
                    >
                      {submitting ? "Đang lưu..." : "Lưu thay đổi"}
                    </button>
                  </div>
                </form>
              )}

              {/* Form Unconfirm */}
              {showUnconfirm && (
                <form onSubmit={handleUnconfirmSubmit} className={s.subformSection}>
                  <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                    Huỷ xác nhận để đưa phiếu về Chờ xác nhận
                  </div>
                  <div>
                    <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                      Lý do huỷ xác nhận
                    </label>
                    <input
                      type="text"
                      className={s.searchInput}
                      value={unconfirmReason}
                      onChange={(e) => setUnconfirmReason(e.target.value)}
                      placeholder="VD: Bấm nhầm đơn, khách đổi giờ hẹn..."
                      required
                    />
                  </div>
                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className={s.btnSecondary}
                      onClick={() => setShowUnconfirm(false)}
                    >
                      Huỷ
                    </button>
                    <button
                      type="submit"
                      className={s.btnDanger}
                      disabled={submitting}
                    >
                      {submitting ? "Đang huỷ..." : "Xác nhận huỷ"}
                    </button>
                  </div>
                </form>
              )}

              {/* CS-09: Guidance D5 & Refund Info for REFUND_CALL */}
              {item.confirm_state === "REFUND_CALL" && (
                <>
                  <div className={`${s.alertBox} ${s.alertWarn}`}>
                    💡 <strong>Hướng dẫn CSKH:</strong> {item.guidance || "Không ghi số tài khoản khách vào hệ thống. Chủ sẽ lấy số tài khoản trực tiếp từ khách khi chuyển khoản."}
                  </div>

                  {item.refund && (
                    <div className={s.subformSection} style={{ background: "#fefce8", borderColor: "#fef08a" }}>
                      <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "#854d0e" }}>
                        Thông tin hoàn tiền cho khách
                      </div>
                      <div style={{ fontSize: "0.9375rem", color: "#1f2937" }}>
                        Số tiền cần hoàn: <strong style={{ color: "#dc2626" }}>{Number(item.refund.amount).toLocaleString("vi-VN")} đ</strong>
                      </div>
                      <div style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                        Trạng thái: <strong>{item.refund.status_label || (item.refund.status === "PENDING" ? "Chờ Chủ chuyển" : "Đã hoàn")}</strong>
                        {item.refund.deadline && <span> · Hạn hoàn: {item.refund.deadline}</span>}
                        {item.cancelled_at && <span> · Huỷ lúc: {item.cancelled_at.slice(11, 16)}</span>}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* CS-07: Manager Decision Block for ESCALATED */}
              {item.confirm_state === "ESCALATED" && (
                <div className={s.subformSection} style={{ background: "#fff1f2", borderColor: "#fecdd3" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ fontWeight: 700, fontSize: "0.9375rem", color: "#9f1239" }}>
                      🚨 Cần Quản lý quyết định xử lý
                    </div>
                    {item.decide_deadline && (
                      <span style={{ fontSize: "0.75rem", color: "#be123c", fontWeight: 600 }}>
                        Hạn quyết định: {item.decide_deadline.slice(11, 16)}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "#4c0519", lineHeight: "1.4" }}>
                    {item.escalation_reason === "WANT_CHANGE" ? (
                      <span>💡 <strong>Khách muốn đổi món:</strong> Quản lý huỷ đơn và tạo phiếu hoàn tiền. Mời khách đặt đơn mới trên Shop sau khi đơn cũ được huỷ.</span>
                    ) : item.escalation_reason === "WANT_CANCEL" ? (
                      <span>💡 <strong>Khách muốn huỷ đơn:</strong> Quản lý huỷ đơn và lập phiếu hoàn tiền cho khách.</span>
                    ) : (
                      <span>Đơn hàng đã gọi {item.attempts} lần không liên lạc được hoặc thông tin liên lạc sai.</span>
                    )}
                  </div>

                  {/* Decision Selector */}
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "4px" }}>
                    <button
                      type="button"
                      className={`${s.btnSecondary} ${decisionType === "DELIVER_WITHOUT_CONFIRM" ? s.tabActive : ""}`}
                      onClick={() => setDecisionType("DELIVER_WITHOUT_CONFIRM")}
                      style={{ fontSize: "0.8125rem", padding: "6px 12px", minHeight: "36px" }}
                    >
                      Giao không xác nhận
                    </button>
                    <button
                      type="button"
                      className={`${s.btnSecondary} ${decisionType === "EXTEND" ? s.tabActive : ""}`}
                      onClick={() => setDecisionType("EXTEND")}
                      style={{ fontSize: "0.8125rem", padding: "6px 12px", minHeight: "36px" }}
                    >
                      Gia hạn thêm
                    </button>
                    <button
                      type="button"
                      className={`${s.btnSecondary} ${decisionType === "CANCEL" ? s.tabActive : ""}`}
                      onClick={() => setDecisionType("CANCEL")}
                      style={{ fontSize: "0.8125rem", padding: "6px 12px", minHeight: "36px", color: "#dc2626" }}
                    >
                      Huỷ đơn
                    </button>
                  </div>

                  {/* Form for chosen decision */}
                  <form onSubmit={handleManagerDecisionSubmit} style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "6px" }}>
                    {decisionType === "DELIVER_WITHOUT_CONFIRM" && (
                      <div>
                        <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                          Lý do giao không xác nhận (bắt buộc):
                        </label>
                        <input
                          type="text"
                          className={s.searchInput}
                          value={deliverReason}
                          onChange={(e) => setDeliverReason(e.target.value)}
                          placeholder="VD: Khách quen, địa chỉ đã giao nhiều lần..."
                          required
                        />
                      </div>
                    )}

                    {decisionType === "EXTEND" && (
                      <>
                        <div>
                          <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                            Gia hạn gọi lại tới (tối đa 24 giờ):
                          </label>
                          <input
                            type="datetime-local"
                            className={s.searchInput}
                            value={extendUntil}
                            onChange={(e) => setExtendUntil(e.target.value)}
                            required
                          />
                        </div>
                        <div>
                          <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                            Lý do gia hạn:
                          </label>
                          <input
                            type="text"
                            className={s.searchInput}
                            value={extendReason}
                            onChange={(e) => setExtendReason(e.target.value)}
                            placeholder="VD: Khách nhắn đang họp, gia hạn đến chiều..."
                            required
                          />
                        </div>
                      </>
                    )}

                    {decisionType === "CANCEL" && (
                      <>
                        <div>
                          <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                            Lý do huỷ đơn:
                          </label>
                          <select
                            className={s.searchInput}
                            value={cancelReasonCode}
                            onChange={(e) => setCancelReasonCode(e.target.value as any)}
                          >
                            <option value="UNREACHABLE">Không liên lạc được khách</option>
                            <option value="CUSTOMER_CHANGED_MIND">Khách đổi ý muốn huỷ</option>
                            <option value="OTHER">Lý do khác</option>
                          </select>
                        </div>
                        <div>
                          <label style={{ fontSize: "0.8125rem", color: "#4b5563" }}>
                            Ghi chú thêm:
                          </label>
                          <input
                            type="text"
                            className={s.searchInput}
                            value={cancelNote}
                            onChange={(e) => setCancelNote(e.target.value)}
                            placeholder="Chi tiết bổ sung (không bắt buộc)..."
                          />
                        </div>
                      </>
                    )}

                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
                      <button
                        type="submit"
                        className={decisionType === "CANCEL" ? s.btnDanger : s.btnPrimary}
                        disabled={submitting}
                      >
                        {submitting
                          ? "Đang lưu..."
                          : decisionType === "CANCEL"
                          ? "Huỷ đơn và lập phiếu hoàn"
                          : decisionType === "EXTEND"
                          ? "Lưu gia hạn"
                          : "Xác nhận chuyển soạn hàng"}
                      </button>
                    </div>
                  </form>
                </div>
              )}

              {/* Call History */}
              <div>
                <div className={s.sectionTitle}>
                  Lịch sử cuộc gọi ({detail?.calls?.length || 0})
                </div>
                {detail?.calls && detail.calls.length > 0 ? (
                  <div className={s.callsHistory}>
                    {detail.calls.map((call) => (
                      <div key={call.id} className={s.callRecord}>
                        <div>
                          <strong>{call.result_label}</strong>
                          {call.note && (
                            <span style={{ marginLeft: "8px", color: "#374151" }}>
                              — {call.note}
                            </span>
                          )}
                        </div>
                        <div className={s.callMeta}>
                          {call.by.display_name} · {call.at.slice(11, 16)} {call.at.slice(8, 10)}/{call.at.slice(5, 7)}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: "0.8125rem", color: "#9ca3af", fontStyle: "italic" }}>
                    Chưa có cuộc gọi nào được ghi lại.
                  </div>
                )}
              </div>

              {/* Call Note Input */}
              <div>
                <div className={s.sectionTitle}>Ghi chú cuộc gọi</div>
                <textarea
                  className={s.noteTextarea}
                  value={callNote}
                  onChange={(e) => setCallNote(e.target.value)}
                  placeholder="Ghi chú ngắn (VD: Giao sau 17h, giao cửa sau... Không ghi SĐT/STK)"
                  maxLength={200}
                  disabled={isLockedByOther}
                />
                <div className={s.noteCharCount}>
                  <span>
                    {hasForbiddenPii && (
                      <span style={{ color: "#dc2626", fontWeight: 600 }}>
                        ⚠️ Không ghi SĐT hoặc số tài khoản (BR-GH-19)
                      </span>
                    )}
                  </span>
                  <span>{callNote.length}/200</span>
                </div>
              </div>

              {/* Callback Time Picker (if Callback chosen) */}
              {selectedResult === "CALLBACK" && (
                <div className={s.subformSection}>
                  <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>
                    Chọn thời gian hẹn gọi lại
                  </div>
                  <input
                    type="datetime-local"
                    className={s.searchInput}
                    value={callbackTime}
                    onChange={(e) => setCallbackTime(e.target.value)}
                    required
                  />
                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      className={s.btnSecondary}
                      onClick={() => setSelectedResult(null)}
                    >
                      Bỏ chọn
                    </button>
                    <button
                      type="button"
                      className={s.btnPrimary}
                      onClick={() => handleRecordCall("CALLBACK")}
                      disabled={!callbackTime || submitting || hasForbiddenPii}
                    >
                      Lưu hẹn gọi lại
                    </button>
                  </div>
                </div>
              )}

              {/* Call Result Buttons Grid (Bottom half, height >= 44px on mobile) */}
              <div>
                <div className={s.sectionTitle}>Chọn kết quả cuộc gọi</div>
                <div className={s.resultsGrid}>
                  {item.confirm_state === "REFUND_CALL" ? (
                    // CS-09: REFUND_CALL only shows NOTIFIED & UNREACHABLE
                    <>
                      <button
                        type="button"
                        className={`${s.resultBtn} ${s.resultBtnConfirmed} ${isLockedByOther ? s.resultBtnDisabled : ""}`}
                        onClick={() => handleRecordCall("NOTIFIED")}
                        disabled={submitting || isLockedByOther || hasForbiddenPii}
                      >
                        <div>Đã báo hoàn tiền</div>
                        <div className={s.resultBtnSub}>Đã báo khách lý do huỷ và số tiền hoàn</div>
                      </button>
                      <button
                        type="button"
                        className={`${s.resultBtn} ${s.resultBtnUnreachable} ${isLockedByOther ? s.resultBtnDisabled : ""}`}
                        onClick={() => handleRecordCall("UNREACHABLE")}
                        disabled={submitting || isLockedByOther || hasForbiddenPii}
                      >
                        <div>Chưa liên lạc được</div>
                        <div className={s.resultBtnSub}>Không nghe máy, bận, thuê bao...</div>
                      </button>
                    </>
                  ) : (
                    // Standard call result options (CONFIRMED, CALLBACK, UNREACHABLE, etc.)
                    CALL_RESULT_OPTIONS.filter((opt) => opt.value !== "NOTIFIED").map((opt) => {
                      const isConfirmed = opt.value === "CONFIRMED";
                      const isCallback = opt.value === "CALLBACK";
                      const isUnreachable = opt.value === "UNREACHABLE";

                      return (
                        <button
                          key={opt.value}
                          type="button"
                          className={`${s.resultBtn} ${
                            isConfirmed
                              ? s.resultBtnConfirmed
                              : isCallback
                              ? s.resultBtnCallback
                              : isUnreachable
                              ? s.resultBtnUnreachable
                              : ""
                          } ${isLockedByOther ? s.resultBtnDisabled : ""}`}
                          onClick={() => handleRecordCall(opt.value)}
                          disabled={submitting || isLockedByOther || hasForbiddenPii}
                        >
                          <div>{opt.label}</div>
                          <div className={s.resultBtnSub}>{opt.hint}</div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className={s.modalFooter}>
          <button type="button" className={s.btnSecondary} onClick={onClose}>
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
