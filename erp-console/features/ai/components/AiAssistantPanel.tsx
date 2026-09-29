"use client";

// Tấm AI NẶNG — chỉ nạp khi `ai_enabled` VÀ đã đồng ý (AiAssistantGate, next/dynamic ssr:false).
// Gồm: kiểm tra máy (RAM/WebGPU/mạng) → tải model (sequential GGUF, % + ETA, tạm dừng/tải tiếp/huỷ,
// cache IndexedDB) → hộp chat.
// DW-14: Chat gọi lệnh qua call + chọn lệnh 2 bước (planCommand -> callCommand).
// DW-19: Thông báo AI đã ghi + nút Hoàn tác đếm ngược tới undo_until.
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
import { fetchCommandIndex, fetchCommandDescriptor } from "../commands/index";
import { planCommand } from "../commands/planner";
import { callCommand } from "../commands/call";
import { undoAiAction } from "../actions/api";
import { useAuth } from "@/features/auth/components/AuthProvider";
import s from "./ai.module.css";

const HIDE_GRACE_MS = 60 * 1000;
const EXAMPLES = ["Còn bao nhiêu cá thu?", "Lô nào sắp tới hạn?", "Có đơn nào đang chờ?"];

type ChatMsg = {
  id: number;
  role: "user" | "ai";
  text: string;
  pending?: boolean;
  undoAction?: {
    actionId: string;
    undoUntil: string;
    commandTitle: string;
    undone?: boolean;
  };
};

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

function UndoCountdownButton({
  actionId,
  undoUntil,
  onSuccess,
}: {
  actionId: string;
  undoUntil: string;
  onSuccess: () => void;
}) {
  const [remaining, setRemaining] = useState<number>(() => {
    return Math.max(0, Math.floor((new Date(undoUntil).getTime() - Date.now()) / 1000));
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      const diff = Math.max(0, Math.floor((new Date(undoUntil).getTime() - Date.now()) / 1000));
      setRemaining(diff);
      if (diff <= 0) clearInterval(timer);
    }, 1000);
    return () => clearInterval(timer);
  }, [undoUntil]);

  const handleUndo = async () => {
    if (!confirm("Bạn có chắc chắn muốn hoàn tác thao tác này?")) return;
    try {
      setSubmitting(true);
      setError(null);
      await undoAiAction(actionId);
      onSuccess();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Hoàn tác thất bại.");
    } finally {
      setSubmitting(false);
    }
  };

  if (remaining <= 0) {
    return <span className="mt-2 block text-xs text-gray-400">Đã hết thời gian có thể hoàn tác.</span>;
  }

  const mm = Math.floor(remaining / 60).toString().padStart(2, "0");
  const ss = (remaining % 60).toString().padStart(2, "0");

  return (
    <div className="mt-2.5 flex flex-col gap-1.5">
      <button
        type="button"
        onClick={handleUndo}
        disabled={submitting}
        className="inline-flex w-fit items-center gap-1.5 rounded-md bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-50"
      >
        <Icon name="undo" />
        <span>{submitting ? "Đang hoàn tác..." : `Hoàn tác (${mm}:${ss})`}</span>
      </button>
      {error && <span className="text-xs text-red-500 font-medium">{error}</span>}
    </div>
  );
}

