/**
 * Phần thuần của ô mã giảm giá (SHOP-3b-05/06): chuẩn hoá chữ gõ, ánh xạ kết quả kiểm mã sang loại lỗi và câu chữ,
 * dựng dòng điều kiện của mã. Số tiền giảm và tổng luôn do máy chủ trả (`total_after`), FE không tự tính.
 * Test: `scripts/test-voucher.mjs`.
 */
import { formatPriceVnd, formatTimeDayVn } from "@/lib/format";

export type VoucherErrorKind = "INVALID" | "EXPIRED" | "MIN_ORDER" | "USED_UP" | "BETTER_PROMO" | "NETWORK" | "THROTTLED";

export const VOUCHER_CODE_MAX = 20;

/** Chữ tự in hoa, bỏ khoảng trắng (B5). */
export function normalizeVoucherInput(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase().slice(0, VOUCHER_CODE_MAX);
}

const REASONS = new Set(["INVALID", "EXPIRED", "MIN_ORDER", "USED_UP", "BETTER_PROMO"]);

/** Lý do máy chủ trả (kết quả kiểm mã hoặc lỗi VOUCHER_INVALID) -> loại lỗi; lạ thì coi là mã không dùng được. */
export function reasonToKind(reason: string | null | undefined): VoucherErrorKind {
  return reason && REASONS.has(reason) ? (reason as VoucherErrorKind) : "INVALID";
}

/** Câu lỗi dưới ô (COMPONENTS #48 mục 10). `minOrderAmount` là đơn tối thiểu của mã, số đồng. */
export function voucherMessage(kind: VoucherErrorKind, minOrderAmount?: string | null, promoAmount?: string | null): string {
  switch (kind) {
    case "INVALID":
    case "EXPIRED":
      return "Mã không đúng hoặc đã hết hạn.";
    case "MIN_ORDER":
      return minOrderAmount ? `Đơn cần từ ${formatPriceVnd(minOrderAmount)} để dùng mã này.` : "Đơn chưa đủ điều kiện để dùng mã này.";
    case "USED_UP":
      return "Mã đã hết lượt dùng.";
    case "BETTER_PROMO":
      // Số lấy từ máy chủ (`auto_discount_amount`); thiếu thì giữ câu gốc của 02a.
      return promoAmount && Number(promoAmount) > 0 ? `Ưu đãi đang áp (−${formatPriceVnd(promoAmount)}) đã có lợi hơn mã này.` : "Ưu đãi đang áp đã có lợi hơn mã này.";
    case "NETWORK":
      return "Chưa kiểm được mã.";
    case "THROTTLED":
      return "Bạn thao tác hơi nhanh. Đợi 1 phút rồi thử lại.";
  }
}

/** Lỗi nào là thông tin (màu `ink-2`, ô không viền đỏ), không phải lỗi người dùng sai. */
export function isInfoKind(kind: VoucherErrorKind): boolean {
  return kind === "BETTER_PROMO";
}

type TermsLike = {
  kind: "PERCENT" | "AMOUNT";
  value: string;
  max_discount: string | null;
  min_order_amount: string;
  ends_at: string;
  customer_terms: string;
};

/** "23:59 31/10" (giờ VN) từ ISO. */
function deadlineText(iso: string): string {
  return formatTimeDayVn(iso).replace(" · ", " ");
}

/**
 * Dòng điều kiện của mã ở giỏ (02a mục 9.5, BR-DM-24): mức giảm, trần, đơn tối thiểu, hạn, "Số lượt có hạn".
 * KHÔNG có số lượt còn lại. Câu không cộng dồn là chữ cố định (xem `VOUCHER_STACK_NOTE`).
 */
export function describeTerms(terms: TermsLike): string {
  const parts: string[] = [];
  if (terms.kind === "PERCENT") {
    const cap = terms.max_discount ? `, tối đa ${formatPriceVnd(terms.max_discount)}` : "";
    parts.push(`Giảm ${Number(terms.value)}%${cap}`);
  } else {
    parts.push(`Giảm ${formatPriceVnd(terms.value)}`);
  }
  if (Number(terms.min_order_amount) > 0) parts.push(`Đơn từ ${formatPriceVnd(terms.min_order_amount)}`);
  if (terms.ends_at) parts.push(`Hạn ${deadlineText(terms.ends_at)}`);
  parts.push("Số lượt có hạn");
  const extra = terms.customer_terms.trim();
  return extra ? `${parts.join(" · ")}. ${extra}` : parts.join(" · ");
}

export const VOUCHER_STACK_NOTE = "Không áp dụng cùng ưu đãi khác; Cá Về tự chọn mức có lợi hơn cho bạn.";

/** Đoạn điều kiện đầy đủ ở giỏ: điều kiện của mã rồi câu không cộng dồn (chữ cố định). */
export function describeTermsFull(terms: TermsLike): string {
  return `${describeTerms(terms).replace(/[.\s]+$/, "")}. ${VOUCHER_STACK_NOTE}`;
}

/** Dấu vân tay các dòng gửi kiểm mã: đổi giỏ thì kết quả cũ hết giá trị. */
export function itemsKey(items: { item_code: string; qty: string }[]): string {
  return [...items]
    .map((i) => `${i.item_code}:${i.qty}`)
    .sort()
    .join("|");
}

/** Đơn tối thiểu của mã (đồng) cho câu MIN_ORDER: ưu tiên `terms`, không thì tạm tính + số còn thiếu; không biết thì null. */
export function minOrderOf(
  result: { terms: { min_order_amount: string } | null; subtotal: string; missing_amount: string | null } | undefined | null
): string | null {
  if (!result) return null;
  if (result.terms && Number(result.terms.min_order_amount) > 0) return result.terms.min_order_amount;
  if (result.missing_amount) return String(Number(result.subtotal) + Number(result.missing_amount));
  return null;
}

/** Giỏ rỗng (đã nạp xong) thì không còn mã nào để giữ: xoá để giỏ mới không tự áp lại mã cũ. */
export function shouldClearVoucher(ready: boolean, itemCount: number): boolean {
  return ready && itemCount === 0;
}
