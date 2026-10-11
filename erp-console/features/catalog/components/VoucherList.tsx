"use client";

// Màn "Mã giảm giá" (SHOP-3b-02, /vouchers/): bảng Mã · Tên · Mức giảm · Đơn tối thiểu · Thời gian · Lượt dùng · Trạng thái · Thao tác.
// Chỉ người có catalog.manage_voucher (Chủ, hoặc người Chủ uỷ). Bộ lọc trạng thái chạy PHÍA SERVER, ô tìm lọc phía máy trong phần đã tải.
// Mỗi dòng: Sửa (trang riêng), Tắt (hộp chọn lý do) hoặc Bật lại, Lượt dùng (hộp danh sách đơn đã giữ/dùng mã). Giờ hiển thị GMT+7.
// Đơn đang giữ lượt vẫn giữ giá đã giảm khi tắt mã (BR-DM-19). Không xoá mã (chứng từ, bất biến 3).

import Link from "next/link";
import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { matches } from "@/shared/lib/search";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { FilterBar } from "@/shared/ui/list/FilterBar";
import { ListPage } from "@/shared/ui/list/ListPage";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { enableVoucher } from "../api";
import { saveErrorMessage } from "../catalogModel";
import { VOUCHER_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { Voucher, VoucherListParams, VoucherStatus } from "../types";
import { useVouchers } from "../useCatalogList";
import { voucherDiscountText } from "../voucherModel";
import { VoucherDisableDialog } from "./VoucherDisableDialog";
import { VoucherRedemptions } from "./VoucherRedemptions";
import { dateTime, vnd } from "@/shared/lib/format";
import s from "../catalog.module.css";

const STATUS_OPTIONS = [{ value: "", label: M.filterStatusAll }, ...(["running", "scheduled", "paused", "expired", "used_up"] as const).map((value) => ({ value, label: ENUMS.voucherStatus[value].label }))];

function asStatus(v: string): "" | VoucherStatus {
  return v === "running" || v === "scheduled" || v === "paused" || v === "expired" || v === "used_up" ? v : "";
}

export function VoucherList() {
  const { me } = useAuth();
  const toast = useToast();
  const ability = catalogAbility(me?.permissions ?? []);
  const [q, setQ] = useState("");
  const [params, setParams] = useState<VoucherListParams>({ status: "" });
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);
  const [disabling, setDisabling] = useState<Voucher | null>(null);
  const [viewing, setViewing] = useState<Voucher | null>(null);
  const list = useVouchers(params, !!me && ability.manageVoucher);
  const rows = useMemo(() => (list.rows ? list.rows.filter((v) => matches(q, v.code, v.name)) : undefined), [list.rows, q]);

  if (!me) return null;
  if (!ability.manageVoucher || (list.error instanceof ApiError && list.error.status === 403)) return <NoPermission />;

  const enable = async (v: Voucher) => {
    if (busyId !== null) return;
    setBusyId(v.id);
    setToggleError(null);
    try {
      await enableVoucher(v.id);
      toast.success(M.enabledToast(v.code));
      await list.reload();
    } catch (err) {
      setToggleError(`${M.toggleFailed} ${saveErrorMessage(err)}`);
    } finally {
      setBusyId(null);
    }
  };

  const columns: Column<Voucher>[] = [
    {
      key: "code",
      header: M.colCode,
      width: "140px",
      render: (v) => (
        <span className={s.wrapCell}>
          <span className="mono">{v.code}</span>
          <span className={`muted ${s.voucherSub}`}>{v.name}</span>
          {/* Hẹp (< 800): cột Trạng thái ẩn, chip chuyển xuống đây để người xem điện thoại vẫn thấy trạng thái. */}
          <span className={s.statusInline}>
            <Chip table={ENUMS.voucherStatus} value={v.status} />
          </span>
        </span>
      ),
    },
    { key: "discount", header: M.colDiscount, width: "140px", render: (v) => <span className={s.wrapCell}>{voucherDiscountText(v)}</span>, hideBelow: 800 },
    { key: "min", header: M.colMinOrder, num: true, width: "110px", render: (v) => (Number(v.min_order_amount) > 0 ? vnd(v.min_order_amount) : <span className="muted">{M.none}</span>), hideBelow: 980 },
    {
      key: "period",
      header: M.colPeriod,
      tabular: true,
      width: "140px",
      render: (v) => (
        <span className={s.wrapCell}>
          {dateTime(v.starts_at)}
          <span className={`muted ${s.voucherSub}`}>{M.periodUpto(dateTime(v.ends_at))}</span>
        </span>
      ),
      hideBelow: 980,
    },
    { key: "uses", header: M.colUses, tabular: true, width: "90px", render: (v) => <span className={s.wrapCell}>{M.usesCell(v.used_count, v.held_count, v.total_uses)}</span>, hideBelow: 800 },
    {
      key: "status",
      header: M.colStatus,
      width: "110px",
      hideBelow: 800,
      render: (v) => (
        <span className={s.wrapCell}>
          <Chip table={ENUMS.voucherStatus} value={v.status} />
          {v.status === "paused" && v.disabled_reason ? <span className={`muted ${s.voucherSub}`}>{ENUMS.voucherDisableReason[v.disabled_reason]?.label ?? v.disabled_reason}</span> : null}
        </span>
      ),
    },
    {
      key: "action",
      header: M.colAction,
      hideBelow: 800,
      render: (v) => (
        <span className={`${s.voucherActions} ${s.voucherActionsRow}`}>
          <Link href={`/vouchers/edit/?id=${v.id}`} className={`btn ${s.cellAction}`} aria-label={M.rowLabel(M.actionEdit, v.code)}>
            {M.actionEdit}
          </Link>
          {v.is_active && (v.status === "running" || v.status === "scheduled") ? (
            <button type="button" className={`btn ${s.cellAction}`} onClick={() => setDisabling(v)} disabled={busyId !== null} aria-label={M.rowLabel(M.actionDisable, v.code)}>
              {M.actionDisable}
            </button>
          ) : !v.is_active ? (
            <button type="button" className={`btn ${s.cellAction}`} onClick={() => void enable(v)} disabled={busyId !== null} aria-busy={busyId === v.id || undefined} aria-label={M.rowLabel(M.actionEnable, v.code)}>
              {busyId === v.id ? <Icon name="progress_activity" className="spin" /> : M.actionEnable}
            </button>
          ) : null}
          <button type="button" className={`btn ${s.cellAction}`} onClick={() => setViewing(v)} aria-label={M.rowLabel(M.actionUses, v.code)}>
            {M.actionUses}
          </button>
        </span>
      ),
    },
  ];

  const filtered = !!params.status;
  const refreshFailed = list.rows !== undefined && list.error != null && !list.loading;

  return (
    <>
      <ListPage
        asOf={list.asOf}
        onRetry={() => void list.reload()}
        actions={
          <Link href="/vouchers/new/" className="btn primary">
            <Icon name="add" />
            <span>{M.addVoucher}</span>
          </Link>
        }
        filters={
          <FilterBar
            query={q}
            onQuery={setQ}
            placeholder={M.searchPlaceholder}
            searchLabel={M.searchLabel}
            selects={[{ key: "status", label: M.filterStatus, value: params.status, options: STATUS_OPTIONS, onChange: (v) => setParams({ status: asStatus(v) }) }]}
            summary={rows ? M.shown(rows.length, list.count) : undefined}
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
          caption={M.listCaption}
          title={M.headTitle}
          countText={rows ? M.headCount(list.count, rows.filter((v) => v.status === "running").length) : undefined}
          columns={columns}
          rows={rows ?? null}
          rowKey={(v) => v.id}
          rowHref={(v) => `/vouchers/edit/?id=${v.id}`}
          loading={list.loading && list.rows === undefined}
          error={list.rows === undefined && list.error != null ? loadErrorText(list.error) : null}
          onRetry={() => void list.reload()}
          query={q.trim()}
          onClearQuery={() => setQ("")}
          noun={M.listNoun}
          empty={{
            icon: filtered ? "filter_list_off" : "price_check",
            title: filtered ? M.emptyFilteredTitle : M.emptyTitle,
            hint: filtered ? M.emptyFilteredHint : M.emptyHint,
            action: !filtered ? (
              <Link href="/vouchers/new/" className="btn primary">
                {M.addVoucher}
              </Link>
            ) : undefined,
          }}
          canViewCost={false}
          dense
        />
      </ListPage>
      {disabling && (
        <VoucherDisableDialog
          voucher={disabling}
          onClose={() => setDisabling(null)}
          onDone={(v) => {
            setDisabling(null);
            toast.success(M.disabledToast(v.code));
            void list.reload();
          }}
        />
      )}
      {viewing && <VoucherRedemptions voucher={viewing} onClose={() => setViewing(null)} />}
    </>
  );
}
