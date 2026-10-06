"use client";

// Khối "Cần chú ý" của Tổng quan (ED-08-AC3 / D1; CS-15-AC6): các dòng việc quá hạn từ /api/dashboard/attention/ (mỗi dòng bấm sang
// màn xử lý), dòng đề xuất AI (có cổng, xem AiProposalsRow), rồi các lô cận hạn từ dashboard/summary.
// Lỗi RIÊNG của khối này (CS-15-AC6): báo "Chưa tải được" + Thử lại, phần còn lại của màn vẫn hiện. 403 = người này không có việc
// nào để báo (vd chỉ có quyền xem tổng quan) nên coi như trống, không phải lỗi. Chỉ số đếm, không có tên/SĐT khách (bất biến 9).
// Giữ data-attention="<khoá>" trên từng dòng (e2e bám vào).

import Link from "next/link";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { ApiError } from "@/shared/lib/http";
import { kg } from "@/shared/lib/format";
import { useResource } from "@/shared/lib/useResource";
import { Icon } from "@/shared/ui/Icon";
import { getDashboardAttention } from "../api";
import type { ExpiryAlert } from "../types";
import { attentionRows, expiryLine } from "../view";
import { AiProposalsRow } from "./AiProposalsRow";
import s from "../overview.module.css";

// Dashboard chỉ trả mã lô (chuỗi), trang chi tiết lô cần id số → dòng cận hạn mở danh sách lô lọc "Cận hạn".
const NEAR_EXPIRY_HREF = "/inventory/?status=NEAR_EXPIRY";

function ExpiryRows({ alerts }: { alerts: ExpiryAlert[] }) {
  return (
    <>
      {alerts.map((a) => {
        const crit = a.days_left <= 1;
        return (
          <li key={a.batch_id} data-attention="near_expiry_batch">
            <Link href={NEAR_EXPIRY_HREF} className={`${s.row}${crit ? ` ${s.rowCrit}` : ""}`}>
              <Icon name={crit ? "error" : "schedule"} className={s.rowIc} />
              <span className={s.code}>{a.batch_id}</span>
              <span className={s.rowMain}>{a.item}</span>
              <span className={s.rowMeta}>
                {expiryLine(a.days_left)} · Tồn {kg(a.qty)}
              </span>
              <Icon name="arrow_forward" className={s.rowGo} />
            </Link>
          </li>
        );
      })}
    </>
  );
}

export function AttentionBlock({ alerts }: { alerts: ExpiryAlert[] }) {
  const { me } = useAuth();
  const res = useResource(me ? `dashboard-attention:${me.id}` : null, getDashboardAttention);
  const forbidden = res.error instanceof ApiError && res.error.status === 403;
  const failed = res.data === undefined && !!res.error && !res.loading && !forbidden;
  const loading = res.data === undefined && !res.error;
  const rows = res.data ? attentionRows(res.data) : [];

  return (
    <>
      {loading && (
        <p className={s.busy} role="status">
          Đang kiểm tra đầu việc…
        </p>
      )}
      {failed && (
        <div className={s.inlineErr} role="alert">
          <Icon name="error" />
          <span>Chưa tải được thông tin việc cần chú ý.</span>
          <button type="button" className="btn" onClick={() => void res.reload()}>
            Thử lại
          </button>
        </div>
      )}
      <ul className={s.list}>
        {rows.map((r) => (
          <li key={r.key} data-attention={r.key}>
            <Link href={r.href} className={`${s.row}${r.crit ? ` ${s.rowCrit}` : ""}`}>
              <Icon name={r.crit ? "error" : "schedule"} className={s.rowIc} />
              <span className={s.rowMain}>
                <b>{r.count}</b> {r.label}
              </span>
              <Icon name="arrow_forward" className={s.rowGo} />
            </Link>
          </li>
        ))}
        <AiProposalsRow />
        <ExpiryRows alerts={alerts} />
      </ul>
      {res.data !== undefined && rows.length === 0 && (
        <p className={s.calm}>
          <Icon name="check_circle" />
          Không có việc gọi hoặc tem bị quá hạn.
        </p>
      )}
      {alerts.length === 0 && (
        <p className={s.calm}>
          <Icon name="check_circle" />
          Không có lô cận hạn.
        </p>
      )}
    </>
  );
}
