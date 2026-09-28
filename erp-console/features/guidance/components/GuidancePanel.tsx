"use client";

// Khối Tiếp theo · Đã làm (02b §6.7, DW-03, DW-14, DW-16).
// Hiển thị việc tiếp theo hợp lệ, ai làm, hạn, vì sao, cảnh báo và dòng thời gian.
// Tự cô lập lỗi mạng/500 — không làm hỏng màn hình cha (DW-03-AC11).
// Hỗ trợ nút "Để AI làm" (DW-14) và nút "Tóm tắt" (DW-16).

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { dateTime } from "@/shared/lib/format";
import { Icon } from "@/shared/ui/Icon";
import { getGuidance } from "../api";
import type { GuidanceData, GuidanceNextStep, GuidanceTimelineEntry } from "../types";
import { callCommand } from "@/features/ai/commands/call";
import { getAiStatus } from "@/features/ai/api";
import { askAi, selectEngineName } from "@/features/ai/runtime/engine";
import { canDownloadModel, detectAiCapability } from "@/features/ai/runtime/feature-detect";
import s from "./guidance.module.css";

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

  // DW-16: Trạng thái tóm tắt timeline
  const [aiEnabled, setAiEnabled] = useState<boolean>(false);
  const [canSummarize, setCanSummarize] = useState<boolean>(false);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState<boolean>(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

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

  // Kiểm tra khả năng AI cho DW-16 (tóm tắt timeline)
  useEffect(() => {
    let alive = true;
    getAiStatus()
      .then((st) => {
        if (!alive) return;
        setAiEnabled(st.ai_enabled);
        if (st.ai_enabled) {
          const engine = selectEngineName();
          const cap = detectAiCapability();
          const verdict = canDownloadModel(cap);
          // DW-16-AC5: nếu máy không đạt hoặc 4G/iOS thì ẩn nút tóm tắt (trừ khi dùng mock)
          if (verdict.ok || engine === "llmock") {
            setCanSummarize(true);
          } else {
            setCanSummarize(false);
          }
        } else {
          setCanSummarize(false);
        }
      })
      .catch(() => {
        if (!alive) return;
        setAiEnabled(false);
        setCanSummarize(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  // DW-16: Xử lý tóm tắt dòng thời gian
  const handleSummarize = useCallback(async () => {
    if (!data?.timeline || data.timeline.length === 0) return;
    setSummarizing(true);
    setSummaryError(null);

    // DW-16-AC2, AC3, AC4: Payload JSON guidance đã lọc của người xem, không chứa PII khách hay giá vốn
    const safeTimeline = data.timeline.map((entry) => ({
      at: entry.at,
      label: entry.label,
      doc: entry.doc,
      actor: entry.actor ? { kind: entry.actor.kind, display: entry.actor.display } : undefined,
    }));

    const prompt =
      "Hãy tóm tắt ngắn gọn trong 2-3 câu diễn biến các bước đã thực hiện của chứng từ này:\n" +
      JSON.stringify(safeTimeline);

    // DW-16-AC6: Giới hạn thời gian tối đa 10 giây
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 10000);

    try {
      const resp = await askAi(prompt, { signal: ctrl.signal });
      clearTimeout(timer);
      setSummaryText(resp);
    } catch (err: unknown) {
      clearTimeout(timer);
      setSummaryText(null);
      setSummaryError("Không thể tóm tắt dòng thời gian. Vui lòng xem dòng thời gian chi tiết bên dưới.");
    } finally {
      setSummarizing(false);
    }
  }, [data]);

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
                  aiEnabled={aiEnabled}
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
            {/* DW-16: Nút "Tóm tắt" — chỉ hiện khi AI được bật và hỗ trợ runtime */}
            {canSummarize && (
              <button
                type="button"
                className={s.summaryBtn}
                onClick={handleSummarize}
                disabled={summarizing}
                title="AI tóm tắt ngắn gọn dòng thời gian"
              >
                <Icon name="auto_awesome" />
                <span>{summarizing ? "Đang tóm tắt..." : "Tóm tắt"}</span>
              </button>
            )}
          </div>

          {/* DW-16: Khối hiển thị câu tóm tắt của AI */}
          {summaryText && (
            <div className={s.summaryBox} aria-label="Tóm tắt của AI">
              <div className={s.summaryHeader}>
                <span className={s.badgeAi}>AI</span>
                <span className={s.summaryTitle}>Tóm tắt sự kiện</span>
              </div>
              <p className={s.summaryContent}>{summaryText}</p>
            </div>
          )}

          {summaryError && <p className={s.summaryError}>{summaryError}</p>}

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
  aiEnabled,
  onAction,
  disabled,
}: {
  step: GuidanceNextStep;
  docType: string;
  docId: string | number;
  aiEnabled: boolean;
  onAction?: (key: string) => void;
  disabled?: boolean;
}) {
  const isSystem = step.actor === "system";
  const canAct = step.allowed && onAction && !isSystem;

  // DW-14: Trạng thái gọi AI cho nút "Để AI làm"
  const [callingAi, setCallingAi] = useState<boolean>(false);
  const [aiSuccessMsg, setAiSuccessMsg] = useState<{ text: string; actionId: string } | null>(null);
  const [aiErrorMsg, setAiErrorMsg] = useState<string | null>(null);

  // DW-14-AC3, AC8: Chỉ hiện nút "Để AI làm" khi AI bật, step.ai.level === "C" và có step.command
  const showAiButton = aiEnabled && step.ai && step.ai.level === "C" && Boolean(step.command);

  const handleAiAction = async () => {
    if (!step.command) return;
    setCallingAi(true);
    setAiSuccessMsg(null);
    setAiErrorMsg(null);

    try {
      const res = await callCommand(step.command, {
        target_id: docId,
        screen: docType,
      });

      if (res.outcome === "proposal") {
        setAiSuccessMsg({
          text: `AI đã soạn nháp đề xuất (mã việc: ${res.action_id}). Vui lòng vào Việc AI để kiểm tra và duyệt.`,
          actionId: res.action_id,
        });
      }
    } catch (err: unknown) {
      // DW-14-AC6: Bắt lỗi 400 nguyên văn tiếng Việt kèm mã lỗi, không tự ý thử lại
      const msg = err instanceof Error ? err.message : "Thao tác AI không thành công.";
      setAiErrorMsg(msg);
    } finally {
      setCallingAi(false);
    }
  };

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
          {/* DW-14: Nút "Để AI làm" */}
          {showAiButton && (
            <button
              type="button"
              className={s.stepAiBtn}
              onClick={handleAiAction}
              disabled={disabled || callingAi}
              title={step.ai?.label || "Giao AI soạn nháp đề xuất"}
            >
              <Icon name="auto_awesome" />
              <span>{callingAi ? "Đang xử lý..." : step.ai?.label || "Để AI làm"}</span>
            </button>
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

      {/* Thông báo kết quả bấm "Để AI làm" */}
      {aiSuccessMsg && (
        <div className={s.aiNotice}>
          <Icon name="check_circle" />
          <div className={s.aiNoticeContent}>
            <span>{aiSuccessMsg.text}</span>
            <Link href="/ai/actions" className={s.aiActionsLink}>
              Đến màn Việc AI
            </Link>
          </div>
        </div>
      )}

      {aiErrorMsg && (
        <div className={`${s.aiNotice} ${s.aiNoticeError}`}>
          <Icon name="error" />
          <span>{aiErrorMsg}</span>
        </div>
      )}

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
