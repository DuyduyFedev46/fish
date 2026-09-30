"use client";

// Khối Tiếp theo · Đã làm (02b §6.7, DW-03, DW-14, DW-16).
// Hiển thị việc tiếp theo hợp lệ, ai làm, hạn, vì sao, cảnh báo và dòng thời gian.
// Tự cô lập lỗi mạng/500 — không làm hỏng màn hình cha (DW-03-AC11).
// Hỗ trợ nút "Để AI làm" (DW-14), "Tóm tắt" (DW-16) — phần AI nằm ở GuidanceAiActions/GuidanceAiSummary,
// nạp bằng next/dynamic (SR-20, BR-AI-17). File này không import runtime AI, không gọi /api/ai/status.
//  - "Để AI làm" (F6-2, Duy chốt 30/09): hiện theo `step.ai` do SERVER trả (null khi Chủ tắt AI toàn cục, nhân viên tắt AI
//    của mình, lệnh chưa giao/OFF hoặc không quyền). KHÔNG phụ thuộc "đã đồng ý tải model" hay việc đã mở tab Trợ lý.
//    Không bước nào có `step.ai` → GuidanceAiActions không bao giờ được tải (0 code AI, 0 request /api/ai/*).
//  - "Tóm tắt" (chạy model local): vẫn cần AI bật + đã đồng ý (gate-state).
// Nút "Nhờ" (DW-23) KHÔNG phải tính năng AI nên render tĩnh (GuidanceEscalate, F6-1).

