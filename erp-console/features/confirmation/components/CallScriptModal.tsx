"use client";

// CS-18 — hộp soạn / sửa MỘT kịch bản gọi (form ngắn = hộp thoại nổi, UI-RULES §6.1). Chỉ Chủ mở được (add/change_callscript).
// Chặn số điện thoại và dãy số dài ở máy khách (BR-GH-19); BE chặn lại. Gửi lỗi → giữ nguyên chữ đã gõ, alert đỏ, nút đổi "Thử lại".
// Nội dung kịch bản là chữ chung, không phải dữ liệu khách; vẫn không ghi vào log, URL hay localStorage.
import { useState } from "react";
import { Field } from "@/shared/ui/form/Field";
import { FormAlert } from "@/shared/ui/form/FormAlert";
import { primaryLabel, useSubmit } from "@/shared/ui/form/useSubmit";
import { Modal } from "@/shared/ui/overlay/Modal";
import { createCallScript, updateCallScript } from "../api";
import { SCRIPT_MAX, scriptError } from "../callScripts";
import type { CallScript, CallScriptSituation } from "../types";

type Props = {
  situation: CallScriptSituation;
  label: string;
  /** Có sẵn = sửa (PATCH); null = soạn mới (POST). */
  existing: CallScript | null;
  onClose: () => void;
  onSaved: (saved: CallScript, created: boolean) => void;
};

export function CallScriptModal({ situation, label, existing, onClose, onSaved }: Props) {
  const [content, setContent] = useState(existing?.content ?? "");
  const [error, setError] = useState<string | null>(null);
  const sub = useSubmit(
    () => (existing ? updateCallScript(situation, { content: content.trim() }) : createCallScript({ situation, content: content.trim(), is_active: true })),
    { onSuccess: (saved) => onSaved(saved, !existing) },
  );

  const trySubmit = () => {
    const bad = scriptError(content);
    setError(bad);
    if (!bad) void sub.submit();
  };

  return (
    <Modal
      title={existing ? `Sửa kịch bản: ${label}` : `Soạn kịch bản: ${label}`}
      onClose={onClose}
      busy={sub.submitting}
      size="lg"
      footer={
        <>
          <button type="button" className="btn" onClick={onClose} disabled={sub.submitting}>
            Quay lại
          </button>
          <button type="button" className="btn primary" onClick={trySubmit} disabled={sub.submitting}>
            {sub.submitting ? "Đang lưu…" : primaryLabel("Lưu kịch bản", sub.failed)}
          </button>
        </>
      }
    >
      {sub.error && <FormAlert>{sub.error}</FormAlert>}
      <Field
        as="textarea"
        label="Nội dung kịch bản"
        required
        value={content}
        onChange={(v) => {
          setContent(v);
          setError(null);
        }}
        rows={8}
        maxLength={SCRIPT_MAX}
        counter
        error={error ?? sub.fieldErrors.content ?? null}
        disabled={sub.submitting}
        autoFocus
      />
    </Modal>
  );
}
