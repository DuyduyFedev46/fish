"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import {
  createEntry,
  deleteEntry,
  fetchCategories,
  getEntry,
  updateEntry,
  updateImageAlt,
} from "@/features/content/api";
import ImageUploader from "@/features/content/editor/ImageUploader";
import type { TiptapEditorHandle } from "@/features/content/editor/TiptapEditor";
import type {
  BodyDoc,
  ContentCategory,
  ContentImage,
  ContentKind,
  ContentStatus,
} from "@/features/content/types";
import { ApiError } from "@/shared/lib/http";
import s from "./edit.module.css";

// Dynamic import TiptapEditor để tránh SSR hydration mismatch trong Next.js static export
const TiptapEditor = dynamic(
  () => import("@/features/content/editor/TiptapEditor"),
  { ssr: false }
);

function ContentEditScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editorRef = useRef<TiptapEditorHandle>(null);

  const queryId = searchParams.get("id");
  const queryNew = searchParams.get("new");

  const [entryId, setEntryId] = useState<number | null>(
    queryId ? parseInt(queryId, 10) : null
  );
  const [kind, setKind] = useState<ContentKind>(
    queryNew === "page" ? "page" : "post"
  );
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [category, setCategory] = useState<number | null>(null);
  const [excerpt, setExcerpt] = useState("");
  const [seoTitle, setSeoTitle] = useState("");
  const [seoDescription, setSeoDescription] = useState("");
  const [coverImageId, setCoverImageId] = useState<number | null>(null);
  const [body, setBody] = useState<BodyDoc>({ type: "doc", blocks: [] });
  const [images, setImages] = useState<ContentImage[]>([]);

  const [rowVersion, setRowVersion] = useState(1);
  const [status, setStatus] = useState<ContentStatus>("draft");
  const [publishedVersion, setPublishedVersion] = useState<number | null>(null);
  const [firstPublishedAt, setFirstPublishedAt] = useState<string | null>(null);

  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [slugSuggestion, setSlugSuggestion] = useState<string | null>(null);

  // Tải danh mục
  useEffect(() => {
    let active = true;
    fetchCategories()
      .then((cats) => {
        if (active) setCategories(cats.filter((c) => c.is_active));
      })
      .catch((err) => {
        console.error("Lỗi tải danh mục:", err);
      });
    return () => {
      active = false;
    };
  }, []);

  // Tải chi tiết bài viết nếu có id
  useEffect(() => {
    if (!entryId) {
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getEntry(entryId)
      .then((data) => {
        if (!active) return;
        setKind(data.kind);
        setTitle(data.title || "");
        setSlug(data.slug || "");
        setCategory(data.category);
        setExcerpt(data.excerpt || "");
        setSeoTitle(data.seo_title || "");
        setSeoDescription(data.seo_description || "");
        setCoverImageId(data.cover_image);
        setBody(data.body || { type: "doc", blocks: [] });
        setImages(data.images || []);
        setRowVersion(data.row_version);
        setStatus(data.status);
        setPublishedVersion(data.published_version);
        setFirstPublishedAt(data.first_published_at);
      })
      .catch((err) => {
        if (active) {
          setErrorMsg(err instanceof Error ? err.message : "Lỗi nạp bài viết.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [entryId]);

  // Lưu nháp (CMS-03)
  const handleSaveDraft = async () => {
    setSaving(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    setSlugSuggestion(null);

    try {
      if (!entryId) {
        // Tạo mới
        const res = await createEntry({
          kind,
          title: title.trim(),
          slug: slug.trim(),
          category: kind === "post" ? category : null,
          excerpt: excerpt.trim(),
          seo_title: seoTitle.trim(),
          seo_description: seoDescription.trim(),
          cover_image: coverImageId,
          body,
        });
        setEntryId(res.id);
        setSlug(res.slug);
        setRowVersion(res.row_version);
        setStatus(res.status);
        setPublishedVersion(res.published_version);
        setFirstPublishedAt(res.first_published_at);
        setImages(res.images || []);
        setSuccessMsg("Đã tạo và lưu nháp thành công!");
        window.history.replaceState(null, "", `/content/edit/?id=${res.id}`);
      } else {
        // Cập nhật nháp
        const res = await updateEntry(entryId, {
          row_version: rowVersion,
          kind,
          title: title.trim(),
          slug: slug.trim(),
          category: kind === "post" ? category : null,
          excerpt: excerpt.trim(),
          seo_title: seoTitle.trim(),
          seo_description: seoDescription.trim(),
          cover_image: coverImageId,
          body,
        });
        setSlug(res.slug);
        setRowVersion(res.row_version);
        setStatus(res.status);
        setPublishedVersion(res.published_version);
        setFirstPublishedAt(res.first_published_at);
        setImages(res.images || []);
        setSuccessMsg("Đã lưu nháp thành công!");
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        // CMS-03-AC7: Xung đột sửa trùng (409 STALE_VERSION)
        if (err.status === 409 && err.code === "STALE_VERSION") {
          setErrorMsg(
            "Bài đã được người khác sửa. Tải lại để xem bản mới (nội dung bạn đang gõ không bị mất)."
          );
        } else if (err.code === "BR-ND-04") {
          // Trùng slug (CMS-03-AC3)
          setErrorMsg(err.message || "Đường dẫn (slug) bị trùng.");
          if (err.message && err.message.includes("Gợi ý:")) {
            const match = err.message.match(/Gợi ý:\s*([\w-]+)/);
            if (match && match[1]) setSlugSuggestion(match[1]);
          }
        } else {
          setErrorMsg(err.message || "Lỗi lưu nháp.");
        }
      } else {
        setErrorMsg("Lỗi kết nối khi lưu nháp. Vui lòng thử lại.");
      }
    } finally {
      setSaving(false);
    }
  };

  // Xoá nháp (CMS-03-AC8, CMS-03-AC9: chỉ nháp chưa từng đăng)
  const canDelete =
    entryId !== null &&
    publishedVersion === null &&
    firstPublishedAt === null;

  const handleDeleteDraft = async () => {
    if (!entryId || !canDelete) return;
    const ok = window.confirm(
      "Bạn có chắc chắn muốn xoá nháp bài viết này không? Hành động này không thể hoàn tác."
    );
    if (!ok) return;

    setDeleting(true);
    setErrorMsg(null);
    try {
      await deleteEntry(entryId);
      router.push("/content/");
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || "Không thể xoá bài viết.");
      } else {
        setErrorMsg("Lỗi khi xoá bài viết.");
      }
      setDeleting(false);
    }
  };

  // Tải lại bài khi bị conflict 409
  const handleReloadLatest = async () => {
    if (!entryId) return;
    if (
      !window.confirm(
        "Tải lại sẽ thay thế nội dung đang sửa bằng bản mới nhất trên máy chủ. Bạn có muốn tiếp tục?"
      )
    ) {
      return;
    }
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await getEntry(entryId);
      setTitle(data.title || "");
      setSlug(data.slug || "");
      setCategory(data.category);
      setExcerpt(data.excerpt || "");
      setSeoTitle(data.seo_title || "");
      setSeoDescription(data.seo_description || "");
      setCoverImageId(data.cover_image);
      setBody(data.body || { type: "doc", blocks: [] });
      setImages(data.images || []);
      setRowVersion(data.row_version);
      setStatus(data.status);
      setPublishedVersion(data.published_version);
      setFirstPublishedAt(data.first_published_at);
      setSuccessMsg("Đã tải lại bản mới nhất từ máy chủ.");
    } catch (err: any) {
      setErrorMsg(err.message || "Lỗi khi tải lại bản mới.");
    } finally {
      setLoading(false);
    }
  };

  // Thao tác với ảnh
  const handleImageUploaded = (newImg: ContentImage) => {
    setImages((prev) => [...prev, newImg]);
    // Nếu chưa có ảnh bìa, tự động đặt ảnh đầu tiên làm bìa
    if (coverImageId === null) {
      setCoverImageId(newImg.id);
    }
    setSuccessMsg(`Đã tải ảnh lên thành công (#${newImg.id}).`);
  };

  const handleSetCover = (imgId: number) => {
    setCoverImageId(imgId);
    setSuccessMsg(`Đã chọn ảnh #${imgId} làm ảnh bìa.`);
  };

  const handleInsertToContent = (img: ContentImage) => {
    if (editorRef.current) {
      editorRef.current.insertImage({
        id: img.id,
        alt: img.alt || "",
        url: img.urls.md || img.urls.sm || img.urls.lg,
      });
      setSuccessMsg(`Đã chèn ảnh #${img.id} vào bài viết.`);
    }
  };

  const handleUpdateAlt = async (imgId: number, newAlt: string) => {
    const updated = await updateImageAlt(imgId, newAlt);
    setImages((prev) =>
      prev.map((item) => (item.id === imgId ? { ...item, alt: updated.alt } : item))
    );
    setSuccessMsg(`Đã cập nhật mô tả alt cho ảnh #${imgId}.`);
  };

  if (loading) {
    return (
      <div className={s.container}>
        <div style={{ padding: "40px 0", textAlign: "center", color: "#64748b" }}>
          Đang nạp bài viết...
        </div>
      </div>
    );
  }

  return (
    <div className={s.container}>
      {/* Top Bar: Điều hướng + Hành động chính */}
      <div className={s.topBar}>
        <Link href="/content/" className={s.backBtn}>
          ← Quay lại danh sách
        </Link>
        <div className={s.actionsGroup}>
          {canDelete && (
            <button
              type="button"
              className={s.deleteBtn}
              onClick={handleDeleteDraft}
              disabled={saving || deleting}
            >
              {deleting ? "Đang xoá..." : "Xoá nháp"}
            </button>
          )}
          <button
            type="button"
            className={s.saveBtn}
            onClick={handleSaveDraft}
            disabled={saving || deleting}
          >
            {saving ? "Đang lưu..." : "Lưu nháp"}
          </button>
        </div>
      </div>

      {/* Thông báo lỗi / thành công */}
      {errorMsg && (
        <div className={`${s.alertBox} ${s.alertError}`}>
          <div>{errorMsg}</div>
          {errorMsg.includes("STALE_VERSION") ||
          errorMsg.includes("người khác sửa") ? (
            <div style={{ marginTop: "8px" }}>
              <button
                type="button"
                className={s.suggestionBtn}
                onClick={handleReloadLatest}
                style={{ fontWeight: 600 }}
              >
                Tải bản mới nhất từ máy chủ
              </button>
            </div>
          ) : null}
        </div>
      )}

      {successMsg && (
        <div className={`${s.alertBox} ${s.alertSuccess}`}>{successMsg}</div>
      )}

      {/* Layout 2 cột: Cột soạn bài và Cột thông tin phụ / Ảnh */}
      <div className={s.mainLayout}>
        {/* Cột trái: Soạn nội dung chính */}
        <div className={s.editorColumn}>
          <div className={s.card}>
            <div className={s.formGroup}>
              <label className={s.label}>Tiêu đề bài viết / trang</label>
              <input
                type="text"
                className={s.input}
                placeholder="Nhập tiêu đề (tối đa 200 ký tự)..."
                value={title}
                maxLength={200}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>Đường dẫn (slug)</label>
              <input
                type="text"
                className={s.input}
                placeholder="vd: cach-ra-dong-ca-thu (để trống sẽ tự sinh từ tiêu đề)"
                value={slug}
                onChange={(e) => {
                  setSlug(e.target.value);
                  setSlugSuggestion(null);
                }}
              />
              {slugSuggestion && (
                <p className={s.hint}>
                  Gợi ý đường dẫn trống:{" "}
                  <button
                    type="button"
                    className={s.suggestionBtn}
                    onClick={() => {
                      setSlug(slugSuggestion);
                      setSlugSuggestion(null);
                    }}
                  >
                    {slugSuggestion}
                  </button>
                </p>
              )}
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>Nội dung bài viết</label>
              <TiptapEditor
                ref={editorRef}
                value={body}
                onChange={(newBody) => setBody(newBody)}
              />
            </div>
          </div>
        </div>

        {/* Cột phải: Thuộc tính bài viết & Ảnh */}
        <div className={s.sidebarColumn}>
          <div className={s.card}>
            <h3 className={s.cardTitle}>Thông tin xuất bản</h3>

            <div className={s.formGroup}>
              <label className={s.label}>Loại nội dung</label>
              <select
                className={s.select}
                value={kind}
                onChange={(e) => setKind(e.target.value as ContentKind)}
                disabled={entryId !== null}
              >
                <option value="post">Bài viết tin tức / công thức</option>
                <option value="page">Trang tĩnh / chính sách</option>
              </select>
            </div>

            {kind === "post" && (
              <div className={s.formGroup}>
                <label className={s.label}>Chuyên mục</label>
                <select
                  className={s.select}
                  value={category ?? ""}
                  onChange={(e) => {
                    const val = e.target.value;
                    setCategory(val ? parseInt(val, 10) : null);
                  }}
                >
                  <option value="">-- Chọn chuyên mục --</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className={s.formGroup}>
              <label className={s.label}>Trạng thái</label>
              <div>
                <span
                  className={`${s.badge} ${
                    status === "published" ? s.badgePublished : s.badgeDraft
                  }`}
                >
                  {status === "draft"
                    ? "Bản nháp"
                    : status === "published"
                    ? "Đã đăng"
                    : status}
                </span>
                {rowVersion > 1 && (
                  <span className="muted" style={{ marginLeft: "8px", fontSize: "12px" }}>
                    (Phiên bản sửa: #{rowVersion})
                  </span>
                )}
              </div>
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>Tóm tắt (excerpt)</label>
              <textarea
                className={s.textarea}
                placeholder="Đoạn văn ngắn tóm tắt bài viết..."
                value={excerpt}
                maxLength={500}
                onChange={(e) => setExcerpt(e.target.value)}
              />
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>SEO Title</label>
              <input
                type="text"
                className={s.input}
                placeholder="Tiêu đề hiển thị trên Google..."
                value={seoTitle}
                maxLength={200}
                onChange={(e) => setSeoTitle(e.target.value)}
              />
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>SEO Description</label>
              <textarea
                className={s.textarea}
                placeholder="Mô tả SEO hiển thị trên Google..."
                value={seoDescription}
                maxLength={300}
                onChange={(e) => setSeoDescription(e.target.value)}
              />
            </div>
          </div>

          {/* Quản lý ảnh (CMS-05) */}
          <ImageUploader
            entryId={entryId}
            images={images}
            coverImageId={coverImageId}
            onImageUploaded={handleImageUploaded}
            onSetCover={handleSetCover}
            onInsertToContent={handleInsertToContent}
            onUpdateAlt={handleUpdateAlt}
            defaultAlt={title}
            disabled={saving || deleting}
          />
        </div>
      </div>
    </div>
  );
}

export default function ContentEditPage() {
  return (
    <ViewGuard view="content">
      <Suspense
        fallback={
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            Đang chuẩn bị trình soạn thảo...
          </div>
        }
      >
        <ContentEditScreen />
      </Suspense>
    </ViewGuard>
  );
}
