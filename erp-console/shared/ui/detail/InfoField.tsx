"use client";

// Một ô trong InfoGrid. Bốn biến thể (UI-RULES §5.4):
//  - text     : chỉ hiển thị.
//  - editable : rê chuột (hoặc focus) hiện bút chì → sửa tại chỗ, Lưu / Huỷ, lỗi dưới ô. Enter = Lưu, Esc = Huỷ. Trên cảm ứng bút chì luôn hiện.
//  - locked   : chỉ đọc, có icon khoá (giá vốn, trường khoá nghiệp vụ); `reason` là lý do ngắn, đọc được bằng trình đọc màn hình.
//  - link     : trỏ tới đối tượng khác; bấm mở LookupCard (popup), không điều hướng.
// Giá trị trống → "—". Không bao giờ truyền giá vốn vào đây khi người xem không có quyền (màn quyết định, không phải ô này).

import { useEffect, useId, useRef, useState } from "react";
import { Icon } from "../Icon";
import { Field } from "../form/Field";
import { useSubmit, primaryLabel, type SubmitConflict } from "../form/useSubmit";
import s from "./InfoField.module.css";

type Base = { label: string };
type TextProps = Base & { kind?: "text"; value: React.ReactNode; mono?: boolean; num?: boolean };
type LockedProps = Base & { kind: "locked"; value: React.ReactNode; reason?: string; mono?: boolean; num?: boolean };
type LinkProps = Base & { kind: "link"; value: React.ReactNode; onOpen: () => void; mono?: boolean };
type EditableProps = Base & {
  kind: "editable";
  /** Giá trị thô để sửa. */
  value: string;
  /** Cách hiện khi chưa sửa (vd "540.000 đ"); mặc định = value. */
  display?: React.ReactNode;
  /** Gọi khi bấm Lưu. Ném lỗi (ApiError) → ô giữ nguyên giá trị đang gõ, hiện lỗi dưới ô. */
  onSave: (next: string) => Promise<void>;
  type?: "text" | "number" | "tel" | "date";
  unit?: string;
  required?: boolean;
  /** Câu báo khi để trống ô bắt buộc (vd "Nhập tên nhà cung cấp."); không truyền thì dùng câu chung. */
  requiredMessage?: string;
  /** Kiểm tại chỗ trước khi gửi; trả chuỗi lỗi hoặc null. */
  validate?: (next: string) => string | null;
  num?: boolean;
  /** Có thì ô sửa là textarea kèm bộ đếm "n/max" (ô chữ dài hiển thị cho khách). */
  maxLength?: number;
  /** Gọi khi lưu gặp xung đột phiên bản (người khác vừa sửa): màn bật ConflictBanner. Không truyền thì ô vẫn tự báo một câu ngắn (L5). */
  onConflict?: (conflict: SubmitConflict) => void;
};

/** Câu ngắn dưới ô khi lưu gặp xung đột (useSubmit đưa 409 vào `conflict`, không vào `error`). */
export const CONFLICT_FIELD_MESSAGE = "Có người vừa sửa mục này. Tải lại để xem bản mới.";

export type InfoFieldProps = TextProps | LockedProps | LinkProps | EditableProps;

const isEmpty = (v: React.ReactNode) => v === null || v === undefined || v === "" || v === false;

export function InfoField(props: InfoFieldProps) {
  const labelId = useId();
  if (props.kind === "editable") return <Editable {...props} labelId={labelId} />;

  let valueNode: React.ReactNode;
  if (props.kind === "link") {
    valueNode = isEmpty(props.value) ? (
      <span className="muted">—</span>
    ) : (
      <button type="button" className={`${s.link} ${props.mono ? s.mono : ""}`} onClick={props.onOpen} aria-haspopup="dialog" aria-describedby={labelId}>
        {props.value}
      </button>
    );
  } else {
    const cls = `${props.mono ? s.mono : ""} ${props.num ? "num" : ""}`;
    valueNode = isEmpty(props.value) ? (
      <span className="muted">—</span>
    ) : (
      <span className={cls}>{props.value}</span>
    );
  }

  return (
    <div className={s.cell} data-kind={props.kind ?? "text"}>
      <dt className={s.label} id={labelId}>
        {props.label}
        {props.kind === "locked" && (
          <span className={s.lock} title={props.reason || "Chỉ đọc"}>
            <Icon name="lock" />
            <span className="sr-only">{props.reason || "Chỉ đọc"}</span>
          </span>
        )}
      </dt>
      <dd className={s.value}>{valueNode}</dd>
    </div>
  );
}

