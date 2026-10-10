"use client";

// Trang chi tiết khách hàng (ED-14 / W5b): /customers/detail/?id=<pk>. Khung DetailPage: header (tên · "Sửa thông tin" · "…"),
// KHÔNG có thanh trạng thái (khách không có vòng đời) và KHÔNG có khối Trợ lý AI (`aiSlot` để trống; dữ liệu cá nhân không đưa cho AI).
// Cột trái: Liên hệ (Tên, Số điện thoại, Địa chỉ, Ghi chú sửa tại chỗ) · Mua hàng (4 số tự tính, khoá) · bảng Đơn hàng · bảng Phiếu hoàn tiền.
// Cột phải: Dòng thời gian (guidance `customer`). URL chỉ có id; không ghi tên/SĐT/địa chỉ vào storage, log hay tiêu đề tab.

import { useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateTime, vnd } from "@/shared/lib/format";
import { loadErrorText } from "@/shared/lib/http";
import { PERM, canView, homePath } from "@/shared/lib/nav";
import { Chip } from "@/shared/ui/Chip";
import { DetailHeader } from "@/shared/ui/detail/DetailHeader";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoGrid } from "@/shared/ui/detail/InfoGrid";
import { Section } from "@/shared/ui/detail/Section";
import type { MoreMenuItem } from "@/shared/ui/detail/MoreMenu";
import { Timeline } from "@/shared/ui/detail/Timeline";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { useToast } from "@/shared/ui/overlay/Toast";
import { PersonalText } from "@/shared/ui/PersonalText";
import { ScopeLostInApp } from "@/features/auth/components/AppStates";
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { updateCustomer } from "../api";
import { normalizePhone, saveErrorMessage, validateField } from "../customersModel";
import { CUSTOMERS_MSG as M } from "../messages";
import type { CustomerDetail, CustomerEditableField, CustomerOrderRow, CustomerRefundRow } from "../types";
import { useCustomerDetail, useCustomerId, type CustomerDetailState } from "../useCustomerDetail";
import { useCustomerTimeline } from "../useCustomerTimeline";
import { EditCustomerModal } from "./EditCustomerModal";
import s from "../customers.module.css";

const PERM_CHANGE_CUSTOMER = "sales.change_customer";

export function DetailSkeleton() {
  return (
    <div className={s.detailSkel} role="status" aria-busy="true">
      <span className="sr-only">{`Đang tải ${M.detailNoun}…`}</span>
      <div aria-hidden="true">
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-m" />
        <span className="sk sk-l" />
        <span className="sk sk-s" />
      </div>
    </div>
  );
}

export function CustomerDetailScreen() {
  const { me } = useAuth();
  const id = useCustomerId();
  const detail = useCustomerDetail(id);
  const home = me ? homePath(me) : undefined;

  if (id === undefined) return <DetailSkeleton />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "scope_lost") return <ScopeLostInApp listHref="/customers/" />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <CustomerDetailBody customer={detail.data} detail={detail} />;
}

