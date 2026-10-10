"use client";

// Trang đơn hàng `/shop/orders/?code=&result=` — cũng là trang tra cứu (SHOP-4-01…4-05). Trạng thái máy chủ (`state`) luôn thắng
// `result` trên URL (features/checkout/orderState.ts). Trang công khai: KHÔNG hiện tên, SĐT, địa chỉ người nhận. SĐT khách gõ
// chỉ nằm trong state của form và bị bỏ ngay khi tra xong; URL chỉ có mã đơn; mã tra đơn ở sessionStorage.

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, USE_MOCK, getCatalog, lookupOrder, startCheckoutSession } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { pickHotline } from "@/lib/phone";
import type { OrderLookupResult } from "@/lib/types";
import { getSiteInfo } from "@/features/site/api";
import type { SiteInfoResponse } from "@/features/site/types";
import ShopFrame from "@/components/ShopFrame";
import { useCart } from "@/components/CartContext";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import Dialog from "@/components/ui/Dialog";
import Skeleton from "@/components/ui/Skeleton";
import { contactTarget } from "@/components/shopLinks";
import { goToMockGateway, redirectToGateway } from "../gateway";
import { clearLegacyContact, readLookupToken, removeLookupToken, saveLookupToken } from "../lookupToken";
import { normalizeVnPhone } from "../formRules";
import {
  effectiveState,
  isPaymentScreen,
  parsePaymentResult,
  screenFor,
  type OrderScreenKey,
} from "../orderState";
import { mergeOrderIntoCart } from "../reorder";
import ExpiredView from "./ExpiredView";
import LookupForm, { type LookupStatus } from "./LookupForm";
import OrderView from "./OrderView";
import PaymentView from "./PaymentView";
import PendingView from "./PendingView";
import s from "./OrderScreen.module.css";

const BANNER_KEY = "shop_paid_banner_dismissed";
// Mốc bắt đầu chờ tiền (D3) giữ trong phiên theo mã đơn, để tải lại trang không đếm lại từ 0. Contract tra đơn không có mốc này.
const PENDING_KEY = "shop_pending_since_v1";

function pendingStart(code: string): number {
  try {
    const raw = window.sessionStorage.getItem(PENDING_KEY);
    const v = raw ? (JSON.parse(raw) as { code?: string; at?: number }) : null;
    if (v && v.code === code && typeof v.at === "number" && v.at <= Date.now()) return v.at;
    const at = Date.now();
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify({ code, at }));
    return at;
  } catch {
    return Date.now();
  }
}

function readDismissed(code: string): boolean {
  try {
    return window.sessionStorage.getItem(BANNER_KEY) === code;
  } catch {
    return false;
  }
}

function OrderSkeleton() {
  return (
    <div className={s.skeleton} aria-busy="true">
      <span className="visually-hidden" role="status">
        Đang tải đơn hàng
      </span>
      <Skeleton height={28} width="60%" radius="md" />
      <Skeleton height={140} radius="lg" />
      <Skeleton height={120} radius="lg" />
    </div>
  );
}

/** Chỗ giữ cho Suspense của trang. */
export function OrderFallback() {
  return (
    <ShopFrame header="sub" title="Tra cứu đơn hàng" footer="full" bottomNav>
      <OrderSkeleton />
    </ShopFrame>
  );
}

