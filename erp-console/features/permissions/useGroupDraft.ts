"use client";

// Bản nháp của trang nhóm W3i (PV-11, PV-09, PV-10): việc và phạm vi đổi TRONG BỘ NHỚ; "Lưu thay đổi" gửi MỘT PUT có `version`.
// Luồng lưu: xem trước ảnh hưởng (POST preview; lỗi mạng thì bỏ qua, BE vẫn chặn ở PUT) → nếu mở rộng dữ liệu khách / thu hẹp có dòng
// bị ảnh hưởng / tắt việc làm hỏng màn → hộp xác nhận → PUT có `confirm_customer_data_widening`. Không có gì đáng hỏi → PUT thẳng.
// PUT trả 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED → mở hộp bằng `impact`, giữ nguyên lựa chọn (PV-09-AC15).
// PUT trả 409 GROUP_CHANGED → báo "Tải lại", KHÔNG tự gửi lại; "Tải lại" xoá bản nháp và lấy bản server (PV-10-AC6, AC7).
// Không lưu bản nháp vào storage/URL, không log thân yêu cầu.

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { useToast } from "@/shared/ui/overlay/Toast";
import { previewGroupChanges, saveGroupChanges } from "./api";
import { PERM_MSG as M } from "./messages";
import {
  EMPTY_DRAFT,
  breakingWarnings,
  cleanDraft,
  draftProblem,
  draftSize,
  saveBodyOf,
  setScopeInDraft,
  toggleInDraft,
  type Draft,
} from "./permissionsModel";
import { isGroupChanged, wideningImpactOf } from "./saveErrors";
import type { GroupDetail, ScopePreview } from "./types";

export type SaveConfirm = { preview: ScopePreview | null; breaking: string[] };

type Args = {
  group: GroupDetail;
  /** BE trả chi tiết nhóm mới sau PUT. */
  onSaved: (next: GroupDetail) => void;
  /** Tải lại từ server (nút "Tải lại" ở thông báo 409). */
  reload: () => Promise<void>;
};

