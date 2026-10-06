// "Nhờ người xử lý" (DW-23, Lô bổ sung A #19): chuyển một bước mình chưa làm được cho người có quyền. Không phải tính năng AI:
// BE không chặn khi AI tắt. Màn chi tiết đã tải guidance cho "Tiếp theo", nên chỉ cần chọn bước ở đây, không gọi thêm API.

import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import type { GuidanceData, GuidanceNextStep } from "./types";

/**
 * Bước đầu tiên người xem CHƯA tự làm được (`allowed=false`) và không phải bước hệ thống (DW-23-AC1).
 * Không có bước nào → null → màn không hiện mục "Nhờ người xử lý".
 * SR-HIDE-AI-02: cờ AI tắt → luôn null (người được nhờ chỉ thấy việc ở màn Việc AI đã ẩn), chặn ở gốc cho mọi màn gọi hàm này.
 */
export function escalatableStep(data: Pick<GuidanceData, "next_steps"> | null | undefined): GuidanceNextStep | null {
  if (!AI_FEATURES_ENABLED) return null;
  const step = data?.next_steps.find((s) => s.actor !== "system" && !s.allowed && Boolean(s.key));
  return step ?? null;
}

/** "Chủ" / "Chủ hoặc Quản lý" — người sẽ nhận việc, lấy từ `who` của BE; thiếu thì nói chung. */
export function whoText(step: Pick<GuidanceNextStep, "who">): string {
  const who = step.who.filter((w) => w && w.trim());
  return who.length ? who.join(" hoặc ") : "người có thẩm quyền";
}

export const ESCALATE_MSG = {
  menuLabel: "Nhờ người xử lý",
  title: "Nhờ người xử lý",
  confirm: "Nhờ người xử lý",
  busy: "Đang chuyển…",
  body: (label: string, who: string) => `Chuyển việc "${label}" cho ${who}. Họ sẽ thấy việc này ở màn Việc của AI, tab Được chuyển.`,
  done: (who: string) => `Đã nhờ ${who} xử lý việc này.`,
} as const;