export default function OrderScreen() {
  const params = useSearchParams();
  const router = useRouter();
  const cart = useCart();
  const code = (params.get("code") ?? "").trim().toUpperCase();
  const result = parsePaymentResult(params.get("result"));

  const [order, setOrder] = useState<OrderLookupResult | null>(null);
  const [phase, setPhase] = useState<"form" | "loading" | "loaded" | "error">(code ? "loading" : "form");
  const [lookupStatus, setLookupStatus] = useState<LookupStatus>("idle");
  const [formCode, setFormCode] = useState(code);
  const [formPhone, setFormPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [info, setInfo] = useState<SiteInfoResponse | null>(null);

  const [expiredLocal, setExpiredLocal] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const pendingSince = useRef<number | null>(null);
  const loadedCode = useRef<string | null>(null);

  const [paying, setPaying] = useState(false);
  const [payError, setPayError] = useState<string | null>(null);
  const [reordering, setReordering] = useState(false);
  const [leave, setLeave] = useState<"back" | "brand" | null>(null);
  const [expiredDialog, setExpiredDialog] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let active = true;
    getSiteInfo()
      .then((v) => active && setInfo(v))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const hotline = useMemo(() => pickHotline(info?.seller?.phone, info?.confirmation_policy?.hotline), [info]);
  const confirmHours = useMemo(() => {
    if (!info?.confirm_call_notice) return null;
    const p = info.confirmation_policy;
    return (p?.enabled && p.working_hours) || info.confirm_call_hours || null;
  }, [info]);

  const accept = useCallback((res: OrderLookupResult) => {
    saveLookupToken(res.order_code, res.lookup_token);
    loadedCode.current = res.order_code;
    setOrder(res);
    setPhase("loaded");
  }, []);

  // Có mã đơn trên URL: tự tra bằng mã tra đơn đã lưu trong phiên. Không có mã tra đơn (hoặc hết hạn) thì hỏi SĐT, điền sẵn mã.
  useEffect(() => {
    clearLegacyContact();
    setFormCode(code);
    if (!code) {
      loadedCode.current = null;
      setOrder(null);
      setPhase("form");
      return;
    }
    if (loadedCode.current === code) return; // vừa tra bằng form, đã có đơn
    loadedCode.current = null;
    setOrder(null);
    setExpiredLocal(false);
    setExpiredDialog(true);
    pendingSince.current = null;
    const token = readLookupToken(code);
    if (!token) {
      setPhase("form");
      return;
    }
    let active = true;
    setPhase("loading");
    lookupOrder({ order_code: code, token })
      .then((res) => {
        if (!active) return;
        if (res) accept(res);
        else {
          removeLookupToken(code);
          setLookupStatus("not_found");
          setPhase("form");
        }
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 401) {
          removeLookupToken(code);
          setPhase("form");
        } else if (err instanceof ApiError && err.status === 429) {
          setLookupStatus("throttled");
          setPhase("form");
        } else {
          setPhase("error");
        }
      });
    return () => {
      active = false;
    };
  }, [code, accept]);

  useEffect(() => {
    setDismissed(code ? readDismissed(code) : false);
  }, [code]);

  const state = order ? (expiredLocal ? effectiveState(order.state, 0) : order.state) : null;
  const waitStarted = order && state === "awaiting_payment" && result === "success";
  if (waitStarted && pendingSince.current === null && order) pendingSince.current = pendingStart(order.order_code);

  const decision = order && state
    ? screenFor(
        {
          state,
          late_payment: order.late_payment,
          cancel_notice: order.cancel_notice,
          payment_pending_minutes: order.payment_pending_minutes,
        },
        result,
        { now, pendingSince: pendingSince.current }
      )
    : null;
  const screen: OrderScreenKey | null = decision?.screen ?? null;

  // Đồng hồ giây chỉ chạy ở màn chờ tiền (để "Đã chờ" và ngưỡng 5 phút cập nhật).
  const pending = screen === "pending" || screen === "pending_slow";
  useEffect(() => {
    if (!pending) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [pending]);

  const refresh = useCallback(async () => {
    const token = code ? readLookupToken(code) : null;
    if (!code || !token) return;
    try {
      const res = await lookupOrder({ order_code: code, token });
      if (res) accept(res);
    } catch {
      // Hỏi lại định kỳ lỗi: giữ màn, thử lại lần sau, không báo đỏ.
    }
  }, [code, accept]);

  // Hỏi lại máy chủ theo nhịp của màn (D3 5 giây rồi 30 giây, D4 hộp thoại 5 giây).
  const pollMs = decision?.pollMs ?? null;
  useEffect(() => {
    if (!pollMs) return;
    const id = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(id);
  }, [pollMs, refresh]);

  async function runLookup(opts: { code: string; phone: string }) {
    const c = opts.code.trim().toUpperCase();
    const p = opts.phone.trim();
    if (!c || !p) {
      setLookupStatus("missing");
      return;
    }
    setSubmitting(true);
    setLookupStatus("idle");
    try {
      const res = await lookupOrder({ order_code: c, phone: normalizeVnPhone(p) });
      if (!res) {
        setLookupStatus("not_found");
        return;
      }
      setFormPhone(""); // bỏ SĐT ngay khi tra xong
      setExpiredLocal(false);
      setExpiredDialog(true);
      pendingSince.current = null;
      accept(res);
      if (c !== code) router.replace(`/shop/orders/?code=${encodeURIComponent(res.order_code)}`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) setLookupStatus("throttled");
      else if (err instanceof ApiError && (err.status === 400 || err.status === 404)) setLookupStatus("not_found");
      else setLookupStatus("network");
    } finally {
      setSubmitting(false);
    }
  }

  async function pay() {
    if (!order || paying) return;
    setPaying(true);
    setPayError(null);
    try {
      const session = await startCheckoutSession(order.order_code);
      if (USE_MOCK) goToMockGateway(order.order_code, Number(order.total_amount));
      else redirectToGateway(session);
      // Trình duyệt sắp điều hướng đi: giữ trạng thái "đang chuyển".
    } catch (err) {
      setPayError(
        err instanceof ApiError && err.status === 429
          ? "Bạn thao tác hơi nhanh. Đợi 1 phút rồi thử lại."
          : "Chưa mở được trang thanh toán. Thử lại."
      );
      setPaying(false);
      void refresh(); // đơn có thể đã hết giờ hoặc đã trả: máy chủ thắng
    }
  }

  async function reorder() {
    if (!order || reordering) return;
    setReordering(true);
    let items = null;
    try {
      items = (await getCatalog({ fresh: true })).items;
    } catch {
      items = null;
    }
    const lines = order.lines;
    cart.updateEntries((prev) => mergeOrderIntoCart(prev, lines, items));
    router.push("/shop/cart/");
  }

  function dismissBanner() {
    setDismissed(true);
    try {
      window.sessionStorage.setItem(BANNER_KEY, code);
    } catch {
      // bỏ qua
    }
  }

  const lookupProps = {
    code: formCode,
    phone: formPhone,
    onCodeChange: setFormCode,
    onPhoneChange: setFormPhone,
    onSubmit: () => void runLookup({ code: formCode, phone: formPhone }),
    loading: submitting,
    status: lookupStatus,
    hotline,
  };

  // ---- Khung theo màn ----
  const paymentFlow = screen !== null && isPaymentScreen(screen);
  const guardLeave = screen === "payment" || screen === "payment_retry";
  let frame: {
    header: "sub" | "checkout";
    title: string;
    footer: "full" | "compact";
    bottomNav: boolean;
    backHref?: string;
  } = { header: "sub", title: "Tra cứu đơn hàng", footer: "full", bottomNav: true };
  if (paymentFlow || pending) {
    frame = { header: "checkout", title: "Thanh toán", footer: "compact", bottomNav: false, backHref: "/shop/cart/" };
  } else if (order && screen) {
    frame = { header: "sub", title: `Đơn hàng ${order.order_code}`, footer: "full", bottomNav: true, backHref: "/shop/" };
  }

  let body;
  if (phase === "loading") {
    body = <OrderSkeleton />;
  } else if (phase === "error") {
    body = (
      <div className={s.narrow}>
        <Banner
          tone="crit"
          live="assertive"
          action={
            <Button size="sm" variant="secondary" onClick={() => window.location.reload()}>
              Thử lại
            </Button>
          }
        >
          Chưa tải được đơn. Thử lại.
        </Banner>
      </div>
    );
  } else if (phase === "form" || !order || !decision) {
    body = (
      <div className={s.narrow}>
        <h1 className={s.title}>Tra cứu đơn hàng</h1>
        <LookupForm {...lookupProps} />
        <section className={s.help} aria-labelledby="lookup-help">
          <h2 id="lookup-help" className={s.helpTitle}>
            Cần giúp?
          </h2>
          <Button variant="outline" href={contactTarget(hotline)}>
            {hotline ? `Gọi ${hotline}` : "Liên hệ chúng tôi"}
          </Button>
        </section>
      </div>
    );
  } else if (screen === "payment" || screen === "payment_retry" || screen === "expired_dialog") {
    body = (
      <div className={s.payPage}>
        <PaymentView
          order={order}
          mode={screen === "payment" ? "payment" : screen === "payment_retry" ? "retry" : "expired"}
          paying={paying}
          payError={payError}
          onPay={() => void pay()}
          onExpire={() => {
            setExpiredLocal(true);
            void refresh();
          }}
          onReorder={() => void reorder()}
          reordering={reordering}
        />
      </div>
    );
  } else if (screen === "pending" || screen === "pending_slow") {
    body = (
      <PendingView
        orderCode={order.order_code}
        total={order.total_amount}
        waitedMs={pendingSince.current ? Math.max(0, now - pendingSince.current) : 0}
        slow={screen === "pending_slow"}
        hotline={hotline}
      />
    );
  } else if (screen === "expired_page") {
    body = (
      <ExpiredView
        orderCode={order.order_code}
        holdMinutes={order.hold_minutes}
        hotline={hotline}
        reordering={reordering}
        onReorder={() => void reorder()}
      />
    );
  } else {
    body = (
      <OrderView
        order={order}
        decision={decision}
        hotline={hotline}
        confirmHours={confirmHours}
        returnReportHours={info?.policies?.return_report_hours ?? null}
        bannerDismissed={dismissed}
        onDismissBanner={dismissBanner}
        reordering={reordering}
        onReorder={() => void reorder()}
        lookup={lookupProps}
      />
    );
  }

  const holdUntil = order?.booked_expires_at ? formatTime(order.booked_expires_at) : null;

  return (
    <ShopFrame
      header={frame.header}
      title={frame.title}
      footer={frame.footer}
      bottomNav={frame.bottomNav}
      backHref={frame.backHref}
      onBack={guardLeave ? () => setLeave("back") : undefined}
      onBrandClick={
        guardLeave
          ? (e) => {
              e.preventDefault();
              setLeave("brand");
            }
          : undefined
      }
    >
      {body}

      {/* D6: rời trang thanh toán. Esc hoặc lớp phủ = ở lại. */}
      <Dialog
        open={leave !== null && guardLeave}
        onClose={() => setLeave(null)}
        title="Rời trang thanh toán?"
        description={
          order
            ? `Đơn ${order.order_code} vẫn được giữ${holdUntil ? ` tới hết ${holdUntil}` : ""}. Bạn có thể quay lại thanh toán từ Tra cứu đơn.`
            : undefined
        }
        kind="alert"
        icon={{ name: "info", tone: "info" }}
        closeLabel="Đóng, ở lại thanh toán"
        actions={
          <>
            <Button size="lg" fullWidth data-autofocus onClick={() => setLeave(null)}>
              Ở lại thanh toán
            </Button>
            <Button
              size="lg"
              fullWidth
              variant="secondary"
              onClick={() => {
                const to = leave === "brand" ? "/" : "/shop/cart/";
                setLeave(null);
                router.push(to);
              }}
            >
              Rời trang
            </Button>
          </>
        }
      />

      {/* D4: hết giờ giữ hàng khi đang xem. Không đóng bằng lớp phủ. */}
      <Dialog
        open={screen === "expired_dialog" && expiredDialog && order !== null}
        onClose={() => setExpiredDialog(false)}
        dismissible={false}
        title="Hết thời gian giữ hàng"
        description={
          order
            ? `Đơn ${order.order_code} đã tự huỷ sau ${order.hold_minutes} phút chưa thanh toán. Hàng đã trả lại kho, bạn chưa bị trừ tiền.`
            : undefined
        }
        footnote={
          <>
            Đã chuyển khoản rồi? Liên hệ {hotline ? <a href={contactTarget(hotline)}>{hotline}</a> : "Cá Về"}, Cá Về sẽ kiểm tra và gọi lại cho bạn.
          </>
        }
        kind="alert"
        icon={{ name: "hourglass", tone: "crit" }}
        closeLabel="Đóng thông báo hết giờ giữ hàng"
        actions={
          <>
            <Button size="lg" fullWidth data-autofocus loading={reordering} onClick={() => void reorder()}>
              Đặt lại đơn này
            </Button>
            <Button size="lg" fullWidth variant="secondary" href="/">
              Về trang chủ
            </Button>
          </>
        }
      />
    </ShopFrame>
  );
}