export function useGroupDraft({ group, onSaved, reload }: Args) {
  const toast = useToast();
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [confirm, setConfirm] = useState<SaveConfirm | null>(null);
  const inFlight = useRef(false);

  const states = group.capabilities;
  const values = group.data_scope_values;
  const size = draftSize(draft);
  const problem = useMemo(() => draftProblem(group.code, states, values, draft), [group.code, states, values, draft]);

  // Rời trang khi còn thay đổi chưa lưu (PV-11-AC5): đóng tab/tải lại → trình duyệt hỏi; bấm link nội bộ trong app → confirm rồi mới chuyển.
  // (Nút Back của trình duyệt chưa chặn.) Bắt click ở pha capture để chạy trước bộ chuyển trang của Next.
  useEffect(() => {
    if (size === 0) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor || (anchor.target && anchor.target !== "_self") || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname + url.search === window.location.pathname + window.location.search) return;
      e.preventDefault();
      e.stopPropagation();
      if (window.confirm(M.draftLeave)) router.push(url.pathname + url.search + url.hash);
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", onClick, true);
    return () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", onClick, true);
    };
  }, [size, router]);

  // L3: `version` đổi (vd sau thêm/bỏ thành viên làm tải lại) khi đang có nháp mà không do lần Lưu của mình → coi là xung đột,
  // để lần Lưu sau không ngầm đổi base và nuốt thay đổi của người khác chen vào giữa.
  const baseVersion = useRef<string | null>(null);
  useEffect(() => {
    if (size === 0) {
      baseVersion.current = group.version;
      return;
    }
    if (baseVersion.current === null) baseVersion.current = group.version;
    else if (baseVersion.current !== group.version) setConflict(true);
  }, [size, group.version]);

  const toggleCap = useCallback(
    (key: string) => {
      setSaveError(null);
      setFailed(false);
      setDraft((cur) => toggleInDraft(group.registry, states, values, cur, key)?.draft ?? cur);
    },
    [group.registry, states, values],
  );

  const setScope = useCallback(
    (key: string, value: string) => {
      setSaveError(null);
      setFailed(false);
      setDraft((cur) => setScopeInDraft(states, values, cur, key, value));
    },
    [states, values],
  );

  const discard = useCallback(() => {
    setDraft(EMPTY_DRAFT);
    setSaveError(null);
    setFailed(false);
  }, []);

  /** PUT thật. Ném lỗi (trừ 409: đặt `conflict` rồi trả về bình thường để hộp xác nhận tự đóng). */
  const commit = useCallback(
    async (withConfirm: boolean): Promise<void> => {
      try {
        const next = await saveGroupChanges(group.code, saveBodyOf(group.version, cleanDraft(draft, states, values), withConfirm));
        onSaved(next);
        setDraft(EMPTY_DRAFT);
        setSaveError(null);
        setFailed(false);
        toast.success(M.draftSaved);
      } catch (err) {
        if (isGroupChanged(err)) {
          setConflict(true);
          return;
        }
        throw err;
      }
    },
    [draft, group.code, group.version, onSaved, states, values, toast],
  );

  /** Bấm "Lưu thay đổi". */
  const save = useCallback(async () => {
    if (inFlight.current || size === 0 || problem) return;
    inFlight.current = true;
    setSaving(true);
    setSaveError(null);
    setFailed(false);
    try {
      const clean = cleanDraft(draft, states, values);
      let preview: ScopePreview | null = null;
      try {
        preview = await previewGroupChanges(group.code, {
          ...(Object.keys(clean.capabilities).length ? { capabilities: clean.capabilities } : {}),
          ...(Object.keys(clean.scopes).length ? { scopes: clean.scopes } : {}),
        });
      } catch (err) {
        // Xem trước hỏng (mạng/5xx) thì bỏ qua: BE vẫn chặn mở rộng chưa xác nhận ở PUT. Lỗi 400 nghiệp vụ của xem trước hiện luôn.
        if (err instanceof ApiError && (err.status === 400 || err.status === 403 || err.status === 404)) throw err;
        if (err instanceof ApiError && err.status === 401) return;
      }
      const breaking = breakingWarnings(group.registry, states, clean, group.member_count).map((b) => b.text);
      const narrowedRows = (preview?.narrowed ?? []).some((n) => n.rows_losing_access > 0);
      if (preview?.widens_customer_data || narrowedRows || breaking.length > 0) {
        setConfirm({ preview, breaking });
        return;
      }
      await commit(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      const impact = wideningImpactOf(err);
      if (impact) {
        setConfirm({ preview: impact, breaking: [] });
      } else {
        setSaveError(errorText(err, M.saveFailed));
        setFailed(true);
      }
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }, [commit, draft, group.code, group.member_count, group.registry, problem, size, states, values]);

  /** "Tôi hiểu, lưu" / "Lưu thay đổi" ở hộp xác nhận. Ném lỗi để hộp hiện alert và giữ mở. */
  const confirmSave = useCallback(async () => {
    try {
      await commit(true);
    } catch (err) {
      const impact = wideningImpactOf(err);
      if (impact) {
        setConfirm({ preview: impact, breaking: [] });
        return;
      }
      throw err;
    }
  }, [commit]);

  const cancelConfirm = useCallback(() => setConfirm(null), []);

  /** "Tải lại" ở thông báo 409: bỏ bản nháp, lấy bản server (không trộn). */
  const reloadAfterConflict = useCallback(async () => {
    setReloading(true);
    try {
      await reload();
      setDraft(EMPTY_DRAFT);
      setConflict(false);
      setSaveError(null);
      setFailed(false);
    } finally {
      setReloading(false);
    }
  }, [reload]);

  return {
    draft,
    size,
    problem,
    saving,
    saveError,
    failed,
    conflict,
    reloading,
    confirm,
    toggleCap,
    setScope,
    discard,
    save,
    confirmSave,
    cancelConfirm,
    reloadAfterConflict,
  };
}
