"use client";

// Bật/tắt MỘT việc của một nhóm (dùng chung ma trận W3h — nhiều nhóm — và chi tiết nhóm W3i — một nhóm). Luồng:
//   bấm ô → planToggle (cặp `requires` đổi cùng lúc) → tắt việc làm hỏng màn thì HỎI LẠI trước (`pendingOff`) → PUT →
//   BE trả chi tiết nhóm mới → `onSaved` (màn thay dữ liệu) + toast "Hoàn tác" (hoàn tác = PUT ngược; không đưa về đúng cũ được thì không hiện nút).
// Lỗi (400 BR-PQ-32 / CAPABILITY_REQUIRES / GROUP_LOCKED, 403 không phải Chủ…): hiện NGUYÊN VĂN câu BE, giá trị trên màn không đổi.
// Không có cập nhật "lạc quan": ô chỉ đổi khi BE đã nhận, nên không bao giờ hiện quyền chưa lưu.
// PV-10: mọi PUT gửi `version` của nhóm; 409 → báo "Nhóm này vừa được người khác đổi…" và tải lại (`onConflict`), không tự gửi lại.
// PV-09: 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED → mở hộp cảnh báo bằng `impact` rồi gửi lại có xác nhận. PO-Q1: bật "Xem khách hàng"
// khi Khách hàng = Không xem thì gửi kèm `scopes.customers = "all"`.

