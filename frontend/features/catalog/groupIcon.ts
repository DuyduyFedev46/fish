import type { GroupIcon, ItemType } from "@/lib/types";

/**
 * Icon nhóm dùng làm ảnh dự phòng và ô nhóm. FE suy từ slug nhóm (02b §1.10): API không trả icon.
 * `ca*` cá · `tom*` tôm · `muc*` mực · `cua*`/`ghe*` cua ghẹ · BUNDLE hoặc nhóm `combo*` combo · còn lại cá.
 */
export function groupIconOf(slug: string, itemType?: ItemType): GroupIcon {
  if (itemType === "BUNDLE") return "combo";
  const key = slug.toLowerCase();
  if (key.startsWith("combo")) return "combo";
  if (key.startsWith("tom")) return "shrimp";
  if (key.startsWith("muc")) return "squid";
  if (key.startsWith("cua") || key.startsWith("ghe")) return "crab"; // naming: allow - tiền tố slug nhóm hàng trong dữ liệu
  if (key.startsWith("ca")) return "fish";
  return "fish";
}
