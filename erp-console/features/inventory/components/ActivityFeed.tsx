"use client";

// Tab "Hoạt động" của cột phải (S8): 8 dòng sổ kho mới nhất, như bản HTML cũ.
// Chỉ người xem được Kho & lô (inventory.view_batch) và có reports.view_dashboard mới tải; người khác thấy câu báo, KHÔNG gọi API.
// RightRail chỉ mount tab này khi người dùng mở nó → không phát request thừa ở các màn khác.
// Dùng chung cache với 3 màn S8: đang ở Tổng quan thì mở tab không gọi thêm request.
// UI5 (theo DESIGN.md): nhóm theo ngày ("Hôm nay", "Hôm qua", dd/mm); icon trung tính theo loại phát sinh (không tô đỏ
// việc bán hàng bình thường — màu trạng thái chỉ khi có nghĩa: hạch toán lỗ/huỷ tô hổ phách); mã lô mono xám như bảng;
// số kg có dấu, tabular, căn phải. Thứ tự chữ trong <p> giữ "mã lô · loại · số kg" (e2e so với bản cũ).

import { useAuth } from "@/features/auth/components/AuthProvider";
import { dashboardSummaryKey } from "@/shared/lib/dashboardSummary";
import type { LedgerActivity, MovementType } from "@/shared/lib/dashboardSummary";
import { kg, timeHM } from "@/shared/lib/format";
import { canView } from "@/shared/lib/nav";
import { useResource } from "@/shared/lib/useResource";
import { Icon } from "@/shared/ui/Icon";
import { ErrorBox, Loading } from "@/shared/ui/StateBox";
import { loadErrorText } from "@/shared/lib/http";
import { getActivity } from "../api";

const TYPE_ICON: Record<MovementType, string> = {
  RECEIPT: "inventory_2",
  SALE: "shopping_bag",
  RETURN_RESTOCK: "assignment_return",
  CANCEL_RESTORE: "undo",
  RECONCILE: "fact_check",
  WRITE_OFF: "delete_sweep",
};

/** Khoá ngày theo giờ máy người dùng: "2026-09-24". */
function dayKey(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function dayLabel(key: string): string {
  if (!key) return "Không rõ ngày";
  const today = new Date();
  const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
  if (key === dayKey(today.toISOString())) return "Hôm nay";
  if (key === dayKey(yesterday.toISOString())) return "Hôm qua";
  const [, m, d] = key.split("-");
  return `${d}/${m}`;
}

/** Gom các dòng liền nhau cùng ngày (dữ liệu BE đã xếp mới → cũ). */
function byDay(rows: LedgerActivity[]): { key: string; rows: LedgerActivity[] }[] {
  const out: { key: string; rows: LedgerActivity[] }[] = [];
  for (const r of rows) {
    const k = dayKey(r.at);
    const last = out[out.length - 1];
    if (last && last.key === k) last.rows.push(r);
    else out.push({ key: k, rows: [r] });
  }
  return out;
}

export function ActivityFeed() {
  const { me } = useAuth();
  // Nguồn tạm là /api/dashboard/summary/ → luật menu "inventory" (nav.ts) đã đòi cả reports.view_dashboard.
  const allowed = canView(me, "inventory");
  const res = useResource(me && allowed ? dashboardSummaryKey(me.id) : null, getActivity);

  let body: React.ReactNode;
  if (!allowed) {
    body = (
      <div className="state">
        <span className="state-ic">
          <Icon name="lock" />
        </span>
        <p>Bạn không có quyền xem sổ kho.</p>
      </div>
    );
  } else if (res.data === undefined) {
    body =
      res.error && !res.loading ? (
        <ErrorBox message={loadErrorText(res.error)} onRetry={() => void res.reload()} />
      ) : (
        <Loading />
      );
  } else if (!res.data.activity.length) {
    body = (
      <div className="state">
        <span className="state-ic">
          <Icon name="history" />
        </span>
        <b className="state-title">Chưa có hoạt động</b>
        <p>Nhập lô, bán hàng, kiểm kê… sẽ hiện ở đây theo thứ tự mới nhất.</p>
      </div>
    );
  } else {
    body = byDay(res.data.activity).map((g, gi) => (
      <section key={`${g.key}-${gi}`} className="feed-day" aria-labelledby={`feed-day-${gi}`}>
        <h3 id={`feed-day-${gi}`} className="feed-day-h">
          {dayLabel(g.key)}
        </h3>
        <ol className="feed">
          {g.rows.map((e, i) => {
            const inbound = e.qty_change >= 0;
            return (
              <li key={`${e.at}-${e.batch_id}-${i}`} className={`fev${e.type === "WRITE_OFF" ? " loss" : ""}`}>
                <span className="fi" aria-hidden="true">
                  <Icon name={TYPE_ICON[e.type] || (inbound ? "south_west" : "north_east")} />
                </span>
                <p>
                  <span className="fe-code">{e.batch_id}</span> <span className="fe-what">{e.type_label}</span>{" "}
                  <span className="fe-qty">
                    {inbound && e.qty_change > 0 ? "+" : ""}
                    {kg(e.qty_change)}
                  </span>
                </p>
                <time dateTime={e.at}>{timeHM(e.at)}</time>
              </li>
            );
          })}
        </ol>
      </section>
    ));
  }

  return (
    <div className="rr-pane">
      <h2 className="rr-title">Sổ kho gần đây</h2>
      {body}
    </div>
  );
}
