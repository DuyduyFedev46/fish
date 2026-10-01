// Thanh trạng thái kiểu mũi tên (UI-RULES §5.2) cho đối tượng CÓ vòng đời: bước đã qua nền `--accent-soft` có ✓,
// bước hiện tại nền `--accent` chữ `--on-accent`, kết thúc xấu (huỷ, thất bại) tông `crit`.
// Ngay dưới, cùng khối: "→ Tiếp theo: …" bên trái, "Đã làm: ✓ … ✓ …" bên phải.
// Đối tượng không có trạng thái (nhóm quyền, khách hàng, mặt hàng) KHÔNG dùng component này.
import { Icon } from "../Icon";
import s from "./StatusPath.module.css";

export type PathStep = { key: string; label: string };

type Props = {
  steps: PathStep[];
  /** `key` của bước hiện tại. Không khớp bước nào → coi như chưa bắt đầu (không bước nào được tô). */
  current: string;
  /** Kết thúc xấu: thay bước hiện tại bằng nhãn này tông đỏ (vd "Đã huỷ"); các bước trước nó vẫn là đã qua. */
  badEnd?: { label: string; after?: string } | null;
  /** Việc tiếp theo, đã là câu hoàn chỉnh (vd "Xác nhận đã nhận tiền"). null = không có việc. */
  next?: string | null;
  /** Các việc đã làm (nhãn ngắn). */
  done?: string[];
  label?: string;
};

export function StatusPath({ steps, current, badEnd, next, done = [], label = "Trạng thái" }: Props) {
  // Với kết thúc xấu: `after` = bước cuối cùng đã qua trước khi hỏng; mặc định coi mọi bước trước `current` là đã qua.
  const anchor = badEnd?.after ?? current;
  const at = steps.findIndex((st) => st.key === anchor);
  return (
    <section className={s.block} aria-label={label}>
      <ol className={s.path}>
        {steps.map((st, i) => {
          const passed = at >= 0 && (badEnd ? i <= at : i < at);
          const isNow = !badEnd && i === at;
          return (
            <li
              key={st.key}
              className={`${s.step} ${passed ? s.passed : ""} ${isNow ? s.now : ""}`}
              aria-current={isNow ? "step" : undefined}
              data-state={isNow ? "current" : passed ? "done" : "todo"}
            >
              {passed && <Icon name="check" />}
              <span>{st.label}</span>
            </li>
          );
        })}
        {badEnd && (
          <li className={`${s.step} ${s.bad}`} aria-current="step" data-state="bad">
            <Icon name="close" />
            <span>{badEnd.label}</span>
          </li>
        )}
      </ol>
      {(next !== undefined || done.length > 0) && (
        <div className={s.foot}>
          <p className={s.next}>
            {next ? (
              <>
                <Icon name="arrow_forward" />
                <span>
                  <b>Tiếp theo:</b> {next}
                </span>
              </>
            ) : (
              <span className="muted">Không còn việc nào cần làm.</span>
            )}
          </p>
          {done.length > 0 && (
            <p className={s.done}>
              <b>Đã làm:</b>{" "}
              {done.map((d, i) => (
                <span key={`${d}-${i}`} className={s.doneItem}>
                  <Icon name="check" />
                  {d}
                </span>
              ))}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
