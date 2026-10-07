"use client";

// Hộp tải/thay ảnh mặt hàng (A2, nay là Modal chung). Một tệp, xem trước ngay bằng blob URL của tệp đã chọn (không gọi mạng
// trước khi bấm Lưu). Đủ trạng thái theo contract: thiếu tệp (báo tại chỗ, không gọi API), đang gửi (khoá nút, chặn bấm đúp,
// A2-AC17), rớt mạng (A2-AC12, nút "Thử lại" giữ nguyên tệp đã chọn), xung đột ghi đè (A2-AC13, nút "Tải lại"), lỗi BE khác
// hiện NGUYÊN VĂN `detail`. Tệp và mô tả chỉ nằm trong state của hộp (không storage, không URL, không log).

import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { uploadItemImage } from "../api";
import { CATALOG_MSG as M } from "../messages";
import type { CatalogItem, UploadImageResponse } from "../types";
import s from "../catalog.module.css";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 10 * 1024 * 1024; // ITEM_IMAGE_MAX_BYTES mặc định — kiểm phía máy cho phản hồi nhanh, BE vẫn kiểm lại

type Props = {
  item: CatalogItem;
  onClose: () => void;
  onUploaded: (item: CatalogItem, res: UploadImageResponse) => void;
  /** A2-AC13: 409 vì ảnh vừa bị người khác đổi — tải lại rồi đóng hộp này. */
  onConflictReload: () => void;
};

export function ImageUploadModal({ item, onClose, onUploaded, onConflictReload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [altText, setAltText] = useState("");
  const [isIllustration, setIsIllustration] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [networkDrop, setNetworkDrop] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [fileMissing, setFileMissing] = useState(false);
  /** Tệp chọn không phải ảnh giải mã được (vd .txt đổi đuôi .jpg) — trình duyệt không vẽ được xem trước. */
  const [previewBroken, setPreviewBroken] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const formId = useId();

  // Dọn blob URL khi đổi tệp / đóng hộp — tránh rò bộ nhớ.
  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl],
  );

  const onFileChange = (f: File | null) => {
    setPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return f ? URL.createObjectURL(f) : null;
    });
    setFile(f);
    setFileMissing(false);
    setPreviewBroken(false);
    setError(null);
    setNetworkDrop(false);
    setConflict(false);
  };

  const isNew = !item.image;
  const title = isNew ? M.imageModalTitleNew(item.name) : M.imageModalTitleReplace(item.name);

  const submit = async () => {
    if (busy) return; // A2-AC17: bấm hai lần không gửi hai lần
    if (!file) {
      setFileMissing(true);
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(M.imageTooBig);
      return;
    }
    setBusy(true);
    setError(null);
    setNetworkDrop(false);
    setConflict(false);
    try {
      const res = await uploadItemImage(item.id, { file, altText, isIllustration, expectedImageId: item.image?.id ?? "" });
      onUploaded(item, res);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setNetworkDrop(true); // mất mạng giữa chừng — ảnh cũ vẫn giữ nguyên phía máy chủ
      } else if (err instanceof ApiError && err.status === 409) {
        setConflict(true);
      } else {
        setError(errorText(err));
      }
    } finally {
      setBusy(false);
    }
  };

  const failed = networkDrop || error !== null;

  return (
    <Modal
      title={title}
      onClose={onClose}
      busy={busy}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            {M.cancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={busy} aria-busy={busy || undefined}>
            {busy ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.busy}</span>
              </>
            ) : failed ? (
              M.retry
            ) : isNew ? (
              M.submitUploadNew
            ) : (
              M.submitUploadReplace
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {networkDrop && <FormAlert>{M.networkDrop}</FormAlert>}
        {conflict && (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{M.imageConflict}</span>
            <button type="button" className="btn" onClick={onConflictReload}>
              {M.reload}
            </button>
          </div>
        )}
        {error && <FormAlert>{error}</FormAlert>}

        <div className={s.previewRow}>
          <span className={s.previewBox}>
            {previewUrl && !previewBroken ? (
              <img src={previewUrl} alt="" onError={() => setPreviewBroken(true)} />
            ) : previewUrl && previewBroken ? (
              <Icon name="broken_image" />
            ) : item.image ? (
              <img src={item.image.urls.card} alt="" />
            ) : (
              <Icon name="add_photo_alternate" />
            )}
          </span>
          <div className={s.previewActions}>
            <button type="button" className="btn" onClick={() => inputRef.current?.click()} disabled={busy} data-autofocus>
              <Icon name="photo_camera" />
              <span>{file ? M.changeFile : M.chooseFile}</span>
            </button>
            <p className="muted">{M.dropHint}</p>
            {file && <p className={s.fileName}>{file.name}</p>}
            {fileMissing && (
              <p className="field-err" role="alert">
                <Icon name="error" />
                {M.imageMissing}
              </p>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            aria-label={M.chooseFile}
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
        </div>

        <Field label={M.fieldAltText} name="alt_text" value={altText} onChange={setAltText} maxLength={125} placeholder={item.name} disabled={busy} />

        <label className="check-row">
          <input type="checkbox" checked={isIllustration} onChange={(e) => setIsIllustration(e.target.checked)} disabled={busy} />
          <span>
            <b>{M.fieldIllustration}</b>
            <small>{M.illustrationNote}</small>
          </span>
        </label>

        <p className={s.privacy}>
          <Icon name="visibility_off" />
          {M.privacyReminder}
        </p>
      </form>
    </Modal>
  );
}
