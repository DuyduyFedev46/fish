"use client";

// Dòng "N đề xuất AI chờ duyệt" trong khối Cần chú ý (ED-08-AC3 / D1), kèm số theo khu: Mua hàng · Đơn & tiền · Kho & lô.
// Có cổng (fail-closed): chỉ hỏi số đề xuất khi (1) người xem được mở màn Việc AI và (2) GET /api/ai/status/ báo AI đang bật.
// AI tắt, lỗi mạng hay không có đề xuất nào thì KHÔNG vẽ gì: dòng này chỉ là lối tắt, thiếu nó không làm hỏng màn.
// Chỉ gọi HTTP nhẹ (status + counts); không import runtime/worker/wllama của AI (check-ai-chunks).
// Đếm cả đề xuất đang chờ (PENDING) và đề xuất đã chuyển cho cấp trên (ESCALATED).

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchAiActionCounts } from "@/features/ai/actions/api";
import { getAiStatus } from "@/features/ai/api";
import { releaseAiEnabled } from "@/features/ai/gate-state";
import { canView } from "@/shared/lib/nav";
import { Icon } from "@/shared/ui/Icon";
import { summarizeProposals, zonesText, type ProposalSummary } from "../view";
import s from "../overview.module.css";

export function AiProposalsRow() {
  const { me } = useAuth();
  const allowed = canView(me, "ai-actions");
  const [summary, setSummary] = useState<ProposalSummary | null>(null);

  useEffect(() => {
    if (!allowed) {
      setSummary(null);
      return;
    }
    const ctrl = new AbortController();
    const owner = Symbol("overview-ai-row");
    getAiStatus(ctrl.signal, owner)
      .then((st) => (st.ai_enabled ? fetchAiActionCounts({ status: "PENDING,ESCALATED" }, ctrl.signal) : null))
      .then((counts) => {
        if (!ctrl.signal.aborted) setSummary(counts ? summarizeProposals(counts.by_target_model) : null);
      })
      .catch(() => {
        if (!ctrl.signal.aborted) setSummary(null);
      });
    return () => {
      ctrl.abort();
      releaseAiEnabled(owner); // rời màn thì nhả cờ, không để "AI bật" dính sang màn khác
    };
  }, [allowed]);

  if (!summary || summary.total === 0) return null;
  const detail = zonesText(summary);
  return (
    <li data-attention="ai_proposals">
      <Link href="/ai/actions/" className={`${s.row} ${s.rowAi}`}>
        <Icon name="auto_awesome" className={s.rowIc} />
        <span className={s.rowMain}>
          <b>{summary.total}</b> đề xuất AI chờ duyệt
        </span>
        {detail && <span className={s.rowMeta}>{detail}</span>}
        <Icon name="arrow_forward" className={s.rowGo} />
      </Link>
    </li>
  );
}
