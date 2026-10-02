"use client";

// F2m — Nhập hàng hoàn về kho (ED-26, BR-HV-01). Chọn phiếu giao đang giao hoặc giao thất bại, chọn lô (chỉ lô nằm trong phiếu),
// nhập số kg. Hiện ngay "Đã giao n kg, đã hoàn m kg, còn hoàn được k kg" từ `returned_qty` của dòng phiếu giao, và chặn tại chỗ khi số nhập
// vượt số còn hoàn được. Id lô lấy từ `batch_pk` của dòng (người giao không có quyền xem lô). BE vẫn là lớp chặn thật (RETURN_QTY_EXCEEDS).
// Giờ rời kho / giờ về do hệ thống ghi (BR-PQ-14): hai ô chỉ đọc. Ghi chú là chữ tự do: chặn số điện thoại / dãy số dài, không lưu vào máy, URL hay log.
// Lỗi theo ô hiện dưới ô (viền đỏ); lỗi khác ở đầu hộp; nút chính đổi thành "Thử lại" sau một lần gửi lỗi.
import { useEffect, useMemo, useState } from "react";
import { kg } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import type { DeliveryNoteItem } from "@/features/deliveries/types";
import { createReturn, getNoteLines, listReturnableNotes } from "../api";
import { RETURNS_MSG as M } from "../messages";
import { NOTE_MAX, batchChoices, createErrorOf, normalizeQty, qtyExceedsOf, qtyFactsText, qtyOverRemaining, showSubmitAlert, validateNote, type CreateField } from "../returnsModel";
import type { ReturnItem, ReturnableLine } from "../types";
import s from "../returns.module.css";

type Props = {
  /** Phiếu giao điền sẵn (nút "Mang hàng về kho" ở Việc giao của tôi). */
  initialNote?: { id: number; code: string };
  onClose: () => void;
  onCreated: (item: ReturnItem) => void;
};

type NotesState = { state: "loading" } | { state: "error" } | { state: "ready"; notes: DeliveryNoteItem[]; truncated: boolean };
type LinesState = { state: "idle" } | { state: "loading" } | { state: "error" } | { state: "ready"; lines: ReturnableLine[] };
type FieldError = { field: CreateField; message: string };

