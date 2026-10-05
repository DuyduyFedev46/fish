// Khung trang chi tiết (UI-RULES §5, 02b §2.3): cột trái = StatusPath, InfoGrid, bảng con; cột phải = khe `aiSlot` rồi `timeline`.
// `aiSlot` bỏ trống → KHÔNG vẽ khối AI (trang khách hàng không có Trợ lý AI). Mobile = một cột: trái → AI → dòng thời gian.
// Chỉ là bố cục: dữ liệu, trạng thái tải/lỗi do màn truyền vào. `banner` = ConflictBanner / FormAlert dưới header.
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import s from "./DetailPage.module.css";

type Props = {
  header: React.ReactNode;
  banner?: React.ReactNode;
  /** Cột trái. */
  children: React.ReactNode;
  /** Khối Trợ lý AI (page ghép <AiDocBlockGate/> vào đây). Bỏ trống = không có khối AI. */
  aiSlot?: React.ReactNode;
  /** Dòng thời gian (<Timeline/>). */
  timeline?: React.ReactNode;
  id?: string;
};

export function DetailPage({ header, banner, children, aiSlot: aiSlotProp, timeline, id }: Props) {
  // Cờ AI tắt (SR-HIDE-AI-01): bỏ khe AI, cột phải chỉ còn dòng thời gian, không để khung rỗng.
  const aiSlot = AI_FEATURES_ENABLED ? aiSlotProp : null;
  const hasRight = Boolean(aiSlot) || Boolean(timeline);
  return (
    <div className={s.page} id={id}>
      {header}
      {banner}
      <div className={`${s.cols} ${hasRight ? s.two : ""}`}>
        <div className={s.left}>{children}</div>
        {hasRight && (
          <aside className={s.right} aria-label="Trợ lý và lịch sử">
            {aiSlot}
            {timeline}
          </aside>
        )}
      </div>
    </div>
  );
}
