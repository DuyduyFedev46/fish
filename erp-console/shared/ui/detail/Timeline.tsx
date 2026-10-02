// Dòng thời gian của chứng từ (UI-RULES §5.5): mỗi dòng = thời gian `dd/mm/yyyy hh:mm` (giờ Việt Nam) | việc (+ người làm).
// Dữ liệu = `timeline` của guidance. KHÔNG hiện mã BR (`why.br`) hay mã nội bộ. Người làm là AI thì có nhãn "AI".
// `truncated` (BE cắt bớt dòng cũ — `timeline_truncated`) → ghi rõ "Chỉ hiện N việc gần nhất" để không tưởng là hết lịch sử.
import Link from "next/link";
import { dateTime } from "@/shared/lib/format";
import { Section } from "./Section";
import s from "./Timeline.module.css";

export type TimelineEntry = {
  at: string;
  label: string;
  /** Tên người/hệ thống làm. */
  actor?: string;
  /** AI làm → nhãn "AI" cạnh tên. */
  byAi?: boolean;
  /** Có thì nhãn việc là liên kết sang chứng từ (vd phiếu hoàn). Màn chỉ đặt khi người xem có quyền mở chứng từ đó. */
  href?: string;
};

type Props = {
  entries: TimelineEntry[];
  truncated?: boolean;
  /** Tiêu đề khối, mặc định "Dòng thời gian". */
  title?: string;
};

export function Timeline({ entries, truncated = false, title = "Dòng thời gian" }: Props) {
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
                    {e.byAi ? <span className={s.ai}>AI</span> : null}
                    {e.byAi ? " " : ""}
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
