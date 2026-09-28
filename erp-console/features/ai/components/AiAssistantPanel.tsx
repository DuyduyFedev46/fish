"use client";

// Tấm AI NẶNG — chỉ nạp khi `ai_enabled` VÀ đã đồng ý (AiAssistantGate, next/dynamic ssr:false).
// Gồm: kiểm tra máy (RAM/WebGPU/mạng) → tải model (sequential GGUF, % + ETA, tạm dừng/tải tiếp/huỷ,
// cache IndexedDB) → hộp chat. Lô 1–2 chat chạy LLMock (dữ liệu giả, không đọc sổ sách thật).
// Vòng đời worker (C.2 dòng 3): ẩn tab 60s → shutdown("close"); unmount (đăng xuất/tắt AI) →
// shutdown("unmount"); nhàn 10 phút → worker tự "idle". Suy luận KHÔNG gọi mạng (S08-AC5),
// KHÔNG log prompt (S08-AC8).

import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorBox } from "@/shared/ui/StateBox";
import { Icon } from "@/shared/ui/Icon";
import { AI_MSG } from "../messages";
import type { AiStatus } from "../types";
import { canDownloadModel, detectAiCapability, type AiCapability, type DownloadVerdict } from "../runtime/feature-detect";
import { getCachedModel, putCachedModel, removeCachedModel } from "../runtime/model-store";
import { GgufDownloader, type DownloadState } from "../runtime/model-downloader";
import { askAi, selectEngineName, setRuntimeModelUrl, shutdownRuntime } from "../runtime/engine";
import s from "./ai.module.css";

const HIDE_GRACE_MS = 60 * 1000;
const EXAMPLES = ["Còn bao nhiêu cá thu?", "Lô nào sắp tới hạn?", "Có đơn nào đang chờ?"];

type ChatMsg = { id: number; role: "user" | "ai"; text: string; pending?: boolean };

let msgSeq = 0;
const nextId = () => ++msgSeq;

