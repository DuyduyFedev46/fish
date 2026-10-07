"use client";

// F2l — Báo giao thất bại (BR-GH-22, B5). Bắt buộc chọn lý do; "Khác" bắt buộc ghi chú ngắn (tối đa 200 ký tự).
// Ghi chú là chữ tự do nên KHÔNG được chứa số điện thoại hay dãy số dài (BE chặn dãy 9 chữ số trở lên, mã DELIVERY_FAILURE_NOTE_PII):
// màn kiểm trước khi gửi (cùng luật `has_long_digit_run` của BE: gộp cả dấu cách, dấu chấm) và hiện lỗi dưới ô nếu BE vẫn trả 400. Ghi chú không lưu vào máy, URL hay log.
// Khối tóm tắt thiếu dòng "Bắt đầu giao": BE chưa có mốc này (xem dev-notes, chỗ lệch).
import { useId, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { ApiError } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { PersonalText } from "@/shared/ui/PersonalText";
import { Modal } from "@/shared/ui/overlay/Modal";
import { reportDeliveryFailure, type DeliveryStatusResponse } from "../api";
import { FAILURE_NOTE_MAX, FAILURE_REASON_KEYS, failureFieldOfCode, isOrderCancelledError, orderCancelledMessage, validateFailureInput } from "../deliveryUi";
import type { DeliveryFailureReason, DeliveryNoteItem } from "../types";
import s from "../deliveries.module.css";

type Props = {
  note: Pick<DeliveryNoteItem, "id" | "code" | "order" | "customer_name">;
  onClose: () => void;
  onReported: (res: DeliveryStatusResponse) => void;
  /** BR-GH-24: đơn đã huỷ. Màn cha đóng hộp và tải lại phiếu. */
  onReload: () => void;
};

export function ReportFailureModal({ note, onClose, onReported, onReload }: Props) {
  const [cancelledText, setCancelledText] = useState<string | null>(null);
  const [reason, setReason] = useState<DeliveryFailureReason | "">("");
  const [text, setText] = useState("");
  const [fieldError, setFieldError] = useState<{ field: "reason" | "note"; message: string } | null>(null);
  const group = useId();

  const sub = useSubmit(
    async () => {
      setFieldError(null);
      try {
        return await reportDeliveryFailure(note.id, { reason: reason as DeliveryFailureReason, note: text });
      } catch (err) {
        if (isOrderCancelledError(err)) setCancelledText(orderCancelledMessage(err));
        else if (err instanceof ApiError) {
          const field = failureFieldOfCode(err.code);
          if (field) {
            setFieldError({ field, message: err.message });
          }
        }
        throw err;
      }
    },
    { onSuccess: onReported },
  );

  // Kiểm tại chỗ trước khi gửi: lỗi nhập hiện dưới ô, không tính là lần gửi lỗi (nút chính không đổi thành "Thử lại").
  const trySubmit = () => {
    const bad = validateFailureInput(reason, text);
    if (bad) {
      setFieldError(bad);
      return;
    }
    void sub.submit();
  };

  // Lỗi theo ô đã hiện dưới ô: không lặp thêm ở alert đầu hộp.
  const showAlert = Boolean(sub.error) && !fieldError && !cancelledText;
  const noteRequired = reason === "OTHER";

  return (
    <Modal
      title="Báo giao thất bại"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          {cancelledText ? (
            <button type="button" className="btn primary" onClick={onReload}>
              Tải lại
            </button>
          ) : (
            <button type="button" className="btn danger" onClick={trySubmit} disabled={sub.submitting}>
              {sub.submitting ? "Đang gửi…" : primaryLabel("Báo giao thất bại", sub.failed)}
            </button>
          )}
        </>
      }
    >
      {cancelledText && <FormAlert>{cancelledText}</FormAlert>}
      {showAlert && <FormAlert>{sub.error}</FormAlert>}
      <SummaryBlock
        label="Phiếu giao cần báo thất bại"
        rows={[
          { label: "Phiếu giao", value: note.code, mono: true },
          { label: "Đơn", value: note.order?.code || "—", mono: true },
          { label: "Khách hàng", value: <PersonalText value={note.customer_name} whenEmpty="—" /> },
        ]}
      />

      <fieldset className={s.pickList} aria-invalid={fieldError?.field === "reason" || undefined}>
        <legend className={s.pickLegend}>
          Lý do <span aria-hidden="true">*</span>
          <span className="sr-only"> (bắt buộc)</span>
        </legend>
        {FAILURE_REASON_KEYS.map((key) => (
          <label key={key} className={`${s.pick} ${reason === key ? s.pickOn : ""}`}>
            <input
              className={s.pickInput}
              type="radio"
              name={`${group}-reason`}
              value={key}
              checked={reason === key}
              onChange={() => {
                setReason(key);
                setFieldError((e) => (e?.field === "reason" ? null : e));
              }}
              disabled={sub.submitting}
            />
            <span className={s.pickBody}>
              <span className={s.pickName}>{ENUMS.deliveryFailureReason[key].label}</span>
            </span>
          </label>
        ))}
        {fieldError?.field === "reason" && (
          <p className="alert-box err" role="alert" data-field-error="reason">
            {fieldError.message}
          </p>
        )}
      </fieldset>

      <Field
        as="textarea"
        label={noteRequired ? "Ghi chú (bắt buộc, không ghi số điện thoại)" : "Ghi chú (không ghi số điện thoại)"}
        required={noteRequired}
        value={text}
        onChange={(v) => {
          setText(v);
          setFieldError((e) => (e?.field === "note" ? null : e));
        }}
        rows={3}
        maxLength={FAILURE_NOTE_MAX}
        error={fieldError?.field === "note" ? fieldError.message : null}
        disabled={sub.submitting}
      />
    </Modal>
  );
}
