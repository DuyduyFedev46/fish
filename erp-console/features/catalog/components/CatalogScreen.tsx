"use client";

// Màn Danh mục tối thiểu (A2, 02-stories.md — hồ sơ 2026-09-26-anh-mat-hang): danh sách mặt hàng có
// ảnh thu nhỏ, bộ lọc "Chưa có ảnh" (UC-A5, lọc PHÍA SERVER qua ?has_image=), tải lên/thay ảnh, "Tải
// thêm" khi còn trang kế (DRF phân trang thật — xem `useCatalogList`/`shared/lib/usePagedList`). Trang
// bọc <ViewGuard view="catalog"> (cần catalog.view_item — warehouse_staff cũng có, chỉ không thấy nút ảnh). Phần
// sửa tên, nhóm, hạn dùng, ẩn/hiện vẫn thuộc S38 — CHƯA làm ở màn này (theo phạm vi A2 đã chốt).
//
// QA REJECTED lô 1 (B1, 04-qa-report.md): bản trước đọc `GET /api/catalog/items/` như mảng trần nên
// sập ngay khi nối BE thật (BE trả {count,next,previous,results}). Sửa bằng `useCatalogList` (khung
// phân trang dùng chung với features/orders, xem shared/lib/usePagedList.ts) thay cho useResource.

import { useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { Icon } from "@/shared/ui/Icon";
import { PERM } from "@/shared/lib/nav";
import { SkeletonScreen, SkeletonTable } from "@/shared/ui/Skeleton";
import { ErrorBox } from "@/shared/ui/StateBox";
import { Toast } from "@/shared/ui/Toast";
import { Toolbar } from "@/shared/ui/Toolbar";
import { filterItems } from "../api";
import { CATALOG_MSG } from "../messages";
import type { CatalogItem, CatalogItemImage, ImageFilter, UploadImageResponse } from "../types";
import { useCatalogList } from "../useCatalogList";
import { ImageUploadSheet } from "./ImageUploadSheet";
import { ItemThumb } from "./ItemThumb";
import s from "../catalog.module.css";

function Row({ item, canChangeImage, onUpload }: { item: CatalogItem; canChangeImage: boolean; onUpload: (item: CatalogItem) => void }) {
  return (
    <li className={s.row}>
      <ItemThumb image={item.image} />
      <span className={s.info}>
        <b className={s.name}>{item.name}</b>
        <span className={s.sub}>
          <code className="code">{item.code}</code>
          <span className="muted">{item.group_name}</span>
          {item.item_type === "BUNDLE" && <span className="tag">Combo</span>}
          {!item.is_active && (
            <span className="status mute">
              <span className="dot" aria-hidden="true" />
              Đang ẩn
            </span>
          )}
        </span>
      </span>
      {canChangeImage && (
        <button
          type="button"
          className="btn"
          onClick={() => onUpload(item)}
          aria-label={`${item.image ? "Thay ảnh" : "Tải ảnh"} — ${item.name}`}
        >
          <Icon name={item.image ? "sync_alt" : "add_photo_alternate"} />
          <span className={s.btnLabel} aria-hidden="true">
            {item.image ? "Thay ảnh" : "Tải ảnh"}
          </span>
        </button>
      )}
    </li>
  );
}

const FILTERS: { key: ImageFilter; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "without_image", label: "Chưa có ảnh" },
];