function fmtBytes(n: number): string {
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function fmtEta(sec: number): string {
  if (sec < 60) return `${sec} giây`;
  return `${Math.round(sec / 60)} phút`;
}

function verdictNotice(v: DownloadVerdict): string | null {
  if (v.ok) return null;
  switch (v.reason) {
    case "ios":
      return AI_MSG.unsupportedIos;
    case "low_ram":
      return `${AI_MSG.lowRamTitle}. ${AI_MSG.lowRamBody}`;
    case "ram_unknown":
      return AI_MSG.ramUnknownBody;
    case "cellular":
      return AI_MSG.needWifi;
    case "network_unknown":
      return AI_MSG.networkUnknown;
    case "no_webgpu":
      return "Máy này chưa bật WebGPU — model thật cần WebGPU để chạy. Ở chế độ thử vẫn thử được.";
    default:
      return null;
  }
}

export function AiAssistantPanel({ status }: { status: AiStatus }) {
  const engine = selectEngineName();
  const [cap, setCap] = useState<AiCapability>(() => detectAiCapability());
  const [cached, setCached] = useState<boolean | null>(null);
  const [dl, setDl] = useState<DownloadState | null>(null);
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const rootRef = useRef<HTMLDivElement | null>(null);
  const downloaderRef = useRef<GgufDownloader | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const verdict = canDownloadModel(cap);
  const block = verdict.ok ? null : verdict.reason;
  const modelUrl = status.model?.gguf_url ?? null;

  // ---- Vòng đời worker: ẩn tab 60s → dọn; unmount → dọn ----
  useEffect(() => {
    const el = rootRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver((entries) => {
      const visible = entries.some((en) => en.isIntersecting);
      if (hideTimer.current) {
        clearTimeout(hideTimer.current);
        hideTimer.current = null;
      }
      if (!visible) hideTimer.current = setTimeout(() => shutdownRuntime("close"), HIDE_GRACE_MS);
    });
    io.observe(el);
    return () => {
      io.disconnect();
      if (hideTimer.current) clearTimeout(hideTimer.current);
      downloaderRef.current?.cancel();
      shutdownRuntime("unmount");
    };
  }, []);

  // ---- Cache model: có bản cũ → dùng luôn; bản hỏng → xoá (S08-AC4) ----
  useEffect(() => {
    let alive = true;
    if (!modelUrl) {
      setCached(false);
      return;
    }
    setCached(null);
    void getCachedModel(modelUrl).then(async (rec) => {
      if (!alive) return;
      if (rec) {
        setRuntimeModelUrl(modelUrl);
        setCached(true);
      } else {
        await removeCachedModel(modelUrl); // dọn bản hỏng nếu có
        if (alive) setCached(false);
      }
    });
    return () => {
      alive = false;
    };
  }, [modelUrl]);

  // ---- Tải model ----
  const startDownload = useCallback(() => {
    if (!modelUrl) return;
    const downloader = new GgufDownloader(modelUrl, {
      onState: setDl,
      onDone: async (blob, meta) => {
        const ok = await putCachedModel({ url: modelUrl, bytes: meta.bytes, fetchedAt: Date.now(), etag: meta.etag, blob });
        if (ok) {
          setRuntimeModelUrl(modelUrl);
          setCached(true);
        }
      },
    });
    downloaderRef.current = downloader;
    downloader.start();
  }, [modelUrl]);

  const recheck = useCallback(() => setCap(detectAiCapability()), []);

  // ---- Chat (LLMock lô 1–2; H4: gửi câu mới huỷ câu cũ) ----
  const finalizePending = useCallback(() => {
    setChat((msgs) => msgs.map((m) => (m.pending ? { ...m, pending: false } : m)));
  }, []);

  const appendAi = useCallback((text: string) => {
    setChat((msgs) => {
      const last = msgs[msgs.length - 1];
      if (last && last.pending) return msgs.slice(0, -1).concat({ ...last, text: last.text + text });
      return msgs.concat({ id: nextId(), role: "ai", text, pending: true });
    });
  }, []);

  const send = useCallback(
    (text: string) => {
      const q = text.trim();
      if (!q) return;
      finalizePending(); // câu cũ đang nghĩ → giữ phần đã có, bỏ trạng thái "đang nghĩ"
      setChatError(null);
      setChat((msgs) => msgs.concat({ id: nextId(), role: "user", text: q }));
      setInput("");
      void askAi(q, { onToken: appendAi })
        .then(() => finalizePending())
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return; // bị thay bằng câu mới — không phải lỗi
          setChatError(AI_MSG.chatError);
          finalizePending();
        });
    },
    [appendAi, finalizePending],
  );

  // H4: không chặn ô nhập khi đang nghĩ — gửi câu mới sẽ huỷ câu cũ.

  return (
    <div className={`rr-pane ${s.panel}`} ref={rootRef}>
      <div className={s.head}>
        <h2 className="rr-title">{AI_MSG.title}</h2>
        <span className={`soon-tag ${s.badge}`}>{engine === "llmock" ? AI_MSG.trialBadge : AI_MSG.onDeviceBadge}</span>
      </div>

      {/* ---- Kiểm tra máy ---- */}
      <section className={s.section} aria-label={AI_MSG.capTitle}>
        <h3 className={s.sectionTitle}>{AI_MSG.capTitle}</h3>
        <div className={s.capRow}>
          <span>
            {AI_MSG.ramLabel}:{" "}
            <b className="num">{cap.deviceMemoryGb !== null ? `${cap.deviceMemoryGb} GB` : AI_MSG.unknown}</b>
          </span>
          <span>
            {AI_MSG.webgpuLabel}: <b className="num">{cap.webgpu ? "Có" : "Không"}</b>
          </span>
          <span>
            {AI_MSG.wifiLabel}:{" "}
            <b className="num">{cap.network === "wifi" ? AI_MSG.wifi : cap.network === "cellular" ? AI_MSG.cellular : AI_MSG.unknown}</b>
          </span>
        </div>
      </section>

      {/* ---- Model ---- */}
      <section className={s.section} aria-label={AI_MSG.downloadTitle}>
        <h3 className={s.sectionTitle}>{AI_MSG.downloadTitle}</h3>
        {!modelUrl ? (
          <p className={s.notice}>{AI_MSG.modelNotPicked}</p>
        ) : cached === true ? (
          <p className={s.notice}>
            <Icon name="check_circle" />
            <span>{AI_MSG.downloaded}</span>
          </p>
        ) : dl ? (
          <div
            className={s.dlBar}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={dl.percent}
            aria-label={AI_MSG.downloading}
          >
            <div className={s.dlFill} style={{ width: `${dl.percent}%` }} />
          </div>
        ) : null}
        {!modelUrl ? null : cached === true ? null : dl ? (
          <>
            <p className={s.dlMeta}>
              {dl.phase === "downloading"
                ? `${dl.percent}% · ${fmtBytes(dl.receivedBytes)}${dl.totalBytes ? ` / ${fmtBytes(dl.totalBytes)}` : ""} · ${fmtBytes(dl.bytesPerSec)}/s${
                    dl.etaSeconds ? ` · còn ${fmtEta(dl.etaSeconds)}` : ""
                  }`
                : dl.phase === "paused"
                  ? AI_MSG.downloadPausedByNetwork
                  : dl.phase === "error"
                    ? AI_MSG.downloadFailed
                    : ""}
            </p>
            <div className={s.dlBtns}>
              {dl.phase === "downloading" ? (
                <button type="button" className="btn" onClick={() => downloaderRef.current?.pause()}>
                  {AI_MSG.pause}
                </button>
              ) : (
                <button type="button" className="btn primary" onClick={() => downloaderRef.current?.start()}>
                  {AI_MSG.resume}
                </button>
              )}
              <button type="button" className="btn" onClick={() => { downloaderRef.current?.cancel(); setDl(null); }}>
                {AI_MSG.cancel}
              </button>
            </div>
          </>
        ) : verdict.ok || (block === "no_webgpu" && engine === "llmock") || block === "ram_unknown" ? (
          <div className={s.dlCard}>
            <p className={s.dlHint}>
              {AI_MSG.downloadHint}
              {verdictNotice(verdict) ? ` ${verdictNotice(verdict)}` : ""}
            </p>
            <button type="button" className="btn primary" onClick={startDownload}>
              {block === "ram_unknown" ? AI_MSG.tryAnyway : AI_MSG.download}
            </button>
          </div>
        ) : (
          <div className={s.dlCard}>
            <p className={s.dlHint}>{verdictNotice(verdict)}</p>
            {(block === "cellular" || block === "network_unknown") && (
              <button type="button" className="btn" onClick={recheck}>
                <Icon name="refresh" />
                <span>{AI_MSG.checkAgain}</span>
              </button>
            )}
          </div>
        )}
      </section>

      {/* ---- Chat ---- */}
      <section className={s.section} aria-label={AI_MSG.chatLabel}>
        <h3 className={s.sectionTitle}>{AI_MSG.chatLabel}</h3>
        <p className={s.dlHint}>{AI_MSG.chatHint}</p>
        <div className={s.msgs} aria-live="polite">
          {chat.length === 0 ? (
            <div className={s.empty}>
              <p className={s.emptyTitle}>{AI_MSG.emptyChatTitle}</p>
              <p className={s.dlHint}>{AI_MSG.emptyChatBody}</p>
            </div>
          ) : (
            chat.map((m) => (
              <div key={m.id} className={`${s.msg} ${m.role === "user" ? s.user : s.ai}`}>
                {m.role === "ai" ? <span className={s.mlabel}>{AI_MSG.aiLabel}</span> : null}
                <span className={s.mtext}>
                  {m.text}
                  {m.pending && (!m.text || m.text.length === 0) ? <span className={s.think}>{AI_MSG.thinking}</span> : null}
                </span>
              </div>
            ))
          )}
        </div>
        {chatError ? <ErrorBox message={chatError} /> : null}
        <div className={s.examples}>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" className={s.chip} onClick={() => send(ex)}>
              {ex}
            </button>
          ))}
        </div>
        <form
          className={s.inputRow}
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            className={s.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={AI_MSG.chatPlaceholder}
            aria-label={AI_MSG.chatPlaceholder}
            maxLength={2000}
          />
          <button type="submit" className="btn primary" disabled={!input.trim()} aria-label={AI_MSG.send}>
            <Icon name="send" />
          </button>
        </form>
      </section>
    </div>
  );
}