export function AiAssistantPanel({ status }: { status: AiStatus }) {
  const { me } = useAuth();
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

  // ---- Chat ----
  const finalizePending = useCallback(() => {
    setChat((msgs) => msgs.map((m) => (m.pending ? { ...m, pending: false } : m)));
  }, []);

  const appendAi = useCallback(
    (text: string, undoAction?: ChatMsg["undoAction"]) => {
      setChat((msgs) => {
        const last = msgs[msgs.length - 1];
        if (last && last.pending) {
          return msgs.slice(0, -1).concat({
            ...last,
            text: last.text + text,
            undoAction: undoAction || last.undoAction,
          });
        }
        return msgs.concat({
          id: nextId(),
          role: "ai",
          text,
          pending: true,
          undoAction,
        });
      });
    },
    []
  );

  // DW-14 & DW-19: Chat gọi lệnh qua call + kiểm tra an toàn giá vốn & PII + hoàn tác mức B
  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q) return;
      finalizePending();
      setChatError(null);
      setChat((msgs) => msgs.concat({ id: nextId(), role: "user", text: q }));
      setInput("");

      // DW-14-AC4: Kiểm tra hỏi giá vốn
      const costKeywords = ["giá vốn", "gia von", "lãi lỗ", "lai lo", "cost", "giá mua", "gia mua"];
      const isAskingCost = costKeywords.some((k) => q.toLowerCase().includes(k));
      const canCost = me?.permissions?.includes("inventory.view_costprice") || me?.groups?.includes("chu");

      if (isAskingCost && !canCost) {
        appendAi("Bạn không có quyền xem thông tin giá vốn.");
        finalizePending();
        return;
      }

      try {
        // Tải chỉ mục lệnh
        const indexRes = await fetchCommandIndex();
        // Lập kế hoạch 2 bước
        const plan = await planCommand(q, indexRes.commands, {
          descriptorFetcher: fetchCommandDescriptor,
        });

        if (plan.type === "execute_ready") {
          try {
            const res = await callCommand(plan.command.id, {
              args: plan.args,
              screen: "chat",
            });

            if (res.outcome === "done") {
              if (res.level === "B") {
                // DW-19-AC9: Lệnh ghi thực thi mức B kèm nút Hoàn tác 10 phút
                const undoUntil =
                  res.undo_until || new Date(Date.now() + 10 * 60 * 1000).toISOString();
                appendAi(
                  `AI đã thực hiện thao tác "${plan.command.title}" (Mã việc: ${res.action_id}). Có thể hoàn tác trong vòng 10 phút.`,
                  {
                    actionId: res.action_id,
                    undoUntil,
                    commandTitle: plan.command.title,
                  }
                );
              } else {
                // DW-14-AC1: Mức A - lệnh đọc thành công
                let reply = `Kết quả thực hiện "${plan.command.title}":\n`;
                if (res.result) {
                  if (Array.isArray(res.result.rows)) {
                    reply += `Tìm thấy ${res.result.rows.length} mục:\n`;
                    res.result.rows.forEach((row, i) => {
                      const code = row.batch_id || row.item_code || row.code || row.id || `Mục ${i + 1}`;
                      const qty = row.qty_available !== undefined ? ` (tồn: ${row.qty_available})` : "";
                      const status = row.status ? ` [${row.status}]` : "";
                      reply += `• ${code}${qty}${status}\n`;
                    });
                  } else if (res.result.total !== undefined) {
                    reply += `Tổng số: ${res.result.total}`;
                  } else {
                    reply += "Thao tác hoàn thành.";
                  }
                } else {
                  reply += "Không có dữ liệu trả về.";
                }
                appendAi(reply.trim());
              }
            } else if (res.outcome === "scheduled") {
              // DW-21: Lệnh xếp lịch
              appendAi(
                `AI đã lên lịch thực thi thao tác "${plan.command.title}" (Mã việc: ${res.action_id}). Dự kiến tự thực thi sau thời gian trì hoãn. Bạn có thể vào màn Việc AI để kiểm tra hoặc huỷ lịch.`
              );
            } else if (res.outcome === "proposal") {
              // Mức C - đề xuất nháp
              appendAi(
                `AI đã tạo đề xuất nháp cho thao tác "${plan.command.title}" (mã: ${res.action_id}). Vui lòng vào màn Việc AI để kiểm tra và duyệt.`
              );
            } else {
              appendAi(`Lệnh "${plan.command.title}" đã được ghi nhận.`);
            }
          } catch (callErr: unknown) {
            const errMsg = callErr instanceof Error ? callErr.message : "Thao tác gặp lỗi khi thực thi.";
            appendAi(`Lỗi thực hiện: ${errMsg}`);
          }
          finalizePending();
          return;
        }

        if (plan.type === "form_only") {
          appendAi(
            `Thao tác "${plan.command.title}" cần mở biểu mẫu để điền thông tin chi tiết. Vui lòng mở màn hình liên quan.`
          );
          finalizePending();
          return;
        }

        if (plan.type === "no_match") {
          if (plan.suggestions && plan.suggestions.length > 0) {
            appendAi(
              `${plan.message}\n` + plan.suggestions.map((s) => `• ${s}`).join("\n")
            );
          } else {
            appendAi(plan.message);
          }
          finalizePending();
          return;
        }

        // Fallback: gọi LLMock trò chuyện thông thường
        void askAi(q, { onToken: appendAi })
          .then(() => finalizePending())
          .catch((err: unknown) => {
            if (err instanceof DOMException && err.name === "AbortError") return;
            setChatError(AI_MSG.chatError);
            finalizePending();
          });
      } catch (err: unknown) {
        void askAi(q, { onToken: appendAi })
          .then(() => finalizePending())
          .catch((mErr: unknown) => {
            if (mErr instanceof DOMException && mErr.name === "AbortError") return;
            setChatError(AI_MSG.chatError);
            finalizePending();
          });
      }
    },
    [appendAi, finalizePending, me]
  );

  return (
    <div className={`rr-pane ${s.panel}`} ref={rootRef}>
      <div className={s.head}>
        <h2 className="rr-title">{AI_MSG.title}</h2>
        <span className={`soon-tag ${s.badge}`}>{engine === "llmock" ? AI_MSG.trialBadge : AI_MSG.onDeviceBadge}</span>
      </div>

      {/* ---- Kiểm tra máy ---- */}
      <section className={s.section} aria-label={AI_MSG.capTitle}>
        <h3 className={s.sectionTitle}>{AI_MSG.capTitle}</h3>
        <div className={s.metrics}>
          <span>
            {AI_MSG.ramLabel}:{" "}
            <b className="num">{cap.deviceMemoryGb !== null ? `${cap.deviceMemoryGb} GB` : AI_MSG.unknown}</b>
          </span>
          <span>
            {AI_MSG.webgpuLabel}:{" "}
            <b>{cap.webgpu ? "Có" : "Không"}</b>
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
                <div className={s.mtext}>
                  <p>{m.text}</p>
                  {m.pending && (!m.text || m.text.length === 0) ? <span className={s.think}>{AI_MSG.thinking}</span> : null}
                  {m.undoAction && (
                    m.undoAction.undone ? (
                      <p className="mt-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                        Đã hoàn tác thao tác thành công. Chứng từ liên quan đã chuyển trạng thái Đã huỷ.
                      </p>
                    ) : (
                      <UndoCountdownButton
                        actionId={m.undoAction.actionId}
                        undoUntil={m.undoAction.undoUntil}
                        onSuccess={() => {
                          setChat((msgs) =>
                            msgs.map((item) =>
                              item.id === m.id
                                ? {
                                    ...item,
                                    undoAction: item.undoAction ? { ...item.undoAction, undone: true } : undefined,
                                  }
                                : item
                            )
                          );
                        }}
                      />
                    )
                  )}
                </div>
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
