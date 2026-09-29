"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import {
  createEntry,
  deleteEntry,
  discardChanges,
  fetchCategories,
  getEntry,
  publishEntry,
  unpublishEntry,
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
  ContentWarning,
  UnpublishReason,
} from "@/features/content/types";
import { ApiError } from "@/shared/lib/http";
import s from "./edit.module.css";

const UNPUBLISH_REASON_OPTIONS: Array<{ key: UnpublishReason; label: string }> = [
  { key: "wrong_price", label: "Giá chưa đúng" },
  { key: "complaint", label: "Khiếu nại / rủi ro pháp lý" },
  { key: "out_of_season", label: "Hết mùa vụ" },
  { key: "wrong_content", label: "Nội dung chưa chuẩn" },
  { key: "other", label: "Khác" },
];

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
  const [publicUrl, setPublicUrl] = useState<string | null>(null);
  const [hasUnpublishedChanges, setHasUnpublishedChanges] = useState(false);
  const [pageRole, setPageRole] = useState<string | null>(null);

  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [unpublishing, setUnpublishing] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [slugSuggestion, setSlugSuggestion] = useState<string | null>(null);

  // Modal Checklist & Cảnh báo (CMS-07, CMS-08, BR-ND-13)
  const [showChecklistModal, setShowChecklistModal] = useState(false);
  const [checklist, setChecklist] = useState<[boolean, boolean, boolean, boolean, boolean]>([
    false,
    false,
    false,
    false,
    false,
  ]);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [warningsList, setWarningsList] = useState<ContentWarning[]>([]);

  // Modal Gỡ bài (CMS-12)
  const [showUnpublishModal, setShowUnpublishModal] = useState(false);
  const [unpublishReason, setUnpublishReason] = useState<UnpublishReason>("wrong_price");

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
        setHasUnpublishedChanges(Boolean(data.has_unpublished_changes));
        setPageRole(data.page_role || null);
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
        setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
        setPageRole(res.page_role || null);
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
        setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
        setPageRole(res.page_role || null);
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

  // Mở modal tự kiểm trước khi đăng (CMS-07, BR-ND-13)
  const handleOpenPublishModal = () => {
    if (!entryId) {
      setErrorMsg("Vui lòng bấm 'Lưu nháp' bài viết trước khi thực hiện đăng.");
      return;
    }
    setChecklist([false, false, false, false, false]);
    setShowChecklistModal(true);
  };

  const handleChecklistChange = (index: number) => {
    setChecklist((prev) => {
      const next = [...prev] as [boolean, boolean, boolean, boolean, boolean];
      next[index] = !next[index];
      return next;
    });
  };

  // Xác nhận đăng bài (CMS-07, CMS-08)
  const handleConfirmPublish = async (acknowledgeWarnings = false) => {
    if (!entryId) return;

    setPublishing(true);
    setErrorMsg(null);
    try {
      const res = await publishEntry(entryId, {
        row_version: rowVersion,
        checklist_confirmed: true,
        acknowledge_warnings: acknowledgeWarnings,
      });

      setStatus(res.status);
      setRowVersion(res.row_version);
      setPublishedVersion(res.version);
      setPublicUrl(res.public_url);
      setHasUnpublishedChanges(false);
      setShowChecklistModal(false);
      setShowWarningModal(false);
      setSuccessMsg(`Đã đăng bài viết thành công (phiên bản ${res.version}).`);
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 409 && err.code === "CONTENT_WARNINGS") {
          // CMS-08: Phát hiện cảnh báo SĐT/giá vốn
          setShowChecklistModal(false);
          const warnings = (err as any).warnings || [];
          setWarningsList(warnings);
          setShowWarningModal(true);
        } else if (err.status === 409 && err.code === "STALE_VERSION") {
          setShowChecklistModal(false);
          setShowWarningModal(false);
          setErrorMsg("Bài đã được người khác sửa. Vui lòng tải lại trang.");
        } else if (err.code === "BR-ND-03") {
          setShowChecklistModal(false);
          setShowWarningModal(false);
          const missing = (err as any).missing || [];
          setErrorMsg(`Bài viết chưa đủ điều kiện xuất bản (BR-ND-03): thiếu ${missing.join(", ")}`);
        } else {
          setShowChecklistModal(false);
          setErrorMsg(err.message || "Lỗi khi đăng bài.");
        }
      } else {
        setShowChecklistModal(false);
        setErrorMsg("Lỗi kết nối khi đăng bài. Vui lòng thử lại.");
      }
    } finally {
      setPublishing(false);
    }
  };

  // Gỡ bài viết (CMS-12)
  const handleOpenUnpublishModal = () => {
    if (pageRole) {
      setErrorMsg(
        `Trang này đang giữ vai trò '${pageRole}'. Không được gỡ trang go-live trực tiếp (BR-ND-16).`
      );
      return;
    }
    setShowUnpublishModal(true);
  };

  const handleConfirmUnpublish = async () => {
    if (!entryId) return;
    setUnpublishing(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await unpublishEntry(entryId, {
        row_version: rowVersion,
        reason: unpublishReason,
      });
      setStatus(res.status);
      setRowVersion(res.row_version);
      setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
      setPageRole(res.page_role || null);
      setShowUnpublishModal(false);
      setSuccessMsg("Đã gỡ bài viết khỏi website (trạng thái: Đã gỡ).");
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 409 && err.code === "STALE_VERSION") {
          setErrorMsg("Bài đã được người khác sửa. Vui lòng tải lại trang.");
        } else if (err.code === "BR-ND-16") {
          setErrorMsg(err.message || "Không thể gỡ trang go-live (BR-ND-16).");
        } else {
          setErrorMsg(err.message || "Lỗi khi gỡ bài.");
        }
      } else {
        setErrorMsg("Lỗi kết nối khi gỡ bài.");
      }
    } finally {
      setUnpublishing(false);
    }
  };

  // Huỷ thay đổi nháp quay lại bản đang đăng (CMS-10)
  const handleDiscardChanges = async () => {
    if (!entryId) return;
    if (
      !window.confirm(
        "Bạn có chắc muốn huỷ toàn bộ thay đổi nháp và quay lại bản đang hiển thị trên web? Thao tác này không thể hoàn tác."
      )
    ) {
      return;
    }
    setDiscarding(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await discardChanges(entryId, {
        row_version: rowVersion,
      });
      setTitle(res.title || "");
      setSlug(res.slug || "");
      setCategory(res.category);
      setExcerpt(res.excerpt || "");
      setSeoTitle(res.seo_title || "");
      setSeoDescription(res.seo_description || "");
      setCoverImageId(res.cover_image);
      setBody(res.body || { type: "doc", blocks: [] });
      setImages(res.images || []);
      setRowVersion(res.row_version);
      setStatus(res.status);
      setPublishedVersion(res.published_version);
      setFirstPublishedAt(res.first_published_at);
      setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
      setPageRole(res.page_role || null);
      setSuccessMsg("Đã huỷ các thay đổi nháp, quay lại bản đang hiển thị trên web.");
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 409 && err.code === "STALE_VERSION") {
          setErrorMsg("Bài đã được người khác sửa. Vui lòng tải lại trang.");
        } else {
          setErrorMsg(err.message || "Lỗi khi huỷ thay đổi nháp.");
        }
      } else {
        setErrorMsg("Lỗi kết nối khi huỷ thay đổi.");
      }
    } finally {
      setDiscarding(false);
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
      setHasUnpublishedChanges(Boolean(data.has_unpublished_changes));
      setPageRole(data.page_role || null);
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
              disabled={saving || deleting || publishing || unpublishing || discarding}
            >
              {deleting ? "Đang xoá..." : "Xoá nháp"}
            </button>
          )}
          <button
            type="button"
            className={s.saveBtn}
            onClick={handleSaveDraft}
            disabled={saving || deleting || publishing || unpublishing || discarding}
          >
            {saving ? "Đang lưu..." : "Lưu nháp"}
          </button>
          {status === "published" && (
            <button
              type="button"
              className={s.unpublishBtn}
              onClick={handleOpenUnpublishModal}
              disabled={saving || deleting || publishing || unpublishing || discarding}
            >
              {unpublishing ? "Đang gỡ..." : "Gỡ bài"}
            </button>
          )}
          <button
            type="button"
            className={s.publishBtn}
            onClick={handleOpenPublishModal}
            disabled={saving || deleting || publishing || unpublishing || discarding}
          >
            {publishing ? "Đang đăng..." : "Đăng bài"}
          </button>
        </div>
      </div>

      {/* Banner cảnh báo bản nháp có thay đổi chưa đăng (CMS-10) */}
      {status === "published" && hasUnpublishedChanges && (
        <div className={s.bannerDiscard}>
          <div>
            ⚠️ <strong>Bản nháp có thay đổi chưa đăng:</strong> Bài viết đã đăng đang có thay đổi nháp chưa cập nhật lên web.
          </div>
          <button
            type="button"
            className={s.discardBtn}
            onClick={handleDiscardChanges}
            disabled={saving || deleting || publishing || unpublishing || discarding}
          >
            {discarding ? "Đang huỷ..." : "Huỷ thay đổi"}
          </button>
        </div>
      )}

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
            disabled={saving || deleting || publishing}
          />
        </div>
      </div>

      {/* Modal 5 mục tự kiểm trước khi đăng (CMS-07, BR-ND-13) */}
      {showChecklistModal && (
        <div className={s.modalBackdrop}>
          <div className={s.modalDialog}>
            <h3 className={s.modalTitle}>Danh sách tự kiểm trước khi đăng bài</h3>
            <p className={s.modalDesc}>
              Vui lòng xác nhận 5 tiêu chí bắt buộc dưới đây để đảm bảo chất lượng và an toàn thông tin:
            </p>

            <div className={s.checklistGroup}>
              <label className={s.checklistItem}>
                <input
                  type="checkbox"
                  checked={checklist[0]}
                  onChange={() => handleChecklistChange(0)}
                />
                <span>1. Đã kiểm tra tính chính xác và không có lỗi chính tả trong nội dung bài viết.</span>
              </label>

              <label className={s.checklistItem}>
                <input
                  type="checkbox"
                  checked={checklist[1]}
                  onChange={() => handleChecklistChange(1)}
                />
                <span>2. Không chứa thông tin giá vốn, giá mua cảng, hay lãi gộp nội bộ (Bất biến 1).</span>
              </label>

              <label className={s.checklistItem}>
                <input
                  type="checkbox"
                  checked={checklist[2]}
                  onChange={() => handleChecklistChange(2)}
                />
                <span>3. Không để lộ số điện thoại cá nhân (chỉ dùng hotline chung của vựa).</span>
              </label>

              <label className={s.checklistItem}>
                <input
                  type="checkbox"
                  checked={checklist[3]}
                  onChange={() => handleChecklistChange(3)}
                />
                <span>4. Ảnh bìa và ảnh trong bài rõ nét, đúng tỉ lệ và có mô tả alt phù hợp.</span>
              </label>

              <label className={s.checklistItem}>
                <input
                  type="checkbox"
                  checked={checklist[4]}
                  onChange={() => handleChecklistChange(4)}
                />
                <span>5. Thẻ mặt hàng đính kèm (nếu có) đang sẵn hàng và đúng quy cách.</span>
              </label>
            </div>

            <div className={s.modalActions}>
              <button
                type="button"
                className={s.cancelBtn}
                onClick={() => setShowChecklistModal(false)}
                disabled={publishing}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className={s.confirmPublishBtn}
                onClick={() => handleConfirmPublish(false)}
                disabled={!checklist.every(Boolean) || publishing}
              >
                {publishing ? "Đang xuất bản..." : "Xác nhận đăng bài"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Cảnh báo an toàn nội dung (CMS-08, CONTENT_WARNINGS 409) */}
      {showWarningModal && (
        <div className={s.modalBackdrop}>
          <div className={s.modalDialog}>
            <h3 className={s.modalTitle} style={{ color: "#b45309" }}>
              Cảnh báo an toàn nội dung
            </h3>
            <p className={s.modalDesc}>
              Hệ thống phát hiện một số thông tin cần lưu ý trước khi đưa bài lên website công khai:
            </p>

            <div className={s.warningBox}>
              {warningsList.map((w, idx) => (
                <div key={idx} className={s.warningItem}>
                  {w.type === "phone_like" && (
                    <span>
                      ⚠️ <strong>Số giống SĐT:</strong> {w.snippet || "Phát hiện số điện thoại"} ({w.field})
                    </span>
                  )}
                  {w.type === "cost_keyword" && (
                    <span>
                      ⚠️ <strong>Từ khóa giá vốn/nhạy cảm:</strong> {w.snippet || "Phát hiện từ khóa giá vốn"} ({w.field})
                    </span>
                  )}
                  {w.type === "item_unavailable" && (
                    <span>
                      ⚠️ <strong>Mặt hàng hết/ngừng bán:</strong> Mã <code>{w.item_code}</code> không khả dụng.
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div className={s.modalActions}>
              <button
                type="button"
                className={s.cancelBtn}
                onClick={() => setShowWarningModal(false)}
                disabled={publishing}
              >
                Quay lại sửa
              </button>
              <button
                type="button"
                className={s.forcePublishBtn}
                onClick={() => handleConfirmPublish(true)}
                disabled={publishing}
              >
                {publishing ? "Đang xuất bản..." : "Tôi đã kiểm tra, vẫn đăng"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Chọn lý do gỡ bài (CMS-12) */}
      {showUnpublishModal && (
        <div className={s.modalBackdrop}>
          <div className={s.modalDialog}>
            <h3 className={s.modalTitle} style={{ color: "#dc2626" }}>
              Gỡ bài viết khỏi website
            </h3>
            <p className={s.modalDesc}>
              Sau khi gỡ, bài viết sẽ không còn hiển thị công khai trên Shop web (khách xem bài sẽ thấy thông báo bài đã gỡ). Vui lòng chọn lý do gỡ bài:
            </p>

            <div className={s.formGroup} style={{ marginTop: "12px", marginBottom: "16px" }}>
              <label className={s.label}>Lý do gỡ</label>
              <select
                className={s.select}
                value={unpublishReason}
                onChange={(e) => setUnpublishReason(e.target.value as UnpublishReason)}
              >
                {UNPUBLISH_REASON_OPTIONS.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className={s.modalActions}>
              <button
                type="button"
                className={s.cancelBtn}
                onClick={() => setShowUnpublishModal(false)}
                disabled={unpublishing}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className={s.unpublishBtn}
                style={{ backgroundColor: "#dc2626", color: "#ffffff", borderColor: "#dc2626" }}
                onClick={handleConfirmUnpublish}
                disabled={unpublishing}
              >
                {unpublishing ? "Đang gỡ bài..." : "Xác nhận gỡ bài"}
              </button>
            </div>
          </div>
        </div>
      )}
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
