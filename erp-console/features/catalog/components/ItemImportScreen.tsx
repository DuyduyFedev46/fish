"use client";

// M2–M6 — Trang Nhập mặt hàng từ Excel: /catalog/import/ (FISH-66 S5, S6; 02a §3–§7, 02b §10).
// - Chỉ người có đủ 4 quyền IMPORT_PERMS (`ability.canImport`) mới dùng được; thiếu quyền hiện `NoPermission`.
// - Giữ `File` và `preview_token` trong state của trang, tuyệt đối không lưu vào URL hay localStorage/sessionStorage.
// - Khi gặp 409 IMPORT_DATA_CHANGED hoặc 410 IMPORT_PREVIEW_EXPIRED, hiện banner vàng W2/W3 kèm nút "Xem trước lại" gửi lại chính `File` đang giữ.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { SkeletonTable } from "@/shared/ui/Skeleton";
import { Section } from "@/shared/ui/detail/Section";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import {
  commitImport,
  exportItems,
  exportTemplate,
  getImportLimits,
  previewImport,
} from "../itemFilesApi";
import {
  extractAlreadyAppliedCounts,
  extractRowErrors,
  formatActionBarSummary,
  formatImportSuccessToast,
  formatMaxMb,
  formatMaxRows,
  groupReadonlyWarnings,
  validateImportFile,
} from "../itemFilesModel";
import {
  IMPORT_ALREADY_APPLIED,
  IMPORT_DATA_CHANGED,
  IMPORT_INVALID_FILE,
  IMPORT_PREVIEW_EXPIRED,
  IMPORT_PREVIEW_INVALID,
  type ImportLimits,
  type ImportPreviewResponse,
  type ImportRowErrorsDetails,
} from "../itemFilesTypes";
import { CATALOG_MSG as CM, ITEM_IMPORT_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import { EMPTY_ITEM_PARAMS } from "../types";
import { ImportConfirmModal, type CommitModalError } from "./ImportConfirmModal";
import { ImportErrors } from "./ImportErrors";
import { ImportPreview } from "./ImportPreview";
import s from "../catalog.module.css";

type Step =
  | "idle"
  | "reading"
  | "preview"
  | "no_changes"
  | "errors"
  | "forbidden_preview";

type StaleBanner = {
  kind: "data_changed" | "expired" | "invalid_token";
  message: string;
} | null;

export function ItemImportScreen() {
  const { me } = useAuth();
  const ability = catalogAbility(me?.permissions ?? []);
  if (!me) return null;
  if (!ability.canImport) return <NoPermission />;
  return <ItemImportBody />;
}

function ItemImportBody() {
  const router = useRouter();
  const toast = useToast();

  const [limits, setLimits] = useState<ImportLimits>({
    max_rows: 1000,
    max_bytes: 2097152,
    preview_ttl_minutes: 30,
  });
  const [step, setStep] = useState<Step>("idle");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [canRetryPreview, setCanRetryPreview] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [downloadBusy, setDownloadBusy] = useState<"list" | "template" | null>(null);

  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null);
  const [rowErrors, setRowErrors] = useState<ImportRowErrorsDetails | null>(null);
  const [staleBanner, setStaleBanner] = useState<StaleBanner>(null);
  const [liveAnnouncement, setLiveAnnouncement] = useState("");

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [commitBusy, setCommitBusy] = useState(false);
  const [commitError, setCommitError] = useState<CommitModalError>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileErrorId = useId();

  useEffect(() => {
    const ctrl = new AbortController();
    getImportLimits(ctrl.signal)
      .then((res) => {
        if (res && typeof res.max_rows === "number" && typeof res.max_bytes === "number") {
          setLimits(res);
        }
      })
      .catch(() => {
        // Giữ mặc định 1.000 dòng / 2 MB nếu chưa lấy được limits
      });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    if (!commitBusy) return;
    function onBeforeUnload(e: BeforeUnloadEvent) {
      e.preventDefault();
      e.returnValue = "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [commitBusy]);

  function focusHeadingSoon() {
    window.requestAnimationFrame(() => {
      headingRef.current?.focus();
    });
  }

  function openFilePicker() {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  }

  async function runPreview(file: File) {
    setSelectedFile(file);
    setFileError(null);
    setCanRetryPreview(false);
    setStaleBanner(null);

    const localErr = validateImportFile(file, limits);
    if (localErr) {
      setStep("idle");
      setFileError(localErr);
      return;
    }

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setStep("reading");

    try {
      const res = await previewImport(file, ctrl.signal);
      if (res.limits) setLimits((prev) => ({ ...prev, ...res.limits }));
      setPreviewData(res);
      setRowErrors(null);
      if (res.has_changes) {
        setStep("preview");
        setLiveAnnouncement(`Đã đọc file: ${formatActionBarSummary(res.summary)}`);
      } else {
        setStep("no_changes");
        setLiveAnnouncement(M.noChangesTitle);
      }
      focusHeadingSoon();
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      const extractedRows = extractRowErrors(err);
      if (extractedRows) {
        if (extractedRows.limits) setLimits((prev) => ({ ...prev, ...extractedRows.limits }));
        setRowErrors(extractedRows);
        setPreviewData(null);
        setStep("errors");
        setLiveAnnouncement(
          M.errRowSummary(extractedRows.error_count, extractedRows.error_row_count),
        );
        focusHeadingSoon();
        return;
      }
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setStep("forbidden_preview");
          return;
        }
        if (err.code === IMPORT_INVALID_FILE || err.status === 400) {
          const d = (err.details || {}) as { limits?: ImportLimits };
          if (d.limits) setLimits((prev) => ({ ...prev, ...d.limits }));
          setStep("idle");
          setFileError(err.message || M.errUnreadable);
          return;
        }
      }
      setStep("idle");
      setFileError(M.errNetworkPreview);
      setCanRetryPreview(true);
    }
  }

  function handleCancelReading() {
    abortRef.current?.abort();
    setStep("idle");
  }

  async function handleDownload(kind: "list" | "template") {
    if (downloadBusy) return;
    setDownloadBusy(kind);
    try {
      if (kind === "list") {
        const saved = await exportItems(EMPTY_ITEM_PARAMS);
        if (saved.rowCount === 0) toast.warn(CM.fileDownloadedEmpty);
        else toast.success(CM.fileDownloaded(saved.filename, saved.rowCount, false));
      } else {
        const saved = await exportTemplate();
        toast.success(CM.templateDownloaded(saved.filename));
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error(CM.fileForbidden);
      } else {
        toast.error(kind === "list" ? CM.fileFailed : CM.templateFailed);
      }
    } finally {
      setDownloadBusy(null);
    }
  }

  async function handleConfirmCommit() {
    if (!previewData?.preview_token || !selectedFile || commitBusy) return;
    setCommitBusy(true);
    setCommitError(null);
    try {
      const res = await commitImport(selectedFile, previewData.preview_token);
      setConfirmOpen(false);
      toast.success(formatImportSuccessToast(res));
      router.push("/catalog/?tab=items");
    } catch (err) {
      const alreadyCounts = extractAlreadyAppliedCounts(err);
      if (alreadyCounts || (err instanceof ApiError && err.code === IMPORT_ALREADY_APPLIED)) {
        setConfirmOpen(false);
        toast.success(M.toastAlreadyApplied);
        router.push("/catalog/?tab=items");
        return;
      }
      if (err instanceof ApiError) {
        if (err.status === 409 && err.code === IMPORT_DATA_CHANGED) {
          setConfirmOpen(false);
          setStaleBanner({
            kind: "data_changed",
            message: err.message || M.bannerDataChanged,
          });
          return;
        }
        if (err.status === 410 || err.code === IMPORT_PREVIEW_EXPIRED) {
          setConfirmOpen(false);
          setStaleBanner({
            kind: "expired",
            message: err.message || M.bannerExpired,
          });
          return;
        }
        if (err.status === 400 && err.code === IMPORT_PREVIEW_INVALID) {
          setConfirmOpen(false);
          setStaleBanner({
            kind: "invalid_token",
            message: err.message || M.bannerDataChanged,
          });
          return;
        }
        if (err.status === 403) {
          setCommitError({ kind: "forbidden", message: M.errForbiddenCommit });
          return;
        }
        if (err.status === 0) {
          setCommitError({ kind: "network", message: M.errNetworkCommit });
          return;
        }
      }
      setCommitError({ kind: "server", message: M.errServerCommit });
    } finally {
      setCommitBusy(false);
    }
  }

  function renderActionBar() {
    if (step === "reading") {
      return (
        <button type="button" className="btn" onClick={handleCancelReading}>
          {M.cancel}
        </button>
      );
    }
    if (step === "preview" && previewData) {
      return (
        <div className={s.barSpread}>
          <span className={s.barSummary} data-testid="import-bar-summary">
            {formatActionBarSummary(previewData.summary)}
          </span>
          <div className={s.barButtons}>
            <button
              type="button"
              className="btn"
              onClick={openFilePicker}
              data-testid="import-choose-another"
            >
              {M.chooseAnotherFile}
            </button>
            <Link href="/catalog/?tab=items" className="btn">
              {M.cancel}
            </Link>
            <button
              type="button"
              className="btn primary"
              onClick={() => {
                setCommitError(null);
                setConfirmOpen(true);
              }}
              data-testid="import-open-confirm"
            >
              {M.confirmImport}
            </button>
          </div>
        </div>
      );
    }
    if (step === "no_changes") {
      return (
        <>
          <button
            type="button"
            className="btn"
            onClick={openFilePicker}
            data-testid="import-choose-another"
          >
            {M.chooseAnotherFile}
          </button>
          <Link href="/catalog/?tab=items" className="btn primary">
            {M.backToList}
          </Link>
        </>
      );
    }
    if (step === "errors") {
      return (
        <>
          <Link href="/catalog/?tab=items" className="btn">
            {M.cancel}
          </Link>
          <button
            type="button"
            className="btn primary"
            onClick={openFilePicker}
            data-testid="import-choose-another"
          >
            {M.chooseAnotherFile}
          </button>
        </>
      );
    }
    return (
      <Link href="/catalog/?tab=items" className="btn">
        {M.cancel}
      </Link>
    );
  }

  const noChangesWarnings =
    step === "no_changes" && previewData ? groupReadonlyWarnings(previewData.warnings) : [];

  return (
    <div className={s.importPage} data-testid="import-screen">
      <header className={s.importHead}>
        <Link href="/catalog/?tab=items" className={s.importBack}>
          <Icon name="arrow_back" />
          <span>{M.back}</span>
        </Link>
        <h2 className={s.importTitle}>{M.title}</h2>
      </header>

      <div className="sr-only" aria-live="polite">
        {liveAnnouncement}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className={s.fileInput}
        aria-label={M.chooseFile}
        aria-invalid={Boolean(fileError) || undefined}
        aria-describedby={fileError ? fileErrorId : undefined}
        data-testid="import-file-input"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void runPreview(f);
        }}
      />

      <div className={s.importStack}>
        {/* Banner W2 / W3 khi 409 IMPORT_DATA_CHANGED hoặc 410 IMPORT_PREVIEW_EXPIRED */}
        {staleBanner && (
          <div className="alert-box warn" role="alert" data-testid="import-stale-banner">
            <Icon name="warning" />
            <div className={s.bannerRow}>
              <span>{staleBanner.message}</span>
              {selectedFile ? (
                <button
                  type="button"
                  className="btn primary"
                  onClick={() => void runPreview(selectedFile)}
                  data-testid="import-repreview-button"
                >
                  {M.repreview}
                </button>
              ) : (
                <button
                  type="button"
                  className="btn primary"
                  onClick={openFilePicker}
                  data-testid="import-choose-another"
                >
                  {M.chooseAnotherFile}
                </button>
              )}
            </div>
          </div>
        )}

        {/* E21: mất quyền khi đọc file */}
        {step === "forbidden_preview" && (
          <div className="alert-box err" role="alert" data-testid="import-forbidden-alert">
            <Icon name="error" />
            <div className={s.bannerRow}>
              <span>{M.errForbiddenPreview}</span>
              <Link href="/catalog/?tab=items" className="btn">
                {M.backToList}
              </Link>
            </div>
          </div>
        )}

        {/* M2 — Chọn file hoặc Đang đọc file */}
        {(step === "idle" || step === "reading") && (
          <>
            <div
              className={[
                s.dropZone,
                dragActive ? s.dropZoneActive : "",
                fileError ? s.dropZoneError : "",
                step === "reading" ? s.dropZoneBusy : "",
              ]
                .filter(Boolean)
                .join(" ")}
              aria-busy={step === "reading" || undefined}
              onDragOver={(e) => {
                e.preventDefault();
                if (step !== "reading") setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                if (step === "reading") return;
                const f = e.dataTransfer.files?.[0];
                if (f) void runPreview(f);
              }}
              data-testid="import-dropzone"
            >
              <div className={s.dropRow}>
                <div className={s.dropMain}>
                  <button
                    type="button"
                    className="btn primary"
                    onClick={openFilePicker}
                    disabled={step === "reading"}
                    data-testid="import-choose-button"
                  >
                    <Icon name="swap_vert" />
                    <span>
                      {step === "reading"
                        ? M.readingFile
                        : selectedFile
                          ? M.chooseAnotherFile
                          : M.chooseFile}
                    </span>
                  </button>
                  <p className={s.dropHint}>
                    {selectedFile ? selectedFile.name : M.dropHint}
                  </p>
                </div>

                <div className={s.dropLinks}>
                  <button
                    type="button"
                    className={s.linkBtn}
                    onClick={() => void handleDownload("list")}
                    disabled={downloadBusy !== null || step === "reading"}
                    data-testid="import-download-current"
                  >
                    <Icon name="description" />
                    <span>{M.downloadCurrent}</span>
                  </button>
                  <button
                    type="button"
                    className={s.linkBtn}
                    onClick={() => void handleDownload("template")}
                    disabled={downloadBusy !== null || step === "reading"}
                    data-testid="import-download-template"
                  >
                    <Icon name="description" />
                    <span>{M.downloadTemplate}</span>
                  </button>
                </div>
              </div>

              {fileError && (
                <div
                  id={fileErrorId}
                  className="alert-box err"
                  role="alert"
                  data-testid="import-file-error"
                >
                  <Icon name="error" />
                  <div className={s.bannerRow}>
                    <span>{fileError}</span>
                    {canRetryPreview && selectedFile && (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => void runPreview(selectedFile)}
                        data-testid="import-retry-preview"
                      >
                        {M.retry}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>

            {step === "reading" ? (
              <div data-testid="import-reading-skeleton">
                <SkeletonTable rows={3} cols={6} />
              </div>
            ) : (
              <Section title={M.guideTitle}>
                <dl className={s.guideList} data-testid="import-guide">
                  <dt className={s.guideTerm}>{M.guideIdentifyLabel}</dt>
                  <dd className={s.guideDef}>{M.guideIdentifyValue}</dd>

                  <dt className={s.guideTerm}>{M.guideMissingLabel}</dt>
                  <dd className={s.guideDef}>{M.guideMissingValue}</dd>

                  <dt className={s.guideTerm}>{M.guideBlankTextLabel}</dt>
                  <dd className={s.guideDef}>{M.guideBlankTextValue}</dd>

                  <dt className={s.guideTerm}>{M.guideBlankPriceLabel}</dt>
                  <dd className={s.guideDef}>{M.guideBlankPriceValue}</dd>

                  <dt className={s.guideTerm}>{M.guideReadonlyLabel}</dt>
                  <dd className={s.guideDef}>{M.guideReadonlyValue}</dd>

                  <dt className={s.guideTerm}>{M.guideInventoryLabel}</dt>
                  <dd className={s.guideDef}>{M.guideInventoryValue}</dd>

                  <dt className={s.guideTerm}>{M.guideLimitLabel}</dt>
                  <dd className={s.guideDef} data-testid="import-guide-limits">
                    {M.guideLimitValue(
                      formatMaxRows(limits.max_rows),
                      formatMaxMb(limits.max_bytes),
                    )}
                  </dd>
                </dl>
              </Section>
            )}
          </>
        )}

        {/* M3 rỗng — N1 "File không có gì mới" */}
        {step === "no_changes" && (
          <div className={s.importStack} data-testid="import-no-changes">
            <h2 ref={headingRef} tabIndex={-1} className="sr-only">
              {M.noChangesTitle}
            </h2>
            {noChangesWarnings.map((w) => (
              <div key={w.column} className="alert-box warn" role="status">
                <Icon name="warning" />
                <div>{w.text}</div>
              </div>
            ))}
            <div className="alert-box info" role="status">
              <Icon name="info" />
              <div>
                <strong>{M.noChangesTitle}</strong> {M.noChangesBody}
              </div>
            </div>
          </div>
        )}

        {/* M3 — Xem trước thay đổi */}
        {step === "preview" && previewData && (
          <ImportPreview preview={previewData} headingRef={headingRef} />
        )}

        {/* M4 — Bảng lỗi theo dòng */}
        {step === "errors" && rowErrors && (
          <ImportErrors details={rowErrors} headingRef={headingRef} />
        )}
      </div>

      <div className={s.importBar} data-action-bar>
        {renderActionBar()}
      </div>

      {/* M5 — Hộp xác nhận nhập */}
      {previewData && previewData.has_changes && (
        <ImportConfirmModal
          open={confirmOpen}
          preview={previewData}
          busy={commitBusy}
          error={commitError}
          onClose={() => {
            if (!commitBusy) setConfirmOpen(false);
          }}
          onConfirm={() => void handleConfirmCommit()}
        />
      )}
    </div>
  );
}
