"use client";

// Trang "Thêm mặt hàng" / "Thêm combo" (ED-30 / F1k, F1m): /catalog/new/ và /catalog/new/?type=BUNDLE. Cần catalog.add_item (Chủ).
// Mặt hàng thường: Mã hàng · Tên · Nhóm hàng · Hạn dùng mặc định · Quản lý theo lô · Có hạn dùng · Đang bán · Mô tả.
// Combo: thêm công thức (các mặt hàng thường và số kg cho MỘT combo). BE tạo mặt hàng trước (POST items) rồi từng dòng (POST bundle-lines):
// nếu dòng nào lỗi thì mặt hàng ĐÃ có, form khoá phần đã lưu, báo rõ và nút chính thành "Thử lại" chỉ gửi nốt các dòng còn thiếu
// (không tạo lại mặt hàng). Mã trùng: BE trả 400 {code:[…]} và form hiện ngay dưới ô Mã hàng. Không có giá vốn, không có giá bán ở form này:
// giá đặt riêng bằng "Đặt giá mới" sau khi tạo.

import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { FormPage } from "@/shared/ui/form/FormPage";
import { useSubmit } from "@/shared/ui/form/useSubmit";
import { Icon } from "@/shared/ui/Icon";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { createBundleLine, createItem } from "../api";
import {
  emptyItemDraft,
  hasItemErrors,
  ITEM_LIMITS,
  itemInputOf,
  lineInputOf,
  parseItemTypeParam,
  saveErrorMessage,
  validateItem,
  type ItemDraft,
  type ItemErrors,
  type LineDraft,
} from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import { useGroupOptions, useItemOptions } from "../useCatalogOptions";
import s from "../catalog.module.css";

export function ItemForm() {
  const { me } = useAuth();
  const params = useSearchParams();
  const type = parseItemTypeParam(`?${params.toString()}`);
  const ability = catalogAbility(me?.permissions ?? []);
  if (!me) return null;
  if (!ability.addItem) return <NoPermission />;
  return <ItemFormBody key={type} type={type} />;
}

