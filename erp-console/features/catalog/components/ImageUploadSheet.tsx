"use client";

// Tấm tải/thay ảnh mặt hàng (A2). Một tệp, xem trước ngay bằng blob URL của tệp đã chọn (không gọi
// mạng trước khi bấm Lưu). Đủ trạng thái theo contract: thiếu tệp (báo tại chỗ, không gọi API),
// đang gửi (khoá nút, chặn bấm đúp — A2-AC17), rớt mạng (A2-AC12, nút "Thử lại" giữ nguyên tệp đã
// chọn), xung đột ghi đè (A2-AC13, nút "Tải lại"), lỗi BE khác hiện NGUYÊN VĂN `detail`.

import { useEffect, useId, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { Icon } from "@/shared/ui/Icon";
import { Sheet } from "@/shared/ui/Sheet";
import { uploadItemImage } from "../api";
import { CATALOG_MSG } from "../messages";
import type { CatalogItem, UploadImageResponse } from "../types";
import s from "../catalog.module.css";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_BYTES = 10 * 1024 * 1024; // ITEM_IMAGE_MAX_BYTES mặc định — kiểm phía máy cho phản hồi nhanh, BE vẫn kiểm lại

type Props = {
  item: CatalogItem;
  onClose: () => void;
  onUploaded: (item: CatalogItem, res: UploadImageResponse) => void;
  /** A2-AC13: 409 vì ảnh vừa bị người khác đổi — tải lại danh sách rồi đóng tấm này. */
  onConflictReload: () => void;
};

export function ImageUploadSheet({ item, onClose, onUploaded, onConflictReload }: Props) {
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
  const uid = useId();

  // Dọn blob URL khi đổi tệp / đóng tấm — tránh rò bộ nhớ.
  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const pickFile = () => inputRef.current?.click();

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
  const title = isNew ? `Tải ảnh — ${item.name}` : `Thay ảnh — ${item.name}`;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy) return; // A2-AC17: bấm hai lần không gửi hai lần
    if (!file) {
      setFileMissing(true);
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("Ảnh vượt 10 MB.");
      return;
    }
    setBusy(true);
    setError(null);
    setNetworkDrop(false);
    setConflict(false);
    try {
      const res = await uploadItemImage(item.id, {
        file,
        altText,
        isIllustration,
        expectedImageId: item.image?.id ?? "",
      });
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

  const altId = `${uid}-alt`;

  return (
    <Sheet title={title} onClose={onClose} busy={busy}>
      <form className="sheet-form" onSubmit={submit} noValidate>
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
            <button type="button" className="btn" onClick={pickFile} disabled={busy} data-autofocus>
              <Icon name="photo_camera" />
              {file ? CATALOG_MSG.changeFile : CATALOG_MSG.chooseFile}
            </button>
            <p className="help">{CATALOG_MSG.dropHint}</p>
            {file && <p className={s.fileName}>{file.name}</p>}
            {fileMissing && (
              <p className="field-err" role="alert">
                <Icon name="error" />
                Chọn một ảnh trước khi lưu.
              </p>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            aria-label={CATALOG_MSG.chooseFile}
            onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
        </div>

        <div className="field">
          <label htmlFor={altId}>Mô tả ảnh (alt text)</label>
          <input
            id={altId}
            value={altText}
            onChange={(e) => setAltText(e.target.value)}
            placeholder={item.name}
            maxLength={125}
            disabled={busy}
          />
          <span className="help">Để trống thì dùng tên mặt hàng.</span>
        </div>

        <label className="check-row">
          <input type="checkbox" checked={isIllustration} onChange={(e) => setIsIllustration(e.target.checked)} disabled={busy} />
          <span>
            <b>Ảnh minh hoạ</b>
            <small>Không phải ảnh Lộc tự chụp — Shop sẽ ghi rõ &quot;Ảnh minh hoạ&quot;.</small>
          </span>
        </label>

        <p className={s.privacy}>
          <Icon name="visibility_off" />
          {CATALOG_MSG.privacyReminder}
        </p>

        {networkDrop && (
          <div className="alert-box err" role="alert">
            <Icon name="wifi_off" />
            <span>{CATALOG_MSG.networkDrop}</span>
          </div>
        )}
        {conflict && (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>
              Ảnh vừa được người khác đổi, tải lại để xem.{" "}
              <button type="button" className="inline-link" onClick={onConflictReload}>
                Tải lại
              </button>
            </span>
          </div>
        )}
        {error && (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{error}</span>
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose} disabled={busy}>
            Huỷ
          </button>
          <button type="submit" className="btn primary" disabled={busy} aria-busy={busy || undefined}>
            {busy && <Icon name="progress_activity" className="spin" />}
            {busy ? "Đang gửi…" : networkDrop ? "Thử lại" : isNew ? "Tải ảnh lên" : "Lưu ảnh mới"}
          </button>
        </div>
      </form>
    </Sheet>
  );
}
