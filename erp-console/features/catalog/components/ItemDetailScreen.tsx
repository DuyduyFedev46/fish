"use client";

// Trang chi tiết mặt hàng (ED-30 / W2d): /catalog/detail/?id=<pk>. Khung DetailPage: header (tên · chip Đang kinh doanh/Đang ẩn · "Đặt giá mới" · "…"),
// cột trái: "Thông tin mặt hàng" (Tên và Mô tả sửa tại chỗ, chỉ Chủ; Mã, Nhóm, Loại, Hạn dùng chỉ đọc; giá niêm yết CHỈ khi BE trả
// `current_price`) · "Thành phần" (combo) · "Lịch sử giá" (cần catalog.view_itemprice). Cột phải: Trợ lý AI (page ghép qua `renderAi`) rồi Dòng thời gian.
// Quyết định #10: sửa giá = đặt giá mới "từ ngày"; giá nằm trong đơn đã đặt không đổi. Không có sửa hay xoá một dòng giá cũ.
// "Ẩn khỏi Shop" / "Hiện lại trên Shop" nằm trong "…" (chỉ Chủ). BE không cho xoá mặt hàng nên FE không bao giờ gọi DELETE.
// Màn này không có giá vốn.

import { Fragment, useMemo, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ENUMS } from "@/shared/lib/enums";
import { dateOnly, kg, money } from "@/shared/lib/format";
import { ApiError, loadErrorText } from "@/shared/lib/http";
import { homePath } from "@/shared/lib/nav";
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
import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";
import { updateItem } from "../api";
import { priceInfo, saveErrorMessage, shelfLifeText, ITEM_LIMITS } from "../catalogModel";
import { CATALOG_MSG as M } from "../messages";
import { catalogAbility } from "../permissions";
import type { BundleLine, CatalogItem, ItemPrice } from "../types";
import { useItemPriceHistory } from "../useCatalogList";
import { usePriceListOptions } from "../useCatalogOptions";
import { useItemDetail, useItemId, type ItemDetailState } from "../useItemDetail";
import { useItemTimeline } from "../useItemTimeline";
import { ImageUploadModal } from "./ImageUploadModal";
import { ItemThumb } from "./ItemThumb";
import { SetPriceModal } from "./SetPriceModal";
import s from "../catalog.module.css";

/** Khối Trợ lý AI do page truyền vào (màn tính năng không import features/ai). */
export type ItemAiTarget = { id: number };
type RenderAi = (target: ItemAiTarget, onApplied: () => void) => React.ReactNode;

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

export function ItemDetailScreen({ renderAi }: { renderAi?: RenderAi }) {
  const { me } = useAuth();
  const id = useItemId();
  const detail = useItemDetail(id);
  const home = me ? homePath(me) : undefined;

  if (id === undefined) return <DetailSkeleton />;
  if (id === null) return <NotFoundScreen homeHref={home} />;
  if (detail.status === "forbidden") return <NoPermission homeHref={home} />;
  if (detail.status === "notfound") return <NotFoundScreen homeHref={home} />;
  if (detail.status === "error") return <ErrorScreen homeHref={home} onRetry={() => void detail.reload()} />;
  if (detail.status === "loading" || !detail.data) return <DetailSkeleton />;
  return <ItemDetailBody key={id} item={detail.data} detail={detail} renderAi={renderAi} />;
}

