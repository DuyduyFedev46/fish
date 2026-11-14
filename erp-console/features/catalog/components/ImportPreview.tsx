"use client";

// M3 — Xem trước thay đổi khi nhập file Excel mặt hàng (FISH-66 S5, S6; 02a §3.2).
// Thứ tự bắt buộc: Dải số tổng -> Cảnh báo cột chỉ đọc (nếu có) -> Phần 1 Đổi giá -> Phần 2 Ẩn/hiện -> Phần 3 Món mới -> Phần 4 Món sửa.
// Tuyệt đối không có cột giá vốn, lãi lỗ hay tồn kho (bất biến 1).

import { useEffect, useState } from "react";
import { dateOnly, timeHM, vnd } from "@/shared/lib/format";
import { Chip } from "@/shared/ui/Chip";
import { Icon } from "@/shared/ui/Icon";
import { InfoField } from "@/shared/ui/detail/InfoField";
import { InfoStrip } from "@/shared/ui/detail/InfoStrip";
import { Section } from "@/shared/ui/detail/Section";
import {
  formatPriceDiffAmount,
  formatPriceDiffPercent,
  formatPriceHeaderSummary,
  groupReadonlyWarnings,
  shopStateLabel,
  sortPriceRows,
  splitPreviewSections,
} from "../itemFilesModel";
import type { ImportPreviewResponse, ShopState } from "../itemFilesTypes";
import { CATALOG_MSG as CM, ITEM_IMPORT_MSG as M } from "../messages";
import s from "../catalog.module.css";

const PAGE_SIZE = 50;

type Props = {
  preview: ImportPreviewResponse;
  headingRef?: React.RefObject<HTMLHeadingElement>;
};

function shopChipTone(state: ShopState): "good" | "mute" | "info" | "warn" {
  switch (state) {
    case "selling":
      return "good";
    case "will_show":
      return "info";
    case "will_hide":
      return "warn";
    case "hidden":
      return "mute";
  }
}