import { useCallback, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { useToast } from "@/shared/ui/overlay/Toast";
import { saveGroupChanges } from "./api";
import { PERM_MSG as M } from "./messages";
import { breakingWarning, planToggle, toggleMessage, type TogglePlan } from "./permissionsModel";
import { CUSTOMERS_KEY } from "./permissionsModel";
import { isGroupChanged, wideningImpactOf } from "./saveErrors";
import type { CapabilityState, GroupDetail, GroupSaveBody, RegistryItem, ScopePreview } from "./types";

/** Nhóm bị bấm: mã, nhãn, trạng thái hiện tại các việc, số người (cho câu cảnh báo). */
export type ToggleGroup = {
  code: string;
  label: string;
  states: Record<string, CapabilityState>;
  memberCount: number;
  /** `version` của nhóm từ lần GET gần nhất (PV-10). */
  version: string;
  /** Giá trị phạm vi đã lưu (cần để áp PO-Q1 khi bật "Xem khách hàng"). */
  scopeValues?: Record<string, string>;
};

export type PendingOff = { group: ToggleGroup; item: RegistryItem; plan: TogglePlan; warning: string };
/** Hộp cảnh báo mở rộng dữ liệu khách (BE trả 400 CUSTOMER_DATA_WIDENING_UNCONFIRMED kèm `impact`). */
export type PendingWiden = { group: ToggleGroup; item: RegistryItem; plan: TogglePlan; impact: ScopePreview };

type Args = {
  registry: RegistryItem[];
  /** BE trả chi tiết nhóm mới sau PUT. */
  onSaved: (next: GroupDetail) => void;
  /** 409: người khác vừa đổi nhóm → màn tải lại danh sách để thấy bản mới. */
  onConflict?: () => void;
};

/** Thân PUT cho một lần bật/tắt: `version` + việc (+ PO-Q1) (+ xác nhận). */
function bodyOf(group: ToggleGroup, plan: TogglePlan, confirm: boolean): GroupSaveBody {
  const body: GroupSaveBody = { version: group.version, capabilities: plan.changes };
  if (plan.changes[CUSTOMERS_KEY] === true && group.scopeValues?.customers === "none") body.scopes = { customers: "all" };
  if (confirm) body.confirm_customer_data_widening = true;
  return body;
}

/** Khoá ô đang gửi: `<mã nhóm>:<việc>`. */
export const cellKey = (group: string, key: string) => `${group}:${key}`;

export function useCapabilityToggle({ registry, onSaved, onConflict }: Args) {
  const toast = useToast();
  const [busyCells, setBusyCells] = useState<string[]>([]);
  const [pendingOff, setPendingOff] = useState<PendingOff | null>(null);
  const [pendingWiden, setPendingWiden] = useState<PendingWiden | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);
  const labelOf = useCallback((key: string) => registry.find((r) => r.key === key)?.label ?? key, [registry]);

  /** Sau khi BE nhận: thay dữ liệu, báo kết quả kèm "Hoàn tác" nếu đưa về đúng cũ được. */
  const saved = useCallback(
    (group: ToggleGroup, item: RegistryItem, plan: TogglePlan, next: GroupDetail) => {
      onSaved(next);
      const undo = plan.undo;
      toast.success(
        toggleMessage(item, group.label, plan, labelOf),
        undo
          ? {
              undo: () => {
                void saveGroupChanges(group.code, { version: next.version, capabilities: undo })
                  .then((back) => {
                    onSaved(back);
                    toast.success(`Đã hoàn tác “${item.label}” cho ${group.label}.`);
                  })
                  .catch((err) => {
                    if (isGroupChanged(err)) onConflict?.();
                    if (!(err instanceof ApiError && err.status === 401)) toast.error(errorText(err, M.saveFailed));
                  });
              },
            }
          : undefined,
      );
    },
    [labelOf, onSaved, onConflict, toast],
  );

  const send = useCallback(
    async (group: ToggleGroup, item: RegistryItem, plan: TogglePlan): Promise<void> => {
      if (inFlight.current) return;
      inFlight.current = true;
      setError(null);
      setBusyCells(Object.keys(plan.changes).map((k) => cellKey(group.code, k)));
      try {
        saved(group, item, plan, await saveGroupChanges(group.code, bodyOf(group, plan, false)));
      } catch (err) {
        const impact = wideningImpactOf(err);
        if (impact) {
          setPendingWiden({ group, item, plan, impact });
        } else if (!(err instanceof ApiError && err.status === 401)) {
          if (isGroupChanged(err)) onConflict?.();
          const text = errorText(err, M.saveFailed);
          setError(text);
          toast.error(text);
        }
      } finally {
        inFlight.current = false;
        setBusyCells([]);
      }
    },
    [saved, onConflict, toast],
  );

  /** Bấm một ô của một nhóm. */
  const toggle = useCallback(
    (group: ToggleGroup, key: string) => {
      if (inFlight.current) return;
      const item = registry.find((r) => r.key === key);
      const plan = planToggle(registry, group.states, key);
      if (!item || !plan) return;
      const warning = breakingWarning(key, plan.wanted, group.memberCount);
      if (warning) {
        setPendingOff({ group, item, plan, warning });
        return;
      }
      void send(group, item, plan);
    },
    [registry, send],
  );

  /** Đồng ý ở hộp xác nhận tắt. Ném lỗi để hộp xác nhận hiện alert và giữ nguyên. */
  const confirmOff = useCallback(async () => {
    if (!pendingOff) return;
    const { group, item, plan } = pendingOff;
    setError(null);
    try {
      const next = await saveGroupChanges(group.code, bodyOf(group, plan, false));
      setPendingOff(null);
      saved(group, item, plan, next);
    } catch (err) {
      const impact = wideningImpactOf(err);
      if (impact) {
        setPendingOff(null);
        setPendingWiden({ group, item, plan, impact });
        return;
      }
      if (isGroupChanged(err)) onConflict?.();
      throw err;
    }
  }, [pendingOff, saved, onConflict]);

  /** "Tôi hiểu, lưu" ở hộp cảnh báo mở rộng: gửi lại có xác nhận. Ném lỗi để hộp hiện alert và giữ mở. */
  const confirmWiden = useCallback(async () => {
    if (!pendingWiden) return;
    const { group, item, plan } = pendingWiden;
    setError(null);
    try {
      const next = await saveGroupChanges(group.code, bodyOf(group, plan, true));
      setPendingWiden(null);
      saved(group, item, plan, next);
    } catch (err) {
      if (isGroupChanged(err)) {
        setPendingWiden(null);
        onConflict?.();
        setError(errorText(err, M.saveFailed));
        return;
      }
      throw err;
    }
  }, [pendingWiden, saved, onConflict]);
  const cancelWiden = useCallback(() => setPendingWiden(null), []);

  const cancelOff = useCallback(() => setPendingOff(null), []);
  const clearError = useCallback(() => setError(null), []);

  return { toggle, busyCells, pendingOff, confirmOff, cancelOff, pendingWiden, confirmWiden, cancelWiden, error, clearError, labelOf };
}
