// Dải 4 số liệu (UI3): phẳng, không hộp viền riêng — chia cột bằng đường mảnh; nhãn nhỏ xám, số lớn tabular-nums,
// phụ chú nhẹ. Chỉ tô màu khi cần chú ý: có đơn sắp hết giữ chỗ (phụ chú hổ phách), có lô cận hạn (số hổ phách).
// "Giá trị tồn kho" chỉ hiện số khi can_cost (bất biến #1); thiếu quyền → "—" + "cần quyền xem giá vốn".
// Class .tile[data-kpi] / .val / .foot giữ nguyên (e2e S7, S8, S48 bám vào).
import { Icon } from "@/shared/ui/Icon";
import { Figure } from "@/shared/ui/Figure";
import { vnd } from "@/shared/lib/format";
import type { OverviewData } from "../types";

type Props = {
  kpis: OverviewData["kpis"];
  canCost: boolean;
  /** Số ngày cận hạn BE trả (near_expiry_days); null → không ghi số ngày (BE cũ chưa có key). */
  nearDays: number | null;
};

export function KpiTiles({ kpis, canCost, nearDays }: Props) {
  const soon = kpis.booked_soon > 0;
  const near = kpis.near_expiry > 0;
  return (
    <div className="kpi-band">
      <h2 className="sr-only">Số liệu hôm nay</h2>
      <dl className="kpis">
        <div className="tile" data-kpi="revenue">
          <dt className="lab">Doanh thu hôm nay</dt>
          <dd className="val">
            <Figure text={vnd(kpis.revenue_today)} />
          </dd>
          <dd className="foot">hoá đơn xuất trong ngày</dd>
        </div>
        <div className="tile" data-kpi="pending">
          <dt className="lab">Đơn chờ xử lý</dt>
          <dd className="val">{kpis.pending_orders}</dd>
          <dd className={`foot${soon ? " attn" : ""}`}>
            {soon ? (
              <>
                <Icon name="timer" />
                {kpis.booked_soon} sắp hết giữ chỗ
              </>
            ) : (
              "đang giữ chỗ / xử lý"
            )}
          </dd>
        </div>
        <div className={`tile${near ? " attn" : ""}`} data-kpi="near">
          <dt className="lab">Lô cận hạn</dt>
          <dd className="val">{kpis.near_expiry}</dd>
          <dd className="foot">{nearDays !== null ? `trong ${nearDays} ngày tới` : "lô sắp hết hạn dùng"}</dd>
        </div>
        <div className="tile" data-kpi="inventory">
          <dt className="lab">Giá trị tồn kho</dt>
          <dd className={`val${canCost ? "" : " nil"}`}>
            {canCost && kpis.inventory_value !== undefined ? <Figure text={vnd(kpis.inventory_value)} /> : "—"}
          </dd>
          <dd className="foot">{canCost ? "theo giá vốn lô" : "cần quyền xem giá vốn"}</dd>
        </div>
      </dl>
    </div>
  );
}