export function ImportPreview({ preview, headingRef }: Props) {
  const { summary, rows, warnings, expires_at } = preview;
  const { priceRows, visibilityRows, newItemRows, updatedFieldRows } = splitPreviewSections(rows);

  const [priceSort, setPriceSort] = useState<"percent" | "row">("percent");
  const [shownPrices, setShownPrices] = useState(PAGE_SIZE);
  const [shownVis, setShownVis] = useState(PAGE_SIZE);
  const [shownNew, setShownNew] = useState(PAGE_SIZE);
  const [shownUpdated, setShownUpdated] = useState(PAGE_SIZE);
  const [expandedCells, setExpandedCells] = useState<Record<string, boolean>>({});
  const [expiringSoon, setExpiringSoon] = useState(false);

  useEffect(() => {
    if (!expires_at) {
      setExpiringSoon(false);
      return;
    }
    function check() {
      const diffMs = new Date(expires_at as string).getTime() - Date.now();
      setExpiringSoon(diffMs <= 2 * 60 * 1000);
    }
    check();
    const timer = window.setInterval(check, 15000);
    return () => window.clearInterval(timer);
  }, [expires_at]);

  const sortedPrices = sortPriceRows(priceRows, priceSort);
  const visiblePrices = sortedPrices.slice(0, shownPrices);
  const visibleVis = visibilityRows.slice(0, shownVis);
  const visibleNew = newItemRows.slice(0, shownNew);
  const visibleUpdated = updatedFieldRows.slice(0, shownUpdated);
  const groupedWarnings = groupReadonlyWarnings(warnings);
  const willShowNewCount = newItemRows.filter((r) => r.shop_state === "will_show").length;

  function scrollToSection(id: string) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function toggleExpand(key: string) {
    setExpandedCells((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  return (
    <div className={s.importStack} data-testid="import-preview">
      <h2 ref={headingRef} tabIndex={-1} className="sr-only">
        {M.previewHeading}
      </h2>

      {/* 1. Dải số tổng */}
      <InfoStrip label={M.stripLabel}>
        <InfoField
          label={M.stripPrices}
          value={
            priceRows.length > 0 ? (
              <button type="button" className={s.linkBtn} onClick={() => scrollToSection("import-sec-prices")}>
                {summary.price_changed}
              </button>
            ) : (
              summary.price_changed
            )
          }
          num
        />
        <InfoField
          label={M.stripNewItems}
          value={
            newItemRows.length > 0 ? (
              <button type="button" className={s.linkBtn} onClick={() => scrollToSection("import-sec-new")}>
                {summary.created}
              </button>
            ) : (
              summary.created
            )
          }
          num
        />
        <InfoField
          label={M.stripUpdatedItems}
          value={
            updatedFieldRows.length > 0 ? (
              <button type="button" className={s.linkBtn} onClick={() => scrollToSection("import-sec-updated")}>
                {summary.updated}
              </button>
            ) : (
              summary.updated
            )
          }
          num
        />
        <InfoField
          label={M.stripVisibility}
          value={
            visibilityRows.length > 0 ? (
              <button type="button" className={s.linkBtn} onClick={() => scrollToSection("import-sec-visibility")}>
                {summary.visibility_changed}
              </button>
            ) : (
              summary.visibility_changed
            )
          }
          num
        />
        <InfoField label={M.stripUnchanged} value={summary.unchanged} num />
        <InfoField label={M.stripWillShow} value={summary.will_show_on_shop} num />
        {expires_at && (
          <InfoField
            label={M.stripExpires}
            value={
              <span className={expiringSoon ? s.expiresWarn : undefined}>
                {timeHM(expires_at)}
              </span>
            }
            num
          />
        )}
      </InfoStrip>

      {/* 2. Cảnh báo sửa cột chỉ để xem (W1) */}
      {groupedWarnings.map((w) => (
        <div key={w.column} className="alert-box warn" role="status" data-testid="import-readonly-warning">
          <Icon name="warning" />
          <div>{w.text}</div>
        </div>
      ))}

      {/* 3. Phần 1 — Đổi giá */}
      {priceRows.length > 0 && (
        <div id="import-sec-prices">
          <Section
            title={M.sectionPrices(priceRows.length)}
            action={<span className="muted">{formatPriceHeaderSummary(priceRows)}</span>}
          >
            <div className={s.tableWrap}>
              <table className={s.importTable} data-testid="import-prices-table">
                <caption className="sr-only">Giá đổi trong file</caption>
                <thead>
                  <tr>
                    <th
                      scope="col"
                      className={s.numCol}
                      aria-sort={priceSort === "row" ? "ascending" : "none"}
                    >
                      <button
                        type="button"
                        className={s.sortBtn}
                        onClick={() => setPriceSort("row")}
                      >
                        <span>{M.colRow}</span>
                        {priceSort === "row" && <span aria-hidden="true">▲</span>}
                      </button>
                    </th>
                    <th scope="col">{M.colCode}</th>
                    <th scope="col">{M.colItem}</th>
                    <th scope="col">{M.colShop}</th>
                    <th scope="col" className={s.numCol}>{M.colOldPrice}</th>
                    <th scope="col" className={s.numCol}>{M.colNewPrice}</th>
                    <th scope="col" className={s.numCol}>{M.colDiff}</th>
                    <th
                      scope="col"
                      className={s.numCol}
                      aria-sort={priceSort === "percent" ? "descending" : "none"}
                    >
                      <button
                        type="button"
                        className={s.sortBtn}
                        onClick={() => setPriceSort("percent")}
                      >
                        <span>{M.colDiffPct}</span>
                        {priceSort === "percent" && <span aria-hidden="true">▼</span>}
                      </button>
                    </th>
                    <th scope="col" className={s.numCol}>{M.colValidFrom}</th>
                    <th scope="col">{M.colFlags}</th>
                  </tr>
                </thead>
                <tbody>
                  {visiblePrices.map((r) => {
                    const p = r.price!;
                    const hasZeroFlag = p.flags.includes("check_zeros");
                    return (
                      <tr key={`price-${r.row}-${r.code}`}>
                        <td className={`${s.numCol} ${hasZeroFlag ? s.critRowFirstCell : ""}`}>
                          {r.row}
                        </td>
                        <td className="mono">{r.code}</td>
                        <td>
                          {r.name}
                          {r.action === "create" ? ` ${M.newItemSuffix}` : ""}
                        </td>
                        <td>
                          <Chip entry={{ tone: shopChipTone(r.shop_state), label: shopStateLabel(r.shop_state) }} />
                        </td>
                        <td className={s.numCol}>{p.old != null ? vnd(p.old) : CM.none}</td>
                        <td className={s.newPriceCell}>{vnd(p.new)}</td>
                        <td className={s.numCol}>{formatPriceDiffAmount(p.change_amount)}</td>
                        <td className={s.numCol}>{formatPriceDiffPercent(p.change_percent)}</td>
                        <td className={s.numCol}>{dateOnly(p.valid_from)}</td>
                        <td>
                          <div className={s.chipGroup}>
                            {p.flags.includes("check_zeros") && (
                              <Chip entry={{ tone: "crit", label: M.flagCheckZeros }} />
                            )}
                            {p.flags.includes("large_change") && (
                              <Chip entry={{ tone: "warn", label: M.flagLargeChange }} />
                            )}
                            {p.flags.includes("backdated") && (
                              <Chip entry={{ tone: "warn", label: M.flagBackdated }} />
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {priceRows.length > visiblePrices.length && (
              <div className={s.sectionFoot}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShownPrices((n) => n + PAGE_SIZE)}
                >
                  {M.showMore(Math.min(PAGE_SIZE, priceRows.length - visiblePrices.length))}
                </button>
              </div>
            )}
          </Section>
        </div>
      )}

      {/* 4. Phần 2 — Ẩn/hiện trên Shop */}
      {visibilityRows.length > 0 && (
        <div id="import-sec-visibility">
          <Section title={M.sectionVisibility(visibilityRows.length)}>
            <div className={s.tableWrap}>
              <table className={s.importTable} data-testid="import-visibility-table">
                <caption className="sr-only">Mặt hàng đổi trạng thái ẩn hiện</caption>
                <thead>
                  <tr>
                    <th scope="col" className={s.numCol}>{M.colRow}</th>
                    <th scope="col">{M.colCode}</th>
                    <th scope="col">{M.colItem}</th>
                    <th scope="col">{M.colBefore}</th>
                    <th scope="col">{M.colAfter}</th>
                    <th scope="col">{M.colShop}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleVis.map((v) => (
                    <tr key={`vis-${v.row}-${v.code}`}>
                      <td className={s.numCol}>{v.row}</td>
                      <td className="mono">{v.code}</td>
                      <td>{v.name}</td>
                      <td>{v.oldText}</td>
                      <td>{v.newText}</td>
                      <td>
                        {v.shopState === "will_show" ? (
                          <Chip entry={{ tone: "info", label: M.shopWillShowChip }} />
                        ) : v.shopState === "will_hide" ? (
                          <Chip entry={{ tone: "warn", label: M.shopWillHideChip }} />
                        ) : (
                          <Chip entry={{ tone: shopChipTone(v.shopState), label: shopStateLabel(v.shopState) }} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {visibilityRows.length > visibleVis.length && (
              <div className={s.sectionFoot}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShownVis((n) => n + PAGE_SIZE)}
                >
                  {M.showMore(Math.min(PAGE_SIZE, visibilityRows.length - visibleVis.length))}
                </button>
              </div>
            )}
          </Section>
        </div>
      )}

      {/* 5. Phần 3 — Món mới */}
      {newItemRows.length > 0 && (
        <div id="import-sec-new">
          <Section
            title={M.sectionNewItems(newItemRows.length)}
            action={willShowNewCount > 0 ? <span className="muted">{M.newItemsShopNote(willShowNewCount)}</span> : undefined}
          >
            <div className={s.tableWrap}>
              <table className={s.importTable} data-testid="import-new-items-table">
                <caption className="sr-only">Mặt hàng mới trong file</caption>
                <thead>
                  <tr>
                    <th scope="col" className={s.numCol}>{M.colRow}</th>
                    <th scope="col">{M.colCode}</th>
                    <th scope="col">{M.colName}</th>
                    <th scope="col">{M.colGroup}</th>
                    <th scope="col">{M.colActive}</th>
                    <th scope="col" className={s.numCol}>{M.colNewPrice}</th>
                    <th scope="col">{M.colShop}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleNew.map((r) => (
                    <tr key={`new-${r.row}-${r.code}`}>
                      <td className={s.numCol}>{r.row}</td>
                      <td className="mono">{r.code}</td>
                      <td>{r.name}</td>
                      <td>{r.item_group || CM.none}</td>
                      <td>{r.is_active_after ? CM.yes : CM.no}</td>
                      <td className={s.numCol}>{r.price ? vnd(r.price.new) : CM.none}</td>
                      <td>
                        {r.shop_state === "will_show" ? (
                          <Chip entry={{ tone: "info", label: M.shopWillShowChip }} />
                        ) : (
                          <Chip entry={{ tone: "mute", label: M.shopHidden }} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {newItemRows.length > visibleNew.length && (
              <div className={s.sectionFoot}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShownNew((n) => n + PAGE_SIZE)}
                >
                  {M.showMore(Math.min(PAGE_SIZE, newItemRows.length - visibleNew.length))}
                </button>
              </div>
            )}
          </Section>
        </div>
      )}

      {/* 6. Phần 4 — Món sửa */}
      {updatedFieldRows.length > 0 && (
        <div id="import-sec-updated">
          <Section title={M.sectionUpdatedItems(summary.updated)}>
            <div className={s.tableWrap}>
              <table className={s.importTable} data-testid="import-updated-items-table">
                <caption className="sr-only">Các trường thông tin mặt hàng thay đổi</caption>
                <thead>
                  <tr>
                    <th scope="col" className={s.numCol}>{M.colRow}</th>
                    <th scope="col">{M.colCode}</th>
                    <th scope="col">{M.colItem}</th>
                    <th scope="col">{M.colField}</th>
                    <th scope="col">{M.colBefore}</th>
                    <th scope="col">{M.colAfter}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUpdated.map((u) => {
                    const isLong = (u.old?.length || 0) > 80 || (u.new?.length || 0) > 80;
                    const expanded = Boolean(expandedCells[u.key]);
                    return (
                      <tr key={u.key}>
                        <td className={s.numCol}>{u.row}</td>
                        <td className="mono">{u.code}</td>
                        <td>{u.name}</td>
                        <td>{u.label}</td>
                        <td>
                          <span className={!expanded && isLong ? s.clampText : s.fullText}>
                            {u.old || CM.none}
                          </span>
                        </td>
                        <td>
                          <span className={!expanded && isLong ? s.clampText : s.fullText}>
                            {u.new || CM.none}
                          </span>
                          {isLong && (
                            <div>
                              <button
                                type="button"
                                className={s.linkBtn}
                                aria-expanded={expanded}
                                onClick={() => toggleExpand(u.key)}
                              >
                                {expanded ? M.collapseText : M.expandText}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {updatedFieldRows.length > visibleUpdated.length && (
              <div className={s.sectionFoot}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => setShownUpdated((n) => n + PAGE_SIZE)}
                >
                  {M.showMore(Math.min(PAGE_SIZE, updatedFieldRows.length - visibleUpdated.length))}
                </button>
              </div>
            )}
          </Section>
        </div>
      )}
    </div>
  );
}
