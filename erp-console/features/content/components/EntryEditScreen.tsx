"use client";

// Soạn bài viết / trang (ED-35 / W3c, F3i-F3l). Một màn, hai chế độ: "Viết bài" (tiêu đề, đường dẫn, nội dung, ảnh) và
// "Thiết lập bài viết" (phân loại, tóm tắt/tìm kiếm, ảnh bìa). Quyền theo quyền thật của app content (UI-RULES §8.1).
//
// Luồng: Lưu nháp -> (Gửi duyệt) -> Đăng. Người đăng được bài đăng thẳng, có hộp "Kiểm tra trước khi đăng" (5 mục) và hộp
// "Có chỗ cần xem lại" khi BE báo cảnh báo (409 CONTENT_WARNINGS). Xung đột phiên bản (409 STALE_VERSION) hiện banner vàng + tải lại.
// Tự lưu mỗi 10 giây khi có thay đổi; mất mạng hoặc chưa có id thì giữ bản nháp trên máy (chỉ chữ do người viết soạn).

import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { clearDraft, loadDraft, saveDraft } from "@/shared/lib/drafts";
import { ENUMS } from "@/shared/lib/enums";
import { timeHM } from "@/shared/lib/format";
import { ApiError } from "@/shared/lib/http";
import { useResource } from "@/shared/lib/useResource";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { StatusPath } from "@/shared/ui/detail/StatusPath";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { fieldErrorsOf, isConflictError, conflictOf, type SubmitConflict } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { SkeletonScreen } from "@/shared/ui/Skeleton";
import { ConflictBanner } from "@/shared/ui/states/ConflictBanner";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import {
  createEntry,
  deleteEntry,
  discardChanges,
  fetchCategories,
  getEntry,
  publishEntry,
  restoreEntryVersion,
  returnEntry,
  submitEntry,
  unpublishEntry,
  updateEntry,
  updateImageAlt,
} from "../api";
import {
  CONTENT_PERM,
  STATUS_STEPS,
  applyLocalDraft,
  canDeleteEntry,
  coverImageOf,
  createPayloadOf,
  deleteBlockedReason,
  discardBlockedReason,
  draftDiffers,
  draftIsCurrent,
  emptyForm,
  errorText,
  formOf,
  hasPerm,
  historyBlockedReason,
  isApiCode,
  isStale,
  localDraftOf,
  missingOf,
  missingSentence,
  pathViewOf,
  positiveIntParam,
  primaryActionOf,
  reasonLabelOf,
  suggestionOf,
  unpublishBlockedReason,
  updatePayloadOf,
  warningsOf,
  type EntryFacts,
  type EntryForm,
  type LocalDraft,
} from "../contentModel";
import type { TiptapEditorHandle } from "../editor/TiptapEditor";
import { isSafeHref } from "../editor/safeHref";
import { CONTENT_MSG as M } from "../messages";
import type { ContentCategory, ContentEntryDetail, ContentImage, ContentKind, ContentStatus, ContentWarning } from "../types";
import ImageUploader from "../editor/ImageUploader";
import { ChecklistModal, HistoryModal, ReasonModal, WarningsModal } from "./EntryDialogs";
import { EntrySettings } from "./EntrySettings";
import PolicyVersionSheet from "./PolicyVersionSheet";
import s from "../content.module.css";

// Trình soạn thảo nặng (Tiptap): chỉ tải khi mở màn soạn bài (BR-AI-17: không làm chậm các màn khác).
const TiptapEditor = lazy(() => import("../editor/TiptapEditor"));

const AUTOSAVE_IDLE_MS = 10000;
const LOCAL_SAVE_MS = 800;

/** Tiêu đề còn trống: chưa gọi máy chủ, chỉ nhắc ngay tại ô tiêu đề. */
class TitleRequiredError extends Error {}

type Meta = {
  rowVersion: number;
  status: ContentStatus;
  publishedVersion: number | null;
  firstPublishedAt: string | null;
  hasUnpublishedChanges: boolean;
  returnReason: string;
  publicUrl: string | null;
  slugLocked: boolean;
  source: "human" | "ai";
};

const NEW_META: Meta = {
  rowVersion: 1,
  status: "draft",
  publishedVersion: null,
  firstPublishedAt: null,
  hasUnpublishedChanges: false,
  returnReason: "",
  publicUrl: null,
  slugLocked: false,
  source: "human",
};

function metaOf(d: ContentEntryDetail): Meta {
  return {
    rowVersion: d.row_version,
    status: d.status,
    publishedVersion: d.published_version,
    firstPublishedAt: d.first_published_at,
    hasUnpublishedChanges: d.has_unpublished_changes,
    returnReason: d.return_reason || "",
    publicUrl: d.public_url,
    slugLocked: d.slug_locked,
    source: d.source,
  };
}

