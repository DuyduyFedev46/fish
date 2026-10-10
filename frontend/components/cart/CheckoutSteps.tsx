import { cx } from "../ui/cx";
import s from "./CheckoutSteps.module.css";

export interface CheckoutStepsProps {
  current: 1 | 2 | 3;
}

const STEPS = ["Giỏ hàng", "Nhận hàng", "Thanh toán"] as const;

/**
 * Chỉ báo 3 bước: Giỏ hàng, Nhận hàng, Thanh toán. Không bấm được (quay lại dùng nút ở header).
 * Điện thoại là ba vạch; máy tính là ba chấm số nối nhau (đổi bằng CSS).
 */
export default function CheckoutSteps({ current }: CheckoutStepsProps) {
  return (
    <ol className={s.steps} aria-label="Bước đặt hàng">
      {STEPS.map((label, i) => {
        const n = (i + 1) as 1 | 2 | 3;
        const state = n < current ? "done" : n === current ? "current" : "todo";
        return (
          <li key={label} className={cx(s.step, s[state])} aria-current={state === "current" ? "step" : undefined}>
            <span className={s.mark} aria-hidden="true">
              <span className={s.num}>{n}</span>
            </span>
            <span className={s.label}>
              <span className={s.prefix} aria-hidden="true">
                {n}.{" "}
              </span>
              {label}
              {state === "done" ? <span className="visually-hidden"> (xong)</span> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
