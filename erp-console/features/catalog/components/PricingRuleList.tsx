"use client";

// Tab "Ưu đãi" (ED-31 / W5o): bảng Ưu đãi · Áp dụng cho · Điều kiện · Mức giảm · Từ ngày · Đến ngày · Trạng thái · Thao tác.
// Chỉ có khi người xem có catalog.view_pricingrule (Chủ, Quản lý). Chủ có thêm nút "Tạo ưu đãi" và nút Bật/Tắt ở mỗi dòng
// (catalog.change_pricingrule). Ưu đãi giảm giá lúc đặt đơn; đơn đã đặt không đổi giá khi bật hay tắt ưu đãi.
// Bộ lọc trạng thái, loại chạy PHÍA SERVER; ô tìm tên lọc phía máy trong phần đã tải.

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { matches } from "@/shared/lib/search";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { setPricingRuleActive } from "../api";
import { asActiveFilter, ruleCondition, ruleDiscountText, saveErrorMessage } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { PricingRule, PricingRuleListParams, RuleApplyOn } from "../types";
import { usePricingRules } from "../useCatalogList";
import s from "../catalog.module.css";

const ACTIVE_OPTIONS = [
  { value: "", label: M.filterRuleActiveAll },
  { value: "1", label: M.optRuleOn },
  { value: "0", label: M.optRuleOff },
];
const APPLY_OPTIONS = [
  { value: "", label: M.filterApplyOnAll },
  { value: "ITEM", label: ENUMS.pricingRuleApplyOn.ITEM.label },
  { value: "ORDER", label: ENUMS.pricingRuleApplyOn.ORDER.label },
];

function asApplyOn(v: string): "" | RuleApplyOn {
  return v === "ITEM" || v === "ORDER" ? v : "";
}

export function PricingRuleList({ tabs }: { tabs: React.ReactNode }) {
  const { me } = useAuth();
  const toast = useToast();
  const ability = catalogAbility(me?.permissions ?? []);
  const [q, setQ] = useState("");
  const [params, setParams] = useState<PricingRuleListParams>({ active: "", applyOn: "" });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const list = usePricingRules(params, !!me && ability.viewRules);
  const rows = useMemo(() => (list.rows ? list.rows.filter((r) => matches(q, r.name, r.item_name ?? "")) : undefined), [list.rows, q]);

  if (!ability.viewRules || (list.error instanceof ApiError && list.error.status === 403)) return <NoPermission />;

  const toggle = async (rule: PricingRule) => {
    if (busyId !== null) return;
    setBusyId(rule.id);
    setToggleError(null);
    try {
      const next = await setPricingRuleActive(rule.id, !rule.is_active);
      list.patch(rule.id, { is_active: next.is_active });
      toast.success(next.is_active ? M.ruleTurnedOn : M.ruleTurnedOff);
    } catch (err) {
      setToggleError(`${M.ruleToggleFailed} ${saveErrorMessage(err)}`);
    } finally {
      setBusyId(null);
    }
  };

  const columns: Column<PricingRule>[] = [
    { key: "name", header: M.colRuleName, width: "200px", render: (r) => <span className={s.wrapCell}>{r.name}</span> },
    { key: "apply", header: M.colRuleApplyOn, render: (r) => <Chip table={ENUMS.pricingRuleApplyOn} value={r.apply_on} /> },
    { key: "cond", header: M.colRuleCondition, width: "220px", render: (r) => <span className={s.wrapCell}>{ruleCondition(r) ?? <span className="muted">{M.none}</span>}</span>, hideBelow: 720 },
    { key: "discount", header: M.colRuleDiscount, num: true, render: (r) => ruleDiscountText(r) },
    { key: "from", header: M.colRuleFrom, num: true, render: (r) => (r.valid_from ? dateOnly(r.valid_from) : <span className="muted">{M.none}</span>), hideBelow: 980 },
    { key: "upto", header: M.colRuleUpto, num: true, render: (r) => (r.valid_upto ? dateOnly(r.valid_upto) : <span className="muted">{M.none}</span>), hideBelow: 980 },
    { key: "status", header: M.colRuleStatus, render: (r) => <Chip table={ENUMS.pricingRuleActive} value={r.is_active} /> },
    ...(ability.changeRule
      ? ([
          {
            key: "action",
            header: M.colRuleAction,
            render: (r) => (
              <button
                type="button"
                className={`btn ${s.cellAction}`}
                onClick={() => void toggle(r)}
                disabled={busyId !== null}
                aria-busy={busyId === r.id || undefined}
                aria-label={`${r.is_active ? M.ruleTurnOff : M.ruleTurnOn} ${r.name}`}
              >
                {busyId === r.id ? <Icon name="progress_activity" className="spin" /> : r.is_active ? M.ruleTurnOff : M.ruleTurnOn}
              </button>
            ),
          },
        ] satisfies Column<PricingRule>[])
      : []),
  ];

  const filtered = !!(params.active || params.applyOn);
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <ListPage
      id="catalog-panel"
      tabs={tabs}
      actions={
        ability.addRule ? (
          <Link href="/catalog/rules/new/" className="btn primary">
            <Icon name="add" />
            <span>{M.addRule}</span>
          </Link>
        ) : undefined
      }
      asOf={list.asOf}
      onRetry={() => void list.reload()}
      filters={
        <FilterBar
          query={q}
          onQuery={setQ}
          placeholder={M.ruleSearchPlaceholder}
          searchLabel={M.ruleSearchLabel}
          selects={[
            { key: "active", label: M.filterRuleActive, value: params.active, options: ACTIVE_OPTIONS, onChange: (v) => setParams((p) => ({ ...p, active: asActiveFilter(v) })) },
            { key: "apply", label: M.filterApplyOn, value: params.applyOn, options: APPLY_OPTIONS, onChange: (v) => setParams((p) => ({ ...p, applyOn: asApplyOn(v) })) },
          ]}
          summary={rows ? M.ruleShown(rows.length, list.count) : undefined}
        />
      }
      banner={
        toggleError ? (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{toggleError}</span>
          </div>
        ) : refreshFailed ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(list.error)}</span>
          </div>
        ) : undefined
      }
      footer={
        <>
          {list.moreError != null && (
            <span className="field-err" role="alert">
              {M.loadMoreFailed} {loadErrorText(list.moreError)}
            </span>
          )}
          {list.hasMore && (
            <button type="button" className="btn" onClick={() => void list.loadMore()} disabled={list.moreLoading} aria-busy={list.moreLoading || undefined}>
              {list.moreLoading ? M.loadingMore : M.loadMore}
            </button>
          )}
        </>
      }
    >
      <DataTable
        caption={M.rulesCaption}
        columns={columns}
        rows={rows ?? null}
        rowKey={(r) => r.id}
        loading={list.loading && list.rows === undefined}
        error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
        onRetry={() => void list.reload()}
        query={q.trim()}
        onClearQuery={() => setQ("")}
        noun={M.rulesNoun}
        empty={{
          icon: filtered ? "filter_list_off" : "percent",
          title: filtered ? M.emptyFilteredTitle : M.rulesEmptyTitle,
          hint: filtered ? M.emptyFilteredHint : ability.addRule ? M.rulesEmptyHint : M.rulesEmptyReadOnlyHint,
          action:
            ability.addRule && !filtered ? (
              <Link href="/catalog/rules/new/" className="btn primary">
                {M.addRule}
              </Link>
            ) : undefined,
        }}
        canViewCost={false}
        dense
      />
    </ListPage>
  );
}
