"use client";

// Nút "Nhờ" (DW-23): chuyển việc cho người có thẩm quyền. KHÔNG phải tính năng AI: DW-23-AC7 "AI tắt → Nhờ vẫn chạy",
// BE không chặn escalate khi AI tắt. Vì vậy render tĩnh trong StepItem, không phụ thuộc cờ AI bật/đã đồng ý (SR-20, F6-1).
// Chỉ import `escalateStep` từ ai/actions/api (thuần http, không kéo runtime AI); seed mock nằm ở ai/actions/mock.ts.
// Thông báo kết quả đưa vào `noticeHost` bằng portal để giữ nguyên bố cục.

import React, { useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import { escalateStep } from "@/features/ai/actions/api";
import type { GuidanceNextStep } from "../types";
import s from "./guidance.module.css";

type Props = {
  step: GuidanceNextStep;
  docType: string;
  docId: string | number;
  disabled?: boolean;
  noticeHost: HTMLElement | null;
};

export default function GuidanceEscalate({ step, docType, docId, disabled, noticeHost }: Props) {
  const [escalating, setEscalating] = useState<boolean>(false);
  const [escalatedGroup, setEscalatedGroup] = useState<string | null>(null);
  const [escalateError, setEscalateError] = useState<string | null>(null);

  // DW-23-AC1: hiện khi bước chưa được phép thực hiện (allowed === false) và không phải bước hệ thống.
  const show = AI_FEATURES_ENABLED && !step.allowed && step.actor !== "system" && Boolean(step.key);
  if (!show) return null;

  const handleEscalate = async () => {
    setEscalating(true);
    setEscalateError(null);
    try {
      const res = await escalateStep({ doc_type: docType, doc_id: docId, step_key: step.key });
      setEscalatedGroup(res.assignee_group);
    } catch (err: unknown) {
      setEscalateError(err instanceof Error ? err.message : "Không thể chuyển việc lúc này.");
    } finally {
      setEscalating(false);
    }
  };

  const notices = (
    <>
      {escalatedGroup && (
        <div className={s.aiNotice}>
          <Icon name="check_circle" />
          <div className={s.aiNoticeContent}>
            <span>
              Đã chuyển việc cho nhóm <strong>{escalatedGroup}</strong>.
              {AI_FEATURES_ENABLED && <> Việc hiển thị trong tab &quot;Được chuyển&quot; của màn Việc AI.</>}
            </span>
            {AI_FEATURES_ENABLED && (
              <Link href="/ai/actions?status=ESCALATED" className={s.aiActionsLink}>
                Đến tab Được chuyển
              </Link>
            )}
          </div>
        </div>
      )}
      {escalateError && (
        <div className={`${s.aiNotice} ${s.aiNoticeError}`}>
          <Icon name="error" />
          <span>{escalateError}</span>
        </div>
      )}
    </>
  );

  return (
    <>
      <button
        type="button"
        className={s.stepEscalateBtn}
        onClick={handleEscalate}
        disabled={disabled || escalating || Boolean(escalatedGroup)}
        title="Chuyển việc cho người có thẩm quyền thực hiện (DW-23)"
      >
        <Icon name="handshake" />
        <span>{escalating ? "Đang chuyển..." : escalatedGroup ? `Đã nhờ (${escalatedGroup})` : "Nhờ"}</span>
      </button>
      {noticeHost ? createPortal(notices, noticeHost) : null}
    </>
  );
}
