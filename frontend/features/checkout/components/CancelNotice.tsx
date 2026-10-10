import Link from "next/link";
import Banner from "@/components/ui/Banner";
import { contactTarget } from "@/components/shopLinks";
import { validHotline } from "@/lib/phone";
import type { CancelNotice as CancelNoticeData } from "@/lib/types";
import s from "./CancelNotice.module.css";

export interface CancelNoticeProps {
  notice: CancelNoticeData;
  /** Hotline của site-info, dùng khi thông báo không có số hợp lệ. */
  fallbackHotline?: string;
  /** full: đơn đã huỷ (E2). partial: một phần đơn không giao được (E5). */
  variant: "full" | "partial";
}

/** Đường dẫn nội bộ an toàn cho link chính sách; giá trị lạ thì dùng đường mặc định. */
function policyHref(url: string): string {
  return url.startsWith("/") && !url.startsWith("//") ? url : "/pages/?slug=doi-tra#xu-ly-tien";  // naming: allow - slug trang CMS (dữ liệu)
}

/**
 * Thông báo đơn huỷ sau khi khách đã trả tiền (BR-HT-12, E2/E5). Câu bản A do máy chủ dựng (`message`: thời hạn đọc từ cấu hình,
 * số tiền là phần bị huỷ); FE thêm hotline và link tới mục chính sách. KHÔNG hiện tiến độ phiếu hoàn, KHÔNG ghi chú tự do của nhân viên.
 */
export default function CancelNotice({ notice, fallbackHotline, variant }: CancelNoticeProps) {
  const hotline = validHotline(notice.hotline) ?? fallbackHotline;
  const call = hotline ? contactTarget(hotline) : null;
  const body = (
    <>
      <p className={s.message}>{notice.message}</p>
      {hotline && call ? (
        <p className={s.message}>
          Cần gấp, bạn gọi <a href={call}>{hotline}</a>.
        </p>
      ) : null}
      <Link href={policyHref(notice.policy_url)} className={s.link}>
        Xem cách Cá Về trả lại tiền
      </Link>
    </>
  );

  if (variant === "partial") {
    return (
      <Banner tone="warn" title={notice.reason_label}>
        {body}
      </Banner>
    );
  }
  return (
    <section className={s.box} aria-labelledby="cancel-notice-title">
      <p className={s.reason}>
        <span className={s.reasonLabel}>Lý do</span>
        <span className={s.reasonValue}>{notice.reason_label}</span>
      </p>
      <h2 id="cancel-notice-title" className={s.title}>
        Cá Về sẽ gọi cho bạn
      </h2>
      {body}
    </section>
  );
}