export function CreateReturnModal({ initialNote, onClose, onCreated }: Props) {
  const [notes, setNotes] = useState<NotesState>({ state: "loading" });
  const [noteId, setNoteId] = useState(initialNote ? String(initialNote.id) : "");
  const [lines, setLines] = useState<LinesState>({ state: "idle" });
  const [batchKey, setBatchKey] = useState("");
  const [qty, setQty] = useState("");
  const [text, setText] = useState("");
  const [fieldError, setFieldError] = useState<FieldError | null>(null);
  // Số đã hoàn do BE báo kèm lỗi vượt kg (người khác vừa nhập thêm); dùng thay cho `returned_qty` lúc mở phiếu giao.
  const [alreadyReturned, setAlreadyReturned] = useState<number | null>(null);
  // Lỗi lần gửi đã gắn vào một ô: ô bị sửa/xoá lỗi thì câu đó không được nhảy lên đầu hộp (TL9-M2).
  const [errorAttached, setErrorAttached] = useState(false);
  const [notesAttempt, setNotesAttempt] = useState(0);
  const [linesAttempt, setLinesAttempt] = useState(0);

  useEffect(() => {
    const c = new AbortController();
    setNotes({ state: "loading" });
    listReturnableNotes(c.signal)
      .then((r) => setNotes({ state: "ready", notes: r.notes, truncated: r.truncated }))
      .catch(() => {
        if (!c.signal.aborted) setNotes({ state: "error" });
      });
    return () => c.abort();
  }, [notesAttempt]);

  useEffect(() => {
    if (!noteId) {
      setLines({ state: "idle" });
      return;
    }
    const c = new AbortController();
    setLines({ state: "loading" });
    getNoteLines(Number(noteId), c.signal)
      .then((l) => setLines({ state: "ready", lines: l }))
      .catch(() => {
        if (!c.signal.aborted) setLines({ state: "error" });
      });
    return () => c.abort();
  }, [noteId, linesAttempt]);

  const choices = useMemo(() => (lines.state === "ready" ? batchChoices(lines.lines) : []), [lines]);
  // Phiếu chỉ có một lô: chọn sẵn.
  useEffect(() => {
    if (choices.length === 1) setBatchKey(choices[0].key);
  }, [choices]);
  const choice = choices.find((c) => c.key === batchKey) ?? null;
  // Số BE vừa báo kèm lỗi vượt kg là số mới nhất, nên ưu tiên hơn số lúc mở phiếu giao.
  const returnedKnown = choice ? alreadyReturned ?? choice.returned : null;

  const noteOptions = useMemo(() => {
    const list = notes.state === "ready" ? notes.notes : [];
    const opts = list.map((n) => ({ value: String(n.id), label: `${n.code}${n.order?.code ? ` · đơn ${n.order.code}` : ""}` }));
    if (initialNote && !list.some((n) => n.id === initialNote.id)) opts.unshift({ value: String(initialNote.id), label: initialNote.code });
    return [{ value: "", label: M.pickNotePlaceholder }, ...opts];
  }, [notes, initialNote]);

  const sub = useSubmit(
    async () => {
      setFieldError(null);
      setErrorAttached(false);
      const batch = (choice as NonNullable<typeof choice>).line.batch_pk as number;
      try {
        return await createReturn({ delivery_note: Number(noteId), batch, qty: normalizeQty(qty) as string, note: text.trim() || undefined });
      } catch (err) {
        const ex = qtyExceedsOf(err);
        if (ex) setAlreadyReturned(ex.already);
        const mapped = createErrorOf(err, kg);
        if (mapped.field) setFieldError({ field: mapped.field, message: mapped.message });
        setErrorAttached(mapped.field !== null);
        throw err instanceof ApiError ? new Error(mapped.message) : err;
      }
    },
    { onSuccess: onCreated },
  );

  // Kiểm tại chỗ trước khi gửi: lỗi nhập hiện dưới ô, không tính là lần gửi lỗi (nút chính không đổi thành "Thử lại").
  const trySubmit = () => {
    if (!noteId) return setFieldError({ field: "deliveryNote", message: M.errNotePick });
    if (!choice) return setFieldError({ field: "batch", message: M.errBatchPick });
    if (!qty.trim()) return setFieldError({ field: "qty", message: M.errQtyRequired });
    if (typeof choice.line.batch_pk !== "number") return setFieldError({ field: "batch", message: M.batchMissing });
    const normalized = normalizeQty(qty);
    if (!normalized) return setFieldError({ field: "qty", message: M.errQtyInvalid });
    const over = qtyOverRemaining(normalized, choice.delivered, returnedKnown, kg);
    if (over) return setFieldError({ field: "qty", message: over });
    const bad = validateNote(text);
    if (bad) return setFieldError({ field: "note", message: bad });
    setFieldError(null);
    void sub.submit();
  };

  const clear = (f: FieldError["field"]) => setFieldError((e) => (e?.field === f ? null : e));
  const showAlert = showSubmitAlert(sub.error, errorAttached);
  const busy = sub.submitting;
  const notesEmpty = notes.state === "ready" && noteOptions.length === 1;

  return (
    <Modal
      title={M.createTitle}
      onClose={onClose}
      busy={busy}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            {M.cancel}
          </button>
          <button type="button" className="btn primary" onClick={trySubmit} disabled={busy || notes.state === "loading"} aria-busy={busy || undefined}>
            {busy ? M.submitting : primaryLabel(M.createSubmit, sub.failed)}
          </button>
        </>
      }
    >
      <div className={s.form}>
        {showAlert && <FormAlert>{sub.error}</FormAlert>}

        {notes.state === "error" && (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{M.notesFailed}</span>
            <button type="button" className="btn" onClick={() => setNotesAttempt((n) => n + 1)}>
              {M.retry}
            </button>
          </div>
        )}
        {notes.state === "loading" && (
          <p className={s.qtyFacts} role="status">
            {M.notesLoading}
          </p>
        )}
        {notes.state === "ready" && notes.truncated && (
          <p className={s.qtyFacts} role="status" data-notes-truncated>
            {M.notesTruncated(notes.notes.length)}
          </p>
        )}
        {notesEmpty && (
          <p className="alert-box warn" role="status">
            <Icon name="info" />
            <span>{M.notesEmpty}</span>
          </p>
        )}

        <Field
          as="select"
          label={M.fieldDeliveryNotePick}
          required
          value={noteId}
          onChange={(v) => {
            setNoteId(v);
            setBatchKey("");
            setAlreadyReturned(null);
            clear("deliveryNote");
          }}
          options={noteOptions}
          error={fieldError?.field === "deliveryNote" ? fieldError.message : null}
          disabled={busy || notes.state === "loading"}
        />

        {lines.state === "loading" && (
          <p className={s.qtyFacts} role="status">
            {M.detailLoading}
          </p>
        )}
        {lines.state === "error" && (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{M.detailFailed}</span>
            <button type="button" className="btn" onClick={() => setLinesAttempt((n) => n + 1)}>
              {M.retry}
            </button>
          </div>
        )}

        <Field
          as="select"
          label={M.fieldBatchPick}
          required
          value={batchKey}
          onChange={(v) => {
            setBatchKey(v);
            setAlreadyReturned(null);
            clear("batch");
          }}
          options={[{ value: "", label: M.pickBatchPlaceholder }, ...choices.map((c) => ({ value: c.key, label: c.label }))]}
          error={fieldError?.field === "batch" ? fieldError.message : null}
          disabled={busy || lines.state !== "ready"}
        />
        {choice && (
          <p className={`${s.qtyFacts} num`} data-qty-facts>
            {qtyFactsText(choice.delivered, returnedKnown, kg)}
          </p>
        )}

        <Field
          label={M.fieldQtyInput}
          required
          type="number"
          unit="kg"
          value={qty}
          onChange={(v) => {
            setQty(v);
            clear("qty");
          }}
          error={fieldError?.field === "qty" ? fieldError.message : null}
          disabled={busy}
        />

        <div className={s.times}>
          <div className={s.timeCell}>
            <span className={s.timeLabel}>{M.leftAtLabel}</span>
            <span className={s.timeValue} data-time="left">
              {M.timeLeftValue}
            </span>
          </div>
          <div className={s.timeCell}>
            <span className={s.timeLabel}>{M.returnedAtLabel}</span>
            <span className={s.timeValue} data-time="returned">
              {M.timeReturnedValue}
            </span>
          </div>
        </div>

        <Field
          as="textarea"
          label={M.fieldNoteInput}
          value={text}
          onChange={(v) => {
            setText(v);
            clear("note");
          }}
          rows={3}
          maxLength={NOTE_MAX}
          error={fieldError?.field === "note" ? fieldError.message : null}
          disabled={busy}
        />
      </div>
    </Modal>
  );
}
