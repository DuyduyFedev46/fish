"use client";

// Màn đặt hàng `/shop/checkout/` (SHOP-3-03, 3-04, 3-05): form nhận hàng, bản đồ, gửi đơn. Luồng/câu chữ: 02a mục 4–6;
// màn mẫu Checkout, C1b, C1c, C2, C3, C4, C5, X2, X3, X4. Dữ liệu cá nhân (tên, SĐT, địa chỉ) chỉ nằm trong state của form:
// không localStorage, không URL, không console.

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import { orderLimitMessage } from "../orderLimitError";
import { ApiError, USE_MOCK, checkVoucher, createOrder, getCatalog, startCheckoutSession } from "@/lib/api";
import { formatPriceVnd } from "@/lib/format";
import { parseQtyRule, qtyToApiString, formatQty } from "@/lib/quantity";
import { contactTarget } from "@/components/shopLinks";
import type { AddressUnitSuggestion, CreateOrderPayload, OutOfStockLine } from "@/lib/types";
import { getPrivacyPolicy, getSiteInfo } from "@/features/site/api";
import type { PrivacyPolicyResponse, SiteInfoResponse } from "@/features/site/types";
import { pickHotline } from "@/lib/phone";
import ShopFrame from "@/components/ShopFrame";
import { useCart } from "@/components/CartContext";
import CartSummary from "@/components/cart/CartSummary";
import CheckoutSteps from "@/components/cart/CheckoutSteps";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import Dialog from "@/components/ui/Dialog";
import EmptyState from "@/components/ui/EmptyState";
import FormErrorSummary from "@/components/ui/FormErrorSummary";
import Skeleton from "@/components/ui/Skeleton";
import TextField from "@/components/ui/TextField";
import { focusSoon } from "@/components/ui/focusSoon";
import { useVoucher } from "@/features/cart/useVoucher";
import { clearVoucherCode, readVoucherCode } from "@/features/cart/voucherStorage";
import { hasDistinctDiscountedTotal, minOrderOf, pendingVoucherText, voucherCodeToSend, voucherMessage } from "@/features/cart/voucherView";
import { cartFingerprint, clearRequestId, getRequestId, renewRequestId } from "../requestId";
import { saveLookupToken } from "../lookupToken";
import { goToMockGateway, redirectToGateway } from "../gateway";
import { orderUrl } from "../afterCreate";
import { isAddressSearchEnabled, shouldOpenFallbackDirectly } from "../addressSearch";
import {
  INITIAL_SELECTION,
  STREET_MAX,
  errorSummary,
  mapServerFields,
  normalizeVnPhone,
  selectDistrict,
  selectProvince,
  selectScheme,
  selectWard,
  validateForm,
  type AddressSelection,
  type FormErrors,
  type FormField,
} from "../formRules";
import AddressField from "./AddressField";
import AddressSearchSheet, { type AddressSearchConfirmResult } from "./AddressSearchSheet";
import PaymentChoice from "./PaymentChoice";
import SoldOutSheet, { type SoldOutLine } from "./SoldOutSheet";
import s from "./CheckoutScreen.module.css";

// Chỉ tồn tại ở chế độ mock: điều kiện literal `process.env.NEXT_PUBLIC_USE_MOCK === "1"` được bundler thay bằng hằng số,
// nên ở bản build thật cả lệnh dynamic import này bị cắt — chunk MockGatewayPanel (kéo theo lib/mock) không được sinh ra
// (kiểm bằng scripts/check-no-mock.mjs).
const MockGatewayPanel =
  process.env.NEXT_PUBLIC_USE_MOCK === "1"
    ? dynamic(() => import("./MockGatewayPanel"), { ssr: false })
    : null;

/** Trang cổng thanh toán giả lập (chỉ mock) hay form đặt hàng thật. */
export default function CheckoutScreen() {
  const searchParams = useSearchParams();
  if (MockGatewayPanel && searchParams.get("mock_gateway") === "1") {
    return (
      <ShopFrame header="checkout" title="Thanh toán" footer="compact" bottomNav={false} backHref="/shop/cart/">
        <MockGatewayPanel />
      </ShopFrame>
    );
  }
  return <CheckoutForm />;
}

