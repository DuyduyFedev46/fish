"use client";

import React, { Suspense, useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { dateTimeFull, timeHM } from "@/shared/lib/format";
import { ROLE } from "@/shared/lib/roles";
import {
  createEntry,
  deleteEntry,
  discardChanges,
  fetchCategories,
  fetchEntryVersions,
  getEntry,
  getEntryVersion,
  publishEntry,
  restoreEntryVersion,
  returnEntry,
  submitEntry,
  unpublishEntry,
  updateEntry,
  updateImageAlt,
} from "@/features/content/api";
import PolicyVersionSheet from "@/features/content/components/PolicyVersionSheet";
import ImageUploader from "@/features/content/editor/ImageUploader";
import type { TiptapEditorHandle } from "@/features/content/editor/TiptapEditor";
import type {
  BodyDoc,
  ContentCategory,
  ContentEntryVersionDetail,
  ContentEntryVersionListItem,
  ContentImage,
  ContentKind,
  ContentPageRole,
  ContentStatus,
  ContentWarning,
  ReturnReason,
  UnpublishReason,
} from "@/features/content/types";
import { clearDraft, loadDraft, saveDraft } from "@/shared/lib/drafts";
import { ApiError } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import s from "./edit.module.css";

const AUTOSAVE_IDLE_MS = 10000;

const UNPUBLISH_REASON_OPTIONS: Array<{ key: UnpublishReason; label: string }> = [
  { key: "wrong_price", label: "Giá chưa đúng" },
  { key: "complaint", label: "Khiếu nại / rủi ro pháp lý" },
  { key: "out_of_season", label: "Hết mùa vụ" },
  { key: "wrong_content", label: "Nội dung chưa chuẩn" },
  { key: "other", label: "Khác" },
];

const RETURN_REASON_OPTIONS: Array<{ key: ReturnReason; label: string }> = [
  { key: "missing_info", label: "Thiếu thông tin / hình ảnh" },
  { key: "wrong_content", label: "Nội dung chưa chuẩn / cần sửa" },
  { key: "legal_risk", label: "Rủi ro pháp lý / bản quyền" },
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
  // SR-19: `version=N` (link bằng chứng đồng ý ở chi tiết đơn) → mở thẳng phiên bản N ở chế độ chỉ đọc.
  // Chỉ nhận số nguyên dương thuần; giá trị lạ thì bỏ qua, mở màn soạn như thường.
  const queryVersionRaw = searchParams.get("version");
  const queryVersion =
    queryVersionRaw && /^\d{1,9}$/.test(queryVersionRaw) && Number(queryVersionRaw) > 0
      ? Number(queryVersionRaw)
      : null;
  const [viewVersion, setViewVersion] = useState<number | null>(queryVersion);

  const { me } = useAuth();
  const canPublish = Boolean(
    me?.permissions?.includes(PERM.publishContentEntry) ||
    me?.groups?.includes(ROLE.owner) ||
    me?.groups?.includes(ROLE.manager)
  );

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
  const [pageRole, setPageRole] = useState<ContentPageRole>(null);
  const [showInFooter, setShowInFooter] = useState(false);
  const [footerOrder, setFooterOrder] = useState(0);

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

  // CMS-09: Gửi duyệt & Trả về
  const [submitting, setSubmitting] = useState(false);
  const [returning, setReturning] = useState(false);
  const [returnReason, setReturnReason] = useState("");
  const [showReturnModal, setShowReturnModal] = useState(false);
  const [selectedReturnReason, setSelectedReturnReason] = useState<ReturnReason>("missing_info");

  // CMS-11: Lịch sử phiên bản & Khôi phục
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [versionsList, setVersionsList] = useState<ContentEntryVersionListItem[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [selectedVersionDetail, setSelectedVersionDetail] = useState<ContentEntryVersionDetail | null>(null);
  const [restoring, setRestoring] = useState(false);

  // CMS-04: Tự lưu nháp & Offline
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const isDirtyRef = useRef(false);
  const draftFormKey = `content_entry_${entryId ?? "new"}`;
  const ownerId = (me as any)?.id || 1;

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
        setReturnReason(data.return_reason || "");
        setPageRole(data.page_role || null);
        setShowInFooter(Boolean(data.show_in_footer));
        setFooterOrder(data.footer_order || 0);
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

  const markDirty = () => {
    isDirtyRef.current = true;
  };

  const saveLocalDraft = useCallback(() => {
    const currentBody = body;
    const payload = {
      title,
      slug,
      excerpt,
      seo_title: seoTitle,
      seo_description: seoDescription,
      category,
      cover_image: coverImageId,
      body: currentBody,
    };
    saveDraft(draftFormKey, ownerId, payload);
  }, [draftFormKey, ownerId, title, slug, excerpt, seoTitle, seoDescription, category, coverImageId, body]);

  const clearLocalDraft = useCallback(() => {
    clearDraft(draftFormKey);
    isDirtyRef.current = false;
  }, [draftFormKey]);

  // Khôi phục nháp lúc mở màn (CMS-04-AC2)
  useEffect(() => {
    const cached = loadDraft<any>(draftFormKey, ownerId);
    if (cached) {
      if (cached.title !== undefined) setTitle(cached.title);
      if (cached.slug !== undefined) setSlug(cached.slug);
      if (cached.category !== undefined) setCategory(cached.category);
      if (cached.excerpt !== undefined) setExcerpt(cached.excerpt);
      if (cached.seo_title !== undefined) setSeoTitle(cached.seo_title);
      if (cached.seo_description !== undefined) setSeoDescription(cached.seo_description);
      if (cached.cover_image !== undefined) setCoverImageId(cached.cover_image);
      if (cached.body) setBody(cached.body);
      setSuccessMsg("Đã khôi phục bản nháp chưa lưu từ thiết bị này.");
    }
  }, [entryId, ownerId, draftFormKey]);

  // Bắt sự kiện mạng và beforeunload (CMS-04-AC2, CMS-04-AC3, CMS-04-AC5)
  useEffect(() => {
    const handleOnline = () => {
      if (isDirtyRef.current) {
        setSaveStatus("Đang tự lưu...");
      }
    };
    const handleOffline = () => {
      saveLocalDraft();
      setSaveStatus("Chưa lưu, đang giữ trên máy");
    };
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirtyRef.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [saveLocalDraft]);

  // Tự lưu sau 10s không gõ (CMS-04-AC1)
  useEffect(() => {
    if (!isDirtyRef.current) return;

    const timer = setTimeout(async () => {
      if (!navigator.onLine || !entryId) {
        saveLocalDraft();
        setSaveStatus("Chưa lưu, đang giữ trên máy");
        return;
      }

      setSaveStatus("Đang tự lưu...");
      try {
        const currentBody = body;
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
          body: currentBody,
          ...(kind === "page"
            ? {
                page_role: pageRole || null,
                show_in_footer: showInFooter,
                footer_order: footerOrder,
              }
            : {}),
        });
        setSlug(res.slug);
        setRowVersion(res.row_version);
        setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
        clearLocalDraft();
        const nowStr = timeHM(new Date());
        setSaveStatus(`Đã lưu lúc ${nowStr}`);
      } catch (err: any) {
        saveLocalDraft();
        if (err instanceof ApiError && err.status === 409 && err.code === "STALE_VERSION") {
          setSaveStatus("Xung đột phiên bản");
        } else {
          setSaveStatus("Chưa lưu, đang giữ trên máy");
        }
      }
    }, AUTOSAVE_IDLE_MS);

    return () => clearTimeout(timer);
  }, [
    title,
    slug,
    category,
    excerpt,
    seoTitle,
    seoDescription,
    coverImageId,
    body,
    entryId,
    rowVersion,
    kind,
    pageRole,
    showInFooter,
    footerOrder,
    saveLocalDraft,
    clearLocalDraft,
  ]);

  // Lưu nháp thủ công (CMS-03)
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
          ...(kind === "page"
            ? {
                page_role: pageRole || null,
                show_in_footer: showInFooter,
                footer_order: footerOrder,
              }
            : {}),
        });
        setEntryId(res.id);
        setSlug(res.slug);
        setRowVersion(res.row_version);
        setStatus(res.status);
        setPublishedVersion(res.published_version);
        setFirstPublishedAt(res.first_published_at);
        setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
        setPageRole(res.page_role || null);
        setShowInFooter(Boolean(res.show_in_footer));
        setFooterOrder(res.footer_order || 0);
        setImages(res.images || []);
        clearLocalDraft();
        const nowStr = timeHM(new Date());
        setSaveStatus(`Đã lưu lúc ${nowStr}`);
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
          ...(kind === "page"
            ? {
                page_role: pageRole || null,
                show_in_footer: showInFooter,
                footer_order: footerOrder,
              }
            : {}),
        });
        setSlug(res.slug);
        setRowVersion(res.row_version);
        setStatus(res.status);
        setPublishedVersion(res.published_version);
        setFirstPublishedAt(res.first_published_at);
        setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
        setPageRole(res.page_role || null);
        setShowInFooter(Boolean(res.show_in_footer));
        setFooterOrder(res.footer_order || 0);
        setImages(res.images || []);
        clearLocalDraft();
        const nowStr = timeHM(new Date());
        setSaveStatus(`Đã lưu lúc ${nowStr}`);
        setSuccessMsg("Đã lưu nháp thành công!");
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        // CMS-03-AC7: Xung đột sửa trùng (409 STALE_VERSION)
        if (err.status === 409 && err.code === "STALE_VERSION") {
          saveLocalDraft();
          setSaveStatus("Xung đột phiên bản");
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
        saveLocalDraft();
        setSaveStatus("Chưa lưu, đang giữ trên máy");
        setErrorMsg("Lỗi kết nối khi lưu nháp. Vui lòng thử lại.");
      }
    } finally {
      setSaving(false);
    }
  };

  // CMS-09: Gửi duyệt bài viết
  const handleSubmitEntry = async (acknowledgeWarnings = false) => {
    if (!entryId) {
      setErrorMsg("Vui lòng bấm 'Lưu nháp' bài viết trước khi gửi duyệt.");
      return;
    }
    setSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await submitEntry(entryId, {
        row_version: rowVersion,
        acknowledge_warnings: acknowledgeWarnings,
      });
      setStatus(res.status as ContentStatus);
      setRowVersion(res.row_version);
      setShowWarningModal(false);
      clearLocalDraft();
      setSuccessMsg("Bài viết đã được gửi cho Quản lý / Chủ duyệt.");
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 409 && err.code === "CONTENT_WARNINGS") {
          const warnings = (err as any).warnings || [];
          setWarningsList(warnings);
          setShowWarningModal(true);
        } else if (err.status === 409 && err.code === "STALE_VERSION") {
          setErrorMsg("Bài đã được người khác sửa. Vui lòng tải lại trang.");
        } else if (err.code === "BR-ND-03") {
          const missing = (err as any).missing || [];
          setErrorMsg(`Bài viết chưa đủ điều kiện gửi duyệt (BR-ND-03): thiếu ${missing.join(", ")}`);
        } else {
          setErrorMsg(err.message || "Lỗi khi gửi duyệt bài.");
        }
      } else {
        setErrorMsg("Lỗi kết nối khi gửi duyệt.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // CMS-09: Trả về nháp
  const handleReturnEntry = async () => {
    if (!entryId) return;
    setReturning(true);
    setErrorMsg(null);
    try {
      const res = await returnEntry(entryId, {
        row_version: rowVersion,
        reason: selectedReturnReason,
      });
      setStatus(res.status as ContentStatus);
      setRowVersion(res.row_version);
      setReturnReason(selectedReturnReason);
      setShowReturnModal(false);
      clearLocalDraft();
      setSuccessMsg("Đã trả bài về trạng thái nháp.");
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || "Lỗi khi trả bài về nháp.");
      } else {
        setErrorMsg("Lỗi kết nối khi trả bài.");
      }
    } finally {
      setReturning(false);
    }
  };

  // CMS-11: Lịch sử phiên bản
  const handleOpenHistoryModal = async () => {
    if (!entryId) return;
    setShowHistoryModal(true);
    setLoadingVersions(true);
    setSelectedVersionDetail(null);
    try {
      const versions = await fetchEntryVersions(entryId);
      setVersionsList(versions);
    } catch (err: any) {
      setErrorMsg("Không thể tải lịch sử phiên bản.");
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleConfirmRestore = async (verNo: number) => {
    if (!entryId) return;
    if (hasUnpublishedChanges || isDirtyRef.current) {
      const ok = window.confirm(
        "Bản đang soạn sẽ bị thay thế bởi phiên bản này. Bạn có chắc chắn muốn khôi phục?"
      );
      if (!ok) return;
    }
    setRestoring(true);
    try {
      const res = await restoreEntryVersion(entryId, verNo, { row_version: rowVersion });
      setTitle(res.title);
      setSlug(res.slug);
      setCategory(res.category);
      setExcerpt(res.excerpt);
      setSeoTitle(res.seo_title);
      setSeoDescription(res.seo_description);
      setCoverImageId(res.cover_image);
      setBody(res.body);
      setRowVersion(res.row_version);
      setHasUnpublishedChanges(Boolean(res.has_unpublished_changes));
      setShowHistoryModal(false);
      clearLocalDraft();
      setSuccessMsg(`Đã khôi phục nội dung từ phiên bản #${verNo}. Vui lòng bấm Cập nhật bài để xuất bản.`);
    } catch (err: any) {
      if (err instanceof ApiError) {
        setErrorMsg(err.message || "Lỗi khi khôi phục phiên bản.");
      } else {
        setErrorMsg("Lỗi kết nối khi khôi phục phiên bản.");
      }
    } finally {
      setRestoring(false);
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
          {saveStatus && (
            <span
              className={`${s.saveStatusText} ${
                saveStatus.includes("Chưa lưu") ? s.saveStatusOffline : ""
              }`}
            >
              {saveStatus}
            </span>
          )}
          {entryId !== null && (firstPublishedAt !== null || status === "published" || status === "unpublished") && (
            <button
              type="button"
              className={s.historyBtn}
              onClick={handleOpenHistoryModal}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              📜 Lịch sử
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              className={s.deleteBtn}
              onClick={handleDeleteDraft}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              {deleting ? "Đang xoá..." : "Xoá nháp"}
            </button>
          )}
          <button
            type="button"
            className={s.saveBtn}
            onClick={handleSaveDraft}
            disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
          >
            {saving ? "Đang lưu..." : "Lưu nháp"}
          </button>
          {status === "pending_review" && canPublish && (
            <button
              type="button"
              className={s.returnBtn}
              onClick={() => setShowReturnModal(true)}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              {returning ? "Đang trả về..." : "Trả về nháp"}
            </button>
          )}
          {!canPublish && status === "draft" && (
            <button
              type="button"
              className={s.submitBtn}
              onClick={() => handleSubmitEntry(false)}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              {submitting ? "Đang gửi..." : "Gửi duyệt"}
            </button>
          )}
          {status === "published" && !pageRole && (
            <button
              type="button"
              className={s.unpublishBtn}
              onClick={handleOpenUnpublishModal}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              {unpublishing ? "Đang gỡ..." : "Gỡ bài"}
            </button>
          )}
          {canPublish && (
            <button
              type="button"
              className={s.publishBtn}
              onClick={handleOpenPublishModal}
              disabled={saving || deleting || publishing || unpublishing || discarding || submitting || returning}
            >
              {publishing ? "Đang đăng..." : "Đăng bài"}
            </button>
          )}
        </div>
      </div>

      {/* Banner thông báo trạng thái Chờ duyệt (CMS-09) */}
      {status === "pending_review" && (
        <div className={s.bannerPending}>
          <div>
            ⏳ <strong>Đang chờ duyệt:</strong> Bài viết đã được gửi cho Quản lý / Chủ duyệt trước khi xuất bản.
            {returnReason && (
              <div style={{ marginTop: "4px", fontSize: "13px" }}>
                Lý do trước đó: <em>{RETURN_REASON_OPTIONS.find((o) => o.key === returnReason)?.label || returnReason}</em>
              </div>
            )}
          </div>
        </div>
      )}

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
                onChange={(e) => {
                  setTitle(e.target.value);
                  markDirty();
                }}
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
                  markDirty();
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
                      markDirty();
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
                onChange={(newBody) => {
                  setBody(newBody);
                  markDirty();
                }}
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
                onChange={(e) => {
                  setKind(e.target.value as ContentKind);
                  markDirty();
                }}
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
                    markDirty();
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

            {kind === "page" && (
              <>
                <div className={s.formGroup}>
                  <label className={s.label}>Vai trò trang (Bắt buộc go-live)</label>
                  <select
                    className={s.select}
                    value={pageRole || ""}
                    onChange={(e) => {
                      setPageRole((e.target.value as ContentPageRole) || null);
                      markDirty();
                    }}
                    disabled={status === "published" && Boolean(pageRole)}
                  >
                    <option value="">-- Không (Trang tự do) --</option>
                    <option value="privacy">Chính sách bảo mật (privacy)</option>
                    <option value="terms">Điều khoản dịch vụ (terms)</option>
                    <option value="refund">Đổi trả & hoàn tiền (refund)</option>
                    <option value="seller_info">Thông tin người bán (seller_info)</option>
                  </select>
                  {status === "published" && Boolean(pageRole) && (
                    <p className={s.hint} style={{ color: "#d97706", marginTop: "4px", fontSize: "12px" }}>
                      Trang bắt buộc go-live đang đăng không được bỏ hoặc đổi vai trò (TD-3).
                    </p>
                  )}
                </div>

                <div className={s.formGroup}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "14px" }}>
                    <input
                      type="checkbox"
                      checked={showInFooter}
                      onChange={(e) => {
                        setShowInFooter(e.target.checked);
                        markDirty();
                      }}
                    />
                    <span>Hiện ở chân trang (Footer)</span>
                  </label>
                </div>

                {showInFooter && (
                  <div className={s.formGroup}>
                    <label className={s.label}>Thứ tự chân trang (footer_order)</label>
                    <input
                      type="number"
                      className={s.input}
                      value={footerOrder}
                      onChange={(e) => {
                        setFooterOrder(parseInt(e.target.value, 10) || 0);
                        markDirty();
                      }}
                    />
                  </div>
                )}
              </>
            )}

            <div className={s.formGroup}>
              <label className={s.label}>Trạng thái</label>
              <div>
                <span
                  className={`${s.badge} ${
                    status === "published"
                      ? s.badgePublished
                      : status === "pending_review"
                      ? s.badgePending
                      : s.badgeDraft
                  }`}
                >
                  {status === "draft"
                    ? "Bản nháp"
                    : status === "pending_review"
                    ? "Chờ duyệt"
                    : status === "published"
                    ? "Đã đăng"
                    : status === "unpublished"
                    ? "Đã gỡ"
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
                onChange={(e) => {
                  setExcerpt(e.target.value);
                  markDirty();
                }}
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
                onChange={(e) => {
                  setSeoTitle(e.target.value);
                  markDirty();
                }}
              />
            </div>

            <div className={s.formGroup}>
              <label className={s.label}>SEO Description</label>
              <textarea
                className={s.textarea}
                placeholder="Mô tả SEO hiển thị trên Google..."
                value={seoDescription}
                maxLength={300}
                onChange={(e) => {
                  setSeoDescription(e.target.value);
                  markDirty();
                }}
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

      {/* Modal Trả bài về nháp (CMS-09) */}
      {showReturnModal && (
        <div className={s.modalBackdrop}>
          <div className={s.modalDialog}>
            <h3 className={s.modalTitle} style={{ color: "#d97706" }}>
              Trả bài viết về nháp
            </h3>
            <p className={s.modalDesc}>
              Vui lòng chọn lý do trả về để người soạn bài biết và chỉnh sửa lại:
            </p>

            <div className={s.formGroup} style={{ marginTop: "12px", marginBottom: "16px" }}>
              <label className={s.label}>Lý do trả về</label>
              <select
                className={s.select}
                value={selectedReturnReason}
                onChange={(e) => setSelectedReturnReason(e.target.value as ReturnReason)}
              >
                {RETURN_REASON_OPTIONS.map((opt) => (
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
                onClick={() => setShowReturnModal(false)}
                disabled={returning}
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                className={s.returnBtn}
                style={{ backgroundColor: "#d97706", color: "#ffffff", borderColor: "#d97706" }}
                onClick={handleReturnEntry}
                disabled={returning}
              >
                {returning ? "Đang trả về..." : "Xác nhận trả về nháp"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SR-19: xem đúng phiên bản chính sách khách đã đồng ý — chỉ đọc, không khôi phục */}
      {viewVersion !== null && entryId !== null && (
        <PolicyVersionSheet
          entryId={entryId}
          versionNo={viewVersion}
          onClose={() => {
            setViewVersion(null);
            window.history.replaceState(null, "", `/content/edit/?id=${entryId}`);
          }}
        />
      )}

      {/* Modal Lịch sử phiên bản & Khôi phục (CMS-11) */}
      {showHistoryModal && (
        <div className={s.modalBackdrop}>
          <div className={s.modalDialog} style={{ maxWidth: "680px" }}>
            <h3 className={s.modalTitle}>Lịch sử phiên bản</h3>
            <p className={s.modalDesc}>
              Danh sách các phiên bản đã xuất bản của bài viết này. Bạn có thể khôi phục lại nội dung bản cũ vào bản đang soạn.
            </p>

            {loadingVersions ? (
              <div style={{ padding: "20px 0", textAlign: "center", color: "#64748b" }}>
                Đang tải lịch sử phiên bản...
              </div>
            ) : versionsList.length === 0 ? (
              <div style={{ padding: "20px 0", textAlign: "center", color: "#64748b" }}>
                Chưa có phiên bản đã đăng nào.
              </div>
            ) : (
              <div className={s.versionList}>
                {versionsList.map((ver) => (
                  <div key={ver.version} className={s.versionItem}>
                    <div className={s.versionMeta}>
                      <span className={s.versionBadge}>Phiên bản #{ver.version}</span>
                      <span className={s.versionAuthor}>
                        Bởi {ver.published_by_name || "Hệ thống"}
                      </span>
                      <span className={s.versionDate}>
                        {dateTimeFull(ver.published_at)}
                      </span>
                    </div>
                    <div className={s.versionTitle}>{ver.title}</div>
                    <div className={s.versionActions}>
                      <button
                        type="button"
                        className={s.restoreActionBtn}
                        onClick={() => handleConfirmRestore(ver.version)}
                        disabled={restoring}
                      >
                        {restoring ? "Đang khôi phục..." : "Khôi phục phiên bản này"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className={s.modalActions}>
              <button
                type="button"
                className={s.cancelBtn}
                onClick={() => setShowHistoryModal(false)}
                disabled={restoring}
              >
                Đóng
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
