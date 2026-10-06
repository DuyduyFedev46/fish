// Dòng thời gian của chứng từ (UI-RULES §5.5): mỗi dòng = thời gian `dd/mm/yyyy hh:mm` (giờ Việt Nam) | việc (+ người làm).
// Dữ liệu = `timeline` của guidance. KHÔNG hiện mã BR (`why.br`) hay mã nội bộ. Tên người làm do BE dựng sẵn (vd "AI của <tên>"), FE không thêm nhãn "AI" nữa.
// `truncated` (BE cắt bớt dòng cũ — `timeline_truncated`) → ghi rõ "Chỉ hiện N việc gần nhất" để không tưởng là hết lịch sử.
import Link from "next/link";
import { dateTime } from "@/shared/lib/format";
import { aiVisible } from "@/shared/lib/features";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { Section } from "./Section";
import s from "./Timeline.module.css";

export type TimelineEntry = {
  at: string;
  label: string;
  /** Tên người/hệ thống làm. */
  actor?: string;
  /** Có thì nhãn việc là liên kết sang chứng từ (vd phiếu hoàn). Màn chỉ đặt khi người xem có quyền mở chứng từ đó. */
  href?: string;
  /** Việc do AI làm: ẩn khi giao diện AI tắt (W39). Dòng dựng từ tên người làm "AI của …" cũng bị coi là việc của AI. */
  ai?: boolean;
};

const AI_ACTOR_PREFIX = "AI của ";
export const isAiEntry = (e: TimelineEntry): boolean => Boolean(e.ai) || Boolean(e.actor?.startsWith(AI_ACTOR_PREFIX));

type Props = {
  entries: TimelineEntry[];
  truncated?: boolean;
  /** Tiêu đề khối, mặc định "Dòng thời gian". */
  title?: string;
};

export function Timeline({ entries: allEntries, truncated = false, title = "Dòng thời gian" }: Props) {
  const { me } = useAuth();
  const entries = aiVisible(me) ? allEntries : allEntries.filter((e) => !isAiEntry(e));
  return (
    <Section title={title} flush aria-label={title}>
      {entries.length === 0 ? (
        <p className={s.empty}>Chưa có việc nào được ghi lại.</p>
      ) : (
        <ol className={s.list}>
          {entries.map((e, i) => (
            <li key={`${e.at}-${i}`} className={s.row} data-timeline-row>
              <span className={s.dot} aria-hidden="true" />
              <time className={`${s.at} num`} dateTime={e.at}>
                {dateTime(e.at)}
              </time>
              <span className={s.what}>
                {e.href ? (
                  <Link href={e.href} className={s.link}>
                    {e.label}
                  </Link>
                ) : (
                  e.label
                )}
                {e.actor ? (
                  <span className={s.who}>
                    {" · "}
                    {e.actor}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ol>
      )}
      {truncated && entries.length > 0 && <p className={s.cut}>Chỉ hiện {entries.length} việc gần nhất.</p>}
    </Section>
  );
}
