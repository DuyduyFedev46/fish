"use client";

import type { FormEvent } from "react";
import Banner from "@/components/ui/Banner";
import Button from "@/components/ui/Button";
import TextField from "@/components/ui/TextField";
import { contactTarget } from "@/components/shopLinks";
import s from "./LookupForm.module.css";

export type LookupStatus = "idle" | "missing" | "not_found" | "throttled" | "network";

export interface LookupFormProps {
  idPrefix?: string;
  code: string;
  phone: string;
  onCodeChange: (v: string) => void;
  onPhoneChange: (v: string) => void;
  onSubmit: () => void;
  loading: boolean;
  status: LookupStatus;
  hotline?: string;
}

/**
 * Form tra đơn (F1/F2): mã đơn + số điện thoại đặt hàng. Khi không tìm thấy chỉ có MỘT câu chung, không nói ô nào sai và
 * không gắn aria-invalid (UI-RULES §3.2, bất biến 9). Form dùng method="post" để dù gửi trước khi trang nạp xong,
 * SĐT cũng không lên URL.
 */
export default function LookupForm({
  idPrefix = "lookup",
  code,
  phone,
  onCodeChange,
  onPhoneChange,
  onSubmit,
  loading,
  status,
  hotline,
}: LookupFormProps) {
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!loading) onSubmit();
  }
  return (
    <form method="post" className={s.form} onSubmit={submit} noValidate aria-busy={loading || undefined}>
      {status === "not_found" ? (
        <Banner tone="crit" live="assertive">
          Không tìm thấy đơn khớp mã và số điện thoại.{" "}
          {hotline ? (
            <>
              Kiểm tra lại, hoặc gọi <a href={contactTarget(hotline)}>{hotline}</a>.
            </>
          ) : (
            "Kiểm tra lại mã đơn và số điện thoại."
          )}
        </Banner>
      ) : null}
      {status === "missing" ? (
        <Banner tone="crit" live="assertive">
          Nhập mã đơn và số điện thoại đặt hàng.
        </Banner>
      ) : null}
      {status === "throttled" ? (
        <Banner tone="warn" live="assertive">
          Bạn thử lại sau ít phút.
        </Banner>
      ) : null}
      {status === "network" ? (
        <Banner
          tone="crit"
          live="assertive"
          action={
            <Button size="sm" variant="secondary" loading={loading} onClick={onSubmit}>
              Thử lại
            </Button>
          }
        >
          Chưa tải được đơn. Thử lại.
        </Banner>
      ) : null}
      <TextField
        id={`${idPrefix}-code`}
        name="order_code"
        label="Mã đơn"
        value={code}
        onChange={onCodeChange}
        placeholder="SO…"
        hint="Mã đơn hiện ngay sau khi bạn đặt hàng, bắt đầu bằng SO"
        autoComplete="off"
        autoCapitalize="characters"
        spellCheck={false}
        readOnly={loading}
      />
      <TextField
        id={`${idPrefix}-phone`}
        name="phone"
        label="Số điện thoại đặt hàng"
        type="tel"
        inputMode="numeric"
        value={phone}
        onChange={onPhoneChange}
        placeholder="09xx xxx xxx"
        autoComplete="tel"
        readOnly={loading}
      />
      <Button type="submit" size="lg" fullWidth loading={loading} loadingText="Đang tra cứu…">
        Tra cứu
      </Button>
    </form>
  );
}
