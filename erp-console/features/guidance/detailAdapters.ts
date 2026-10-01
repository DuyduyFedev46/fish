// Nối dữ liệu guidance (GET /api/guidance/<loại>/<id>/) vào khối trang chi tiết dùng chung (shared/ui/detail).
// Hàm thuần, không React. Quy tắc: KHÔNG đưa `why.br` / mã BR ra giao diện; người làm là AI thì gắn cờ `byAi`.
import type { TimelineEntry } from "@/shared/ui/detail/Timeline";
import type { GuidanceData, GuidanceTimelineEntry } from "./types";

/** Dòng thời gian của guidance → dòng của <Timeline/>. Mới nhất trước (BE trả cũ → mới thì đảo lại). */
export function toTimelineEntries(entries: GuidanceTimelineEntry[] | null | undefined): TimelineEntry[] {
  return [...(entries ?? [])]
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))
    .map((e) => ({
      at: e.at,
      label: e.label,
      actor: e.actor?.display || undefined,
      byAi: e.actor?.kind === "ai",
    }));
}

/** Nhãn "Tiếp theo" của <StatusPath/>: bước người dùng đầu tiên còn làm được; không có → null. */
export function nextStepLabel(data: Pick<GuidanceData, "next_steps"> | null | undefined): string | null {
  const step = data?.next_steps.find((s) => s.actor === "user" && s.allowed);
  return step ? step.label : null;
}
