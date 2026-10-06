// Khung TĨNH của khối "Trợ lý AI" ở cột phải trang chi tiết (UI-RULES §5.5): ai/giờ nào đề xuất, việc đề xuất,
// thay đổi (trước → sau), nút Từ chối / Đồng ý, rồi khe `chat` (chip câu hỏi nhanh + ô chat do trợ lý nạp động).
// Chỉ VẼ, nhận props — không gọi API, không import runtime AI (để chunk màn nghiệp vụ không chứa code AI, BR-AI-17).
// Dữ liệu thật do features/ai/components/AiDocBlock nạp. Không bao giờ truyền dữ liệu cá nhân của khách vào đây.
import { Icon } from "../Icon";
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import { dateTime } from "@/shared/lib/format";
import { Section } from "./Section";
import s from "./AiBlockFrame.module.css";

export type AiChange = { label: string; before?: string; after: string };

export type AiProposalView = {
  id: string;
  /** "AI của Lộc". */
  proposedBy: string;
  proposedAt: string;
  /** Việc đề xuất, vd "Xác nhận phiếu nhập hàng". */
  title: string;
  changes: AiChange[];
  /** PENDING = chờ duyệt (Từ chối / Đồng ý); ESCALATED = được nhờ chuyển, chỉ hiện thông tin. */
  state: "PENDING" | "ESCALATED";
  /** Nhóm nhận việc khi ESCALATED. */
  assigneeGroup?: string | null;
  /** Còn phải xem thêm n giây mới được Đồng ý (BR-AI-14); 0 = đã được. */
  waitSeconds?: number;
  /** Chưa mở được chi tiết đề xuất (BR-AI-14 cần chi tiết): khoá Đồng ý, không đếm ngược; Từ chối vẫn dùng được. */
  blocked?: boolean;
};

/** Khung hỏi nhanh tĩnh: chip + ô + nút gửi. Chưa nạp gì; chạm vào mới nhờ cha nạp trợ lý. */
export type AiStarter = {
  chips: string[];
  value: string;
  onChange: (next: string) => void;
  /** Ô được focus: cha nạp trợ lý (giữ chữ đã gõ). */
  onFocus: () => void;
  /** Bấm chip hoặc gửi: cha nạp trợ lý và chuyển câu hỏi sang. */
  onAsk: (question: string) => void;
  /** Cha giữ ref ô nhập để trả focus về ô sau khi đồng ý dùng trợ lý (phím gõ tiếp không rơi về body). */
  inputRef?: React.Ref<HTMLInputElement>;
};

type Props = {
  proposals: AiProposalView[];
  /** Id đề xuất đang gửi (khoá nút của đề xuất đó). */
  busyId?: string | null;
  error?: string | null;
  onReject: (id: string) => void;
  onConfirm: (id: string) => void;
  /** Khe chat khi trợ lý đã được mở (panel nạp động / thẻ đồng ý). Có `chat` thì khung hỏi nhanh `starter` nhường chỗ. */
  chat?: React.ReactNode;
  /** Khung hỏi nhanh tĩnh hiện sẵn khi chưa có `chat` (kể cả khi không có đề xuất nào). */
  starter?: AiStarter;
  /** true = giữ khung hỏi nhanh cả khi đã có `chat` (panel còn đang nạp / chưa đồng ý): ô gõ không biến mất, phím gõ không rơi mất, focus không về body (B6, L9). */
  keepStarter?: boolean;
  /** Đang tải đề xuất. */
  loading?: boolean;
  onRetry?: () => void;
};

export function AiBlockFrame({ proposals, busyId = null, error, onReject, onConfirm, chat, starter, keepStarter = false, loading = false, onRetry }: Props) {
  if (!AI_FEATURES_ENABLED) return null; // SR-HIDE-AI-01
  return (
    <Section
      aria-label="Trợ lý AI"
      data-ai-block
      title={
        <>
          <Icon name="auto_awesome" />
          <span>Trợ lý AI</span>
        </>
      }
      action={proposals.length > 0 ? `${proposals.length} đề xuất` : undefined}
    >

      {loading && (
        <p className={s.note} role="status">
          <Icon name="progress_activity" className="spin" /> Đang kiểm tra đề xuất…
        </p>
      )}
      {error && (
        <div className={s.err} role="alert">
          <span>{error}</span>
          {onRetry && (
            <button type="button" className="btn" onClick={onRetry}>
              Thử lại
            </button>
          )}
        </div>
      )}
      {!loading && !error && proposals.length === 0 && <p className={s.note}>Chưa có đề xuất nào cho chứng từ này.</p>}

      {proposals.map((p) => {
        const busy = busyId === p.id;
        const waiting = (p.waitSeconds ?? 0) > 0;
        const confirmOff = busy || waiting || Boolean(p.blocked);
        return (
          <article key={p.id} className={s.card} data-proposal={p.id} data-state={p.state}>
            <p className={s.what}>{p.title}</p>
            <p className={s.by}>
              <span className={s.ai}>AI</span>
              <span>
                {p.proposedBy} · <time className="num" dateTime={p.proposedAt}>{dateTime(p.proposedAt)}</time>
              </span>
            </p>
            {p.changes.length > 0 && (
              <dl className={s.changes}>
                {p.changes.map((c) => (
                  <div key={c.label} className={s.change}>
                    <dt>{c.label}</dt>
                    <dd className="num">
                      {c.before !== undefined && (
                        <>
                          <span className={s.before}>{c.before}</span>
                          <Icon name="arrow_forward" />
                        </>
                      )}
                      <span>{c.after}</span>
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            {p.state === "PENDING" ? (
              <div className={s.actions}>
                <button type="button" className="btn" onClick={() => onReject(p.id)} disabled={busy}>
                  Từ chối
                </button>
                <button type="button" className="btn primary" onClick={() => onConfirm(p.id)} disabled={confirmOff} aria-disabled={confirmOff}>
                  {busy ? "Đang gửi…" : waiting ? `Đồng ý (${p.waitSeconds})` : "Đồng ý"}
                </button>
              </div>
            ) : (
              <p className={s.escalated}>
                <Icon name="forward_to_inbox" />
                <span>Đã nhờ nhóm {p.assigneeGroup || "có thẩm quyền"} xử lý.</span>
              </p>
            )}
          </article>
        );
      })}

      {/* Starter chỉ có MỘT vị trí cố định (con thứ nhất), `chat` ở vị trí kế: chat xuất hiện/biến mất không làm React dựng lại ô nhập. */}
      {starter && (!chat || keepStarter) ? <Starter {...starter} /> : null}
      {chat}
    </Section>
  );
}

function Starter({ chips, value, onChange, onFocus, onAsk, inputRef }: AiStarter) {
  return (
    <div className={s.starter} data-ai-starter>
      {chips.length > 0 && (
        <div className={s.chips}>
          {chips.map((c) => (
            <button key={c} type="button" className={s.chip} onClick={() => onAsk(c)}>
              {c}
            </button>
          ))}
        </div>
      )}
      <form
        className={s.askRow}
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim()) onAsk(value);
        }}
      >
        <input
          ref={inputRef}
          className={s.ask}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          placeholder="Hỏi AI về chứng từ này…"
          aria-label="Hỏi AI về chứng từ này"
          maxLength={2000}
          autoComplete="off"
        />
        <button type="submit" className="btn primary" disabled={!value.trim()} aria-label="Gửi câu hỏi">
          <Icon name="send" />
        </button>
      </form>
    </div>
  );
}
