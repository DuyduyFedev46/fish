"use client";

// F2k "Quyết định đơn chưa xác nhận" (CS-07, ED-15-AC4). Chỉ Chủ/Quản lý (BE đưa "decide:*" vào `available_actions`; CSKH không có nút mở hộp này).
// Ba lựa chọn: Giao không xác nhận (cần lý do) · Gia hạn thêm (giờ mới, tối đa 24 giờ, cần lý do) · Huỷ đơn (nút đỏ, hỏi lại một lần).
// Lý do là chữ tự do: không ghi số điện thoại hay số tài khoản. Không lưu vào máy, URL hay log.
import { useId, useState } from "react";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnInputToIso } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { ModalAlert } from "./ModalAlert";
import { SummaryBlock } from "@/shared/ui/form/SummaryBlock";
import { primaryLabel } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { decideConfirmation } from "../api";
import { CANCEL_REASON_CODES, DECIDE_REASON_MAX, decisionsOf, extendError, noteError } from "../confirmationUi";
import type { ConfirmationDecision, DecideResponse } from "../types";
import { useGuardedSubmit } from "../useGuardedSubmit";
import s from "../confirmation.module.css";

type Props = {
  noteId: number;
  orderCode: string;
  escalationLabel: string | null;
  attempts: number;
  decideDeadline: string | null;
  /** `available_actions` của phiếu: quyết định nào được phép. */
  actions: string[];
  onClose: () => void;
  onDone: (decision: ConfirmationDecision, res: DecideResponse) => void;
  onStale: () => void;
};

type Errors = { decision?: string; reason?: string; until?: string };
type CancelCode = (typeof CANCEL_REASON_CODES)[number]["value"];

export function DecideModal({ noteId, orderCode, escalationLabel, attempts, decideDeadline, actions, onClose, onDone, onStale }: Props) {
  const options = decisionsOf(actions);
  const [decision, setDecision] = useState<ConfirmationDecision | "">("");
  const [reason, setReason] = useState("");
  const [until, setUntil] = useState("");
  const [cancelCode, setCancelCode] = useState<CancelCode>("UNREACHABLE");
  const [errors, setErrors] = useState<Errors>({});
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const group = useId();
  const untilIso = vnInputToIso(until);

  const sub = useGuardedSubmit(
    async () => {
      const d = decision as ConfirmationDecision;
      const res = await decideConfirmation(
        noteId,
        d === "DELIVER_WITHOUT_CONFIRM"
          ? { decision: d, reason: reason.trim() }
          : d === "EXTEND"
            ? { decision: d, until: untilIso, reason: reason.trim() }
            : { decision: d, reason_code: cancelCode, note: reason.trim() },
      );
      return { d, res };
    },
    { onSuccess: ({ d, res }) => onDone(d, res) },
  );

  const requireReason = decision === "DELIVER_WITHOUT_CONFIRM" || decision === "EXTEND";
  const validate = (): boolean => {
    const next: Errors = {};
    if (!decision) next.decision = "Chọn một cách xử lý.";
    if (requireReason && !reason.trim()) next.reason = "Nhập lý do.";
    else next.reason = noteError(reason, DECIDE_REASON_MAX) ?? undefined;
    if (decision === "EXTEND") next.until = extendError(untilIso) ?? undefined;
    const bad = next.decision || next.reason || next.until;
    setErrors(bad ? next : {});
    return !bad;
  };

  const trySubmit = () => {
    if (!validate()) return;
    if (decision === "CANCEL" && !confirmingCancel) {
      setConfirmingCancel(true);
      return;
    }
    void sub.submit();
  };

  const pick = (d: ConfirmationDecision) => {
    setDecision(d);
    setConfirmingCancel(false);
    setErrors({});
  };

  const busy = sub.submitting || Boolean(sub.stale);
  const isCancel = decision === "CANCEL";
  const primaryText = isCancel ? (confirmingCancel ? "Xác nhận huỷ đơn" : "Huỷ đơn") : "Lưu quyết định";

  return (
    <Modal
      title="Quyết định đơn chưa xác nhận"
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={confirmingCancel ? () => setConfirmingCancel(false) : onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          {sub.stale ? (
            <button type="button" className="btn primary" onClick={onStale}>
              Tải lại
            </button>
          ) : (
            <button type="button" className={`btn ${isCancel ? "danger" : "primary"}`} onClick={trySubmit} disabled={sub.submitting || options.length === 0}>
              {sub.submitting ? "Đang gửi…" : primaryLabel(primaryText, sub.failed)}
            </button>
          )}
        </>
      }
    >
      {(sub.error || sub.stale) && <ModalAlert>{sub.stale ?? sub.error}</ModalAlert>}
      {confirmingCancel && !sub.stale && <ModalAlert kind="warn">Huỷ đơn sẽ dừng việc giao và chuyển sang hoàn tiền cho khách. Bấm Xác nhận huỷ đơn để tiếp tục.</ModalAlert>}
      <SummaryBlock
        label="Đơn cần quyết định"
        rows={[
          { label: "Đơn hàng", value: orderCode, mono: true },
          { label: "Lý do chuyển lên", value: escalationLabel || "—" },
          { label: "Lần gọi", value: String(attempts), num: true },
          ...(decideDeadline ? [{ label: "Hạn quyết định", value: dateTime(decideDeadline), num: true }] : []),
        ]}
      />
      <div className={s.form}>
        <fieldset className={s.pickList} aria-invalid={errors.decision ? true : undefined}>
          <legend className={s.pickLegend}>
            Cách xử lý <span aria-hidden="true">*</span>
            <span className="sr-only"> (bắt buộc)</span>
          </legend>
          {options.map((d) => (
            <label key={d} className={`${s.pick} ${d === "CANCEL" ? s.pickDanger : ""} ${decision === d ? s.pickOn : ""}`}>
              <input className={s.pickInput} type="radio" name={`${group}-decision`} value={d} checked={decision === d} onChange={() => pick(d)} disabled={busy} />
              <span className={s.pickBody}>
                <span className={s.pickName}>{ENUMS.unconfirmedDecision[d].label}</span>
              </span>
            </label>
          ))}
          {options.length === 0 && <p className="muted">Bạn không có quyền quyết định đơn này.</p>}
          {errors.decision && (
            <p className="alert-box err" role="alert" data-field-error="decision">
              {errors.decision}
            </p>
          )}
        </fieldset>

        {decision === "EXTEND" && (
          <Field
            label="Gia hạn tới lúc"
            type="datetime-local"
            required
            value={until}
            onChange={(v) => {
              setUntil(v);
              setErrors((e) => ({ ...e, until: undefined }));
            }}
            error={errors.until}
            disabled={busy}
          />
        )}

        {decision === "CANCEL" && (
          <Field
            as="select"
            label="Lý do huỷ"
            value={cancelCode}
            onChange={(v) => setCancelCode(v as CancelCode)}
            options={CANCEL_REASON_CODES.map((c) => ({ value: c.value, label: c.label }))}
            disabled={busy}
          />
        )}

        {decision && (
          <Field
            as="textarea"
            label={requireReason ? "Lý do (không ghi số điện thoại hay số tài khoản)" : "Ghi chú (không ghi số điện thoại hay số tài khoản)"}
            required={requireReason}
            value={reason}
            onChange={(v) => {
              setReason(v);
              setErrors((e) => ({ ...e, reason: undefined }));
            }}
            rows={3}
            maxLength={DECIDE_REASON_MAX}
            counter
            error={errors.reason}
            disabled={busy}
          />
        )}
      </div>
    </Modal>
  );
}
