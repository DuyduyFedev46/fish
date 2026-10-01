// Không có quyền (UI-RULES §7): vào thẳng URL của màn mình không được xem → màn này, KHÔNG mount màn đó nên không
// có request API nào bị gọi (S7-AC3). Backend vẫn là lớp chặn thật.
import Link from "next/link";
import { Icon } from "../Icon";
import { homeLabel } from "@/shared/lib/nav";
import { MSG } from "@/shared/lib/messages";

export function NoPermission({ homeHref = "/overview/" }: { homeHref?: string }) {
  return (
    <div className="page-state">
      <span className="state-ic">
        <Icon name="lock" />
      </span>
      <h2 className="state-title">{MSG.noViewPermission}</h2>
      <p>{MSG.noViewPermissionHint}</p>
      <div className="page-state-actions">
        <Link href={homeHref} className="btn">
          {homeLabel(homeHref)}
        </Link>
      </div>
    </div>
  );
}