/** Chỗ giữ cho Suspense của trang. */
export function CheckoutFallback() {
  return (
    <ShopFrame header="checkout" title="Thông tin nhận hàng" footer="compact" bottomNav={false} backHref="/shop/cart/">
      <div className={s.page} aria-busy="true">
        <span className="visually-hidden" role="status">
          Đang tải
        </span>
        <div className={s.skeleton}>
          <Skeleton height={120} radius="lg" />
          <Skeleton height={160} radius="lg" />
        </div>
      </div>
    </ShopFrame>
  );
}

function focusAddressEnd() {
  const el = document.getElementById("f-addr") as HTMLTextAreaElement | null;
  if (!el) return;
  el.focus();
  const n = el.value.length;
  el.setSelectionRange(n, n);
}

function CheckoutForm() {
  const router = useRouter();
  const cart = useCart();

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  // Địa chỉ có cấu trúc (STA-02): chỉ trong state, không storage/URL/console.
  const [selection, setSelection] = useState<AddressSelection>(INITIAL_SELECTION);
  const [street, setStreet] = useState("");
  const [consent, setConsent] = useState(false); // KHÔNG tick sẵn (BR-BH-17)
  const [errors, setErrors] = useState<FormErrors>({});
  const [summaryToken, setSummaryToken] = useState(0);
  // Khối "Còn N chỗ cần sửa" chỉ hiện sau khi bấm "Đặt hàng"; lỗi khi rời ô chỉ hiện dưới ô, không đẩy bố cục (QA B1).
  const [summaryShown, setSummaryShown] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const placedRef = useRef(false);
  const openingRef = useRef(false); // đã tạo đơn và đang chuyển sang cổng: không mở khoá nút
  // Mức tối thiểu của từng món theo catalog (C3 đổi về mức này). Chưa tải được thì dùng 1 (min_qty hiện hành).
  const minQtyRef = useRef<Map<string, number>>(new Map());

  const [siteInfo, setSiteInfo] = useState<SiteInfoResponse | null>(null);
  const [policy, setPolicy] = useState<PrivacyPolicyResponse | null>(null);
  const [consentRequired, setConsentRequired] = useState<boolean | null>(null);
  const [shopClosed, setShopClosed] = useState(false);

  const [mapOpen, setMapOpen] = useState(false);
  const [mapFailedOpen, setMapFailedOpen] = useState(false);
  const [filledFromMap, setFilledFromMap] = useState(false);
  const [wardSuggestion, setWardSuggestion] = useState<AddressUnitSuggestion | null>(null);
  const addressSearchEnabled = isAddressSearchEnabled(siteInfo);

  const [soldOut, setSoldOut] = useState<SoldOutLine[] | null>(null);
  const [networkOpen, setNetworkOpen] = useState(false);
  const [throttledOpen, setThrottledOpen] = useState(false);
  const [policyOpen, setPolicyOpen] = useState(false);
  // B8: mã hết hiệu lực đúng lúc đặt. Hỏi khách, không tự đặt với giá khác giá họ đã thấy.
  const [voucherGone, setVoucherGone] = useState<{ code: string; fullPrice: string; discountedPrice: string | null } | null>(null);

  const hotline = useMemo(
    () => pickHotline(siteInfo?.seller?.phone, siteInfo?.confirmation_policy?.hotline),
    [siteInfo]
  );

  // Site-info và chính sách quyền riêng tư: hai nguồn độc lập. Thiếu chính sách đã đăng mà phải xin đồng ý thì Shop tạm ngưng (X2, GL-03-AC5).
  useEffect(() => {
    let active = true;
    Promise.allSettled([getSiteInfo(), getPrivacyPolicy()]).then(([siteRes, policyRes]) => {
      if (!active) return;
      let required = true;
      if (siteRes.status === "fulfilled" && siteRes.value) {
        setSiteInfo(siteRes.value);
        if (siteRes.value.privacy_consent_required === false) required = false;
      }
      setConsentRequired(required);
      if (policyRes.status === "fulfilled" && policyRes.value) setPolicy(policyRes.value);
      else if (required) setShopClosed(true);
    });
    return () => {
      active = false;
    };
  }, []);

  // Giỏ trống thì về giỏ (trừ khi vừa đặt xong và đã xoá giỏ).
  useEffect(() => {
    if (cart.ready && cart.lines.length === 0 && !placedRef.current) router.replace("/shop/cart/");
  }, [cart.ready, cart.lines.length, router]);

  // Giỏ còn món đã hết (theo catalog mới tải) thì quay về giỏ để bỏ món trước (02b §6.1).
  useEffect(() => {
    if (!cart.ready || cart.lines.length === 0) return;
    let active = true;
    getCatalog()
      .then((c) => {
        if (!active || placedRef.current) return;
        minQtyRef.current = new Map(c.items.map((i) => [i.item_code, parseQtyRule(i.min_qty, i.qty_step, i.unit).minQty]));
        const live = new Map(c.items.map((i) => [i.item_code, i.stock_level]));
        if (cart.lines.some((l) => (live.get(l.item_code) ?? "out") === "out")) router.replace("/shop/cart/");
      })
      .catch(() => {});
    return () => {
      active = false;
    };
    // Chỉ kiểm lần đầu vào trang.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart.ready]);

  // Mã giảm giá (3b, GUI-01): số giảm và tổng lấy từ máy chủ; kiểm lại bị lỗi mạng thì hiện giá chưa giảm kèm nhắc "sẽ kiểm khi đặt" và vẫn gửi mã để máy chủ quyết.
  const voucherItems = useMemo(
    () => cart.lines.map((l) => ({ item_code: l.item_code, qty: qtyToApiString(l.qty) })),
    [cart.lines]
  );
  const voucher = useVoucher(voucherItems, cart.ready);
  const quote = voucher.quote;
  const pendingVoucher = pendingVoucherText(voucher.code, Boolean(quote), voucher.error !== null && !voucher.checking);
  const localTotal = String(Math.round(cart.totalAmount));
  const total = quote ? quote.total_after : localTotal;
  const itemCount = cart.lines.length;
  const summaryLines = useMemo(
    () =>
      cart.lines.map((l) => ({
        name: l.name,
        qtyText: `${formatQty(l.qty)} ${l.unit}`,
        unitText: `${formatQty(l.qty)} ${l.unit} × ${formatPriceVnd(l.price)}`,
        amount: String(Math.round(l.qty * (Number(l.price) || 0))),
      })),
    [cart.lines]
  );

  const setFieldError = useCallback((field: FormField, message: string | undefined) => {
    setErrors((prev) => {
      if (prev[field] === message) return prev;
      const next = { ...prev };
      if (message) next[field] = message;
      else delete next[field];
      return next;
    });
  }, []);

  /** Kiểm một ô khi rời ô (blur). Không báo lỗi khi khách đang gõ lần đầu. */
  function checkOnBlur(field: FormField) {
    const all = validateForm({ name, phone, ...selection, street, consent }, false);
    setFieldError(field, all[field]);
  }

  /** Ô đang có lỗi: sửa đúng thì lỗi tắt ngay khi gõ. */
  function recheck(field: FormField, next: { name: string; phone: string; street: string; selection: AddressSelection }) {
    if (!errors[field]) return;
    const all = validateForm({ name: next.name, phone: next.phone, street: next.street, ...next.selection, consent }, false);
    setFieldError(field, all[field]);
  }

  /** Đổi một cấp địa chỉ: xoá cấp con (formRules), lỗi của ô nào đã hết thì tắt, ô con bị xoá không báo lỗi sớm. */
  function changeSelection(next: AddressSelection) {
    const prev = selection;
    setSelection(next);
    setErrors((cur) => {
      const all = validateForm({ name, phone, ...next, street, consent }, false);
      const out = { ...cur };
      const codes = [
        ["province", "provinceCode"],
        ["district", "districtCode"],
        ["ward", "wardCode"],
      ] as const;
      for (const [field, key] of codes) {
        const justCleared = !!prev[key] && !next[key];
        if (out[field] && (!all[field] || justCleared)) delete out[field];
      }
      return out;
    });
  }

  /**
   * Gửi đơn. `lines` dùng khi vừa sửa giỏ ở C3 (state giỏ chưa kịp cập nhật). `withoutVoucher` là "Đặt hàng không dùng mã"
   * (B8): bỏ mã và dùng `client_request_id` mới.
   */
  const send = useCallback(
    async (opts?: { lines?: typeof cart.lines; withoutVoucher?: boolean }) => {
      if (submittingRef.current) return; // chống bấm đúp
      const lines = opts?.lines ?? cart.lines;
      if (lines.length === 0) return;
      const items = lines.map((l) => ({ item_code: l.item_code, qty: qtyToApiString(l.qty) }));
      const fingerprint = cartFingerprint(items);
      const payload: CreateOrderPayload = {
        client_request_id: opts?.withoutVoucher ? renewRequestId(fingerprint) : getRequestId(fingerprint),
        customer: { name: name.trim(), phone: normalizeVnPhone(phone) },
        delivery_address_parts: {
          scheme: selection.scheme,
          province_code: selection.provinceCode,
          district_code: selection.scheme === "legacy" ? selection.districtCode : null,
          ward_code: selection.wardCode,
          street: street.split(/\s+/).filter(Boolean).join(" "),
        },
        items,
      };
      if (consentRequired && policy) {
        payload.privacy_consent = { accepted: consent, policy_version_id: policy.version_id };
      }
      const codeToSend = voucherCodeToSend(voucher.code, readVoucherCode(), !!opts?.withoutVoucher);
      if (codeToSend) payload.voucher_code = codeToSend;

      submittingRef.current = true;
      setSubmitting(true);
      setBanner(null);
      try {
        const res = await createOrder(payload);
        // Thành công (201 hoặc 200 khi gửi lại): nhớ mã tra đơn trong phiên, xoá giỏ, sang trang đơn.
        placedRef.current = true;
        clearVoucherCode(); // đơn xong: giỏ mới không tự áp lại mã cũ
        saveLookupToken(res.order_code, res.lookup_token);
        clearRequestId();
        cart.clear();
        // SHOP-FIX-01: mở cổng ngay, khách vào thẳng trang quét mã. Lỗi thì vào trang đơn (D1) có nút "Thanh toán".
        try {
          const session = await startCheckoutSession(res.order_code);
          if (USE_MOCK) goToMockGateway(res.order_code, Number(res.total_amount));
          else redirectToGateway(session);
          // Trình duyệt sắp điều hướng đi: giữ nút ở trạng thái đang xử lý.
          openingRef.current = true;
          return;
        } catch {
          router.replace(orderUrl(res.order_code, true));
          return;
        }
      } catch (err) {
        if (opts?.withoutVoucher) setVoucherGone(null);
        handleSendError(err, lines);
      } finally {
        if (!openingRef.current) {
          submittingRef.current = false;
          setSubmitting(false);
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [cart, name, phone, selection, street, consent, consentRequired, policy, router, voucher.code, voucher.quote]
  );

  function handleSendError(err: unknown, lines: typeof cart.lines) {
    setNetworkOpen(false);
    if (!(err instanceof ApiError)) {
      // Không nhận được phản hồi: đơn có thể đã được tạo. "Thử lại" gửi CÙNG client_request_id (C4).
      setNetworkOpen(true);
      return;
    }
    const code = err.code ?? "";
    if (code === "VOUCHER_INVALID") {
      // Mã hết hiệu lực giữa lúc điền form (B8): hỏi khách. Mã bị bỏ khỏi giỏ để lần sau không gửi lại.
      // Chưa có quote máy chủ ở bước đặt hàng thì discountedPrice = null để không gạch trùng số tổng (GUI-02).
      setVoucherGone({
        code: voucher.code ?? readVoucherCode() ?? "",
        fullPrice: localTotal,
        discountedPrice: voucher.quote ? voucher.quote.total_after : null,
      });
      voucher.remove();
      // "Giá chưa giảm" lấy từ máy chủ (kiểm không mã); lỗi mạng thì giữ số tạm tính của giỏ đang hiện.
      checkVoucher({ items: lines.map((l) => ({ item_code: l.item_code, qty: qtyToApiString(l.qty) })) })
        .then((r) => setVoucherGone((g) => (g ? { ...g, fullPrice: r.total_after } : g)))
        .catch(() => {});
      return;
    }
    if (code === "OUT_OF_STOCK" && Array.isArray(err.data?.lines)) {
      const byCode = new Map(lines.map((l) => [l.item_code, l]));
      const rows: SoldOutLine[] = [];
      for (const row of err.data.lines as OutOfStockLine[]) {
        const l = byCode.get(row.item_code);
        if (!l) continue;
        rows.push({
          itemCode: l.item_code,
          name: l.name,
          unit: l.unit,
          qty: l.qty,
          minQty: minQtyRef.current.get(l.item_code) ?? parseQtyRule(undefined, undefined, l.unit).minQty,
          level: row.stock_level === "out" ? "out" : "short",
          changed: false,
        });
      }
      if (rows.length > 0) {
        setSoldOut(rows);
        return;
      }
    }
    if (code === "POLICY_CHANGED" || err.status === 409) {
      setConsent(false);
      const cur = err.data?.current;
      if (cur && typeof cur.version_id === "number") {
        setPolicy((prev) => ({
          slug: String(cur.slug ?? prev?.slug ?? "quyen-rieng-tu"),  // naming: allow - slug trang CMS (dữ liệu)
          title: prev?.title ?? "Chính sách quyền riêng tư",
          version: Number(cur.version ?? prev?.version ?? 0),
          version_id: cur.version_id,
          effective_from: prev?.effective_from ?? null,
        }));
      }
      setPolicyOpen(true);
      return;
    }
    if (code === "SHOP_CLOSED" || err.status === 503) {
      setShopClosed(true);
      return;
    }
    if (code === "throttled" || err.status === 429) {
      setThrottledOpen(true);
      return;
    }
    if (code === "VALIDATION" && err.data?.fields && typeof err.data.fields === "object") {
      const next: FormErrors = mapServerFields(err.data.fields as Record<string, string>);
      if (Object.keys(next).length > 0) {
        setErrors(next);
        setSummaryShown(true);
        setSummaryToken((n) => n + 1);
        return;
      }
    }
    const limitMessage = orderLimitMessage(code, err.data?.detail ?? err.message);
    if (limitMessage) {
      setBanner(limitMessage);
      return;
    }
    if (code === "INVALID_QTY") {
      setBanner("Số lượng trong giỏ chưa đúng mức bán. Quay lại giỏ hàng để chỉnh rồi đặt lại.");
      return;
    }
    setBanner(err.message || "Chưa đặt được hàng. Bạn thử lại sau ít phút.");
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (submittingRef.current || consentRequired === null) return;
    const found = validateForm({ name, phone, ...selection, street, consent }, consentRequired && !!policy);
    setErrors(found);
    if (Object.keys(found).length > 0) {
      setSummaryShown(true);
      setSummaryToken((n) => n + 1);
      return;
    }
    void send();
  }

  // ---- Tìm địa chỉ VietMap qua máy chủ Cá Về (SHOP-3-04, 02b §1.9b) ----
  function openMap() {
    if (!addressSearchEnabled) return;
    // Đã lỗi 503/mạng hai lần trong phiên: mở thẳng C5, không mở lại hộp tìm (02b §1.9b.5, AC5).
    if (shouldOpenFallbackDirectly()) setMapFailedOpen(true);
    else setMapOpen(true);
  }

  function onMapFailed() {
    // Đóng hộp tìm trước rồi mới mở C5 (không chồng hai modal).
    setMapOpen(false);
    window.setTimeout(() => setMapFailedOpen(true), 320);
  }

  function onMapConfirm(result: AddressSearchConfirmResult) {
    setStreet(result.street.slice(0, STREET_MAX)); // chỉ điền ô số nhà; tỉnh/phường chỉ đổi khi khách bấm "Dùng phường này" (Q-5, AC3)
    setFilledFromMap(true);
    setWardSuggestion(result.suggestion);
    setFieldError("street", undefined);
    setMapOpen(false);
    // Hộp tìm trả tiêu điểm về nút khi đóng xong; ta đưa vào cuối ô số nhà sau đó.
    window.setTimeout(focusAddressEnd, 320);
  }

  function applyWardSuggestion() {
    if (!wardSuggestion) return;
    // Đúng thứ tự xoá cấp con trong formRules: selectScheme → selectProvince → [selectDistrict] → selectWard (02b §1.9b.4, AC3c).
    let next = selectScheme(selection, wardSuggestion.scheme);
    next = selectProvince(next, wardSuggestion.province_code);
    if (wardSuggestion.scheme === "legacy") {
      next = selectDistrict(next, wardSuggestion.district_code ?? "");
    }
    next = selectWard(next, wardSuggestion.ward_code);
    changeSelection(next);
  }

  function closeMapFailed() {
    setMapFailedOpen(false);
    window.setTimeout(focusAddressEnd, 230);
  }

  // ---- C3: cập nhật giỏ rồi đặt lại ----
  function changeToMin(code: string) {
    const unit = cart.lines.find((l) => l.item_code === code)?.unit ?? "kg";
    cart.setQty(code, minQtyRef.current.get(code) ?? parseQtyRule(undefined, undefined, unit).minQty);
    setSoldOut((prev) => prev && prev.map((l) => (l.itemCode === code ? { ...l, changed: true } : l)));
  }

  function updateAndRetry() {
    if (!soldOut) return;
    const byCode = new Map(soldOut.map((l) => [l.itemCode, l]));
    const next = cart.lines
      .map((l) => {
        const row = byCode.get(l.item_code);
        if (!row) return l;
        if (row.level === "out") return null;
        if (row.qty <= row.minQty && !row.changed) return null; // không đủ hàng ở mức tối thiểu: bỏ
        return { ...l, qty: row.minQty };
      })
      .filter((l): l is NonNullable<typeof l> => l !== null);
    cart.updateEntries(() => next);
    setSoldOut(null);
    if (next.length === 0) {
      router.replace("/shop/cart/");
      return;
    }
    void send({ lines: next });
  }

  const ready = cart.ready && consentRequired !== null;

  if (shopClosed) {
    return (
      <ShopFrame header="checkout" title="Thông tin nhận hàng" footer="compact" bottomNav={false} backHref="/shop/cart/">
        <div className={s.page}>
          <CheckoutSteps current={2} />
          <div className={s.paused}>
            <EmptyState
              icon="phone"
              title="Cá Về tạm ngưng nhận đơn online"
              description={hotline ? `Gọi ${hotline} để đặt hàng.` : "Liên hệ Cá Về để đặt hàng."}
              primaryAction={{ label: "Xem giỏ", href: "/shop/cart/" }}
              contactHref={contactTarget(hotline)}
              contactLabel={hotline ? `Gọi ${hotline}` : "Liên hệ chúng tôi"}
              headingLevel={1}
            >
              <p className={s.pausedNote}>Giỏ hàng vẫn được giữ.</p>
            </EmptyState>
          </div>
        </div>
      </ShopFrame>
    );
  }

  const errorList = summaryShown ? errorSummary(errors) : [];
  const showConsent = consentRequired === true && policy !== null;

  return (
    <ShopFrame header="checkout" title="Thông tin nhận hàng" footer="compact" bottomNav={false} backHref="/shop/cart/">
      <div className={s.page}>
        <div className={s.head}>
          <h1 className={s.title}>Thông tin nhận hàng</h1>
          <CheckoutSteps current={2} />
        </div>

        <div className={s.layout}>
          <div className={s.formCol}>
            {banner ? (
              <div className={s.block}>
                <Banner tone="crit" live="assertive">
                  {banner}
                </Banner>
              </div>
            ) : null}
            {voucher.dropped ? (
              <div className={s.block}>
                <Banner tone="info" live="polite">
                  Mã {voucher.dropped.code} không còn dùng được. {voucherMessage(voucher.dropped.kind, minOrderOf(voucher.dropped.result), voucher.dropped.result?.auto_discount_amount)} Đơn tính theo giá chưa giảm.
                </Banner>
              </div>
            ) : null}
            {errorList.length > 0 ? (
              <div className={s.block}>
                <FormErrorSummary errors={errorList} focusToken={summaryToken} />
              </div>
            ) : null}

            <form id="checkout-form" method="post" noValidate onSubmit={onSubmit} className={s.form}>
              <section aria-labelledby="h-recipient" className={s.section}>
                <h2 id="h-recipient" className={s.sectionTitle}>
                  Người nhận
                </h2>
                <TextField
                  id="f-name"
                  name="name"
                  label="Họ và tên"
                  value={name}
                  onChange={(v) => {
                    setName(v);
                    recheck("name", { name: v, phone, street, selection });
                  }}
                  onBlur={() => checkOnBlur("name")}
                  required
                  autoComplete="name"
                  placeholder="Nguyễn Văn A"
                  error={errors.name}
                  readOnly={submitting}
                />
                <TextField
                  id="f-phone"
                  name="phone"
                  label="Số điện thoại"
                  type="tel"
                  inputMode="tel"
                  value={phone}
                  onChange={(v) => {
                    setPhone(v);
                    recheck("phone", { name, phone: v, street, selection });
                  }}
                  onBlur={() => checkOnBlur("phone")}
                  required
                  autoComplete="tel"
                  placeholder="09xx xxx xxx"
                  error={errors.phone}
                  readOnly={submitting}
                />
              </section>

              <section className={s.section}>
                <AddressField
                  selection={selection}
                  onScheme={(v) => {
                    if (v !== selection.scheme) setWardSuggestion(null);
                    changeSelection(selectScheme(selection, v));
                  }}
                  onProvince={(v) => changeSelection(selectProvince(selection, v))}
                  onDistrict={(v) => changeSelection(selectDistrict(selection, v))}
                  onWard={(v) => changeSelection(selectWard(selection, v))}
                  street={street}
                  onStreet={(v) => {
                    setStreet(v);
                    setFilledFromMap(false);
                    setWardSuggestion(null);
                    recheck("street", { name, phone, street: v, selection });
                  }}
                  onStreetBlur={() => checkOnBlur("street")}
                  errors={errors}
                  filledFromMap={filledFromMap}
                  wardSuggestion={wardSuggestion}
                  onApplyWardSuggestion={applyWardSuggestion}
                  addressSearchEnabled={addressSearchEnabled}
                  readOnly={submitting}
                  onOpenMap={openMap}
                />
              </section>

              <section className={s.section}>
                <PaymentChoice disabled={submitting} />
              </section>

              {consentRequired === null ? (
                <section className={s.section} aria-busy="true">
                  <Skeleton height={44} radius="md" />
                </section>
              ) : showConsent ? (
                <section className={s.section}>
                  <Checkbox
                    id="f-consent"
                    name="privacy_consent"
                    checked={consent}
                    onChange={(v) => {
                      setConsent(v);
                      if (v) setFieldError("consent", undefined);
                    }}
                    error={errors.consent}
                    disabled={submitting}
                  >
                    Tôi đồng ý để Cá Về dùng họ tên, số điện thoại và địa chỉ này để giao và hỗ trợ đơn hàng, theo{" "}
                    <a href={`/pages/?slug=${encodeURIComponent(policy.slug)}`} target="_blank" rel="noopener">
                      Chính sách quyền riêng tư<span className="visually-hidden"> (mở tab mới)</span>
                    </a>
                    . Dữ liệu được lưu trên máy chủ đặt ở nước ngoài.
                  </Checkbox>
                </section>
              ) : null}
            </form>
          </div>

          <div className={s.summaryCol}>
            <CartSummary
              context="checkout"
              itemCount={itemCount}
              total={total}
              discount={quote && voucher.code ? { code: voucher.code, amount: quote.discount_amount } : undefined}
              pendingVoucherNote={pendingVoucher}
              title={`Đơn hàng (${itemCount} món)`}
              totalLabel={`${itemCount} món · tổng tiền hàng`}
              lines={summaryLines}
              cta={{
                label: "Đặt hàng",
                form: "checkout-form",
                loading: submitting || !ready || voucher.checking,
                loadingText: submitting ? "Đang đặt…" : "Đang tải…",
              }}
            />
          </div>
        </div>
      </div>

      <AddressSearchSheet
        open={mapOpen}
        scheme={selection.scheme}
        onClose={() => setMapOpen(false)}
        onConfirm={onMapConfirm}
        onSearchFailed={onMapFailed}
      />

      {/* C5: chưa tìm được địa chỉ (02b §1.9b, phương án A không có bản đồ). Một nút; mọi cách đóng đưa tiêu điểm vào ô số nhà. */}
      <Dialog
        open={mapFailedOpen}
        onClose={closeMapFailed}
        title="Chưa tìm được địa chỉ"
        description="Bạn gõ địa chỉ trực tiếp vào ô số nhà, vẫn đặt hàng bình thường."
        kind="alert"
        icon={{ name: "map-pin", tone: "warn" }}
        closeLabel="Đóng, nhập địa chỉ bằng tay"
        actions={
          <Button size="lg" fullWidth data-autofocus onClick={closeMapFailed}>
            Nhập tay
          </Button>
        }
      />

      <SoldOutSheet
        open={soldOut !== null}
        lines={soldOut ?? []}
        hotline={hotline}
        busy={submitting}
        onChangeToMin={changeToMin}
        onUpdateAndRetry={updateAndRetry}
        onBackToCart={() => {
          setSoldOut(null);
          router.push("/shop/cart/");
        }}
      />

      {/* B8 (C6): mã giảm giá không còn dùng được lúc đặt. Mặc định tiêu điểm ở "Quay lại giỏ" (hành động an toàn). */}
      <Dialog
        open={voucherGone !== null}
        onClose={() => {
          setVoucherGone(null);
          focusSoon(document.querySelector<HTMLElement>('button[form="checkout-form"]'));
        }}
        title={`Mã ${voucherGone?.code ?? ""} không còn dùng được`}
        description="Đơn sẽ tính theo giá chưa giảm."
        kind="alert"
        icon={{ name: "warning", tone: "warn" }}
        busy={submitting}
        closeLabel="Đóng thông báo mã giảm giá"
        actions={
          <>
            <Button
              size="lg"
              fullWidth
              loading={submitting}
              loadingText="Đang đặt…"
              onClick={() => void send({ withoutVoucher: true })}
            >
              Đặt hàng không dùng mã
            </Button>
            <Button
              variant="secondary"
              size="lg"
              fullWidth
              data-autofocus
              disabled={submitting}
              onClick={() => {
                setVoucherGone(null);
                router.push("/shop/cart/");
              }}
            >
              Quay lại giỏ
            </Button>
          </>
        }
      >
        {voucherGone ? (
          <p className={s.goneTotal}>
            <span>Tổng tiền hàng</span>
            <span className="num">
              {hasDistinctDiscountedTotal(voucherGone.discountedPrice, voucherGone.fullPrice) ? (
                <>
                  <del className={s.goneOld}>{formatPriceVnd(voucherGone.discountedPrice)}</del>{" "}
                </>
              ) : null}
              <strong>{formatPriceVnd(voucherGone.fullPrice)}</strong>
            </span>
          </p>
        ) : null}
      </Dialog>

      {/* C4: mất mạng khi đặt. "Thử lại" gửi cùng client_request_id; đang gửi lại thì không đóng được. */}
      <Dialog
        open={networkOpen}
        onClose={() => setNetworkOpen(false)}
        title="Chưa gửi được đơn"
        description="Đơn chưa được tạo. Kiểm tra mạng rồi thử lại."
        kind="alert"
        icon={{ name: "wifi-off", tone: "neutral" }}
        busy={submitting}
        closeLabel="Đóng thông báo chưa gửi được đơn"
        actions={
          <>
            <Button size="lg" fullWidth loading={submitting} loadingText="Đang đặt…" data-autofocus onClick={() => void send()}>
              Thử lại
            </Button>
            {hotline ? (
              <Button variant="outline" size="lg" fullWidth href={contactTarget(hotline)}>
                Gọi {hotline}
              </Button>
            ) : null}
            <Button variant="secondary" size="lg" fullWidth disabled={submitting} onClick={() => setNetworkOpen(false)}>
              Để sau
            </Button>
          </>
        }
      />

      {/* C8: quá nhanh (429). Form giữ nguyên. */}
      <Dialog
        open={throttledOpen}
        onClose={() => setThrottledOpen(false)}
        title="Bạn thao tác hơi nhanh"
        description="Đợi 1 phút rồi thử lại."
        kind="alert"
        icon={{ name: "clock", tone: "warn" }}
        closeLabel="Đóng thông báo thao tác nhanh"
        actions={
          <Button size="lg" fullWidth data-autofocus onClick={() => setThrottledOpen(false)}>
            Đã hiểu
          </Button>
        }
      />

      {/* C9: chính sách vừa đổi (409). Đóng thì bỏ tick, tiêu điểm vào ô đồng ý, thông tin đã điền giữ nguyên. */}
      <Dialog
        open={policyOpen}
        onClose={() => {
          setPolicyOpen(false);
          focusSoon(document.getElementById("f-consent"));
        }}
        title="Chính sách quyền riêng tư vừa cập nhật"
        description="Đọc bản mới rồi đồng ý để đặt hàng. Thông tin bạn điền vẫn giữ nguyên."
        kind="alert"
        icon={{ name: "info", tone: "info" }}
        closeLabel="Đóng thông báo chính sách"
        actions={
          <>
            <Button
              variant="outline"
              size="lg"
              fullWidth
              external
              href={`/pages/?slug=${encodeURIComponent(policy?.slug ?? "quyen-rieng-tu")}`}  // naming: allow - slug trang CMS (dữ liệu)
            >
              Xem chính sách
            </Button>
            <Button
              size="lg"
              fullWidth
              data-autofocus
              onClick={() => {
                setPolicyOpen(false);
                focusSoon(document.getElementById("f-consent"));
              }}
            >
              Đã hiểu
            </Button>
          </>
        }
      />
    </ShopFrame>
  );
}
