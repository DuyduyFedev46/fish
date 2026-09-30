"use client";

// Nút "Để AI làm" (DW-14) của từng bước trong khối Tiếp theo (SR-20, BR-AI-17). Nút "Nhờ" (DW-23) KHÔNG nằm ở đây
// (không phải tính năng AI, xem GuidanceEscalate.tsx).
// Component này import tĩnh `ai/commands/call` (thuần http, không kéo runtime local wllama/Worker) nên CHỈ được nạp
// bằng next/dynamic từ GuidancePanel, và chỉ khi bước có `step.ai` do server trả (F6-2). Không có bước nào có
// `step.ai` → file này không bao giờ được tải. Không phụ thuộc "đã đồng ý tải model": "Để AI làm" không dùng model.
//
// Vị trí: nút nằm trong hàng nút của bước (con của StepItem); thông báo kết quả được đưa vào `noticeHost`
// (một thẻ div ngay dưới đầu bước) bằng portal để giữ nguyên bố cục cũ.

import React, { useState } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { Icon } from "@/shared/ui/Icon";
import { callCommand } from "@/features/ai/commands/call";
import type { GuidanceNextStep } from "../types";
import s from "./guidance.module.css";

type Props = {
  step: GuidanceNextStep;
  docType: string;
  docId: string | number;
  disabled?: boolean;
  noticeHost: HTMLElement | null;
};

export default function GuidanceAiActions({ step, docType, docId, disabled, noticeHost }: Props) {
  // DW-14: Trạng thái gọi AI cho nút "Để AI làm"
  const [callingAi, setCallingAi] = useState<boolean>(false);
  const [aiSuccessMsg, setAiSuccessMsg] = useState<{ text: string; actionId: string } | null>(null);
  const [aiErrorMsg, setAiErrorMsg] = useState<string | null>(null);

  // DW-14-AC3, AC8: Chỉ hiện nút "Để AI làm" khi step.ai.level === "C" và có step.command (GuidancePanel đã kiểm và chỉ render khi đúng)
  const showAiButton = step.ai && step.ai.level === "C" && Boolean(step.command);

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

  const notices = (
    <>
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
    </>
  );

  return (
    <>
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

      {noticeHost ? createPortal(notices, noticeHost) : null}
    </>
  );
}
