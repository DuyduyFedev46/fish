"use client";

// Cột phải: Ghi chú · Trợ lý · Hoạt động (kế thừa bản HTML cũ).
// ≥1024px là cột cố định; nhỏ hơn là ngăn kéo (Shell điều khiển `open`).
// Nội dung "Trợ lý" (S45, features/assistant) và "Hoạt động" (S8) được truyền vào qua props;
// bỏ trống thì hiện khung "sắp có".
// UI5: tab chỉ chữ (không xuống dòng ở 360px), phím ← → Home End chuyển tab (WAI-ARIA tabs, roving tabindex).

import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";
import { MSG } from "@/shared/lib/messages";

type Pane = "notes" | "ai" | "feed";

const TABS: { key: Pane; label: string }[] = [
  { key: "notes", label: "Ghi chú" },
  { key: "ai", label: "Trợ lý" },
  { key: "feed", label: "Hoạt động" },
];

// Ghi chú ca: lưu cục bộ trên máy (Q19), cùng key với bản HTML cũ để không mất ghi chú đang có.
const NOTES_KEY = "cave_notes";

function Notes() {
  const [text, setText] = useState("");
  const [state, setState] = useState("Tự lưu trên máy này");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      const v = localStorage.getItem(NOTES_KEY);
      if (v != null) setText(v);
    } catch {
      /* bỏ qua */
    }
  }, []);

  const onChange = (v: string) => {
    setText(v);
    setState("Đang lưu…");
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      try {
        localStorage.setItem(NOTES_KEY, v);
        setState("Đã lưu · " + new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }));
      } catch {
        setState(MSG.noteSaveFailed);
      }
    }, 500);
  };

  return (
    <div className="rr-pane notes">
      <label className="rr-title" htmlFor="rr-notes">
        Ghi chú ca trực
      </label>
      <textarea
        id="rr-notes"
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Ghi nhanh việc ngoài luồng: dặn tài xế, hẹn NCC, khách quen…"
      />
      <div className="save" aria-live="polite">
        <Icon name="cloud_done" />
        <span>{state}</span>
      </div>
    </div>
  );
}

/** Tab "Trợ lý" khi chưa nối (S45): nói rõ "sắp có" và trợ lý sẽ trả lời được gì. */
function AssistantSoon() {
  return (
    <div className="rr-pane rr-soon">
      <span className="state-ic">
        <Icon name="auto_awesome" />
      </span>
      <h2 className="state-title">
        Trợ lý vận hành <span className="soon-tag">Sắp có</span>
      </h2>
      <p>Trợ lý đang được nối, sắp có. Khi xong, bạn hỏi về đơn, tồn kho, cận hạn ngay tại đây.</p>
      <p className="rr-examples-h" id="rr-examples-h">
        Ví dụ câu bạn sẽ hỏi được:
      </p>
      <ul className="rr-examples" aria-labelledby="rr-examples-h">
        <li>“Hôm nay còn mấy đơn chờ xử lý?”</li>
        <li>“Lô nào sắp tới hạn?”</li>
      </ul>
    </div>
  );
}

type Props = {
  panelRef?: React.Ref<HTMLElement>;
  open: boolean;
  onClose: () => void;
  assistant?: React.ReactNode;
  activity?: React.ReactNode;
};

export function RightRail({ panelRef, open, onClose, assistant, activity }: Props) {
  const [pane, setPane] = useState<Pane>("notes");
  // Tab chỉ mount khi mở lần đầu (rồi giữ lại) → nội dung tự tải dữ liệu (vd sổ kho) không gọi API khi chưa ai xem.
  const [opened, setOpened] = useState<Record<Pane, boolean>>({ notes: true, ai: false, feed: false });
  const choose = (p: Pane) => {
    setPane(p);
    setOpened((o) => (o[p] ? o : { ...o, [p]: true }));
  };
  const onTabKey = (e: React.KeyboardEvent) => {
    const i = TABS.findIndex((t) => t.key === pane);
    const next =
      e.key === "ArrowRight" ? (i + 1) % TABS.length
      : e.key === "ArrowLeft" ? (i - 1 + TABS.length) % TABS.length
      : e.key === "Home" ? 0
      : e.key === "End" ? TABS.length - 1
      : -1;
    if (next < 0) return;
    e.preventDefault();
    choose(TABS[next].key);
    document.getElementById(`rr-tab-${TABS[next].key}`)?.focus();
  };

  return (
    <aside
      id="rail-right"
      ref={panelRef}
      className={`rail-right${open ? " open" : ""}`}
      aria-label="Ghi chú, trợ lý, hoạt động"
    >
      <div className="rr-head">
        <div className="rr-tabs" role="tablist" aria-label="Cột bên phải" onKeyDown={onTabKey}>
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              id={`rr-tab-${t.key}`}
              className="rr-tab"
              aria-selected={pane === t.key}
              aria-controls={`rr-pane-${t.key}`}
              tabIndex={pane === t.key ? 0 : -1}
              onClick={() => choose(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <button type="button" className="iconbtn rr-close" onClick={onClose} aria-label="Đóng ngăn bên phải">
          <Icon name="close" />
        </button>
      </div>
      <div className="rr-body">
        <div id="rr-pane-notes" role="tabpanel" aria-labelledby="rr-tab-notes" hidden={pane !== "notes"}>
          <Notes />
        </div>
        <div id="rr-pane-ai" role="tabpanel" aria-labelledby="rr-tab-ai" hidden={pane !== "ai"}>
          {assistant ?? <AssistantSoon />}
        </div>
        <div id="rr-pane-feed" role="tabpanel" aria-labelledby="rr-tab-feed" hidden={pane !== "feed"}>
          {opened.feed && activity}
          {!activity && (
            <div className="rr-pane">
              <div className="state">
                <span className="state-ic">
                  <Icon name="history" />
                </span>
                <p>Hoạt động sổ kho sẽ hiện ở đây.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