function ItemFormBody({ type }: { type: "SIMPLE" | "BUNDLE" }) {
  const router = useRouter();
  const toast = useToast();
  const isBundle = type === "BUNDLE";
  const [draft, setDraft] = useState<ItemDraft>(() => emptyItemDraft(type));
  const [errs, setErrs] = useState<ItemErrors>({ line: {} });
  const [createdId, setCreatedId] = useState<number | null>(null);
  const [savedLines, setSavedLines] = useState<number[]>([]);
  const createdRef = useRef<number | null>(null);
  const savedRef = useRef<Set<number>>(new Set());
  const nextKey = useRef(2);
  const groups = useGroupOptions(true);
  const items = useItemOptions(isBundle);

  const components = items.rows.filter((i) => i.item_type === "SIMPLE" && i.is_active);
  const locked = createdId !== null;

  const sub = useSubmit(
    async () => {
      if (createdRef.current === null) {
        const created = await createItem(itemInputOf(draft));
        createdRef.current = created.id;
        setCreatedId(created.id);
      }
      const id = createdRef.current;
      if (isBundle) {
        for (const line of draft.lines) {
          if (savedRef.current.has(line.key)) continue;
          try {
            await createBundleLine(lineInputOf(id, line));
          } catch (err) {
            throw new Error(`${M.linesPartial} ${saveErrorMessage(err)}`);
          }
          savedRef.current.add(line.key);
          setSavedLines([...savedRef.current]);
        }
      }
      return id;
    },
    {
      onSuccess: (id) => {
        toast.success(M.itemCreated);
        router.push(`/catalog/detail/?id=${id}`);
      },
    },
  );

  const set = <K extends keyof ItemDraft>(key: K) => (value: ItemDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setErrs((e) => (key in e ? { ...e, [key]: undefined } : e));
  };
  const setLine = (key: number, change: Partial<LineDraft>) => {
    setDraft((d) => ({ ...d, lines: d.lines.map((l) => (l.key === key ? { ...l, ...change } : l)) }));
    setErrs((e) => {
      const line = { ...e.line };
      delete line[key];
      return { ...e, lines: undefined, line };
    });
  };
  const addLine = () => {
    setDraft((d) => ({ ...d, lines: [...d.lines, { key: nextKey.current++, component: "", qty: "" }] }));
    setErrs((e) => ({ ...e, lines: undefined }));
  };
  const removeLine = (key: number) => setDraft((d) => ({ ...d, lines: d.lines.filter((l) => l.key !== key) }));

  const submit = () => {
    const found = validateItem(draft);
    setErrs(found);
    if (hasItemErrors(found)) return;
    void sub.submit();
  };

  const optionsFailed = groups.status === "error" || (isBundle && items.status === "error");
  const loadingOptions = groups.status === "loading" || (isBundle && items.status === "loading");
  const lineError = (key: number) => errs.line[key];

  const alert = optionsFailed ? (
    <div className="alert-box err" role="alert">
      <Icon name="sync_problem" />
      <span>{M.optionsFailed}</span>
      <button
        type="button"
        className="btn"
        onClick={() => {
          groups.reload();
          items.reload();
        }}
      >
        {M.retry}
      </button>
    </div>
  ) : sub.error ? (
    <FormAlert>{sub.error}</FormAlert>
  ) : undefined;

  return (
    <FormPage
      title={isBundle ? M.bundleFormTitle : M.itemFormTitle}
      back={{ href: "/catalog/", label: M.backToList }}
      alert={alert}
      onSubmit={submit}
      primaryText={isBundle ? M.bundleSubmit : M.itemSubmit}
      submitting={sub.submitting}
      failed={sub.failed}
      primaryDisabled={optionsFailed || loadingOptions}
      secondary={{ label: M.cancel, onClick: () => router.push("/catalog/") }}
    >
      <div className={s.formBody}>
        <div className={s.formGroup}>
          <h3 className={s.formHead}>{M.itemSectionInfo}</h3>
          <div className={s.formRow}>
            <Field label={M.fieldItemCode} required name="code" value={draft.code} onChange={set("code")} maxLength={ITEM_LIMITS.code} error={errs.code ?? sub.fieldErrors.code} disabled={locked} autoFocus />
            <Field label={M.fieldItemName} required name="name" value={draft.name} onChange={set("name")} maxLength={ITEM_LIMITS.name} error={errs.name ?? sub.fieldErrors.name} disabled={locked} />
          </div>
          <div className={s.formRow}>
            <Field
              as="select"
              label={M.fieldItemGroup}
              required
              name="item_group"
              value={draft.itemGroup}
              onChange={set("itemGroup")}
              options={[{ value: "", label: groups.status === "loading" ? M.loadingMore : M.groupPlaceholder }, ...groups.rows.map((g) => ({ value: String(g.id), label: g.name }))]}
              error={errs.itemGroup ?? sub.fieldErrors.item_group}
              disabled={locked}
            />
            <Field label={M.fieldItemShelfLife} type="number" unit="ngày" required name="shelf_life_in_days" value={draft.shelfLife} onChange={set("shelfLife")} error={errs.shelfLife ?? sub.fieldErrors.shelf_life_in_days} disabled={locked} />
          </div>
          <Field as="textarea" label={M.fieldItemDescription} name="description" value={draft.description} onChange={set("description")} rows={3} maxLength={ITEM_LIMITS.description} counter error={errs.description ?? sub.fieldErrors.description} disabled={locked} />
          {!isBundle && (
            <>
              <label className="check-row">
                <input type="checkbox" checked={draft.hasBatch} onChange={(e) => set("hasBatch")(e.target.checked)} disabled={locked} />
                <span>
                  <b>{M.fieldItemBatch}</b>
                </span>
              </label>
              <label className="check-row">
                <input type="checkbox" checked={draft.hasExpiry} onChange={(e) => set("hasExpiry")(e.target.checked)} disabled={locked} />
                <span>
                  <b>{M.fieldItemExpiry}</b>
                </span>
              </label>
            </>
          )}
          <label className="check-row">
            <input type="checkbox" checked={draft.isActive} onChange={(e) => set("isActive")(e.target.checked)} disabled={locked} />
            <span>
              <b>{M.fieldItemActive}</b>
            </span>
          </label>
        </div>

        {isBundle && (
          <div className={s.formGroup}>
            <h3 className={s.formHead}>{M.sectionBundleLines}</h3>
            {errs.lines && (
              <p className="field-err" role="alert">
                <Icon name="error" />
                {errs.lines}
              </p>
            )}
            <ul className={s.lines}>
              {draft.lines.map((line, idx) => {
                const saved = savedLines.includes(line.key);
                const le = lineError(line.key);
                return (
                  <li key={line.key} className={s.line}>
                    <Field
                      as="select"
                      label={M.fieldLineComponent}
                      required
                      name={`component-${idx}`}
                      value={line.component}
                      onChange={(v) => setLine(line.key, { component: v })}
                      options={[{ value: "", label: items.status === "loading" ? M.loadingMore : M.linePlaceholder }, ...components.map((i) => ({ value: String(i.id), label: i.name }))]}
                      error={le?.component}
                      disabled={saved}
                    />
                    <Field label={M.fieldLineQty} type="number" unit="kg" required name={`qty-${idx}`} value={line.qty} onChange={(v) => setLine(line.key, { qty: v })} error={le?.qty} disabled={saved} />
                    {!saved && draft.lines.length > 1 && (
                      <button type="button" className={`btn ${s.lineRemove}`} onClick={() => removeLine(line.key)} aria-label={`${M.removeLine} ${idx + 1}`}>
                        <Icon name="close" />
                        <span className="sr-only">{M.removeLine}</span>
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
            <div>
              <button type="button" className="btn" onClick={addLine} disabled={sub.submitting}>
                <Icon name="add" />
                <span>{M.addLine}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </FormPage>
  );
}
