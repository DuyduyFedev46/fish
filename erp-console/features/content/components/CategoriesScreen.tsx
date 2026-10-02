"use client";

// Quản lý chuyên mục (ED-36 / W3d, F3h): bảng STT · Tên · Mô tả · Đường dẫn · Bài đăng · Trạng thái · Thao tác.
// Thêm / Sửa: hộp CategoryFormModal. Ngừng dùng: hộp xác nhận; còn bài đang đăng thì BE chặn (BR-ND-02) và hộp nói rõ
// "Còn N bài…" kèm link xem các bài đó. Kích hoạt lại không cần hỏi. Quyền theo quyền thật add_category / change_category.

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { useResource } from "@/shared/lib/useResource";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { DataTable, type Column } from "@/shared/ui/list/DataTable";
import { ListPage } from "@/shared/ui/list/ListPage";
import { ConfirmModal } from "@/shared/ui/overlay/ConfirmModal";
import { useToast } from "@/shared/ui/overlay/Toast";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { fetchCategories, updateCategory } from "../api";
import { CONTENT_PERM, blockedDetailsOf, errorText, hasPerm } from "../contentModel";
import { CONTENT_MSG as M } from "../messages";
import type { ContentCategory, DeactivateCategoryBlockedDetails } from "../types";
import { CategoryFormModal } from "./CategoryFormModal";
import s from "../content.module.css";

type Modal = { kind: "add" } | { kind: "edit"; category: ContentCategory } | { kind: "deactivate"; category: ContentCategory } | null;

export function CategoriesScreen() {
  const { me } = useAuth();
  const toast = useToast();
  const canView = hasPerm(me, CONTENT_PERM.view);
  const canAdd = hasPerm(me, CONTENT_PERM.addCategory);
  const canChange = hasPerm(me, CONTENT_PERM.changeCategory);
  const res = useResource(me && canView ? "content-categories" : null, () => fetchCategories(), 0);
  const [modal, setModal] = useState<Modal>(null);
  const [blocked, setBlocked] = useState<DeactivateCategoryBlockedDetails | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  if (me && !canView) return <NoPermission />;
  if (res.error instanceof ApiError && res.error.status === 403) return <NoPermission />;

  const rows = res.data;
  const nextOrder = rows && rows.length > 0 ? Math.max(...rows.map((c) => c.order)) + 1 : 1;
  const close = () => {
    setModal(null);
    setBlocked(null);
  };

  const activate = async (c: ContentCategory) => {
    setBusyId(c.id);
    try {
      await updateCategory(c.id, { is_active: true });
      toast.success(M.catActivated);
      await res.reload();
    } catch (err) {
      toast.error(errorText(err, M.genericFail));
    } finally {
      setBusyId(null);
    }
  };

  const columns: Column<ContentCategory>[] = [
    { key: "index", header: M.catColIndex, num: true, width: "64px", hideBelow: 720, render: (r) => r.order },
    { key: "name", header: M.catColName, render: (r) => <b>{r.name}</b> },
    { key: "desc", header: M.catColDesc, hideBelow: 980, render: (r) => r.description || <span className="muted">—</span> },
    { key: "path", header: M.catColPath, mono: true, hideBelow: 800, render: (r) => r.slug },
    { key: "count", header: M.catColCount, num: true, render: (r) => r.published_count },
    { key: "status", header: M.catColStatus, render: (r) => <Chip table={ENUMS.categoryActive} value={r.is_active} /> },
    {
      key: "actions",
      header: M.catColActions,
      width: "220px",
      render: (r) =>
        canChange ? (
          <span className={s.rowActions}>
            <button type="button" className="btn" onClick={() => setModal({ kind: "edit", category: r })}>
              {M.catEditRow}
            </button>
            {r.is_active ? (
              <button type="button" className="btn" onClick={() => setModal({ kind: "deactivate", category: r })}>
                {M.catDeactivate}
              </button>
            ) : (
              <button type="button" className="btn" onClick={() => void activate(r)} disabled={busyId === r.id} aria-busy={busyId === r.id || undefined}>
                {M.catActivate}
              </button>
            )}
          </span>
        ) : (
          <span className="muted">—</span>
        ),
    },
  ];

  return (
    <ListPage
      actions={
        <>
          <Link href="/content/" className="btn">
            <Icon name="arrow_back" />
            <span>{M.catBack}</span>
          </Link>
          {canAdd && (
            <button type="button" className="btn primary" onClick={() => setModal({ kind: "add" })}>
              <Icon name="add" />
              <span>{M.catAdd}</span>
            </button>
          )}
        </>
      }
      asOf={res.asOf}
      onRetry={() => void res.reload()}
    >
      <DataTable
        canViewCost={false}
        caption={M.catListTitle}
        columns={columns}
        rows={rows ?? null}
        rowKey={(r) => r.id}
        loading={res.loading && rows === undefined}
        error={rows === undefined && res.error != null ? loadErrorText(res.error) : null}
        onRetry={() => void res.reload()}
        noun={M.catNoun}
        dense
        empty={{
          icon: "category",
          title: M.catEmptyTitle,
          hint: M.catEmptyHint,
          action: canAdd ? (
            <button type="button" className="btn primary" onClick={() => setModal({ kind: "add" })}>
              {M.catAdd}
            </button>
          ) : undefined,
        }}
      />
      {(modal?.kind === "add" || modal?.kind === "edit") && (
        <CategoryFormModal
          category={modal.kind === "edit" ? modal.category : undefined}
          nextOrder={nextOrder}
          onClose={close}
          onSaved={() => {
            toast.success(modal.kind === "edit" ? M.catUpdated : M.catCreated);
            close();
            void res.reload();
          }}
        />
      )}
      {modal?.kind === "deactivate" && (
        <ConfirmModal
          title={M.catDeactivateTitle}
          confirmLabel={M.catDeactivate}
          busyLabel={M.catDeactivateBusy}
          backLabel={M.catCancel}
          danger
          noun={M.catNoun}
          disabled={blocked !== null}
          run={() => updateCategory(modal.category.id, { is_active: false })}
          onError={(err) => setBlocked(blockedDetailsOf(err))}
          errorText={(err) => {
            const b = blockedDetailsOf(err);
            return b ? M.catBlocked(b.total) : errorText(err, M.genericFail);
          }}
          onReload={() => {
            close();
            void res.reload();
          }}
          onDone={() => {
            toast.success(M.catDeactivated);
            close();
            void res.reload();
          }}
          onClose={close}
        >
          <p className={s.confirmBody}>
            {M.catDeactivateBody}
          </p>
          {blocked && (
            <div className={s.blockedList}>
              <ul>
                {blocked.entries.map((e) => (
                  <li key={e.id}>{e.title || "Chưa đặt tiêu đề"}</li>
                ))}
              </ul>
              <Link href={`/content/?category=${modal.category.id}`} className="inline-link">
                {M.catSeeEntries(blocked.total)}
              </Link>
            </div>
          )}
        </ConfirmModal>
      )}
    </ListPage>
  );
}
