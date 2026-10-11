"use client";

// Trang "Tạo mã giảm giá" (/vouchers/new/) và "Sửa mã" (/vouchers/edit/?id=) — SHOP-3b-02, 02b §3.9, BR-DM-22.
// Giờ bắt đầu/kết thúc nhập theo GIỜ VIỆT NAM (ô datetime-local) và gửi ISO qua `vnInputToIso`. Mã, kiểu giảm không đổi sau khi tạo.
// Mã đã bắt đầu chạy: chỉ sửa được tên, giờ kết thúc (lùi về sau), tổng lượt (tăng), đơn tối thiểu (giảm), mức giảm và mức tối đa (tăng);
// ô khác bị khoá. Sửa ngược hướng: báo ngay trên form, BE vẫn kiểm lại (UNFAVORABLE_CHANGE). Lỗi theo trường của BE hiện dưới ô tương ứng,
// lỗi khác ở alert đầu form, nút chính đổi "Thử lại", giá trị đã nhập được giữ. Không ghi gì vào storage, URL hay log.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { Chip } from "@/shared/ui/Chip";
import { Field } from "@/shared/ui/form/Field";
import { RadioGroup } from "@/shared/ui/form/Choice";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { FormGrid, FormSection, FormSpan } from "@/shared/ui/form/FormSection";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { createVoucher, enableVoucher, updateVoucher } from "../api";
import { CURRENCY_UNIT, saveErrorMessage } from "../catalogModel";
import { VOUCHER_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { Voucher } from "../types";
import { useVoucherDetail, useVoucherId } from "../useVoucherDetail";
import {
  draftOfVoucher,
  emptyVoucherDraft,
  lockedFields,
  normalizeCode,
  serverFieldMessages,
  unfavorableChanges,
  validateVoucher,
  voucherInputOf,
  voucherPatchOf,
  voucherServerErrors,
  type VoucherDraft,
  type VoucherErrors,
} from "../voucherModel";
import { VoucherDisableDialog } from "./VoucherDisableDialog";
import { VoucherRedemptions } from "./VoucherRedemptions";
import s from "../catalog.module.css";

const KIND_OPTIONS = [
  { value: "PERCENT", label: M.optPercent },
  { value: "AMOUNT", label: M.optAmount },
];

const BACK = { href: "/vouchers/", label: M.formBack };

/** Trang tạo mã. */
export function VoucherCreateScreen() {
  const { me } = useAuth();
  const ability = catalogAbility(me?.permissions ?? []);
  if (!me) return null;
  if (!ability.manageVoucher) return <NoPermission />;
  return <VoucherFormBody />;
}

/** Trang sửa mã: tải mã theo `?id=` rồi dựng form. */
export function VoucherEditScreen() {
  const { me } = useAuth();
  const ability = catalogAbility(me?.permissions ?? []);
  const id = useVoucherId();
  const detail = useVoucherDetail(ability.manageVoucher ? id : null);
  if (!me) return null;
  if (!ability.manageVoucher || detail.status === "forbidden") return <NoPermission />;
  if (id === undefined) return null;
  if (id === null || detail.status === "notfound") {
    return (
      <div className="page-state">
        <span className="state-ic">
          <Icon name="search_off" />
        </span>
        <h2 className="state-title">{M.notFound}</h2>
        <div className="page-state-actions">
          <Link href="/vouchers/" className="btn">
            {M.formBack}
          </Link>
        </div>
      </div>
    );
  }
  if (detail.status === "error") return <ErrorScreen onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) {
    return (
      <SkeletonScreen>
        <SkeletonTable rows={5} cols={2} />
      </SkeletonScreen>
    );
  }
  return <VoucherFormBody voucher={detail.data} />;
}

