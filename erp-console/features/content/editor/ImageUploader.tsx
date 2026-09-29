"use client";

import React, { useRef, useState } from "react";
import type { ContentImage } from "../types";
import { uploadEntryImage } from "../api";
import { ApiError } from "@/shared/lib/http";
import s from "./ImageUploader.module.css";

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

  const handleTriggerUpload = () => {
    if (disabled || uploading) return;
    if (!entryId) {
      setError("Vui lòng lưu nháp bài viết trước khi tải ảnh.");
      return;
    }
    setError(null);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input để có thể chọn lại cùng file nếu muốn
    e.target.value = "";

    if (!entryId) {
      setError("Vui lòng lưu nháp bài viết trước khi tải ảnh.");
      return;
    }

    if (images.length >= 20) {
      setError("Bài viết đã có tối đa 20 ảnh (BR-ND-07).");
      return;
    }

    // Kiểm tra định dạng cơ bản trên client
    const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      setError("Định dạng ảnh không hợp lệ. Chỉ chấp nhận JPG, PNG, WebP (BR-DM-10).");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("Dung lượng ảnh vượt quá giới hạn 10MB (BR-DM-10).");
      return;
    }

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const alt = defaultAlt ? defaultAlt.trim().slice(0, 200) : undefined;
      const uploaded = await uploadEntryImage(entryId, file, alt, (pct) => {
        setProgress(pct);
      });
      onImageUploaded(uploaded);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Tải ảnh lỗi, thử lại");
      } else {
        setError("Tải ảnh lỗi, thử lại");
      }
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const handleEditAlt = async (img: ContentImage) => {
    const newAlt = window.prompt("Nhập mô tả ảnh (alt):", img.alt);
    if (newAlt === null) return;
    if (newAlt.length > 200) {
      alert("Mô tả ảnh tối đa 200 ký tự.");
      return;
    }
    try {
      await onUpdateAlt(img.id, newAlt);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Cập nhật mô tả ảnh thất bại.");
    }
  };

  const isMaxReached = images.length >= 20;

  return (
    <div className={s.container}>
      <div className={s.header}>
        <h3 className={s.title}>Ảnh trong bài</h3>
        <span className={s.count}>
          {images.length}/20 ảnh {isMaxReached && "(Đã đạt giới hạn)"}
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      <div className={s.uploadZone}>
        <button
          type="button"
          className={s.uploadBtn}
          onClick={handleTriggerUpload}
          disabled={disabled || uploading || isMaxReached}
        >
          {uploading ? "Đang tải ảnh lên..." : "📷 Tải ảnh từ máy / điện thoại"}
        </button>
        <p className={s.uploadHint}>Hỗ trợ camera, thư viện ảnh (JPEG, PNG, WebP tối đa 10MB)</p>

        {uploading && (
          <div className={s.progressContainer}>
            <div className={s.progressBar}>
              <div className={s.progressFill} style={{ width: `${progress}%` }} />
            </div>
            <div className={s.progressText}>Tiến trình tải lên: {progress}%</div>
          </div>
        )}
      </div>

      {error && <div className={s.errorMsg}>{error}</div>}

      {images.length > 0 && (
        <div className={s.imageList}>
          {images.map((img) => {
            const isCover = coverImageId === img.id;
            return (
              <div key={img.id} className={s.imageCard}>
                <div className={s.thumbWrapper}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.urls.sm || img.urls.md || img.urls.lg}
                    alt={img.alt || "Ảnh bài viết"}
                    className={s.thumb}
                    loading="lazy"
                  />
                  {isCover && <span className={s.coverBadge}>Ảnh bìa</span>}
                </div>
                <div className={s.cardBody}>
                  <p className={s.altText} title={img.alt}>
                    {img.alt || "(Chưa có mô tả alt)"}
                  </p>
                  <div className={s.cardActions}>
                    <button
                      type="button"
                      className={`${s.actionBtn} ${s.actionBtnPrimary}`}
                      onClick={() => onInsertToContent(img)}
                      disabled={disabled}
                      title="Chèn ảnh vào vị trí con trỏ trong bài viết"
                    >
                      Chèn vào bài
                    </button>
                    {!isCover && (
                      <button
                        type="button"
                        className={s.actionBtn}
                        onClick={() => onSetCover(img.id)}
                        disabled={disabled}
                      >
                        Đặt làm ảnh bìa
                      </button>
                    )}
                    <button
                      type="button"
                      className={s.actionBtn}
                      onClick={() => handleEditAlt(img)}
                      disabled={disabled}
                    >
                      Sửa alt
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
