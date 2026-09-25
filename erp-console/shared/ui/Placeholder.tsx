// Khung chờ cho màn chưa làm: lấy tiêu đề/mô tả/story từ bảng menu (shared/lib/nav.ts).
// Module làm xong thì page.tsx render màn của module thay cho <Placeholder>.
import { Empty } from "./StateBox";
import { navItem, type ViewKey } from "@/shared/lib/nav";

export function Placeholder({ view }: { view: ViewKey }) {
  const item = navItem(view);
  return (
    <Empty icon={item.icon} title={item.label}>
      {item.summary} <span className="muted">(sắp có · {item.plannedIn})</span>
    </Empty>
  );
}
