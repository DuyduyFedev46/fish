"use client";

// Hộp "Đặt giá mới" (ED-30 / F1l): Mặt hàng · Bảng giá · Giá bán (đ) * · Áp dụng từ * · Áp dụng đến. Mở từ trang chi tiết (mặt hàng đã biết,
// chỉ hiện tên) hoặc từ tab Bảng giá (chọn mặt hàng).
// Quyết định #10 của Duy: giá chỉ áp dụng TỪ NGÀY, giá nằm trong đơn đã đặt không đổi. "Áp dụng từ" mặc định NGÀY MAI; ngày trước hôm nay
// bị chặn ngay trên form (BE chỉ từ chối lùi ngày khi đã có đơn trong khoảng đó), kèm gợi ý "từ ngày mai". Giá đã có đơn dùng:
// BE trả PRICE_USED_BY_ORDERS và hộp hiện NGUYÊN VĂN câu của BE ở đầu form, giữ nguyên số đã nhập, nút chính đổi "Thử lại".
// Giá bán là giá BÁN (không phải giá vốn). Không ghi gì vào storage, URL hay log.

import { useId, useMemo, useState } from "react";
import { todayInVietnam } from "@/shared/lib/format";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { Modal } from "@/shared/ui/overlay/Modal";
import { setItemPrice } from "../api";
import { CURRENCY_UNIT, moneyDigits, priceInfo, tomorrowOf, validatePrice, type PriceDraft, type PriceErrors } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import type { CatalogItem, ItemPrice, PriceList } from "../types";
import s from "../catalog.module.css";

type Props = {
  /** Có = đặt giá cho mặt hàng này (không chọn lại). Không có = chọn trong `items`. */
  item?: CatalogItem;
  items?: CatalogItem[];
  priceLists: PriceList[];
  onClose: () => void;
  onSaved: (price: ItemPrice) => void;
};

export function SetPriceModal({ item, items = [], priceLists, onClose, onSaved }: Props) {
  const formId = useId();
  const today = useMemo(() => todayInVietnam(), []);
  const defaultList = priceLists.find((l) => l.is_default) ?? priceLists[0];
  const [draft, setDraft] = useState<PriceDraft>({
    itemId: item ? String(item.id) : "",
    priceListId: defaultList ? String(defaultList.id) : "",
    rate: "",
    validFrom: tomorrowOf(today),
    validUpto: "",
  });
  const [errs, setErrs] = useState<PriceErrors>({});

  const sub = useSubmit(
    async () => {
      const digits = moneyDigits(draft.rate) ?? "0";
      return setItemPrice({
        price_list: Number(draft.priceListId),
        item: Number(draft.itemId),
        rate: `${digits}.00`,
        valid_from: draft.validFrom,
        valid_upto: draft.validUpto || null,
      });
    },
    { onSuccess: onSaved },
  );

  const set = <K extends keyof PriceDraft>(key: K) => (value: PriceDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
    if (errs[key]) setErrs((e) => ({ ...e, [key]: undefined }));
  };

  const submit = () => {
    const found = validatePrice(draft, today);
    setErrs(found);
    if (Object.keys(found).length) return;
    void sub.submit();
  };

  const picked = item ?? items.find((i) => String(i.id) === draft.itemId);
  const hasFieldErrors = Object.keys(sub.fieldErrors).length > 0;
  const currentPrice = picked ? priceInfo(picked) : null;

  return (
    <Modal
      title={M.setPriceTitle}
      onClose={onClose}
      busy={sub.submitting}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            {M.cancel}
          </button>
          <button type="submit" form={formId} className="btn primary" disabled={sub.submitting} aria-busy={sub.submitting || undefined}>
            {sub.submitting ? (
              <>
                <Icon name="progress_activity" className="spin" />
                <span>{M.busy}</span>
              </>
            ) : (
              primaryLabel(M.setPriceSubmit, sub.failed)
            )}
          </button>
        </>
      }
    >
      <form
        id={formId}
        noValidate
        className={s.form}
        onSubmit={(e) => {
          e.preventDefault();
          if (!sub.submitting) submit();
        }}
      >
        {sub.error && !hasFieldErrors && <FormAlert>{sub.error}</FormAlert>}

        {item ? (
          <p className={s.itemLine}>
            <span className={s.itemLineName}>{item.name}</span>
            {currentPrice && <span className={s.itemLineNote}>{M.currentPrice(currentPrice)}</span>}
          </p>
        ) : (
          <>
            <Field
              as="select"
              label={M.fieldPriceItem}
              required
              name="item"
              value={draft.itemId}
              onChange={set("itemId")}
              options={[{ value: "", label: M.linePlaceholder }, ...items.map((i) => ({ value: String(i.id), label: i.name }))]}
              error={errs.itemId ?? sub.fieldErrors.item}
              autoFocus
            />
            {currentPrice && <p className={s.itemLineNote}>{M.currentPrice(currentPrice)}</p>}
          </>
        )}

        <Field
          as="select"
          label={M.fieldPriceList}
          name="price_list"
          value={draft.priceListId}
          onChange={set("priceListId")}
          options={priceLists.map((l) => ({ value: String(l.id), label: l.name }))}
          error={errs.priceListId ?? sub.fieldErrors.price_list}
        />
        <Field
          label={M.fieldRate}
          type="money"
          unit={CURRENCY_UNIT}
          required
          name="rate"
          value={draft.rate}
          onChange={set("rate")}
          error={errs.rate ?? sub.fieldErrors.rate}
          autoFocus={!!item}
        />
        <div className={s.formRow}>
          <Field label={M.fieldValidFrom} type="date" required name="valid_from" value={draft.validFrom} onChange={set("validFrom")} error={errs.validFrom ?? sub.fieldErrors.valid_from} />
          <Field label={M.fieldValidUpto} type="date" name="valid_upto" value={draft.validUpto} onChange={set("validUpto")} error={errs.validUpto ?? sub.fieldErrors.valid_upto} />
        </div>
      </form>
    </Modal>
  );
}
