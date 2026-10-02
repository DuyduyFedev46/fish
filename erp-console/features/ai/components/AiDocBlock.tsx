"use client";

// Khối "Trợ lý AI" của một chứng từ (UI-RULES §5.5, 02b §2.4): đề xuất AI đang chờ duyệt / đã nhờ nhóm xử lý cho ĐÚNG chứng từ này
// (R1: lọc target_model + target_id), nút Từ chối / Đồng ý, và ô chat nạp động khi đã đồng ý dùng trợ lý trên máy.
// Việc AI ESCALATED không còn menu "Việc AI" nên hiện ở đây (02b T10).
//
// Đồng ý theo BR-AI-14: phải MỞ chi tiết đề xuất trước (BE ghi viewed_at, trả confirm_nonce) và đợi ≥ 3 giây; nút đếm ngược.
// Dữ liệu cá nhân của khách không xuất hiện: chỉ hiện các khoá trong bảng nhãn (docBlockModel). Không ghi gì vào localStorage/log.
// Chuỗi của runtime nặng (model, worker, đường gọi lệnh) KHÔNG xuất hiện trong file này: AiAssistantPanel chỉ nạp qua next/dynamic.

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";
import { AiBlockFrame, type AiProposalView } from "@/shared/ui/detail/AiBlockFrame";
import { confirmAiAction, fetchAiActionDetail, fetchAiActions, rejectAiAction } from "../actions/api";
import { hasAiConsent, setAiConsent, subscribeAiConsent } from "../consent";
import { AI_MSG } from "../messages";
import type { AiActionRow, AiStatus } from "../types";
import { DOC_CHAT_CHIPS, askWithDocContext, readyAtOf, toProposalView, waitLeft } from "./docBlockModel";
import s from "./ai.module.css";
import d from "./AiDocBlock.module.css";

const AiAssistantPanel = dynamic(() => import("./AiAssistantPanel").then((m) => m.AiAssistantPanel), {
  ssr: false,
  loading: () => (
    <p role="status" className="muted">
      Đang mở trợ lý…
    </p>
  ),
});

type Props = {
  status: AiStatus;
  targetModel: string;
  targetId: string;
  onApplied?: () => void;
  /** Câu hỏi nhanh hiện sẵn (mặc định DOC_CHAT_CHIPS). Không chứa dữ liệu cá nhân. */
  chips?: string[];
};

type Ready = { nonce?: string; readyAt: number };

const MSG_STALE = "Đề xuất này đã được xử lý hoặc hết hạn. Đã tải lại danh sách.";

function messageOf(err: unknown, fallback: string): string {
  return err instanceof ApiError && err.message ? err.message : fallback;
}

