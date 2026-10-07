// Nối dữ liệu guidance (GET /api/guidance/<loại>/<id>/) vào khối trang chi tiết dùng chung (shared/ui/detail).
// Hàm thuần, không React. Quy tắc: KHÔNG đưa `why.br` / mã BR ra giao diện.
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import type { GuidanceData, GuidanceTimelineEntry } from "./types";

/** Dòng do AI làm, hoặc dòng Hệ thống chạy theo đề xuất AI (`proposal_ref`). Khi giao diện AI tắt, `<Timeline/>` bỏ các dòng này. */
export function isAiTimelineEntry(e: Pick<GuidanceTimelineEntry, "actor" | "proposal_ref">): boolean {
  return e.actor?.kind === "ai" || (e.actor?.kind === "system" && Boolean(e.proposal_ref));
}

/** Dòng thời gian của guidance → dòng của <Timeline/>. Mới nhất trước (BE trả cũ → mới thì đảo lại). */
export function toTimelineEntries(entries: GuidanceTimelineEntry[] | null | undefined): TimelineEntry[] {
  return [...(entries ?? [])]
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
    .map((e) => ({
      at: e.at,
      label: e.label,
      actor: e.actor?.display || undefined,
      ai: isAiTimelineEntry(e) || undefined,
    }));
}

/** Nhãn "Tiếp theo" của <StatusPath/>: bước người dùng đầu tiên còn làm được; không có → null. */
export function nextStepLabel(data: Pick<GuidanceData, "next_steps"> | null | undefined): string | null {
  const step = data?.next_steps.find((s) => s.actor === "user" && s.allowed);
  return step ? step.label : null;
}