function ItemDetailBody({ item, detail, renderAi }: { item: CatalogItem; detail: ItemDetailState; renderAi?: RenderAi }) {
  const { me } = useAuth();
  const toast = useToast();
  const ability = catalogAbility(me?.permissions ?? []);
  const [modal, setModal] = useState<"price" | "image" | null>(null);
  const [version, setVersion] = useState(0);
  const [aiApplied, setAiApplied] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);
  const timeline = useItemTimeline(item.id, version);
  const history = useItemPriceHistory(item.id, ability.viewPrices, version);
  const priceLists = usePriceListOptions(ability.setPrice);

  const afterChange = (message: string) => {
    toast.success(message);
    setVersion((n) => n + 1);
    void detail.reload();
  };

  /** Lưu MỘT trường tại chỗ: chỉ gửi khi đổi; lỗi ném lên cho ô hiện dưới ô, giữ nguyên giá trị đang gõ. */
  const saveField = (field: "name" | "description") => async (next: string) => {
    const value = next.trim();
    if (value === item[field]) return;
    try {
      await updateItem(item.id, { [field]: value });
    } catch (err) {
      throw new Error(saveErrorMessage(err));
    }
    afterChange(M.saved);
  };

  const toggleShop = async () => {
    if (toggling) return;
    setToggling(true);
    setActionError(null);
    try {
      await updateItem(item.id, { is_active: !item.is_active });
      afterChange(item.is_active ? M.hidden : M.shown);
    } catch (err) {
      setActionError(saveErrorMessage(err));
    } finally {
      setToggling(false);
    }
  };

  const more: MoreMenuItem[] = [
    ability.changeItem
      ? { key: "shop", label: item.is_active ? M.hideFromShop : M.showOnShop, danger: item.is_active, onSelect: () => void toggleShop() }
      : { key: "shop", label: item.is_active ? M.hideFromShop : M.showOnShop, blockedReason: M.ownerOnly },
    {
      key: "log",
      label: M.viewLog,
      onSelect: () => {
        const el = document.getElementById("item-timeline");
        el?.scrollIntoView({ block: "start" });
        el?.focus();
      },
    },
  ];

  const lineCols: Column<BundleLine>[] = useMemo(
    () => [
      { key: "name", header: M.colComponent, render: (l) => l.component_name },
      { key: "code", header: M.colCode, mono: true, render: (l) => l.component_code, hideBelow: 720 },
      { key: "qty", header: M.colQtyPerBundle, num: true, render: (l) => kg(l.qty_per_bundle) },
    ],
    [],
  );
  const priceCols: Column<ItemPrice>[] = useMemo(
    () => [
      { key: "rate", header: M.colRate, num: true, render: (p) => money(p.rate) },
      { key: "from", header: M.colValidFrom, num: true, render: (p) => dateOnly(p.valid_from) },
      { key: "upto", header: M.colValidUpto, num: true, render: (p) => (p.valid_upto ? dateOnly(p.valid_upto) : <span className="muted">{M.none}</span>) },
    ],
    [],
  );

  const showPrice = item.current_price !== undefined;
  const current = priceInfo(item);
  const priceReady = priceLists.status === "ok";

  return (
    <DetailPage
      id="item-detail"
      header={
        <DetailHeader
          back={{ href: "/catalog/", label: M.backToList }}
          title={item.name || `#${item.id}`}
          status={<Chip table={ENUMS.itemActive} value={item.is_active} />}
          primary={
            ability.setPrice ? (
              <button type="button" className="btn primary" onClick={() => setModal("price")} disabled={!priceReady} aria-busy={!priceReady || undefined}>
                {M.setPrice}
              </button>
            ) : null
          }
          more={more}
        />
      }
      banner={
        actionError ? (
          <div className="alert-box err" role="alert">
            <Icon name="error" />
            <span>{actionError}</span>
          </div>
        ) : detail.error != null && !detail.reloading ? (
          <div className="alert-box err" role="alert">
            <Icon name="sync_problem" />
            <span>{loadErrorText(detail.error)}</span>
            <button type="button" className="btn" onClick={() => void detail.reload()}>
              {M.retry}
            </button>
          </div>
        ) : undefined
      }
      aiSlot={
        renderAi ? (
          <Fragment key={aiApplied}>
            {renderAi({ id: item.id }, () => {
              setAiApplied((n) => n + 1);
              setVersion((n) => n + 1);
              void detail.reload();
            })}
          </Fragment>
        ) : null
      }
      timeline={
        <div id="item-timeline" tabIndex={-1}>
          {timeline.status === "error" && (
            <p className={s.railNote} role="alert">
              <span>{M.timelineFailed}</span>
              <button type="button" className="btn" onClick={timeline.retry}>
                {M.retry}
              </button>
            </p>
          )}
          {timeline.status !== "error" && <Timeline entries={timeline.entries} truncated={timeline.truncated} title={M.timelineTitle} />}
        </div>
      }
    >
      <InfoGrid title={M.sectionInfo}>
        {ability.changeItem ? (
          <InfoField
            kind="editable"
            label={M.fieldName}
            value={item.name}
            required
            requiredMessage={M.nameRequired}
            validate={(v) => (v.trim().length > ITEM_LIMITS.name ? M.nameTooLong : null)}
            onSave={saveField("name")}
          />
        ) : (
          <InfoField label={M.fieldName} value={item.name} />
        )}
        <InfoField kind="locked" label={M.fieldCode} mono reason={M.lockedReason} value={item.code} />
        <InfoField label={M.fieldGroup} value={item.group_name} />
        <InfoField label={M.fieldType} value={ENUMS.itemType[item.item_type].label} />
        <InfoField label={M.fieldShop} value={item.is_active ? M.shopVisible : M.shopHidden} />
        <InfoField label={M.fieldShelfLife} num value={shelfLifeText(item.shelf_life_in_days)} />
        <InfoField label={M.fieldUnit} value={item.item_type === "BUNDLE" ? "Combo" : item.stock_uom} />
        {showPrice && <InfoField label={M.fieldPrice} num value={current} />}
        {showPrice && <InfoField label={M.fieldPriceFrom} num value={item.current_price ? dateOnly(item.current_price.valid_from) : null} />}
        {ability.changeItem ? (
          <InfoField
            kind="editable"
            label={M.fieldDescription}
            value={item.description}
            validate={(v) => (v.length > ITEM_LIMITS.description ? M.descriptionTooLong : null)}
            onSave={saveField("description")}
          />
        ) : (
          <InfoField label={M.fieldDescription} value={item.description} />
        )}
        <InfoField
          label={M.fieldImage}
          value={
            <span className={s.imageField}>
              <ItemThumb image={item.image} size={56} />
              {ability.changeImage ? (
                <button type="button" className="btn" onClick={() => setModal("image")}>
                  <Icon name="photo_camera" />
                  <span>{item.image ? M.replaceImage : M.uploadImage}</span>
                </button>
              ) : (
                !item.image && <span className="muted">{M.noImage}</span>
              )}
            </span>
          }
        />
      </InfoGrid>

      {item.item_type === "BUNDLE" && (
        <Section title={M.sectionBundle} count={M.bundleCount(item.bundle_lines.length)} aria-label={M.sectionBundle} flush>
          <DataTable
            caption={M.bundleCaption}
            columns={lineCols}
            rows={item.bundle_lines}
            rowKey={(l) => l.id}
            rowHref={(l) => `/catalog/detail/?id=${l.component}`}
            noun="thành phần"
            empty={{ icon: "inventory_2", title: M.bundleEmpty, hint: M.bundleEmptyHint }}
            canViewCost={false}
          />
        </Section>
      )}

      {ability.viewPrices && !(history.error instanceof ApiError && history.error.status === 403) && <PriceHistory history={history} columns={priceCols} />}

      {modal === "price" && priceReady && (
        <SetPriceModal
          item={item}
          priceLists={priceLists.rows}
          onClose={() => setModal(null)}
          onSaved={() => {
            setModal(null);
            afterChange(M.priceSaved);
          }}
        />
      )}
      {modal === "image" && (
        <ImageUploadModal
          item={item}
          onClose={() => setModal(null)}
          onUploaded={(it) => {
            setModal(null);
            afterChange(M.uploaded(it.name));
          }}
          onConflictReload={() => {
            setModal(null);
            void detail.reload();
          }}
        />
      )}
    </DetailPage>
  );
}