import React, { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { dateTime } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { getGuidance } from "../api";
import type { GuidanceData, GuidanceNextStep, GuidanceTimelineEntry } from "../types";
import GuidanceEscalate from "./GuidanceEscalate";
import { useAiEnabledAndConsented } from "@/features/ai/gate-state";
import s from "./guidance.module.css";

// Phần AI: chunk riêng, chỉ tải khi thật sự render (có bước có step.ai / Tóm tắt khi AI bật + đã đồng ý).
const GuidanceAiActions = dynamic(() => import("./GuidanceAiActions"), { ssr: false, loading: () => null });
const GuidanceAiSummary = dynamic(() => import("./GuidanceAiSummary"), { ssr: false, loading: () => null });

type Props = {
  docType: string;
  docId: string | number;
  onAction?: (actionKey: string) => void;
  onDataLoaded?: (data: GuidanceData) => void;
  /** Tăng key này khi component cha muốn ép tải lại khối (vd: sau khi action bị 400 — AC8). */
  refreshSignal?: number;
};

export function GuidancePanel({ docType, docId, onAction, onDataLoaded, refreshSignal = 0 }: Props) {
  const [data, setData] = useState<GuidanceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // "Tóm tắt" (model local): "AI bật và đã đồng ý" đọc từ gate-state — không tự gọi /api/ai/status/. KHÔNG dùng cho "Để AI làm".
  const aiOn = useAiEnabledAndConsented();
  // Chỗ đặt kết quả của phần AI (portal) — giữ bố cục cũ dù nút do component nạp động vẽ.
  const [summaryHost, setSummaryHost] = useState<HTMLDivElement | null>(null);

  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getGuidance(docType, docId, signal);
      setData(res);
      onDataLoaded?.(res);
    } catch (err: unknown) {
      if (signal?.aborted) return;
      const msg = err instanceof Error ? err.message : "Không thể tải hướng dẫn tiếp theo";
      setError(msg);
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [docType, docId, onDataLoaded]);

  useEffect(() => {
    const ac = new AbortController();
    loadData(ac.signal);
    return () => ac.abort();
  }, [loadData, refreshSignal]);

  return (
    <div className={s.panel} data-guidance-panel>
      {/* 1. Trạng thái tải / lỗi */}
      {loading && !data && (
        <div className={s.stateBox}>
          <span>Đang kiểm tra việc tiếp theo...</span>
        </div>
      )}

      {error && (
        <div className={`${s.stateBox} ${s.errBox}`}>
          <span>Lỗi tải việc tiếp theo: {error}</span>
          <button type="button" className={s.retryBtn} onClick={() => loadData()}>
            Thử lại
          </button>
        </div>
      )}

      {/* 2. Cảnh báo (warnings) */}
      {data?.warnings && data.warnings.length > 0 && (
        <div className={s.warnBox}>
          {data.warnings.map((w, idx) => (
            <div key={`${w.code}-${idx}`} className={s.warnItem}>
              <Icon name="warning" />
              <span>{w.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* 3. Việc tiếp theo (Next Steps) */}
      {data && (
        <section className={s.part} aria-label="Việc tiếp theo">
          <h3 className={s.partH}>
            <span>Việc tiếp theo</span>
            <button
              type="button"
              className={s.refreshBtn}
              onClick={() => loadData()}
              title="Cập nhật hướng dẫn"
            >
              <Icon name="sync" />
              <span>Làm mới</span>
            </button>
          </h3>

          {data.next_steps.length === 0 ? (
            <p className={s.nil}>Không có việc cần xử lý ở trạng thái hiện tại.</p>
          ) : (
            <ul className={s.stepList}>
              {data.next_steps.map((step) => (
                <StepItem
                  key={step.key}
                  step={step}
                  docType={docType}
                  docId={data.doc.id}
                  onAction={onAction}
                  disabled={loading}
                />
              ))}
            </ul>
          )}
        </section>
      )}

      {/* 4. Đã làm (Dòng thời gian / Timeline) */}
      {data && data.timeline && data.timeline.length > 0 && (
        <section className={s.part} aria-label="Đã làm">
          <div className={s.partH}>
            <div className={s.partHTitle}>
              <span>Đã làm</span>
              <span className={`${s.partCount} num`}>{data.timeline.length}</span>
            </div>
            {/* DW-16: Nút "Tóm tắt" — chỉ nạp và hiện khi AI bật + đã đồng ý */}
            {aiOn && <GuidanceAiSummary timeline={data.timeline} resultHost={summaryHost} />}
          </div>
          <div ref={setSummaryHost} className={s.aiHost} />

          <GuidanceTimelineView entries={data.timeline} />
        </section>
      )}
    </div>
  );
}

function StepItem({
  step,
  docType,
  docId,
  onAction,
  disabled,
}: {
  step: GuidanceNextStep;
  docType: string;
  docId: string | number;
  onAction?: (key: string) => void;
  disabled?: boolean;
}) {
  const isSystem = step.actor === "system";
  const canAct = step.allowed && onAction && !isSystem;
  // F6-2 / DW-14-AC3, AC8: nút "Để AI làm" theo `step.ai` (server đã lọc quyền/cờ AI) + mức C + có lệnh.
  const showAiButton = Boolean(step.ai && step.ai.level === "C" && step.command);
  // Nơi phần AI (nạp động) đặt thông báo kết quả — ngay dưới đầu bước.
  const [noticeHost, setNoticeHost] = useState<HTMLDivElement | null>(null);

  return (
    <li
      className={`${s.stepCard} ${step.allowed ? s.stepCardAllowed : s.stepCardDisabled}`}
      data-step-key={step.key}
      data-allowed={step.allowed ? "true" : "false"}
    >
      <div className={s.stepHead}>
        <div className={s.stepTitle}>
          {isSystem ? <Icon name="schedule" /> : <Icon name="play_arrow" />}
          <span>{step.label}</span>
          {isSystem && <span className={s.badgeSystem}>Hệ thống</span>}
          {step.ai && (
            <span className={s.badgeAi}>AI {step.ai.level ? `(${step.ai.level})` : ""}</span>
          )}
        </div>

        <div className={s.stepActions}>
          {/* DW-23 "Nhờ": không phụ thuộc AI (DW-23-AC7) */}
          <GuidanceEscalate step={step} docType={docType} docId={docId} disabled={disabled} noticeHost={noticeHost} />
          {/* DW-14 "Để AI làm": chunk riêng, chỉ nạp khi có bước có step.ai; bấm là gọi server (không dùng model local) */}
          {showAiButton && (
            <GuidanceAiActions step={step} docType={docType} docId={docId} disabled={disabled} noticeHost={noticeHost} />
          )}

          {canAct && (
            <button
              type="button"
              className={s.stepActionBtn}
              onClick={() => onAction(step.key)}
              disabled={disabled}
            >
              Thực hiện
            </button>
          )}
        </div>
      </div>

      {/* Thông báo kết quả của "Để AI làm"/"Nhờ" (portal từ GuidanceAiActions/GuidanceEscalate) */}
      <div ref={setNoticeHost} className={s.aiHost} />

      <div className={s.stepMeta}>
        {step.who && step.who.length > 0 && !isSystem && (
          <span className={s.badgeActor}>Thực hiện: {step.who.join(", ")}</span>
        )}
        {step.deadline && (
          <span>
            Hạn: <time dateTime={step.deadline}>{dateTime(step.deadline)}</time>
          </span>
        )}
        {step.missing && step.missing.length > 0 && (
          <span className={s.badgeMissing}>
            Chưa thể làm: {step.missing.map((m) => m.text).join("; ")}
          </span>
        )}
      </div>

      {step.why && (
        <div className={s.stepReason}>
          <span>Lý do: {step.why.text}</span>
          {step.why.br && <span className="num"> ({step.why.br})</span>}
        </div>
      )}
    </li>
  );
}

/** Component hiển thị timeline từ guidance có hỗ trợ tag doc và hiển thị AI actor (L-4). */
export function GuidanceTimelineView({ entries }: { entries: GuidanceTimelineEntry[] }) {
  if (!entries || entries.length === 0) {
    return <p className={s.nil}>Chưa có lịch sử sự kiện.</p>;
  }

  return (
    <ol className={s.tl}>
      {entries.map((e, idx) => {
        const isAi = e.actor?.kind === "ai";
        return (
          <li key={`${e.at}-${idx}`} className={s.tlItem} data-kind={e.kind}>
            <span className={s.tlBullet} aria-hidden="true" />
            <div className={s.tlBody}>
              <div className={s.tlLabel}>
                {e.label}
                {e.doc && <span className={s.docTag}> [{e.doc}]</span>}
              </div>
              <div className={s.tlMeta}>
                <time className="num" dateTime={e.at}>
                  {dateTime(e.at)}
                </time>
                {e.actor?.display && (
                  <span>
                    {" · "}
                    {isAi ? <span className={s.badgeAi}>AI</span> : null}{" "}
                    {e.actor.display}
                    {isAi && e.actor.level ? ` (Mức ${e.actor.level})` : null}
                  </span>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