export function CatalogScreen() {
  const { me } = useAuth();
  const [filter, setFilter] = useState<ImageFilter>("all");
  const [q, setQ] = useState("");
  const list = useCatalogList(filter, !!me);
  const [uploadFor, setUploadFor] = useState<CatalogItem | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const canChangeImage = !!me?.permissions.includes(PERM.changeItemImage);
  const forbidden = list.error instanceof ApiError && list.error.status === 403;

  const closeUpload = () => setUploadFor(null);
  const onUploaded = (item: CatalogItem, response: UploadImageResponse) => {
    setUploadFor(null);
    const message = response.warnings.length
      ? `${CATALOG_MSG.uploaded(item.name)} ${response.warnings.map((w) => w.message).join(" ")}`
      : CATALOG_MSG.uploaded(item.name);
    setToast(message);
    // Sửa đúng dòng tại chỗ (giống Đơn & tiền) thay vì tải lại cả trang — nhanh hơn, giữ vị trí cuộn.
    // `image` của danh sách KHÔNG có `uploaded_by` (contract A2 "bỏ uploaded_by") — chỉ lấy phần chung.
    const image: CatalogItemImage = {
      id: response.image.id,
      alt: response.image.alt,
      is_illustration: response.image.is_illustration,
      urls: response.image.urls,
      uploaded_at: response.image.uploaded_at,
    };
    list.patch(item.id, { image });
  };
  const onConflictReload = () => {
    setUploadFor(null);
    void list.reload();
  };

  // Tìm phía máy chỉ trong các trang ĐÃ TẢI (contract A2 chưa có tham số tìm kiếm phía server cho
  // /api/catalog/items/) — bấm "Tải thêm" trước nếu cần tìm mặt hàng chưa hiện.
  const shown = list.rows ? filterItems(list.rows, q) : undefined;
  const searching = !!q.trim();

  return (
    <div className="screen">
      <p className="view-head">
        {canChangeImage
          ? "Mỗi mặt hàng một ảnh. Ảnh cũ vẫn giữ lại khi thay — không mất nếu bấm nhầm."
          : `Danh sách mặt hàng và ảnh đang dùng. ${CATALOG_MSG.noImagePermissionHint}`}
      </p>

      <div className={s.bar}>
        <div className="seg" role="group" aria-label="Lọc theo ảnh">
          {FILTERS.map((f) => (
            <button key={f.key} type="button" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
              {f.label}
            </button>
          ))}
        </div>
        <Toolbar
          query={q}
          onQuery={setQ}
          placeholder="Tìm tên, mã mặt hàng…"
          onRefresh={() => void list.reload()}
          refreshing={list.loading}
        />
      </div>

      {shown === undefined ? (
        list.error && !list.loading ? (
          <ErrorBox icon={forbidden ? "lock" : undefined} message={loadErrorText(list.error)} onRetry={() => void list.reload()} />
        ) : (
          <SkeletonScreen label="Đang tải danh mục…">
            <SkeletonTable rows={6} cols={3} />
          </SkeletonScreen>
        )
      ) : (
        <section className={`sect ${s.list}`} aria-labelledby="cat-h" aria-busy={list.loading}>
          <div className="sect-h">
            <h2 id="cat-h">Mặt hàng</h2>
            <span className="sub num" aria-live="polite">
              {list.loading
                ? "Đang tải…"
                : searching
                  ? `${shown.length} / ${list.rows!.length} khớp`
                  : `${list.rows!.length} / ${list.count} mặt hàng`}
            </span>
          </div>
          {list.error != null && !list.loading && (
            <div className="alert-box err" role="alert">
              <Icon name="sync_problem" />
              <span>
                Không làm mới được, đang hiện danh sách lần tải trước. {loadErrorText(list.error)}
              </span>
            </div>
          )}
          {shown.length ? (
            <>
              <ul className={`${s.rows} ${s.rowsWrap}`}>
                {shown.map((item) => (
                  <Row key={item.id} item={item} canChangeImage={canChangeImage} onUpload={setUploadFor} />
                ))}
              </ul>
              {list.moreError != null && (
                <div className="alert-box err" role="alert">
                  <Icon name="error" />
                  <span>Không tải thêm được. {loadErrorText(list.moreError)}</span>
                </div>
              )}
              {!searching && list.hasMore && (
                <div className={s.more}>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => void list.loadMore()}
                    disabled={list.moreLoading}
                    aria-busy={list.moreLoading || undefined}
                  >
                    {list.moreLoading ? <Icon name="progress_activity" className="spin" /> : <Icon name="expand_more" />}
                    {list.moreLoading ? "Đang tải…" : "Tải thêm"}
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className={`state ${s.rowsWrap}`}>
              <span className="state-ic">
                <Icon name={searching ? "search_off" : filter === "without_image" ? "check_circle" : "inbox"} />
              </span>
              <h3 className="state-title">
                {searching
                  ? "Không khớp tìm kiếm"
                  : filter === "without_image"
                    ? CATALOG_MSG.emptyFilteredTitle
                    : CATALOG_MSG.emptyTitle}
              </h3>
              <p>
                {searching
                  ? `Không có mặt hàng nào (đã tải) khớp “${q.trim()}”.${list.hasMore ? " Bấm “Tải thêm” để tìm rộng hơn." : ""}`
                  : filter === "without_image"
                    ? CATALOG_MSG.emptyFilteredHint
                    : CATALOG_MSG.emptyHint}
              </p>
              {searching ? (
                <button type="button" className="btn" onClick={() => setQ("")}>
                  <Icon name="close" />
                  Xoá tìm kiếm
                </button>
              ) : filter === "without_image" ? (
                <button type="button" className="btn" onClick={() => setFilter("all")}>
                  Xem tất cả mặt hàng
                </button>
              ) : null}
            </div>
          )}
        </section>
      )}

      {uploadFor && (
        <ImageUploadSheet item={uploadFor} onClose={closeUpload} onUploaded={onUploaded} onConflictReload={onConflictReload} />
      )}
      {toast && !uploadFor && <Toast key={toast} message={toast} onClose={() => setToast(null)} />}
    </div>
  );
}
