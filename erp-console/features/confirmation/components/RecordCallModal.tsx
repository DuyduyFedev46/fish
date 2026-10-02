"use client";

// F2h "Ghi kết quả gọi" và F2i "Hẹn gọi lại" (ED-15-AC2/AC3). Một hộp cho cả hai: F2i là cùng hộp, chỉ cho chọn "Hẹn gọi lại".
// Chọn "Hẹn gọi lại" thì hiện ô giờ hẹn; giờ phải sau bây giờ (câu lỗi nêu mốc). Ghi chú là chữ tự do: không ghi số điện thoại
// hay số tài khoản (BE chặn dãy 9 chữ số trở lên, màn kiểm trước). Ghi chú không lưu vào máy, URL hay log.
// 409 STALE_STATE: hiện câu của BE + "Tải lại". 409 CLAIMED: lỗi đỏ thường, giữ nguyên câu của BE.
import { useId, useRef, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { vnInputToIso } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { ModalAlert } from "./ModalAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { PersonalText } from "@/shared/ui/PersonalText";
import { Modal } from "@/shared/ui/overlay/Modal";
import { recordConfirmationCall } from "../api";
import { CALL_NOTE_MAX, callbackError, noteError } from "../confirmationUi";
import type { CallResult, RecordCallResponse } from "../types";
import { CALL_RESULT_OPTIONS } from "../types";
import { useGuardedSubmit } from "../useGuardedSubmit";
import s from "../confirmation.module.css";

type Props = {
  noteId: number;
  orderCode: string;
  customerName: string | null;
  phone: string | null;
  attempts: number;
  maxAttempts: number;
  /** Các kết quả được ghi (từ `available_actions`). */
  results: CallResult[];
  /** "callback" = F2i: chỉ chọn Hẹn gọi lại. */
  mode: "call" | "callback";
  onClose: () => void;
  onDone: (res: RecordCallResponse, ctx: { result: CallResult; callbackAt: string | null }) => void;
  /** Phiếu đã đổi (409 STALE_STATE): đóng hộp và tải lại trang. */
  onStale: () => void;
};

function newRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `req-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

type Errors = { result?: string; callback?: string; note?: string };

export function RecordCallModal({ noteId, orderCode, customerName, phone, attempts, maxAttempts, results, mode, onClose, onDone, onStale }: Props) {
  const callbackOnly = mode === "callback";
  const [result, setResult] = useState<CallResult | "">(callbackOnly ? "CALLBACK" : "");
  const [note, setNote] = useState("");
  const [callbackAt, setCallbackAt] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const group = useId();
  // Mỗi lần người dùng đổi nội dung thì dùng mã yêu cầu mới; chỉ "Thử lại" nguyên nội dung mới giữ mã cũ (chống ghi trùng khi mạng chập chờn).
  const requestId = useRef(newRequestId());
  const touch = () => {
    requestId.current = newRequestId();
  };

  const options = CALL_RESULT_OPTIONS.filter((o) => results.includes(o.value) && (!callbackOnly || o.value === "CALLBACK"));
  const iso = vnInputToIso(callbackAt);

  const sub = useGuardedSubmit(
    async () => {
      const r = result as CallResult;
      const at = r === "CALLBACK" ? iso : null;
      const res = await recordConfirmationCall(noteId, { result: r, note: note.trim(), callback_at: at, request_id: requestId.current });
      return { res, r, at };
    },
    { onSuccess: ({ res, r, at }) => onDone(res, { result: r, callbackAt: at }) },
  );

  const trySubmit = () => {
    const next: Errors = {};
    if (!result) next.result = "Chọn kết quả cuộc gọi.";
    if (result === "CALLBACK") next.callback = callbackError(iso) ?? undefined;
    next.note = noteError(note) ?? undefined;
    const bad = next.result || next.callback || next.note;
    setErrors(bad ? next : {});
    if (bad) return;
    void sub.submit();
  };

  const title = callbackOnly ? "Hẹn gọi lại" : "Ghi kết quả gọi";
  const showAlert = Boolean(sub.error) || Boolean(sub.stale);

  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          {sub.stale ? (
            <button type="button" className="btn primary" onClick={onStale}>
              Tải lại
            </button>
          ) : (
            <button type="button" className="btn primary" onClick={trySubmit} disabled={sub.submitting}>
              {sub.submitting ? "Đang gửi…" : primaryLabel(callbackOnly ? "Lưu hẹn gọi lại" : "Lưu kết quả", sub.failed)}
            </button>
          )}
        </>
      }
    >
      {showAlert && <ModalAlert>{sub.stale ?? sub.error}</ModalAlert>}
      <SummaryBlock
        label="Đơn đang gọi"
        rows={[
          { label: "Đơn hàng", value: orderCode, mono: true },
          { label: "Khách hàng", value: <PersonalText value={customerName} whenEmpty="—" /> },
          { label: "Số điện thoại", value: <PersonalText value={phone} whenEmpty="—" />, num: true },
          { label: "Lần gọi", value: `${attempts}/${maxAttempts}`, num: true },
        ]}
      />
      <div className={s.form}>
        {!callbackOnly && (
          <fieldset className={s.pickList} aria-invalid={errors.result ? true : undefined}>
            <legend className={s.pickLegend}>
              Kết quả cuộc gọi <span aria-hidden="true">*</span>
              <span className="sr-only"> (bắt buộc)</span>
            </legend>
            {options.map((o) => (
              <label key={o.value} className={`${s.pick} ${result === o.value ? s.pickOn : ""}`}>
                <input
                  className={s.pickInput}
                  type="radio"
                  name={`${group}-result`}
                  value={o.value}
                  checked={result === o.value}
                  onChange={() => {
                    touch();
                    setResult(o.value);
                    setErrors((e) => ({ ...e, result: undefined }));
                  }}
                  disabled={sub.submitting || Boolean(sub.stale)}
                />
                <span className={s.pickBody}>
                  <span className={s.pickName}>{ENUMS.confirmCallResult[o.value]?.label ?? o.label}</span>
                </span>
              </label>
            ))}
            {errors.result && (
              <p className="alert-box err" role="alert" data-field-error="result">
                {errors.result}
              </p>
            )}
          </fieldset>
        )}

        {result === "CALLBACK" && (
          <Field
            label="Hẹn gọi lại lúc"
            type="datetime-local"
            required
            value={callbackAt}
            onChange={(v) => {
              touch();
              setCallbackAt(v);
              setErrors((e) => ({ ...e, callback: undefined }));
            }}
            error={errors.callback}
            disabled={sub.submitting || Boolean(sub.stale)}
            autoFocus={callbackOnly}
          />
        )}

        <Field
          as="textarea"
          label="Ghi chú (không ghi số điện thoại hay số tài khoản)"
          value={note}
          onChange={(v) => {
            touch();
            setNote(v);
            setErrors((e) => ({ ...e, note: undefined }));
          }}
          rows={3}
          maxLength={CALL_NOTE_MAX}
          counter
          error={errors.note}
          disabled={sub.submitting || Boolean(sub.stale)}
        />
      </div>
    </Modal>
  );
}