export function AiDocBlock({ status, targetModel, targetId, onApplied, chips = DOC_CHAT_CHIPS }: Props) {
  const [rows, setRows] = useState<AiActionRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [chatOpen, setChatOpen] = useState(false);
  // B6/L9: khung hỏi nhanh tĩnh ở lại tới khi panel nạp xong (và đã đồng ý), để phím gõ sớm không rơi mất và focus không về body.
  const [panelReady, setPanelReady] = useState(false);
  // Khung hỏi nhanh TĨNH: chữ đang gõ và câu chuyển sang trợ lý khi nó được nạp (chỉ nằm trong state, không lưu đâu cả).
  const [draft, setDraft] = useState("");
  const [handoff, setHandoff] = useState<{ text: string; autoSend: boolean }>({ text: "", autoSend: false });
  const [consented, setConsented] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const ready = useRef<Map<string, Ready>>(new Map());
  const seq = useRef(0);
  const inFlight = useRef(false);
  const starterInput = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setConsented(hasAiConsent());
    return subscribeAiConsent(() => setConsented(hasAiConsent()));
  }, []);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const mine = ++seq.current;
      setLoadError(null);
      try {
        const page = await fetchAiActions({ status: "PENDING,ESCALATED", target_model: targetModel, target_id: targetId }, signal);
        if (mine !== seq.current) return;
        setRows(page.results);
        // BR-AI-14: mở chi tiết đề xuất chờ duyệt (mỗi đề xuất một lần) để BE ghi viewed_at và cấp confirm_nonce.
        for (const r of page.results) {
          if (r.status !== "PENDING" || ready.current.has(r.id)) continue;
          const startedAt = Date.now();
          ready.current.set(r.id, { readyAt: startedAt + 3000 }); // tạm; cập nhật khi có chi tiết
          fetchAiActionDetail(r.id, signal)
            .then((d) => {
              ready.current.set(r.id, { nonce: d.confirm_nonce, readyAt: readyAtOf(d, Date.now()) });
              setNow(Date.now());
            })
            .catch(() => {
              if (signal?.aborted || mine !== seq.current) return;
              // Không mở được chi tiết thì không có nonce/viewed_at nên chưa Đồng ý được: báo lỗi + "Thử lại" (load() tải lại chi tiết).
              ready.current.delete(r.id);
              setLoadError(AI_MSG.detailLoadFailed);
            });
        }
      } catch (err) {
        if (signal?.aborted || mine !== seq.current) return;
        if (err instanceof ApiError && err.status === 403) setForbidden(true);
        else setLoadError(messageOf(err, "Chưa tải được đề xuất của trợ lý."));
      }
    },
    [targetModel, targetId]
  );

  useEffect(() => {
    const ctrl = new AbortController();
    ready.current = new Map();
    setRows(null);
    setForbidden(false);
    load(ctrl.signal);
    return () => ctrl.abort();
  }, [load]);

  // Đếm ngược chỉ chạy khi còn đề xuất đang phải chờ.
  // Đề xuất thiếu mốc (chi tiết chưa/không tải được) không tính: nếu không, bộ đếm chạy mãi mà không bao giờ về 0.
  const anyWaiting = (rows ?? []).some((r) => {
    const at = ready.current.get(r.id)?.readyAt;
    return r.status === "PENDING" && at !== undefined && waitLeft(at, now) > 0;
  });
  useEffect(() => {
    if (!anyWaiting) return;
    const t = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(t);
  }, [anyWaiting]);

  const act = useCallback(
    async (id: string, kind: "confirm" | "reject") => {
      if (inFlight.current) return; // ref, không phải state: nhiều lần bấm trong cùng một tác vụ JS chỉ ra một POST
      inFlight.current = true;
      setBusyId(id);
      setActionError(null);
      try {
        if (kind === "confirm") await confirmAiAction(id, ready.current.get(id)?.nonce);
        else await rejectAiAction(id);
        await load();
        if (kind === "confirm") onApplied?.();
      } catch (err) {
        if (err instanceof ApiError && (err.status === 409 || err.status === 410)) {
          setActionError(MSG_STALE);
          await load();
        } else {
          setActionError(messageOf(err, kind === "confirm" ? "Chưa đồng ý được đề xuất. Thử lại nhé." : "Chưa từ chối được đề xuất. Thử lại nhé."));
        }
      } finally {
        inFlight.current = false;
        setBusyId(null);
      }
    },
    [load, onApplied]
  );

  if (forbidden) return null;

  const proposals = (rows ?? [])
    .map((r) => {
      const at = ready.current.get(r.id)?.readyAt;
      const view = toProposalView(r, at === undefined ? 0 : waitLeft(at, now));
      return view && at === undefined && view.state === "PENDING" ? { ...view, blocked: true } : view;
    })
    .filter((p): p is AiProposalView => p !== null);

  // Trợ lý chỉ được nạp khi người dùng chạm vào khung hỏi nhanh (focus ô, bấm chip, gửi).
  const openChat = (text: string, autoSend: boolean) => {
    // L8: câu hỏi mang theo loại + mã chứng từ ("đơn hàng SO…"), không có dữ liệu khách.
    setHandoff({ text: autoSend ? askWithDocContext(text, targetModel, targetId) : text, autoSend });
    setChatOpen(true);
  };
  const onPanelReady = useCallback(() => setPanelReady(true), []);

  const chat = chatOpen ? (
    <div className={d.docChat} data-doc-chat>
      {consented ? (
        <AiAssistantPanel status={status} initialText={handoff.autoSend ? handoff.text : draft} autoSend={handoff.autoSend} onReady={onPanelReady} />
      ) : (
        <div className={s.consent}>
          <h4 className="rr-title">{AI_MSG.consentTitle}</h4>
          <p className={s.consentBody}>{AI_MSG.consentBody}</p>
          <label className={s.check}>
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
            <span>{AI_MSG.consentCheck}</span>
          </label>
          <div className={s.consentActions}>
            <button type="button" className="btn primary" disabled={!agreed} onClick={() => {
                setAiConsent(true);
                starterInput.current?.focus({ preventScroll: true }); // nút đồng ý sắp biến mất: trả focus về ô hỏi, gõ tiếp không mất chữ
              }}>
              {AI_MSG.consentAgree}
            </button>
          </div>
        </div>
      )}
    </div>
  ) : undefined;

  return (
    <AiBlockFrame
      proposals={proposals}
      busyId={busyId}
      error={actionError ?? loadError}
      loading={rows === null && !loadError}
      onRetry={loadError ? () => load() : undefined}
      onReject={(id) => act(id, "reject")}
      onConfirm={(id) => act(id, "confirm")}
      chat={chat}
      keepStarter={chatOpen && (!consented || !panelReady)}
      starter={{
        chips,
        value: draft,
        onChange: setDraft,
        onFocus: () => openChat(draft, false),
        onAsk: (q) => openChat(q, true),
        inputRef: starterInput,
      }}
    />
  );
}
