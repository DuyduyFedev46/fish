"use client";

// Cánh cổng MỎNG của trợ lý (Phụ lục C.2 dòng 2) — file DUY NHẤT trong features/ai được import
// tĩnh bởi layout. Chỉ gọi GET /api/ai/status/ + đọc cờ đồng ý; `ai_enabled=false` HOẶC lỗi → null
// (không vẽ gì).
// Tấm NẶNG (AiAssistantPanel: runtime, tải model, chat) chỉ nạp động khi `ai_enabled` VÀ đã đồng ý.
// Chú ý C.4 #3: KHÔNG được để chuỗi wllama/vosk/whisper xuất hiện trong file này (chunk ban đầu phải sạch).

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { getAiStatus } from "../api";
import { hasAiConsent, setAiConsent } from "../consent";
import { AI_MSG } from "../messages";
import type { AiStatus } from "../types";
import s from "./ai.module.css";

const AiAssistantPanel = dynamic(() => import("./AiAssistantPanel").then((m) => m.AiAssistantPanel), { ssr: false });

export function AiAssistantGate() {
  const [status, setStatus] = useState<AiStatus | null>(null);
  const [consented, setConsented] = useState<boolean | null>(null);
  const [agreed, setAgreed] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const askedRef = useRef(false);
  const seqRef = useRef(0);

  // Chỉ gọi /api/ai/status/ khi người MỞ tab Trợ lý LẦN ĐẦU (pane `[hidden]` không giao cắt nên
  // IntersectionObserver chỉ bắn lúc hiện) → AI không bật mà không ai mở tab = 0 request (C.4 #10).
  useEffect(() => {
    const el = rootRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((en) => en.isIntersecting)) return;
      io.disconnect();
      if (askedRef.current) return;
      askedRef.current = true;
      const id = ++seqRef.current;
      getAiStatus()
        .then((st) => {
          if (id === seqRef.current) setStatus(st);
        })
        .catch(() => {
          if (id === seqRef.current) setStatus(null); // lỗi mạng → coi như tắt (S05-AC5 fail-closed)
        });
    });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // Cờ đồng ý đọc khi mount (boolean thuần — không ghi gì khác, bất biến 9).
  useEffect(() => {
    setConsented(hasAiConsent());
  }, []);

  const onAgree = useCallback(() => {
    setAiConsent(true);
    setConsented(true);
  }, []);

  return (
    <div ref={rootRef}>
      {status?.ai_enabled ? (
        consented === true ? (
          <AiAssistantPanel status={status} />
        ) : consented === false ? (
          <div className={`rr-pane ${s.consent}`}>
            <h2 className="rr-title">{AI_MSG.consentTitle}</h2>
            <p className={s.consentBody}>{AI_MSG.consentBody}</p>
            <label className={s.check}>
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
              <span>{AI_MSG.consentCheck}</span>
            </label>
            <div className={s.consentActions}>
              <button type="button" className="btn primary" disabled={!agreed} onClick={onAgree}>
                {AI_MSG.consentAgree}
              </button>
            </div>
            {!agreed ? <p className={s.consentHint}>{AI_MSG.consentHint}</p> : null}
          </div>
        ) : null
      ) : null}
    </div>
  );
}
