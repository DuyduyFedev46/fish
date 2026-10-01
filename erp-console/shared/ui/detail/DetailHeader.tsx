// Header trang chi tiết (UI-RULES §5.1): "← tên danh sách" · tiêu đề (mã mono nếu là chứng từ) · chip trạng thái ·
// bên phải: nút thao tác chính rồi nút "…". KHÔNG có dòng xám dưới tiêu đề (thông tin đó nằm ở phần Thông tin).
import Link from "next/link";
import { Icon } from "../Icon";
import { MoreMenu, type MoreMenuItem } from "./MoreMenu";
import s from "./DetailHeader.module.css";

type Props = {
  back: { href: string; label: string };
  title: string;
  /** Tiêu đề là mã chứng từ → chữ mono. */
  mono?: boolean;
  /** Chip trạng thái (<Chip …/>). */
  status?: React.ReactNode;
  /** Nút thao tác chính (đã dựng sẵn, vd <button className="btn primary">). */
  primary?: React.ReactNode;
  /** Mục của menu "…". Rỗng → không vẽ nút "…". */
  more?: MoreMenuItem[];
};

export function DetailHeader({ back, title, mono = false, status, primary, more = [] }: Props) {
  return (
    <header className={s.head}>
      <Link href={back.href} className={s.back}>
        <Icon name="arrow_back" />
        <span>{back.label}</span>
      </Link>
      <div className={s.row}>
        <div className={s.titleWrap}>
          <h2 className={`${s.title} ${mono ? s.mono : ""}`}>{title}</h2>
          {status}
        </div>
        <div className={s.actions}>
          {primary}
          <MoreMenu items={more} />
        </div>
      </div>
    </header>
  );
}
