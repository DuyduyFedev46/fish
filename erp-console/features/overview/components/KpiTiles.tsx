// Dải 5 số liệu của Tổng quan (ED-08-AC1 / D1): Doanh thu dd/mm/yyyy · Đơn chờ xử lý · Sắp hết giữ chỗ · Lô cận hạn (N ngày tới)
// · Giá trị tồn kho theo giá vốn (icon khoá). Ô giá trị tồn chỉ có trong DOM khi người xem có quyền giá vốn (bất biến 1, ED-08-AC4):
// thiếu quyền thì KHÔNG vẽ ô đó và cũng không đọc `inventory_value`, dù response có lỡ trả.
// Class .tile[data-kpi] / .val / .foot toàn cục giữ nguyên (e2e bám vào); lưới 5 ô chỉnh ở overview.module.css.
import { vnd } from "@/shared/lib/format";
import { Figure } from "@/shared/ui/Figure";
import { Icon } from "@/shared/ui/Icon";
import type { OverviewData } from "../types";
import { nearExpiryLabel, revenueLabel } from "../view";
import s from "../overview.module.css";

type Props = {
  kpis: OverviewData["kpis"];
  canCost: boolean;
  /** Số ngày cận hạn BE trả (near_expiry_days); null → bỏ số ngày (BE cũ chưa có key). */
  nearDays: number | null;
  /** Mốc dữ liệu của BE, để ghi đúng ngày doanh thu. */
  asOf?: string;
};

export function KpiTiles({ kpis, canCost, nearDays, asOf }: Props) {
  const soon = kpis.booked_soon > 0;
  const near = kpis.near_expiry > 0;
  const showCost = canCost && kpis.inventory_value !== undefined;
  return (
    <div className={`kpi-band ${s.band}${canCost ? "" : ` ${s.four}`}`}>
      <h2 className="sr-only">Số liệu hôm nay</h2>
      <dl className="kpis">
        <div className="tile" data-kpi="revenue">
          <dt className="lab">{revenueLabel(asOf)}</dt>
          <dd className="val">
            <Figure text={vnd(kpis.revenue_today)} />
          </dd>
        </div>
        <div className="tile" data-kpi="pending">
          <dt className="lab">Đơn chờ xử lý</dt>
          <dd className="val">{kpis.pending_orders}</dd>
        </div>
        <div className={`tile${soon ? " attn" : ""}`} data-kpi="soon">
          <dt className="lab">
            Sắp hết giữ chỗ
            <Icon name="timer" className={s.labIc} />
          </dt>
          <dd className="val">{kpis.booked_soon}</dd>
        </div>
        <div className={`tile${near ? " attn" : ""}`} data-kpi="near">
          <dt className="lab">{nearExpiryLabel(nearDays)}</dt>
          <dd className="val">{kpis.near_expiry}</dd>
        </div>
        {canCost && (
          <div className="tile" data-kpi="inventory">
            <dt className="lab">
              Giá trị tồn kho theo giá vốn
              <Icon name="lock" className={s.labIc} />
            </dt>
            <dd className={`val${showCost ? "" : " nil"}`}>{showCost ? <Figure text={vnd(kpis.inventory_value)} /> : "—"}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}