function PriceHistory({ history, columns }: { history: ReturnType<typeof useItemPriceHistory>; columns: Column<ItemPrice>[] }) {
  return (
    <Section title={M.sectionPriceHistory} count={history.rows !== undefined ? M.priceCount(history.count) : undefined} aria-label={M.sectionPriceHistory} flush>
      <DataTable
        caption={M.priceHistoryCaption}
        columns={columns}
        rows={history.rows ?? null}
        rowKey={(p) => p.id}
        loading={history.loading && history.rows === undefined}
        error={history.rows === undefined && history.error != null ? `${M.priceHistoryFailed} ${loadErrorText(history.error)}` : null}
        onRetry={() => void history.reload()}
        noun="mức giá"
        empty={{ icon: "sell", title: M.priceHistoryEmpty, hint: M.priceHistoryEmptyHint }}
        canViewCost={false}
      />
      {(history.hasMore || history.moreError != null) && (
        <div className={s.sectionFoot}>
          {history.moreError != null && (
            <span className="field-err" role="alert">
              {M.loadMoreFailed} {loadErrorText(history.moreError)}
            </span>
          )}
          {history.hasMore && (
            <button type="button" className="btn" onClick={() => void history.loadMore()} disabled={history.moreLoading} aria-busy={history.moreLoading || undefined}>
              {history.moreLoading ? M.loadingMore : M.priceMore}
            </button>
          )}
        </div>
      )}
    </Section>
  );
}
