"use client";

// Trang "Tạo ưu đãi giảm giá" (ED-31 / W5o, F1n): /catalog/rules/new/. Cần catalog.add_pricingrule (Chủ).
// Áp dụng cho "Theo mặt hàng" (chọn mặt hàng + mua từ N kg) hoặc "Theo đơn" (tổng đơn từ M đồng); mức giảm theo số tiền hoặc phần trăm
// (phần trăm 0 đến 100). Từ ngày / Đến ngày là ngày thuần, có thể để trống. Kiểm cùng luật với BE rồi mới gửi; lỗi BE theo trường hiện
// dưới ô tương ứng, lỗi khác hiện alert đầu form, nút chính đổi "Thử lại", giá trị đã nhập được giữ.
// Ưu đãi chỉ giảm giá lúc đặt đơn mới; đơn đã đặt không đổi giá.

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { RadioGroup, Switch } from "@/shared/ui/form/Choice";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { FormGrid, FormSection, FormSpan } from "@/shared/ui/form/FormSection";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { createPricingRule } from "../api";
import { CURRENCY_UNIT, emptyRuleDraft, ruleInputOf, validateRule, type RuleDraft, type RuleErrors } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import { useItemOptions } from "../useCatalogOptions";

const APPLY_OPTIONS = [
  { value: "ITEM", label: M.optApplyItem },
  { value: "ORDER", label: M.optApplyOrder },
];
const DISCOUNT_OPTIONS = [
  { value: "PERCENT", label: ENUMS.pricingRuleDiscountType.PERCENT.label },
  { value: "AMOUNT", label: ENUMS.pricingRuleDiscountType.AMOUNT.label },
];

export function PricingRuleForm() {
  const { me } = useAuth();
  const ability = catalogAbility(me?.permissions ?? []);
  if (!me) return null;
  if (!ability.addRule) return <NoPermission />;
  return <PricingRuleFormBody />;
}

function PricingRuleFormBody() {
  const router = useRouter();
  const toast = useToast();
  const [draft, setDraft] = useState<RuleDraft>(emptyRuleDraft);
  const [errs, setErrs] = useState<RuleErrors>({});
  const isItem = draft.applyOn === "ITEM";
  const items = useItemOptions(isItem);

  const sub = useSubmit(() => createPricingRule(ruleInputOf(draft)), {
    onSuccess: () => {
      toast.success(M.ruleCreated);
      router.push("/catalog/?tab=rules");
    },
  });

  const set = <K extends keyof RuleDraft>(key: K) => (value: RuleDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setErrs((e) => ({ ...e, [key]: undefined }));
  };

  const submit = () => {
    const found = validateRule(draft);
    setErrs(found);
    if (Object.values(found).some(Boolean)) return;
    void sub.submit();
  };

  const optionsFailed = isItem && items.status === "error";
  const alert = optionsFailed ? (
    <div className="alert-box err" role="alert">
      <Icon name="sync_problem" />
      <span>{M.optionsFailed}</span>
      <button type="button" className="btn" onClick={items.reload}>
        {M.retry}
      </button>
    </div>
  ) : sub.error && Object.keys(sub.fieldErrors).length === 0 ? (
    <FormAlert>{sub.error}</FormAlert>
  ) : undefined;
  const fe = sub.fieldErrors;
  const itemOptions = items.rows.filter((i) => i.is_active).map((i) => ({ value: String(i.id), label: i.name }));

  return (
    <FormPage
      title={M.ruleFormTitle}
      back={{ href: "/catalog/?tab=rules", label: M.ruleFormBack }}
      alert={alert}
      onSubmit={submit}
      primaryText={M.ruleSubmit}
      submitting={sub.submitting}
      failed={sub.failed}
      primaryDisabled={optionsFailed}
      secondary={{ label: M.cancel, onClick: () => router.push("/catalog/?tab=rules") }}
    >
      <FormSection title={M.ruleSectionTitle}>
        <FormGrid>
          <FormSpan>
            <Field label={M.fieldRuleName} required name="name" value={draft.name} onChange={set("name")} maxLength={200} error={errs.name ?? fe.name} autoFocus />
          </FormSpan>
          <RadioGroup label={M.fieldRuleApplyOn} required name="apply_on" value={draft.applyOn} onChange={(v) => set("applyOn")(v === "ORDER" ? "ORDER" : "ITEM")} options={APPLY_OPTIONS} error={fe.apply_on} />
          <RadioGroup
            label={M.fieldDiscountType}
            required
            name="discount_type"
            value={draft.discountType}
            onChange={(v) => {
              setDraft((d) => ({ ...d, discountType: v === "AMOUNT" ? "AMOUNT" : "PERCENT", discountValue: "" }));
              setErrs((e) => ({ ...e, discountValue: undefined }));
            }}
            options={DISCOUNT_OPTIONS}
            error={fe.discount_type}
          />
          {isItem ? (
            <>
              <Field
                as="select"
                label={M.fieldRuleItem}
                required
                name="item"
                value={draft.item}
                onChange={set("item")}
                options={[{ value: "", label: items.status === "loading" ? M.loadingMore : M.fieldRuleItemPlaceholder }, ...itemOptions]}
                error={errs.item ?? fe.item}
              />
              <Field label={M.fieldMinQty} type="number" unit="kg" required name="min_qty" value={draft.minQty} onChange={set("minQty")} error={errs.minQty ?? fe.min_qty} />
            </>
          ) : (
            <Field label={M.fieldMinAmount} type="money" unit={CURRENCY_UNIT} required name="min_amount" value={draft.minAmount} onChange={set("minAmount")} error={errs.minAmount ?? fe.min_amount} />
          )}
          {draft.discountType === "AMOUNT" ? (
            <Field label={M.fieldDiscountValue} type="money" unit={CURRENCY_UNIT} required name="discount_value" value={draft.discountValue} onChange={set("discountValue")} error={errs.discountValue ?? fe.discount_value} />
          ) : (
            <Field label={M.fieldDiscountValue} type="number" unit="%" required name="discount_value" value={draft.discountValue} onChange={set("discountValue")} error={errs.discountValue ?? fe.discount_value} />
          )}
          <Field label={M.fieldRuleFrom} type="date" name="valid_from" value={draft.validFrom} onChange={set("validFrom")} error={errs.validFrom ?? fe.valid_from} />
          <Field label={M.fieldRuleUpto} type="date" name="valid_upto" value={draft.validUpto} onChange={set("validUpto")} error={errs.validUpto ?? fe.valid_upto} />
        </FormGrid>
        <Switch label={M.fieldRuleActive} checked={draft.isActive} onChange={set("isActive")} />
      </FormSection>
    </FormPage>
  );
}
