"use client";

// Bật/tắt MỘT việc của một nhóm (dùng chung ma trận W3h — nhiều nhóm — và chi tiết nhóm W3i — một nhóm). Luồng:
//   bấm ô → planToggle (cặp `requires` đổi cùng lúc) → tắt việc làm hỏng màn thì HỎI LẠI trước (`pendingOff`) → PUT →
//   BE trả chi tiết nhóm mới → `onSaved` (màn thay dữ liệu) + toast "Hoàn tác" (hoàn tác = PUT ngược; không đưa về đúng cũ được thì không hiện nút).
// Lỗi (400 BR-PQ-32 / CAPABILITY_REQUIRES / GROUP_LOCKED, 403 không phải Chủ…): hiện NGUYÊN VĂN câu BE, giá trị trên màn không đổi.
// Không có cập nhật "lạc quan": ô chỉ đổi khi BE đã nhận, nên không bao giờ hiện quyền chưa lưu.

import { useCallback, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { errorText } from "@/shared/lib/messages";
import { useToast } from "@/shared/ui/overlay/Toast";
import { setGroupCapabilities } from "./api";
import { PERM_MSG as M } from "./messages";
import { breakingWarning, planToggle, toggleMessage, type TogglePlan } from "./permissionsModel";
import type { CapabilityState, GroupDetail, RegistryItem } from "./types";

/** Nhóm bị bấm: mã, nhãn, trạng thái hiện tại các việc, số người (cho câu cảnh báo). */
export type ToggleGroup = { code: string; label: string; states: Record<string, CapabilityState>; memberCount: number };

export type PendingOff = { group: ToggleGroup; item: RegistryItem; plan: TogglePlan; warning: string };

type Args = {
  registry: RegistryItem[];
  /** BE trả chi tiết nhóm mới sau PUT. */
  onSaved: (next: GroupDetail) => void;
};

/** Khoá ô đang gửi: `<mã nhóm>:<việc>`. */
export const cellKey = (group: string, key: string) => `${group}:${key}`;

export function useCapabilityToggle({ registry, onSaved }: Args) {
  const toast = useToast();
  const [busyCells, setBusyCells] = useState<string[]>([]);
  const [pendingOff, setPendingOff] = useState<PendingOff | null>(null);
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
                void setGroupCapabilities(group.code, undo)
                  .then((back) => {
                    onSaved(back);
                    toast.success(`Đã hoàn tác “${item.label}” cho ${group.label}.`);
                  })
                  .catch((err) => {
                    if (!(err instanceof ApiError && err.status === 401)) toast.error(errorText(err, M.saveFailed));
                  });
              },
            }
          : undefined,
      );
    },
    [labelOf, onSaved, toast],
  );

  const send = useCallback(
    async (group: ToggleGroup, item: RegistryItem, plan: TogglePlan): Promise<void> => {
      if (inFlight.current) return;
      inFlight.current = true;
      setError(null);
      setBusyCells(Object.keys(plan.changes).map((k) => cellKey(group.code, k)));
      try {
        saved(group, item, plan, await setGroupCapabilities(group.code, plan.changes));
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 401)) {
          const text = errorText(err, M.saveFailed);
          setError(text);
          toast.error(text);
        }
      } finally {
        inFlight.current = false;
        setBusyCells([]);
      }
    },
    [saved, toast],
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
    const next = await setGroupCapabilities(group.code, plan.changes);
    setPendingOff(null);
    saved(group, item, plan, next);
  }, [pendingOff, saved]);

  const cancelOff = useCallback(() => setPendingOff(null), []);
  const clearError = useCallback(() => setError(null), []);

  return { toggle, busyCells, pendingOff, confirmOff, cancelOff, error, clearError, labelOf };
}
