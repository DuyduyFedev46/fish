"use client";

/**
 * Trạng thái mã giảm giá của giỏ (SHOP-3b-05, 3b-06). Mã lưu cùng giỏ (voucherStorage), số giảm và tổng do máy chủ trả
 * (`POST /api/shop/vouchers/check/`), FE không tự tính. Kết quả gắn với dấu vân tay các dòng; đổi giỏ thì kiểm lại và
 * kết quả cũ không dùng để hiển thị. Mã không còn dùng được khi kiểm lại thì bỏ khỏi giỏ và báo qua `dropped`.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, checkVoucher } from "@/lib/api";
import type { CreateOrderItemInput, VoucherCheckResult } from "@/lib/types";
import { clearVoucherCode, readVoucherCode, writeVoucherCode } from "./voucherStorage";
import { itemsKey, normalizeVoucherInput, reasonToKind, shouldClearVoucher, type VoucherErrorKind } from "./voucherView";

type Quote = { key: string; result: VoucherCheckResult };
type Failure = { kind: VoucherErrorKind; result?: VoucherCheckResult };

export interface UseVoucher {
  /** Mã đang áp (đã lưu), kể cả khi đang kiểm lại. */
  code: string | null;
  /** Kết quả kiểm còn đúng với giỏ hiện tại, hợp lệ; null khi chưa có hoặc giỏ vừa đổi. */
  quote: VoucherCheckResult | null;
  checking: boolean;
  /** Lỗi của lần "Áp dụng" gần nhất. */
  error: Failure | null;
  /** Mã đã tự bỏ vì kiểm lại thấy không còn dùng được (giỏ đổi, hết hạn...). */
  dropped: { code: string; kind: VoucherErrorKind; result?: VoucherCheckResult } | null;
  /** Trả kết quả kiểm khi mã hợp lệ và đã áp; null khi lỗi (lý do nằm ở `error`). */
  apply: (input: string) => Promise<VoucherCheckResult | null>;
  retry: () => Promise<VoucherCheckResult | null>;
  remove: () => void;
  clearError: () => void;
  clearDropped: () => void;
}

function failureOf(err: unknown): Failure {
  if (err instanceof ApiError && err.status === 429) return { kind: "THROTTLED" };
  return { kind: "NETWORK" };
}

export function useVoucher(items: CreateOrderItemInput[], enabled: boolean): UseVoucher {
  const key = itemsKey(items);
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const [code, setCode] = useState<string | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<Failure | null>(null);
  const [dropped, setDropped] = useState<UseVoucher["dropped"]>(null);
  const seq = useRef(0);
  const lastInput = useRef<string>("");
  const loaded = useRef(false);

  // Nạp mã đã lưu một lần khi giỏ đã sẵn sàng. Giỏ rỗng thì xoá mã (sau khi đặt xong giỏ mới không áp lại mã cũ).
  useEffect(() => {
    if (shouldClearVoucher(enabled, items.length)) {
      clearVoucherCode();
      setCode(null);
      setQuote(null);
      loaded.current = true;
      return;
    }
    if (!enabled || loaded.current) return;
    loaded.current = true;
    setCode(readVoucherCode());
  }, [enabled, items.length]);

  // Kiểm lại khi đổi giỏ (hoặc lần đầu có mã). Chờ 250ms để gõ số lượng liên tục không bắn nhiều lần.
  useEffect(() => {
    if (!enabled || !code || itemsRef.current.length === 0) return;
    if (quote && quote.key === key) return;
    const mine = ++seq.current;
    setChecking(true);
    const timer = window.setTimeout(() => {
      checkVoucher({ code, items: itemsRef.current })
        .then((res) => {
          if (mine !== seq.current) return;
          if (res.valid) {
            setQuote({ key, result: res });
          } else {
            clearVoucherCode();
            setCode(null);
            setQuote(null);
            setDropped({ code, kind: reasonToKind(res.reason_code), result: res });
          }
        })
        .catch(() => {
          // Mất mạng khi kiểm lại: giữ mã, chưa có số giảm; trang báo qua `error`.
          if (mine !== seq.current) return;
          setError({ kind: "NETWORK" });
        })
        .finally(() => {
          if (mine === seq.current) setChecking(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      // Hủy lượt kiểm đang chờ: bỏ kết quả về sau.
      seq.current += 1;
      setChecking(false);
    };
    // `quote` chỉ để so khoá; đổi `quote` không cần kiểm lại.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, code, key]);

  const apply = useCallback(async (input: string): Promise<VoucherCheckResult | null> => {
    const next = normalizeVoucherInput(input);
    if (!next || itemsRef.current.length === 0) return null;
    lastInput.current = next;
    const mine = ++seq.current;
    setChecking(true);
    setError(null);
    setDropped(null);
    try {
      const res = await checkVoucher({ code: next, items: itemsRef.current });
      if (mine !== seq.current) return null;
      if (res.valid) {
        writeVoucherCode(next);
        setQuote({ key: itemsKey(itemsRef.current), result: res });
        setCode(next);
        return res;
      }
      setError({ kind: reasonToKind(res.reason_code), result: res });
      return null;
    } catch (err) {
      if (mine === seq.current) setError(failureOf(err));
      return null;
    } finally {
      if (mine === seq.current) setChecking(false);
    }
  }, []);

  const retry = useCallback(() => apply(lastInput.current || readVoucherCode() || ""), [apply]);

  const remove = useCallback(() => {
    seq.current += 1;
    clearVoucherCode();
    setCode(null);
    setQuote(null);
    setError(null);
    setDropped(null);
    setChecking(false);
  }, []);

  const clearError = useCallback(() => setError(null), []);
  const clearDropped = useCallback(() => setDropped(null), []);

  return {
    code,
    quote: quote && quote.key === key && quote.result.valid ? quote.result : null,
    checking,
    error,
    dropped,
    apply,
    retry,
    remove,
    clearError,
    clearDropped,
  };
}
