import Icon from "@/components/ui/Icon";
import { cx } from "@/components/ui/cx";
import { formatTimeDayVn } from "@/lib/format";
import type { TimelineStep } from "../orderState";
import s from "./OrderTimeline.module.css";

const STATE_TEXT: Record<TimelineStep["state"], string> = {
  done: "(đã xong)",
  current: "(đang làm)",
  upcoming: "(chưa tới)",
  failed: "(chưa giao được)",
};

/**
 * Dòng thời gian trạng thái đơn (COMPONENTS #26): 5 bước, dọc trên điện thoại, ngang trên máy tính. Chỉ 3 mốc có giờ
 * (đặt, trả, giao; BR-BH-26), giờ theo GMT+7. Bước giao thất bại màu hổ phách, không đỏ. Không hiện người nhận hay người giao.
 */
export default function OrderTimeline({ steps }: { steps: TimelineStep[] }) {
  if (steps.length === 0) return null;
  return (
    <ol className={s.list} aria-label="Tiến trình đơn">
      {steps.map((step, i) => {
        const last = i === steps.length - 1;
        const time = step.time ? formatTimeDayVn(step.time) : null;
        return (
          <li
            key={step.key}
            className={cx(s.step, s[step.state])}
            aria-current={step.state === "current" ? "step" : undefined}
          >
            <span className={s.rail} aria-hidden="true">
              <span className={s.dot}>
                {step.state === "done" ? <Icon name="check" size={13} strokeWidth={3} /> : null}
                {step.state === "failed" ? <span className={s.bang}>!</span> : null}
              </span>
              {last ? null : <span className={s.line} />}
            </span>
            <span className={s.text}>
              <span className={s.label}>
                {step.label}
                <span className="visually-hidden"> {STATE_TEXT[step.state]}</span>
              </span>
              {step.detail || time ? (
                <span className={s.detail}>
                  {[time, step.detail].filter(Boolean).join(" · ")}
                </span>
              ) : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

const PAYMENT_STEPS = ["Đặt đơn", "Chờ ngân hàng", "Thanh toán xong"] as const;

/** 3 vạch của màn chờ tiền (D3): vạch hiện tại nhấp nháy, đứng yên khi giảm chuyển động. */
export function PaymentProgress({ current }: { current: 0 | 1 | 2 }) {
  return (
    <ol className={s.payment} aria-label="Tiến trình thanh toán">
      {PAYMENT_STEPS.map((label, i) => {
        const state = i < current ? "done" : i === current ? "current" : "todo";
        return (
          <li key={label} className={cx(s.pStep, s[`p_${state}`])} aria-current={state === "current" ? "step" : undefined}>
            <span className={s.pBar} aria-hidden="true" />
            <span className={s.pLabel}>
              {label}
              {state === "done" ? <span className="visually-hidden"> (đã xong)</span> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