/** Lỗi nhập của ô sửa tại chỗ (null = hợp lệ): để trống khi bắt buộc, hoặc `validate` của màn. */
export function validateDraft(draft: string, opts: { required?: boolean; requiredMessage?: string; validate?: (next: string) => string | null }): string | null {
  if (opts.required && !draft.trim()) return opts.requiredMessage ?? "Nhập giá trị cho ô này.";
  return opts.validate ? opts.validate(draft) : null;
}

function Editable({ label, labelId, value, display, onSave, type = "text", unit, required, requiredMessage, validate, num, maxLength, onConflict }: EditableProps & { labelId: string }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [localError, setLocalError] = useState<string | null>(null);
  const pencilRef = useRef<HTMLButtonElement>(null);
  const wasEditing = useRef(false);

  const sub = useSubmit(() => onSave(draft), { onSuccess: () => setEditing(false) });

  // Xung đột: báo màn cha (banner) một lần mỗi lần gặp; ô cũng hiện câu ngắn bên dưới.
  const conflictRef = useRef(onConflict);
  conflictRef.current = onConflict;
  useEffect(() => {
    if (sub.conflict) conflictRef.current?.(sub.conflict);
  }, [sub.conflict]);

  // Kiểm tại chỗ TRƯỚC khi gửi: chưa gửi gì nên đây là lỗi nhập, không phải lỗi gửi (nút giữ "Lưu", không thành "Thử lại").
  const submit = () => {
    const msg = validateDraft(draft, { required, requiredMessage, validate });
    setLocalError(msg);
    if (msg) return;
    void sub.submit();
  };

  // Trả focus về bút chì sau khi đóng ô sửa (bàn phím không bị rơi về đầu trang).
  useEffect(() => {
    if (wasEditing.current && !editing) pencilRef.current?.focus({ preventScroll: true });
    wasEditing.current = editing;
  }, [editing]);

  const start = () => {
    setDraft(value);
    setLocalError(null);
    sub.reset();
    setEditing(true);
  };
  const cancel = () => {
    if (sub.submitting) return;
    setEditing(false);
    setLocalError(null);
    sub.reset();
  };

  if (!editing) {
    const shown = display ?? value;
    return (
      <div className={`${s.cell} ${s.editable}`} data-kind="editable">
        <dt className={s.label} id={labelId}>
          {label}
        </dt>
        <dd className={s.value}>
          <span className={`${s.valueText} ${num ? "num" : ""}`}>{isEmpty(shown) ? <span className="muted">—</span> : shown}</span>
          <button ref={pencilRef} type="button" className={s.pencil} onClick={start} aria-label={`Sửa ${label.toLowerCase()}`}>
            <Icon name="edit" />
          </button>
        </dd>
      </div>
    );
  }

  const error = localError ?? sub.error ?? (sub.conflict ? CONFLICT_FIELD_MESSAGE : null);
  return (
    <div className={`${s.cell} ${s.editing}`} data-kind="editable" data-editing>
      {/* Đang sửa: nhãn của Field ngay dưới đã hiện, nên nhãn ô chỉ giữ cho trình đọc màn hình (không trùng nhãn trên mắt). */}
      <dt className="sr-only" id={labelId}>
        {label}
      </dt>
      <dd
        className={s.value}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.stopPropagation();
            cancel();
          }
        }}
      >
        <form
          className={s.editForm}
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          {maxLength ? (
            <Field as="textarea" label={label} value={draft} onChange={(v) => { setDraft(v); if (localError) setLocalError(null); }} rows={3} maxLength={maxLength} counter error={error} autoFocus disabled={sub.submitting} />
          ) : (
            <Field label={label} value={draft} onChange={(v) => { setDraft(v); if (localError) setLocalError(null); }} type={type} unit={unit} required={required} error={error} autoFocus disabled={sub.submitting} />
          )}
          <div className={s.editActions}>
            <button type="button" className="btn" onClick={cancel} disabled={sub.submitting}>
              Huỷ
            </button>
            <button type="submit" className="btn primary" disabled={sub.submitting}>
              {sub.submitting ? "Đang lưu…" : primaryLabel("Lưu", sub.failed && !localError)}
            </button>
          </div>
        </form>
      </dd>
    </div>
  );
}
