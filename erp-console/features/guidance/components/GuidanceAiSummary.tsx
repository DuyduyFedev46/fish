"use client";

// Nút "Tóm tắt" dòng thời gian (DW-16) — dùng runtime AI (`askAi`) nên CHỈ được nạp bằng next/dynamic từ
// GuidancePanel khi "AI bật và đã đồng ý" (SR-20, BR-AI-17). AI tắt → file này và runtime không được tải.
// Nút nằm ở đầu khối "Đã làm"; câu tóm tắt/lỗi được đưa vào `resultHost` (ngay dưới đầu khối) bằng portal.

import React, { useCallback, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/shared/ui/Icon";
import { askAi, selectEngineName } from "@/features/ai/runtime/engine";
import { canDownloadModel, detectAiCapability } from "@/features/ai/runtime/feature-detect";
import type { GuidanceTimelineEntry } from "../types";
import s from "./guidance.module.css";

type Props = {
  timeline: GuidanceTimelineEntry[];
  resultHost: HTMLElement | null;
};

export default function GuidanceAiSummary({ timeline, resultHost }: Props) {
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState<boolean>(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // DW-16-AC5: nếu máy không đạt hoặc 4G/iOS thì ẩn nút tóm tắt (trừ khi dùng mock)
  const canSummarize = useMemo(() => {
    const verdict = canDownloadModel(detectAiCapability());
    return verdict.ok || selectEngineName() === "llmock";
  }, []);

  // DW-16: Xử lý tóm tắt dòng thời gian
  const handleSummarize = useCallback(async () => {
    if (timeline.length === 0) return;
    setSummarizing(true);
    setSummaryError(null);

    // DW-16-AC2, AC3, AC4: Payload JSON guidance đã lọc của người xem, không chứa PII khách hay giá vốn
    const safeTimeline = timeline.map((entry) => ({
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
    } catch {
      clearTimeout(timer);
      setSummaryText(null);
      setSummaryError("Không thể tóm tắt dòng thời gian. Vui lòng xem dòng thời gian chi tiết bên dưới.");
    } finally {
      setSummarizing(false);
    }
  }, [timeline]);

  if (!canSummarize) return null;

  const result = (
    <>
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
    </>
  );

  return (
    <>
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
      {resultHost ? createPortal(result, resultHost) : null}
    </>
  );
}