type Dialog =
  | { t: "checklist" }
  | { t: "warnings"; action: "publish" | "submit"; warnings: ContentWarning[] }
  | { t: "return" }
  | { t: "unpublish" }
  | { t: "delete" }
  | { t: "discard" }
  | { t: "history" }
  | { t: "restore"; version: number }
  | { t: "reload" }
  | null;

type Notice = { kind: "error" | "warn"; text: string } | null;
type LoadState = "loading" | "error" | "notfound" | "forbidden" | "ready";

const draftKeyOf = (id: number | null) => `content_entry_${id ?? "new"}`;

export function EntryEditScreen() {
  const router = useRouter();
  const sp = useSearchParams();
  const { me } = useAuth();
  const toast = useToast();
  const editorRef = useRef<TiptapEditorHandle>(null);

  const idParam = positiveIntParam(sp.get("id"));
  const newKind: ContentKind = sp.get("new") === "page" ? "page" : "post";
  const versionParam = positiveIntParam(sp.get("version"));
  const [viewVersion, setViewVersion] = useState<number | null>(versionParam);

  const canView = hasPerm(me, CONTENT_PERM.view);
  const canAdd = hasPerm(me, CONTENT_PERM.add);
  const canChange = hasPerm(me, CONTENT_PERM.change);
  const canDelete = hasPerm(me, CONTENT_PERM.delete);
  const canPublish = hasPerm(me, CONTENT_PERM.publish);

  const [entryId, setEntryId] = useState<number | null>(idParam);
  const [form, setForm] = useState<EntryForm>(() => emptyForm(newKind));
  const [images, setImages] = useState<ContentImage[]>([]);
  const [meta, setMeta] = useState<Meta>(NEW_META);
  const [coverAlt, setCoverAlt] = useState("");
  const [load, setLoad] = useState<LoadState>(idParam === null ? "ready" : "loading");
  const [view, setView] = useState<"write" | "settings">("write");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [conflict, setConflict] = useState<SubmitConflict | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [slugSuggestion, setSlugSuggestion] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [acting, setActing] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [online, setOnline] = useState(true);
  const [restoredLocal, setRestoredLocal] = useState(false);
  // Bản nháp trên máy cũ hơn bản máy chủ (người khác đã sửa sau đó): chưa áp, chờ người dùng chọn.
  const [staleDraft, setStaleDraft] = useState<LocalDraft | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);

  // Bản mới nhất cho các hàm async (tránh đọc state cũ trong closure).
  const formRef = useRef(form);
  formRef.current = form;
  const metaRef = useRef(meta);
  metaRef.current = meta;
  const imagesRef = useRef(images);
  imagesRef.current = images;
  const coverAltRef = useRef(coverAlt);
  coverAltRef.current = coverAlt;
  const entryIdRef = useRef(entryId);
  entryIdRef.current = entryId;
  const editSeq = useRef(0);
  const savingRef = useRef(false);
  const loadedRef = useRef<number | null>(null);
  const leavingRef = useRef(false);

  const ownerId = me?.id ?? 0;
  const categoriesRes = useResource(me && canView ? "content-categories-edit" : null, () => fetchCategories(), 0);
  const categories: ContentCategory[] = categoriesRes.data ?? [];
  const categoryName = useMemo(() => new Map(categories.map((c) => [c.id, c.name])), [categories]);

  const saved = entryId !== null;
  const readOnly = !canChange;

  // ---- Áp dữ liệu từ máy chủ ----
  const applyServer = useCallback((d: ContentEntryDetail) => {
    const f = formOf(d);
    formRef.current = f;
    setForm(f);
    setImages(d.images || []);
    setMeta(metaOf(d));
    setCoverAlt(coverImageOf(d.images || [], d.cover_image)?.alt ?? "");
    setDirty(false);
    editSeq.current += 1;
  }, []);

  // ---- Tải bài (sau đó mới áp bản nháp trên máy, để bản nháp không bị bản máy chủ đè) ----
  useEffect(() => {
    if (!me) return;
    if (idParam === null) {
      // Bài mới: chỉ áp bản nháp trên máy (nếu có).
      const ld = loadDraft<LocalDraft>(draftKeyOf(null), me.id);
      if (ld) {
        const f = applyLocalDraft(emptyForm(newKind), ld);
        formRef.current = f;
        setForm(f);
        setDirty(true);
        setRestoredLocal(true);
      }
      return;
    }
    if (entryIdRef.current === idParam && loadedRef.current === idParam) return;
    let live = true;
    setLoad("loading");
    getEntry(idParam)
      .then((d) => {
        if (!live) return;
        applyServer(d);
        loadedRef.current = d.id;
        const ld = loadDraft<LocalDraft>(draftKeyOf(d.id), me.id);
        if (ld) {
          const serverForm = formOf(d);
          if (!draftDiffers(serverForm, ld)) {
            // Nháp giống hệt bản máy chủ: không có gì để khôi phục.
            clearDraft(draftKeyOf(d.id));
          } else if (draftIsCurrent(ld, d.row_version)) {
            const f = applyLocalDraft(serverForm, ld);
            formRef.current = f;
            setForm(f);
            setDirty(true);
            setRestoredLocal(true);
          } else {
            // Máy chủ đã đổi sau lần soạn này: không tự đè, để người dùng chọn.
            setStaleDraft(ld);
          }
        }
        setLoad("ready");
      })
      .catch((err) => {
        if (!live) return;
        if (err instanceof ApiError && err.status === 404) setLoad("notfound");
        else if (err instanceof ApiError && err.status === 403) setLoad("forbidden");
        else setLoad("error");
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.id, idParam, loadAttempt]);

  // ---- Thay đổi của người dùng ----
  const edit = useCallback((patch: Partial<EntryForm>) => {
    editSeq.current += 1;
    const next = { ...formRef.current, ...patch };
    formRef.current = next;
    setForm(next);
    setDirty(true);
    setFieldErrors({});
    if (patch.slug !== undefined) setSlugSuggestion(null);
  }, []);

  const editSettings = useCallback(
    (patch: Partial<EntryForm>) => {
      if (patch.coverImageId !== undefined) setCoverAlt(coverImageOf(imagesRef.current, patch.coverImageId)?.alt ?? "");
      edit(patch);
    },
    [edit],
  );

  // ---- Giữ bản nháp trên máy (chữ do người viết soạn, không có dữ liệu khách) ----
  useEffect(() => {
    if (!me || !dirty || load !== "ready") return;
    const t = setTimeout(() => saveDraft(draftKeyOf(entryId), me.id, localDraftOf(form, entryId === null ? undefined : metaRef.current.rowVersion)), LOCAL_SAVE_MS);
    return () => clearTimeout(t);
  }, [me, dirty, form, entryId, load]);

  useEffect(() => {
    const update = () => setOnline(typeof navigator === "undefined" ? true : navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  useEffect(() => {
    if (!dirty) return;
    const guard = (e: BeforeUnloadEvent) => {
      if (leavingRef.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);

  // ---- Lưu ----
  /** Lưu thật lên máy chủ. Ném lỗi để người gọi quyết định hiện thế nào. */
  const persist = useCallback(async (): Promise<void> => {
    const f = formRef.current;
    const m = metaRef.current;
    const seq = editSeq.current;
    if (!f.title.trim()) throw new TitleRequiredError();
    let imgs = imagesRef.current;
    const cover = coverImageOf(imgs, f.coverImageId);
    const altNow = coverAltRef.current.trim();
    if (cover && altNow && altNow !== cover.alt.trim()) {
      const updated = await updateImageAlt(cover.id, altNow);
      imgs = imgs.map((i) => (i.id === updated.id ? updated : i));
      imagesRef.current = imgs;
      setImages(imgs);
    }
    const id = entryIdRef.current;
    const d = id === null ? await createEntry(createPayloadOf(f)) : await updateEntry(id, updatePayloadOf(f, m.rowVersion));
    if (id === null) {
      entryIdRef.current = d.id;
      loadedRef.current = d.id;
      setEntryId(d.id);
      clearDraft(draftKeyOf(null));
      window.history.replaceState(null, "", `/content/edit/?id=${d.id}`);
    }
    setMeta(metaOf(d));
    metaRef.current = metaOf(d);
    setImages(d.images || imgs);
    if (d.slug && d.slug !== formRef.current.slug && editSeq.current === seq) {
      const withSlug = { ...formRef.current, slug: d.slug };
      formRef.current = withSlug;
      setForm(withSlug);
    }
    if (editSeq.current === seq) {
      setDirty(false);
      clearDraft(draftKeyOf(d.id));
    }
    setSavedAt(new Date().toISOString());
    setRestoredLocal(false);
  }, []);

  /** Đưa lỗi lưu ra màn. */
  const showSaveError = useCallback((err: unknown) => {
    if (err instanceof TitleRequiredError) {
      setFieldErrors({ title: M.titleRequired });
      setNotice(null);
      setView("write");
      return;
    }
    if (isStale(err)) {
      setConflict(conflictOf(err));
      return;
    }
    if (isApiCode(err, "BR-ND-04")) {
      setFieldErrors({ slug: M.pathTaken });
      setSlugSuggestion(suggestionOf(err));
      setNotice(null);
      setView("write");
      return;
    }
    const fe = fieldErrorsOf(err);
    if (Object.keys(fe).length > 0) setFieldErrors(fe);
    setNotice({ kind: "error", text: errorText(err, M.networkSave) });
  }, []);

  /** Lưu có báo lỗi. true = đã lưu. */
  const saveNow = useCallback(async (): Promise<boolean> => {
    if (savingRef.current) return false;
    savingRef.current = true;
    setSaving(true);
    setNotice(null);
    try {
      await persist();
      return true;
    } catch (err) {
      showSaveError(err);
      return false;
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }, [persist, showSaveError]);

  const onSaveDraftClick = async () => {
    const hadId = entryIdRef.current !== null;
    if (await saveNow()) toast.success(hadId ? M.saved : M.created);
  };

  // Tự lưu: im lặng; lỗi mạng thì giữ bản nháp trên máy (đã có ở trên), không làm phiền.
  useEffect(() => {
    if (!dirty || conflict || load !== "ready" || entryId === null || !online || !canChange || acting) return;
    const t = setTimeout(() => {
      if (savingRef.current) return;
      savingRef.current = true;
      setSaving(true);
      persist()
        .catch((err) => {
          if (isStale(err)) setConflict(conflictOf(err));
        })
        .finally(() => {
          savingRef.current = false;
          setSaving(false);
        });
    }, AUTOSAVE_IDLE_MS);
    return () => clearTimeout(t);
  }, [dirty, form, conflict, load, entryId, online, canChange, acting, persist]);

  // ---- Đăng / gửi duyệt ----
  const goToMissing = (missing: string[]) => {
    const inWrite = missing.some((m) => m === "title" || m === "slug" || m === "body");
    setView(inWrite ? "write" : "settings");
    const fe: Record<string, string> = {};
    if (missing.includes("category")) fe.category = "Chọn chuyên mục";
    if (missing.includes("cover_image")) fe.cover_image = "Chọn ảnh bìa";
    if (missing.includes("cover_image_alt")) fe.cover_image_alt = M.coverAltRequired;
    if (missing.includes("description")) fe.excerpt = "Nhập tóm tắt hoặc mô tả khi tìm kiếm";
    if (missing.includes("title")) fe.title = "Nhập tiêu đề";
    setFieldErrors(fe);
  };

  /** Lỗi của đăng / gửi duyệt: true = đã được đưa ra màn bằng cách riêng (hộp cảnh báo, câu "còn thiếu", banner xung đột). */
  const routeActionError = (err: unknown, action: "publish" | "submit"): boolean => {
    const warnings = warningsOf(err);
    if (warnings.length > 0) {
      setDialog({ t: "warnings", action, warnings });
      return true;
    }
    const missing = missingOf(err);
    if (missing.length > 0) {
      setDialog(null);
      setNotice({ kind: "error", text: missingSentence(missing, action) });
      goToMissing(missing);
      return true;
    }
    if (isConflictError(err)) {
      setDialog(null);
      setConflict(conflictOf(err));
      return true;
    }
    return false;
  };

  const runPublish = async (acknowledge: boolean): Promise<void> => {
    const id = entryIdRef.current;
    if (id === null) return;
    try {
      const r = await publishEntry(id, { row_version: metaRef.current.rowVersion, checklist_confirmed: true, acknowledge_warnings: acknowledge || undefined });
      setMeta((m) => ({
        ...m,
        status: r.status,
        rowVersion: r.row_version,
        publishedVersion: r.version,
        publicUrl: r.public_url,
        hasUnpublishedChanges: false,
        firstPublishedAt: m.firstPublishedAt ?? new Date().toISOString(),
        returnReason: "",
        slugLocked: true,
      }));
      setNotice(null);
      setFieldErrors({});
      setDialog(null);
      setView("write");
      toast.success(M.publishedOk(r.version));
    } catch (err) {
      if (routeActionError(err, "publish")) return;
      throw new Error(errorText(err, M.genericFail));
    }
  };

  const runSubmit = async (acknowledge: boolean): Promise<void> => {
    const id = entryIdRef.current;
    if (id === null) return;
    try {
      const r = await submitEntry(id, { row_version: metaRef.current.rowVersion, acknowledge_warnings: acknowledge || undefined });
      setMeta((m) => ({ ...m, status: (r.status as ContentStatus) || "pending_review", rowVersion: r.row_version, returnReason: "" }));
      setNotice(null);
      setFieldErrors({});
      setDialog(null);
      setView("write");
      toast.success(M.submitted);
    } catch (err) {
      if (routeActionError(err, "submit")) return;
      throw new Error(errorText(err, M.genericFail));
    }
  };

  /** Bấm Đăng / Gửi duyệt: lưu trước nếu còn thay đổi, rồi mở hộp (đăng) hoặc gửi luôn (gửi duyệt). */
  const startAction = async (action: "publish" | "submit") => {
    if (acting) return;
    setNotice(null);
    setActing(true);
    try {
      if (dirty || entryIdRef.current === null) {
        savingRef.current = true;
        setSaving(true);
        try {
          await persist();
        } catch (err) {
          showSaveError(err);
          return;
        } finally {
          savingRef.current = false;
          setSaving(false);
        }
      }
      if (action === "publish") {
        setDialog({ t: "checklist" });
      } else {
        try {
          await runSubmit(false);
        } catch (err) {
          setNotice({ kind: "error", text: err instanceof Error ? err.message : M.genericFail });
        }
      }
    } finally {
      setActing(false);
    }
  };

  const onSubmitFromSettings = () => {
    if (coverImageOf(images, form.coverImageId) && !coverAlt.trim()) {
      setFieldErrors({ cover_image_alt: M.coverAltRequired });
      return;
    }
    void startAction("submit");
  };

  const onSaveSettings = async () => {
    if (coverImageOf(images, form.coverImageId) && !coverAlt.trim()) {
      setFieldErrors({ cover_image_alt: M.coverAltRequired });
      return;
    }
    if (await saveNow()) {
      toast.success(M.settingsSaved);
      setView("write");
    }
  };

  // ---- Các thao tác khác (qua hộp xác nhận) ----
  const runReturn = async (reason: string): Promise<void> => {
    const id = entryIdRef.current;
    if (id === null) return;
    try {
      const r = await returnEntry(id, { row_version: metaRef.current.rowVersion, reason: reason as "missing_info" });
      setMeta((m) => ({ ...m, status: "draft", rowVersion: r.row_version, returnReason: r.return_reason ?? reason }));
      setDialog(null);
      toast.success(M.returned);
    } catch (err) {
      if (isConflictError(err)) {
        setDialog(null);
        setConflict(conflictOf(err));
        return;
      }
      throw new Error(errorText(err, M.genericFail));
    }
  };

  const runUnpublish = async (reason: string): Promise<void> => {
    const id = entryIdRef.current;
    if (id === null) return;
    try {
      const d = await unpublishEntry(id, { row_version: metaRef.current.rowVersion, reason: reason as "other" });
      // Máy chủ chỉ trả { status, row_version }: gộp vào meta hiện có, không thay cả meta.
      setMeta((m) => ({ ...m, status: d.status, rowVersion: d.row_version, slugLocked: true, returnReason: reason }));
      setDialog(null);
      toast.success(M.unpublished);
    } catch (err) {
      if (isConflictError(err)) {
        setDialog(null);
        setConflict(conflictOf(err));
        return;
      }
      throw new Error(errorText(err, M.genericFail));
    }
  };

  /** Giữ bản trên máy: dựng lại trên phiên bản cũ, nên lưu sẽ bị máy chủ báo xung đột thay vì đè âm thầm. */
  const keepStaleDraft = () => {
    if (!staleDraft) return;
    const f = applyLocalDraft(formRef.current, staleDraft);
    formRef.current = f;
    setForm(f);
    setMeta((m) => ({ ...m, rowVersion: staleDraft.base_version ?? 0 }));
    metaRef.current = { ...metaRef.current, rowVersion: staleDraft.base_version ?? 0 };
    setStaleDraft(null);
    setDirty(true);
    setRestoredLocal(false);
    setNotice({ kind: "warn", text: M.staleDraftKept });
  };

  const dropStaleDraft = () => {
    const id = entryIdRef.current;
    if (id !== null) clearDraft(draftKeyOf(id));
    setStaleDraft(null);
  };

  const reloadFromServer = async (): Promise<ContentEntryDetail> => {
    const id = entryIdRef.current;
    if (id === null) throw new Error(M.genericFail);
    const d = await getEntry(id);
    clearDraft(draftKeyOf(id));
    applyServer(d);
    setConflict(null);
    setNotice(null);
    setRestoredLocal(false);
    setStaleDraft(null);
    return d;
  };

  const facts: EntryFacts = {
    status: meta.status,
    pageRole: form.pageRole,
    publishedVersion: meta.publishedVersion,
    firstPublishedAt: meta.firstPublishedAt,
    hasUnpublishedChanges: meta.hasUnpublishedChanges,
    saved,
  };

  const more: MoreMenuItem[] = [];
  if (canDelete) more.push({ key: "delete", label: M.moreDelete, danger: true, blockedReason: deleteBlockedReason(facts), onSelect: () => setDialog({ t: "delete" }) });
  if (canView) more.push({ key: "history", label: M.moreHistory, blockedReason: historyBlockedReason(facts), onSelect: () => setDialog({ t: "history" }) });
  if (canPublish) more.push({ key: "unpublish", label: M.moreUnpublish, blockedReason: unpublishBlockedReason(facts), onSelect: () => setDialog({ t: "unpublish" }) });
  if (canChange) more.push({ key: "discard", label: M.moreDiscard, blockedReason: discardBlockedReason(facts), onSelect: () => setDialog({ t: "discard" }) });

  // ---- Màn theo trạng thái tải ----
  if (!me || load === "loading") {
    return (
      <SkeletonScreen label={M.loadingEntry}>
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-l" />
        <span className="sk sk-s" />
      </SkeletonScreen>
    );
  }
  if (idParam === null && !canAdd) return <NoPermission />;
  if (idParam !== null && !canView) return <NoPermission />;
  if (load === "forbidden") return <NoPermission />;
  if (load === "error") {
    return (
      <div className="page-state" role="alert">
        <span className="state-ic">
          <Icon name="sync_problem" />
        </span>
        <h2 className="state-title">{M.loadFailed}</h2>
        <p>{M.loadFailedHint}</p>
        <div className="page-state-actions">
          <button type="button" className="btn primary" onClick={() => setLoadAttempt((n) => n + 1)}>
            {M.retry}
          </button>
        </div>
      </div>
    );
  }
  if (load === "notfound") {
    return (
      <div className="page-state">
        <span className="state-ic">
          <Icon name="link_off" />
        </span>
        <h2 className="state-title">{M.notFoundTitle}</h2>
        <p>{M.notFoundHint}</p>
        <div className="page-state-actions">
          <Link href="/content/" className="btn primary">
            {M.back}
          </Link>
        </div>
      </div>
    );
  }

  const action = primaryActionOf(meta.status, meta.hasUnpublishedChanges, canPublish, canChange);
  const pathView = pathViewOf(meta.status, canPublish, meta.firstPublishedAt, saved);
  const heading = form.title.trim() || (form.kind === "page" ? M.writePage : M.writePost);
  const cover = coverImageOf(images, form.coverImageId);
  const busy = saving || acting;

  const saveText = (() => {
    if (saving) return M.autosaving;
    if (dirty && (!saved || !online)) return M.localOnly;
    if (conflict) return M.conflictShort;
    if (dirty) return null;
    return savedAt ? M.savedAt(timeHM(savedAt)) : null;
  })();

  const primaryButtons = (
    <>
      {canChange && (
        <button type="button" className="btn" onClick={() => void onSaveDraftClick()} disabled={busy}>
          {saving ? <Icon name="progress_activity" className="spin" /> : null}
          <span>{saving ? M.saving : M.saveDraft}</span>
        </button>
      )}
      {meta.status === "pending_review" && canPublish && (
        <button type="button" className="btn" onClick={() => setDialog({ t: "return" })} disabled={busy}>
          {M.returnToDraft}
        </button>
      )}
      {action && (
        <button type="button" className="btn primary" onClick={() => void startAction(action === "submit" ? "submit" : "publish")} disabled={busy || !!conflict} aria-busy={acting || undefined}>
          {acting ? <Icon name="progress_activity" className="spin" /> : null}
          <span>{action === "publish" ? M.publish : action === "publish_changes" ? M.publishChanges : M.submitReview}</span>
        </button>
      )}
    </>
  );

  const conflictBanner = conflict ? (
    <ConflictBanner noun={M.conflictBannerNoun} updatedByName={conflict.updatedByName} updatedAt={conflict.updatedAt} onReload={() => setDialog({ t: "reload" })} />
  ) : null;
  const noticeBox = notice ? <FormAlert kind={notice.kind}>{notice.text}</FormAlert> : null;

  const settingsView = view === "settings";

  return (
    <div className={s.editPage}>
      {settingsView ? (
        <button type="button" className={s.backBtn} onClick={() => setView("write")}>
          <Icon name="arrow_back" />
          <span>{M.settingsBack}</span>
        </button>
      ) : null}

      {!settingsView && (
        <>
          <DetailHeader
            back={{ href: "/content/", label: M.back }}
            title={heading}
            status={saved ? <Chip table={ENUMS.entryStatus} value={meta.status} /> : undefined}
            primary={primaryButtons}
            more={more}
          />
          <StatusPath steps={[...STATUS_STEPS]} current={pathView.current} badEnd={pathView.badEnd} next={pathView.next} done={pathView.done} />
          <p className={s.saveStatus} role="status" aria-live="polite">
            {saveText}
          </p>
          {conflictBanner}
          {noticeBox}
          {restoredLocal && <FormAlert kind="warn">{M.restoredLocal}</FormAlert>}
          {staleDraft && canChange && (
            <div className="alert-box warn" role="status" data-stale-draft>
              <Icon name="warning" />
              <span>
                <strong>{M.staleDraftTitle}</strong> {M.staleDraftBody}
              </span>
              <button type="button" className="btn primary" onClick={dropStaleDraft}>
                {M.staleDraftUseServer}
              </button>
              <button type="button" className="btn" onClick={keepStaleDraft}>
                {M.staleDraftKeep}
              </button>
            </div>
          )}
          {meta.status === "pending_review" && (
            <div className="alert-box info" role="status">
              <Icon name="info" />
              <span>{M.pendingBanner}</span>
            </div>
          )}
          {meta.status === "draft" && meta.returnReason && <FormAlert kind="warn">{M.returnedBanner(reasonLabelOf(meta.returnReason))}</FormAlert>}
          {meta.status === "unpublished" && meta.returnReason && <FormAlert kind="warn">{M.unpublishedBanner(reasonLabelOf(meta.returnReason))}</FormAlert>}
          {meta.status === "published" && meta.hasUnpublishedChanges && (
            <div className="alert-box info" role="status">
              <Icon name="info" />
              <span>{M.unsavedChangesBanner}</span>
              {canChange && (
                <button type="button" className="btn" onClick={() => setDialog({ t: "discard" })}>
                  {M.discardChanges}
                </button>
              )}
            </div>
          )}

          <div className={s.editGrid}>
            <div className={s.editMain}>
              <Field
                label={M.fieldTitle}
                required
                value={form.title}
                maxLength={200}
                disabled={readOnly}
                placeholder={M.fieldTitlePlaceholder}
                error={fieldErrors.title}
                onChange={(v) => edit({ title: v })}
              />
              <div>
                <Field
                  label={M.fieldPath}
                  value={form.slug}
                  maxLength={200}
                  disabled={readOnly || meta.slugLocked}
                  placeholder={M.fieldPathPlaceholder}
                  error={fieldErrors.slug}
                  onChange={(v) => edit({ slug: v })}
                />
                {meta.slugLocked && <p className={s.fieldNote}>{M.pathLocked}</p>}
                {slugSuggestion && (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => {
                      edit({ slug: slugSuggestion });
                      setSlugSuggestion(null);
                    }}
                  >
                    {M.pathSuggest(slugSuggestion)}
                  </button>
                )}
              </div>
              <div className={s.bodyField}>
                <span className={s.bodyLabel} id="entry-body-label">
                  {M.fieldBody}
                </span>
                {fieldErrors.body && <p className="field-err">{fieldErrors.body}</p>}
                <Suspense fallback={<div className={s.editorLoading} role="status">{M.editorLoading}</div>}>
                  <TiptapEditor ref={editorRef} value={form.body} disabled={readOnly} onChange={(body) => edit({ body })} />
                </Suspense>
              </div>
              <ImageUploader
                entryId={entryId}
                images={images}
                coverImageId={form.coverImageId}
                disabled={readOnly}
                defaultAlt={form.title}
                onImageUploaded={(img) => {
                  setImages((list) => [...list, img]);
                  toast.success(M.imageUploaded);
                }}
                onSetCover={(id) => {
                  editSettings({ coverImageId: id });
                  toast.success(M.imageCoverSet);
                }}
                onInsertToContent={(img) => {
                  editorRef.current?.insertImage({ id: img.id, alt: img.alt, url: img.urls.md || img.urls.sm || img.urls.lg });
                  toast.success(M.imageInserted);
                }}
                onUpdateAlt={async (imageId, alt) => {
                  const updated = await updateImageAlt(imageId, alt);
                  setImages((list) => list.map((i) => (i.id === updated.id ? updated : i)));
                  if (form.coverImageId === imageId) setCoverAlt(updated.alt);
                  toast.success(M.imageAltSaved);
                }}
              />
            </div>

            <aside className={s.editSide} aria-label={M.publishInfo}>
              <section className={s.card}>
                <h3 className={s.cardTitle}>{M.publishInfo}</h3>
                <dl className={s.infoList}>
                  <div>
                    <dt>{M.infoKind}</dt>
                    <dd>{form.kind === "page" ? M.kindPageOption : M.kindPostOption}</dd>
                  </div>
                  {form.kind === "post" && (
                    <div>
                      <dt>{M.infoCategory}</dt>
                      <dd>{form.category !== null ? (categoryName.get(form.category) ?? M.infoEmpty) : M.infoEmpty}</dd>
                    </div>
                  )}
                  {meta.publishedVersion !== null && (
                    <div>
                      <dt>{M.infoRevision}</dt>
                      <dd>{M.revision(meta.publishedVersion)}</dd>
                    </div>
                  )}
                  <div>
                    <dt>{M.infoExcerpt}</dt>
                    <dd className={s.clamp}>{form.excerpt.trim() || <span className="muted">{M.infoEmpty}</span>}</dd>
                  </div>
                  <div>
                    <dt>{M.infoSeoTitle}</dt>
                    <dd className={s.clamp}>{form.seoTitle.trim() || <span className="muted">{M.infoEmpty}</span>}</dd>
                  </div>
                  <div>
                    <dt>{M.infoSeoDescription}</dt>
                    <dd className={s.clamp}>{form.seoDescription.trim() || <span className="muted">{M.infoEmpty}</span>}</dd>
                  </div>
                </dl>
                {cover && (
                  <div className={s.coverPreview}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={cover.urls.sm || cover.urls.md || cover.urls.lg} alt={cover.alt || M.sectionCover} />
                  </div>
                )}
                {meta.status === "published" && meta.publicUrl && isSafeHref(meta.publicUrl) && (
                  <a className="inline-link" href={meta.publicUrl} target="_blank" rel="noopener noreferrer">
                    Xem trên website
                  </a>
                )}
                <button type="button" className="btn" onClick={() => setView("settings")}>
                  <Icon name="edit_note" />
                  <span>{M.settingsOpen}</span>
                </button>
              </section>
            </aside>
          </div>
        </>
      )}

      {settingsView && (
        <EntrySettings
          form={form}
          onChange={editSettings}
          categories={categories}
          categoriesFailed={!!categoriesRes.error && form.kind === "post"}
          images={images}
          coverAlt={coverAlt}
          onCoverAlt={(v) => {
            setCoverAlt(v);
            setDirty(true);
            editSeq.current += 1;
            setFieldErrors({});
          }}
          fieldErrors={fieldErrors}
          alert={
            <>
              {conflictBanner}
              {noticeBox}
            </>
          }
          saved={saved}
          pageRoleLocked={form.kind === "page" && meta.status === "published" && form.pageRole !== null}
          isDraft={meta.status === "draft"}
          readOnly={readOnly}
          submitting={busy}
          onSave={() => void onSaveSettings()}
          onBack={() => setView("write")}
          onSubmitReview={action === "submit" ? onSubmitFromSettings : null}
        />
      )}

      {dialog?.t === "checklist" && <ChecklistModal revision={meta.status === "published"} run={() => runPublish(false)} onClose={() => setDialog(null)} />}
      {dialog?.t === "warnings" && (
        <WarningsModal
          warnings={dialog.warnings}
          action={dialog.action}
          run={() => (dialog.action === "publish" ? runPublish(true) : runSubmit(true))}
          onClose={() => setDialog(null)}
        />
      )}
      {dialog?.t === "return" && <ReasonModal mode="return" articleTitle={form.title} run={runReturn} onClose={() => setDialog(null)} />}
      {dialog?.t === "unpublish" && <ReasonModal mode="unpublish" articleTitle={form.title} run={runUnpublish} onClose={() => setDialog(null)} />}
      {dialog?.t === "history" && entryId !== null && (
        <HistoryModal entryId={entryId} onRestore={(version) => setDialog({ t: "restore", version })} onClose={() => setDialog(null)} />
      )}
      {dialog?.t === "delete" && entryId !== null && (
        <ConfirmModal
          title={M.deleteTitle}
          confirmLabel={M.deleteConfirm}
          busyLabel={M.deleteBusy}
          danger
          disabled={!canDeleteEntry(facts)}
          run={() => deleteEntry(entryId)}
          errorText={(err) => errorText(err, M.genericFail)}
          onDone={() => {
            leavingRef.current = true;
            clearDraft(draftKeyOf(entryId));
            toast.success("Đã xoá nháp.");
            router.push("/content/");
          }}
          onClose={() => setDialog(null)}
        >
          <p>{M.deleteBody}</p>
        </ConfirmModal>
      )}
      {dialog?.t === "discard" && entryId !== null && (
        <ConfirmModal
          title={M.discardTitle}
          confirmLabel={M.discardConfirm}
          busyLabel={M.discardBusy}
          danger
          run={() => discardChanges(entryId, { row_version: metaRef.current.rowVersion })}
          errorText={(err) => errorText(err, M.genericFail)}
          onReload={() => setDialog({ t: "reload" })}
          noun={M.conflictBannerNoun}
          onDone={(d) => {
            clearDraft(draftKeyOf(entryId));
            applyServer(d);
            setDialog(null);
            toast.success(M.discarded);
          }}
          onClose={() => setDialog(null)}
        >
          <p>{M.discardBody}</p>
        </ConfirmModal>
      )}
      {dialog?.t === "restore" && entryId !== null && (
        <ConfirmModal
          title={M.restoreTitle}
          confirmLabel={M.restoreConfirm}
          busyLabel={M.restoreBusy}
          run={() => restoreEntryVersion(entryId, dialog.version, { row_version: metaRef.current.rowVersion })}
          errorText={(err) => errorText(err, M.genericFail)}
          onReload={() => setDialog({ t: "reload" })}
          noun={M.conflictBannerNoun}
          onDone={(d) => {
            clearDraft(draftKeyOf(entryId));
            applyServer(d);
            setDialog(null);
            setView("write");
            toast.success(M.restored(dialog.version));
          }}
          onClose={() => setDialog(null)}
        >
          <p>{M.restoreBody}</p>
        </ConfirmModal>
      )}
      {dialog?.t === "reload" && (
        <ConfirmModal
          title={M.reloadTitle}
          confirmLabel={M.reloadConfirm}
          busyLabel={M.reloadBusy}
          run={reloadFromServer}
          errorText={(err) => errorText(err, M.loadFailed)}
          onDone={() => {
            setDialog(null);
            toast.success(M.reloaded);
          }}
          onClose={() => setDialog(null)}
        >
          <p>{M.reloadBody}</p>
        </ConfirmModal>
      )}

      {/* SR-19: xem đúng phiên bản chính sách khách đã đồng ý, chỉ đọc, không khôi phục. */}
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
    </div>
  );
}
