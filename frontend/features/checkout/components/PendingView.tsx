"use client";

import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";
import { contactTarget } from "@/components/shopLinks";
import { formatPriceVnd } from "@/lib/format";
import type { Money } from "@/lib/types";
import { formatWaited } from "../orderState";
import { PaymentProgress } from "./OrderTimeline";
import s from "./PendingView.module.css";

export interface PendingViewProps {
  orderCode: string;
  total: Money;
  /** Đã chờ bao lâu (ms) tính từ lúc trang mở với result=success. */
  waitedMs: number;
  /** Quá ngưỡng: đổi câu sang "Cá Về sẽ kiểm tra giao dịch và gọi cho bạn". */
  slow: boolean;
  hotline?: string;
}

/** D3: đang chờ xác nhận thanh toán. Trang tự hỏi lại máy chủ (5 giây, sau ngưỡng 30 giây); lỗi hỏi lại không báo đỏ. */
export default function PendingView({ orderCode, total, waitedMs, slow, hotline }: PendingViewProps) {
  return (
    <div className={s.page}>
      <section className={s.hero} aria-busy="true">
        <Spinner size={36} />
        <h1 className={s.title}>Đang chờ xác nhận thanh toán</h1>
        {slow ? (
          <p className={s.lead}>
            Cá Về sẽ kiểm tra giao dịch và gọi cho bạn.
            {hotline ? (
              <>
                {" "}
                Cần gấp, bạn gọi <a href={contactTarget(hotline)}>{hotline}</a>.
              </>
            ) : null}
          </p>
        ) : (
          <p className={s.lead}>Ngân hàng thường báo trong vài giây. Trang tự cập nhật, bạn không cần chuyển khoản lại.</p>
        )}
        <p className={s.code}>
          Mã đơn <span className="num">{orderCode}</span>
        </p>
      </section>
      <section className={s.block} aria-labelledby="pending-progress">
        <h2 id="pending-progress" className={s.blockTitle}>
          Tiến trình
        </h2>
        <PaymentProgress current={1} />
        <p className={s.wait}>
          {slow ? "Trang vẫn tự cập nhật." : "Tự kiểm tra lại sau mỗi 5 giây"} · Đã chờ <span className="num">{formatWaited(waitedMs)}</span>
        </p>
      </section>
      <section className={s.block}>
        <dl className={s.facts}>
          <div>
            <dt>Số tiền của đơn</dt>
            <dd className="num">{formatPriceVnd(total)}</dd>
          </div>
          <div>
            <dt>Phương thức</dt>
            <dd>Chuyển khoản ngân hàng</dd>
          </div>
        </dl>
      </section>
      {slow ? (
        <Banner tone="info" icon="info">
          Bạn không cần chuyển khoản lại.
        </Banner>
      ) : null}
      <Button variant="outline" size="lg" fullWidth href="/shop/orders/">
        Tra cứu đơn
      </Button>
    </div>
  );
}