function CustomerDetailBody({ customer: c, detail }: { customer: CustomerDetail; detail: CustomerDetailState }) {
  const { me } = useAuth();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [version, setVersion] = useState(0);
  const timeline = useCustomerTimeline(c.id, version);

  const canEdit = !!me?.permissions.includes(PERM_CHANGE_CUSTOMER);
  const canOpenOrders = !!me?.permissions.includes(PERM.viewSalesOrder);
  const canOpenRefunds = canView(me, "refunds");

  const afterSave = () => {
    toast.success(M.saved);
    setVersion((n) => n + 1);
    void detail.reload();
  };

  /** Lưu MỘT trường tại chỗ: chỉ gửi khi giá trị đổi; lỗi ném lên cho ô hiện dưới ô, giữ nguyên giá trị đang gõ. */
  const saveField = (field: CustomerEditableField) => async (next: string) => {
    const value = field === "phone" ? normalizePhone(next) : next.trim();
    if (value === (field === "phone" ? normalizePhone(c.phone ?? "") : (c[field] ?? ""))) return;
    try {
      await updateCustomer(c.id, { [field]: value });
    } catch (err) {
      throw new Error(saveErrorMessage(err));
    }
    afterSave();
  };
  const validate = (field: CustomerEditableField) => (next: string) => validateField(field, next);

  function copyPhone() {
    const done = () => toast.success(M.copyDone);
    const fail = () => toast.warn(M.copyFailed);
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(c.phone).then(done, fail);
    else fail();
  }

  const more: MoreMenuItem[] = c.phone ? [{ key: "copy_phone", label: M.copyPhone, onSelect: copyPhone }] : [];

  const orderCols: Column<CustomerOrderRow>[] = useMemo(
    () => [
      { key: "code", header: M.colCode, mono: true, render: (o) => o.code },
      { key: "status", header: M.colStatus, render: (o) => <Chip table={ENUMS.salesOrderStatus} value={o.status} /> },
      { key: "total", header: M.colTotal, num: true, render: (o) => vnd(o.total_amount) },
      { key: "at", header: M.colPlacedAt, num: true, render: (o) => dateTime(o.created_at) },
    ],
    [],
  );
  const refundCols: Column<CustomerRefundRow>[] = useMemo(
    () => [
      { key: "order", header: M.colOrder, mono: true, render: (r) => r.order_code },
      { key: "status", header: M.colStatus, render: (r) => <Chip table={ENUMS.refundStatus} value={r.status} /> },
      { key: "amount", header: M.colRefundAmount, num: true, render: (r) => vnd(r.amount) },
      { key: "at", header: M.colCreatedAt, num: true, render: (r) => dateTime(r.created_at) },
    ],
    [],
  );

  const ordersHint = c.order_count > c.orders.length ? M.ordersNewest(c.orders.length, c.order_count) : M.ordersCount(c.orders.length);
  const refundsHint = c.refunds.length >= 50 ? M.refundsNewest(c.refunds.length) : M.refundsCount(c.refunds.length);
  const display = (v: string) => (v ? <PersonalText value={v} /> : undefined);

  const editable = (field: CustomerEditableField, label: string, value: string) =>
    canEdit ? (
      <InfoField kind="editable" label={label} value={value} display={display(value)} onSave={saveField(field)} required={field === "name" || field === "phone"} type={field === "phone" ? "tel" : undefined} num={field === "phone"} validate={validate(field)} />
    ) : (
      <InfoField label={label} value={value ? <PersonalText value={value} /> : null} />
    );

  return (
    <DetailPage
      id="customer-detail"
      header={
        <DetailHeader
          back={{ href: "/customers/", label: M.backToList }}
          title={c.name || `#${c.id}`}
          primary={
            canEdit ? (
              <button type="button" className="btn primary" onClick={() => setEditing(true)}>
                {M.editInfo}
              </button>
            ) : null
          }
          more={more}
        />
      }
      banner={
        detail.error != null && !detail.reloading ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(detail.error)}</span>
            <button type="button" className="btn" onClick={() => void detail.reload()}>
              {M.retry}
            </button>
          </div>
        ) : undefined
      }
      timeline={
        <>
          {timeline.status === "error" && (
            <p className={s.railNote} role="alert">
              <span>{M.timelineFailed}</span>
              <button type="button" className="btn" onClick={timeline.retry}>
                {M.retry}
              </button>
            </p>
          )}
          {timeline.status !== "error" && <Timeline entries={timeline.entries} truncated={timeline.truncated} title={M.timelineTitle} />}
        </>
      }
    >
      <InfoGrid title={M.sectionContact}>
        {editable("name", M.fieldName, c.name ?? "")}
        {editable("phone", M.fieldPhone, c.phone ?? "")}
        {editable("default_address", M.fieldAddress, c.default_address ?? "")}
        {editable("note", M.fieldNote, c.note ?? "")}
      </InfoGrid>

      <InfoGrid title={M.sectionPurchase}>
        <InfoField kind="locked" label={M.fieldSince} num reason={M.derivedReason} value={dateTime(c.created_at)} />
        <InfoField kind="locked" label={M.fieldOrders} num reason={M.derivedReason} value={String(c.order_count)} />
        <InfoField kind="locked" label={M.fieldSpent} num reason={M.derivedReason} value={vnd(c.total_spent)} />
        <InfoField kind="locked" label={M.fieldCancelled} num reason={M.derivedReason} value={String(c.cancelled_count)} />
      </InfoGrid>

      <Section title={M.ordersTitle} count={ordersHint} aria-label={M.ordersTitle} flush>
        <DataTable
          caption={M.ordersCaption}
          columns={orderCols}
          rows={c.orders}
          rowKey={(o) => o.id}
          rowHref={canOpenOrders ? (o) => `/orders/detail/?id=${o.id}` : undefined}
          noun={M.detailNoun}
          empty={{ icon: "inbox", title: M.ordersEmpty, hint: M.ordersEmptyHint }}
          canViewCost={false}
        />
      </Section>

      <Section title={M.refundsTitle} count={refundsHint} aria-label={M.refundsTitle} flush>
        <DataTable
          caption={M.refundsCaption}
          columns={refundCols}
          rows={c.refunds}
          rowKey={(r) => r.id}
          rowHref={canOpenRefunds ? (r) => `/orders/refunds/detail/?id=${r.id}` : undefined}
          noun={M.detailNoun}
          empty={{ icon: "currency_exchange", title: M.refundsEmpty, hint: M.refundsEmptyHint }}
          canViewCost={false}
        />
      </Section>

      {editing && (
        <EditCustomerModal
          customer={c}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            afterSave();
          }}
        />
      )}
    </DetailPage>
  );
}
