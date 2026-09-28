"use client";

// Khối Tiếp theo · Đã làm (02b §6.7, DW-03).
// Hiển thị việc tiếp theo hợp lệ, ai làm, hạn, vì sao, cảnh báo và dòng thời gian.
// Tự cô lập lỗi mạng/500 — không làm hỏng màn hình cha (DW-03-AC11).

import React, { useCallback, useEffect, useState } from "react";
import { dateTime } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { getGuidance } from "../api";
import type { GuidanceData, GuidanceNextStep, GuidanceTimelineEntry } from "../types";
import s from "./guidance.module.css";

type Props = {
  docType: string;
  docId: string | number;
  onAction?: (actionKey: string) => void;
  /** Tăng key này khi component cha muốn ép tải lại khối (vd: sau khi action bị 400 — AC8). */
  refreshSignal?: number;
};

export function GuidancePanel({ docType, docId, onAction, refreshSignal = 0 }: Props) {
  const [data, setData] = useState<GuidanceData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getGuidance(docType, docId, signal);
      setData(res);
    } catch (err: unknown) {
      if (signal?.aborted) return;
      const msg = err instanceof Error ? err.message : "Không thể tải hướng dẫn tiếp theo";
      setError(msg);
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, [docType, docId]);

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
                  onAction={onAction}
                  disabled={loading}
                />
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

function StepItem({
  step,
  onAction,
  disabled,
}: {
  step: GuidanceNextStep;
  onAction?: (key: string) => void;
  disabled?: boolean;
}) {
  const isSystem = step.actor === "system";
  const canAct = step.allowed && onAction && !isSystem;

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
