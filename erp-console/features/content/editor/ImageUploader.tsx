"use client";

// Ảnh trong bài (ED-35): tải ảnh lên (camera / thư viện), chèn vào bài, đặt ảnh bìa, sửa mô tả ảnh.
// Sửa mô tả dùng hộp thoại chung (không dùng prompt/alert của trình duyệt). Chỉ chữ tiếng Việt thường, không mã luật.

import React, { useId, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { uploadEntryImage } from "../api";
import { errorText } from "../contentModel";
import { CONTENT_MSG as M } from "../messages";
import type { ContentImage } from "../types";
import s from "./ImageUploader.module.css";

const MAX_IMAGES = 20;
const MAX_BYTES = 10 * 1024 * 1024;
const ALT_MAX = 200;

export interface ImageUploaderProps {
  entryId: number | null;
  images: ContentImage[];
  coverImageId: number | null;
  onImageUploaded: (image: ContentImage) => void;
  onSetCover: (imageId: number) => void;
  onInsertToContent: (image: ContentImage) => void;
  onUpdateAlt: (imageId: number, newAlt: string) => Promise<void>;
  defaultAlt?: string;
  disabled?: boolean;
}

function AltModal({ image, onSave, onClose }: { image: ContentImage; onSave: (alt: string) => Promise<void>; onClose: () => void }) {
  const formId = useId();
  const [alt, setAlt] = useState(image.alt);
  const sub = useSubmit(
    async () => {
      try {
        await onSave(alt.trim());
      } catch (err) {
        throw new Error(errorText(err, M.genericFail));
      }
    },
    { onSuccess: onClose },
  );
  return (
    <Modal
      title={M.imgAltTitle}
      onClose={onClose}
      busy={sub.submitting}
      size="sm"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.catCancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? M.catBusy : primaryLabel(M.imgAltSave, sub.failed)}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.altForm}
        onSubmit={(e) => {
          e.preventDefault();
          if (!sub.submitting) void sub.submit();
        }}
      >
        {sub.error && <FormAlert>{sub.error}</FormAlert>}
        <Field as="textarea" label={M.imgAltField} value={alt} onChange={setAlt} maxLength={ALT_MAX} counter rows={3} autoFocus />
      </form>
    </Modal>
  );
}

export default function ImageUploader({
  entryId,
  images,
  coverImageId,
  onImageUploaded,
  onSetCover,
  onInsertToContent,
  onUpdateAlt,
  defaultAlt = "",
  disabled = false,
}: ImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ContentImage | null>(null);

  const handleTriggerUpload = () => {
    if (disabled || uploading) return;
    if (!entryId) {
      setError(M.imgSaveFirst);
      return;
    }
    setError(null);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = ""; // cho phép chọn lại đúng file đó
    if (!entryId) {
      setError(M.imgSaveFirst);
      return;
    }
    if (images.length >= MAX_IMAGES) {
      setError("Bài đã có tối đa 20 ảnh. Xoá bớt ảnh trước khi tải thêm.");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Chỉ nhận ảnh JPG, PNG hoặc WebP.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("Ảnh nặng quá 10 MB. Chọn ảnh nhẹ hơn.");
      return;
    }
    setUploading(true);
    setProgress(0);
    setError(null);
    try {
      const alt = defaultAlt ? defaultAlt.trim().slice(0, ALT_MAX) : undefined;
      const uploaded = await uploadEntryImage(entryId, file, alt, (pct) => setProgress(pct));
      onImageUploaded(uploaded);
    } catch (err) {
      setError(err instanceof ApiError ? errorText(err, "Chưa tải được ảnh. Bấm thử lại.") : "Chưa tải được ảnh. Bấm thử lại.");
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const isMaxReached = images.length >= MAX_IMAGES;

  return (
    <section className={s.container} aria-label={M.imagesInPost}>
      <div className={s.header}>
        <h3 className={s.title}>{M.imagesInPost}</h3>
        <span className={s.count}>
          {images.length}/{MAX_IMAGES} ảnh {isMaxReached && "(đã đủ)"}
        </span>
      </div>

      <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={handleFileChange} />

      <div className={s.uploadZone}>
        <button type="button" className={`btn ${s.uploadBtn}`} onClick={handleTriggerUpload} disabled={disabled || uploading || isMaxReached} aria-busy={uploading || undefined}>
          <Icon name={uploading ? "progress_activity" : "photo_camera"} className={uploading ? "spin" : undefined} />
          <span>{uploading ? "Đang tải ảnh lên…" : M.imgUploadBtn}</span>
        </button>
        <p className={s.uploadHint}>{M.imgUploadHint} (JPG, PNG, WebP, tối đa 10 MB)</p>
        {uploading && (
          <div className={s.progressContainer} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Tiến độ tải ảnh">
            <div className={s.progressBar}>
              <div className={s.progressFill} style={{ width: `${progress}%` }} />
            </div>
            <div className={s.progressText}>{progress}%</div>
          </div>
        )}
      </div>

      {error && <FormAlert>{error}</FormAlert>}

      {images.length > 0 && (
        <ul className={s.imageList}>
          {images.map((img) => {
            const isCover = coverImageId === img.id;
            return (
              <li key={img.id} className={s.imageCard}>
                <div className={s.thumbWrapper}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img.urls.sm || img.urls.md || img.urls.lg} alt={img.alt || "Ảnh trong bài"} className={s.thumb} loading="lazy" />
                  {isCover && <span className={s.coverBadge}>{M.imgIsCover}</span>}
                </div>
                <div className={s.cardBody}>
                  <p className={img.alt ? s.altText : `${s.altText} ${s.altMissing}`} title={img.alt}>
                    {img.alt || M.imgAltMissing}
                  </p>
                  <div className={s.cardActions}>
                    <button type="button" className="btn" onClick={() => onInsertToContent(img)} disabled={disabled}>
                      {M.imgInsert}
                    </button>
                    {!isCover && (
                      <button type="button" className="btn" onClick={() => onSetCover(img.id)} disabled={disabled}>
                        {M.imgSetCover}
                      </button>
                    )}
                    <button type="button" className="btn" onClick={() => setEditing(img)} disabled={disabled}>
                      {M.imgEditAlt}
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {editing && <AltModal image={editing} onSave={(alt) => onUpdateAlt(editing.id, alt)} onClose={() => setEditing(null)} />}
    </section>
  );
}
