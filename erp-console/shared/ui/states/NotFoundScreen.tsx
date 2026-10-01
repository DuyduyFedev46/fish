// 404 trong khung app (UI-RULES §7): "Không tìm thấy trang này" + nút về trang chính (đích do người gọi truyền: `homePath(me)`). app/not-found.tsx bọc trong ConsoleGate
// nên có menu; người chưa đăng nhập được chuyển về trang đăng nhập.
import Link from "next/link";
import { Icon } from "../Icon";
import { homeLabel } from "@/shared/lib/nav";

export function NotFoundScreen({ homeHref = "/overview/" }: { homeHref?: string }) {
  return (
    <div className="page-state">
      <span className="state-ic">
        <Icon name="link_off" />
      </span>
      <h2 className="state-title">Không tìm thấy trang này</h2>
      <p>Đường dẫn không đúng hoặc trang đã được chuyển.</p>
      <div className="page-state-actions">
        <Link href={homeHref} className="btn primary">
          {homeLabel(homeHref)}
        </Link>
      </div>
    </div>
  );
}
