"use client";

// Các hộp thoại của màn soạn bài (ED-35 / F3i, F3j, F3k): kiểm tra trước khi đăng, cảnh báo, trả về nháp, gỡ bài, lịch sử.
// Mỗi hộp tự giữ trạng thái "đang gửi / lỗi" bằng useSubmit; việc thật (gọi API, chuyển hộp khác) do màn soạn bài truyền vào qua `run`.

import { useEffect, useId, useState } from "react";
import { dateTimeFull } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { fetchEntryVersions } from "../api";
import { errorText, warningLine } from "../contentModel";
import { CONTENT_MSG as M, RETURN_REASONS, UNPUBLISH_REASONS, WARNING_FIELD_LABELS } from "../messages";
import type { ContentEntryVersionListItem, ContentWarning } from "../types";
import s from "../content.module.css";

/** F3k: tick đủ 5 mục thì mới mở nút Đăng. */
export function ChecklistModal({ revision, run, onClose }: { revision: boolean; run: () => Promise<void>; onClose: () => void }) {
  const [ticked, setTicked] = useState<boolean[]>(() => M.checklistItems.map(() => false));
  const all = ticked.every(Boolean);
  const sub = useSubmit(run);
  return (
    <Modal
      title={M.checklistTitle}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.warningsBackToEdit}
          </button>
          <button type="button" className="btn primary" disabled={!all || sub.submitting} aria-busy={sub.submitting || undefined} onClick={() => void sub.submit()}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.publishBusy}</span>
              </>
            ) : (
              primaryLabel(revision ? M.publishChanges : M.publish, sub.failed)
            )}
          </button>
        </>
      }
    >
      <div className={s.dialogBody}>
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.dialogIntro}>{M.checklistIntro}</p>
        <div className={s.checkList} role="group" aria-label={M.checklistGroup}>
          {M.checklistItems.map((label, i) => (
            <label key={label} className="check-row">
              <input
                type="checkbox"
                checked={ticked[i]}
                disabled={sub.submitting}
                onChange={(e) => setTicked((t) => t.map((v, j) => (j === i ? e.target.checked : v)))}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </div>
    </Modal>
  );
}

/** 409 CONTENT_WARNINGS: liệt kê chỗ cần xem lại; người dùng sửa bài hoặc xác nhận đã kiểm tra rồi vẫn tiếp tục. */
export function WarningsModal({ warnings, action, run, onClose }: { warnings: ContentWarning[]; action: "publish" | "submit"; run: () => Promise<void>; onClose: () => void }) {
  const sub = useSubmit(run);
  return (
    <Modal
      title={M.warningsTitle}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.warningsBackToEdit}
          </button>
          <button type="button" className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined} onClick={() => void sub.submit()}>
            {sub.submitting ? <Icon name="progress_activity" className="spin" /> : null}
            <span>{sub.submitting ? M.publishBusy : primaryLabel(action === "publish" ? M.warningsForcePublish : M.warningsForceSubmit, sub.failed)}</span>
          </button>
        </>
      }
    >
      <div className={s.dialogBody}>
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <p className={s.dialogIntro}>{M.warningsIntro}</p>
        <ul className={s.warnList}>
          {warnings.map((w, i) => (
            <li key={`${w.type}-${i}`} className={s.warnItem}>
              <Icon name="warning" />
              <span>
                {warningLine(w)}
                {w.field && WARNING_FIELD_LABELS[w.field] ? <span className="muted"> ({WARNING_FIELD_LABELS[w.field]})</span> : null}
                {/* Đoạn trích là chữ do người viết bài gõ; React tự thoát ký tự đặc biệt khi hiển thị. */}
                {w.snippet ? <span className={s.warnSnippet}>{w.snippet}</span> : null}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </Modal>
  );
}

/** F3i (trả về nháp) và F3j (gỡ bài): bắt buộc chọn lý do. */
export function ReasonModal({ mode, articleTitle, run, onClose }: { mode: "return" | "unpublish"; articleTitle: string; run: (reason: string) => Promise<void>; onClose: () => void }) {
  const formId = useId();
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | null>(null);
  const isReturn = mode === "return";
  const sub = useSubmit(() => run(reason));
  const options = [{ value: "", label: M.returnReasonPlaceholder }, ...(isReturn ? RETURN_REASONS : UNPUBLISH_REASONS)];
  const label = isReturn ? M.returnReasonLabel : M.unpublishReasonLabel;
  return (
    <Modal
      title={isReturn ? M.returnTitle : M.unpublishTitle}
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.catCancel}
          </button>
          <button type="submit" form={formId} className={`btn ${isReturn ? "primary" : "danger solid"}`} disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{isReturn ? M.returnBusy : M.unpublishBusy}</span>
              </>
            ) : (
              primaryLabel(isReturn ? M.returnConfirm : M.unpublishConfirm, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.dialogBody}
        onSubmit={(e) => {
          e.preventDefault();
          if (sub.submitting) return;
          if (!reason) {
            setReasonError(isReturn ? M.returnReasonRequired : M.unpublishReasonRequired);
            return;
          }
          void sub.submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        {isReturn ? (
          <p className={s.dialogIntro}>
            {M.returnArticle}: <b className={s.dialogTitleText}>{articleTitle || "(chưa có tiêu đề)"}</b>
          </p>
        ) : (
          <p className={s.dialogIntro}>{M.unpublishIntro}</p>
        )}
        <Field
          as="select"
          label={label}
          required
          value={reason}
          error={reasonError}
          autoFocus
          options={options}
          onChange={(v) => {
            setReason(v);
            setReasonError(null);
          }}
        />
      </form>
    </Modal>
  );
}

/** Lịch sử các bản đã đăng; "Khôi phục" mở hộp xác nhận ở màn soạn bài. */
export function HistoryModal({ entryId, onRestore, onClose }: { entryId: number; onRestore: (version: number) => void; onClose: () => void }) {
  const [rows, setRows] = useState<ContentEntryVersionListItem[] | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setRows(null);
    setFailed(null);
    fetchEntryVersions(entryId)
      .then((r) => live && setRows(r || []))
      .catch((err) => live && setFailed(errorText(err, M.loadFailed)));
    return () => {
      live = false;
    };
  }, [entryId, attempt]);

  return (
    <Modal
      title={M.historyTitle}
      onClose={onClose}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          {M.close}
        </button>
      }
    >
      <div className={s.dialogBody}>
        <p className={s.dialogIntro}>{M.historyIntro}</p>
        {failed ? (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{failed}</span>
            <button type="button" className="btn" onClick={() => setAttempt((n) => n + 1)}>
              {M.retry}
            </button>
          </div>
        ) : rows === null ? (
          <p className={s.dialogNote} role="status">
            {M.historyLoading}
          </p>
        ) : rows.length === 0 ? (
          <p className={s.dialogNote}>{M.historyEmpty}</p>
        ) : (
          <ul className={s.historyList}>
            {rows.map((v) => (
              <li key={v.version} className={s.historyItem}>
                <div className={s.historyMain}>
                  <b>{M.historyVersion(v.version)}</b>
                  <span className={s.historyTitle}>{v.title || "(chưa có tiêu đề)"}</span>
                  <span className="muted">
                    {dateTimeFull(v.published_at)} · {M.historyBy(v.published_by_name || M.historySystem)}
                  </span>
                </div>
                <button type="button" className="btn" onClick={() => onRestore(v.version)}>
                  {M.historyRestore}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