function VoucherFormBody({ voucher }: { voucher?: Voucher }) {
  const router = useRouter();
  const toast = useToast();
  const editing = !!voucher;
  const [draft, setDraft] = useState<VoucherDraft>(() => (voucher ? draftOfVoucher(voucher) : emptyVoucherDraft()));
  const [errs, setErrs] = useState<VoucherErrors>({});
  const [serverErrs, setServerErrs] = useState<VoucherErrors>({});
  const [noChange, setNoChange] = useState(false);
  const [disabling, setDisabling] = useState(false);
  const [viewingUses, setViewingUses] = useState(false);
  const [enabling, setEnabling] = useState(false);
  const [stateError, setStateError] = useState<string | null>(null);
  const nowMs = useMemo(() => Date.now(), []);
  const locked = useMemo(() => (voucher ? lockedFields(voucher, nowMs) : new Set<keyof VoucherDraft>()), [voucher, nowMs]);
  const started = !!voucher && !!voucher.starts_at && nowMs >= Date.parse(voucher.starts_at);

  const sub = useSubmit(
    async () => {
      setServerErrs({});
      try {
        if (voucher) return await updateVoucher(voucher.id, voucherPatchOf(voucher, draft, nowMs));
        return await createVoucher(voucherInputOf(draft));
      } catch (err) {
        setServerErrs(voucherServerErrors(err));
        // Khoá lạ của BE (không có ô tương ứng) vẫn nằm trong alert đầu form qua `sub.error`.
        void serverFieldMessages(err);
        throw err;
      }
    },
    {
      onSuccess: () => {
        toast.success(editing ? M.saved : M.created);
        router.push("/vouchers/");
      },
    },
  );

  const set = <K extends keyof VoucherDraft>(key: K) => (value: VoucherDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setErrs((e) => ({ ...e, [key]: undefined }));
    setServerErrs((e) => ({ ...e, [key]: undefined }));
    setNoChange(false);
  };

  const submit = () => {
    let found = validateVoucher(draft);
    if (voucher && started) found = { ...found, ...unfavorableChanges(voucher, draft) };
    setErrs(found);
    if (Object.values(found).some(Boolean)) return;
    if (voucher && Object.keys(voucherPatchOf(voucher, draft, nowMs)).length === 0) {
      setNoChange(true);
      return;
    }
    void sub.submit();
  };

  // Bật lại mã ngay trên trang sửa (điện thoại không có cột Thao tác ở danh sách).
  const enable = async () => {
    if (!voucher || enabling) return;
    setEnabling(true);
    setStateError(null);
    try {
      await enableVoucher(voucher.id);
      toast.success(M.enabledToast(voucher.code));
      router.push("/vouchers/");
    } catch (e) {
      setStateError(`${M.toggleFailed} ${saveErrorMessage(e)}`);
    } finally {
      setEnabling(false);
    }
  };

  const err = (key: keyof VoucherDraft) => errs[key] ?? serverErrs[key] ?? null;
  const percent = draft.kind === "PERCENT";
  const hasFieldErrors = Object.values(serverErrs).some(Boolean);
  const alert =
    noChange ? (
      <FormAlert>{M.noChange}</FormAlert>
    ) : sub.error && !hasFieldErrors ? (
      <FormAlert>{sub.error}</FormAlert>
    ) : stateError ? (
      <FormAlert>{stateError}</FormAlert>
    ) : undefined;

  return (
    <FormPage
      title={voucher ? M.formTitleEdit(voucher.code) : M.formTitleNew}
      back={BACK}
      alert={alert}
      onSubmit={submit}
      primaryText={editing ? M.submitSave : M.submitCreate}
      submitting={sub.submitting}
      failed={sub.failed}
      secondary={{ label: M.cancel, onClick: () => router.push("/vouchers/") }}
    >
      {started && <p className={s.railNote}>{M.lockedNote}</p>}
      <FormSection title={M.formSectionMain}>
        <FormGrid>
          <Field
            label={M.fieldCode}
            required
            name="code"
            value={draft.code}
            onChange={(v) => set("code")(normalizeCode(v))}
            maxLength={20}
            error={err("code")}
            disabled={locked.has("code")}
            autoFocus={!editing}
          />
          <Field label={M.fieldName} required name="name" value={draft.name} onChange={set("name")} maxLength={200} error={err("name")} autoFocus={editing} />
          <RadioGroup
            label={M.fieldKind}
            required
            name="kind"
            value={draft.kind}
            onChange={(v) => {
              setDraft((d) => ({ ...d, kind: v === "AMOUNT" ? "AMOUNT" : "PERCENT", value: "", maxDiscount: "" }));
              setErrs((e) => ({ ...e, value: undefined, maxDiscount: undefined }));
            }}
            options={KIND_OPTIONS}
            disabled={locked.has("kind")}
            error={serverErrs.kind}
          />
          {percent ? (
            <>
              <Field label={M.fieldValuePercent} type="number" unit="%" required name="value" value={draft.value} onChange={set("value")} error={err("value")} />
              <Field label={M.fieldMaxDiscount} type="money" unit={CURRENCY_UNIT} required name="max_discount" value={draft.maxDiscount} onChange={set("maxDiscount")} error={err("maxDiscount")} />
            </>
          ) : (
            <Field label={M.fieldValueAmount} type="money" unit={CURRENCY_UNIT} required name="value" value={draft.value} onChange={set("value")} error={err("value")} />
          )}
        </FormGrid>
        {editing && <p className={s.railNote}>{M.lockedCodeKind}</p>}
      </FormSection>
      <FormSection title={M.formSectionLimit}>
        <FormGrid>
          <Field label={M.fieldMinOrder} type="money" unit={CURRENCY_UNIT} name="min_order_amount" value={draft.minOrderAmount} onChange={set("minOrderAmount")} error={err("minOrderAmount")} />
          <Field label={M.fieldTotalUses} type="number" required name="total_uses" value={draft.totalUses} onChange={set("totalUses")} error={err("totalUses")} />
          <Field label={M.fieldStartsAt} type="datetime-local" required name="starts_at" value={draft.startsAt} onChange={set("startsAt")} error={err("startsAt")} disabled={locked.has("startsAt")} />
          <Field label={M.fieldEndsAt} type="datetime-local" required name="ends_at" value={draft.endsAt} onChange={set("endsAt")} error={err("endsAt")} />
          <FormSpan>
            <Field
              as="textarea"
              label={M.fieldTerms}
              name="customer_terms"
              value={draft.customerTerms}
              onChange={set("customerTerms")}
              rows={3}
              maxLength={300}
              counter
              error={err("customerTerms")}
              disabled={locked.has("customerTerms")}
            />
          </FormSpan>
        </FormGrid>
      </FormSection>
      {voucher && (
        <FormSection title={M.formSectionState}>
          <p className={s.railNote}>
            <span>{M.stateNow}</span>
            <Chip table={ENUMS.voucherStatus} value={voucher.status} />
            <span className="num">{M.usesCell(voucher.used_count, voucher.held_count, voucher.total_uses)}</span>
          </p>
          <div className={s.voucherActions}>
            {voucher.is_active && (voucher.status === "running" || voucher.status === "scheduled") ? (
              <button type="button" className="btn" onClick={() => setDisabling(true)}>
                {M.disableConfirm}
              </button>
            ) : !voucher.is_active ? (
              <button type="button" className="btn" onClick={() => void enable()} disabled={enabling} aria-busy={enabling || undefined}>
                {enabling ? <Icon name="progress_activity" className="spin" /> : M.actionEnable}
              </button>
            ) : null}
            <button type="button" className="btn" onClick={() => setViewingUses(true)}>
              {M.actionUses}
            </button>
          </div>
        </FormSection>
      )}
      {voucher && disabling && (
        <VoucherDisableDialog
          voucher={voucher}
          onClose={() => setDisabling(false)}
          onDone={(v) => {
            toast.success(M.disabledToast(v.code));
            router.push("/vouchers/");
          }}
        />
      )}
      {voucher && viewingUses && <VoucherRedemptions voucher={voucher} onClose={() => setViewingUses(false)} />}
    </FormPage>
  );
}
