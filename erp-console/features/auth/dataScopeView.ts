// PV-14: dựng các dòng của khối "Dữ liệu bạn xem được" ở màn Tài khoản từ `me.data_scopes`. Hàm thuần, không React.
// Chữ phụ: có nhóm → "theo nhóm {nhãn}"; không nhóm, giá trị khác "none", không phải superuser → "theo quyền gán riêng"; "none" → mờ, không chữ phụ.
import { groupLabel } from "@/shared/lib/groups";
import type { Me } from "./types";

export type DataScopeLine = {
  key: string;
  label: string;
  valueLabel: string;
  /** Chữ phụ; null khi không có. */
  note: string | null;
  /** true: dòng "Không xem" → vẽ mờ. */
  muted: boolean;
};

export type DataScopeView =
  | { state: "missing" }
  | { state: "ok"; superuser: boolean; lines: DataScopeLine[] };

export const DATA_SCOPE_MSG = {
  title: "Dữ liệu bạn xem được",
  intro: "Phạm vi do Chủ vựa đặt cho nhóm của bạn. Chỉ để xem, không đổi ở đây.",
  missing: "Chưa có thông tin phạm vi dữ liệu.",
  superuser: "Toàn bộ (quản trị hệ thống)",
  viaOwn: "theo quyền gán riêng",
  via: (label: string) => `theo nhóm ${label}`,
} as const;

export function dataScopeView(me: Pick<Me, "data_scopes" | "group_labels" | "is_superuser">): DataScopeView {
  const rows = me.data_scopes;
  if (!rows || rows.length === 0) return { state: "missing" };
  const superuser = me.is_superuser === true;
  const labelOf = (code: string) => me.group_labels?.find((g) => g.code === code)?.label ?? groupLabel(code);
  return {
    state: "ok",
    superuser,
    lines: rows.map((r) => {
      const none = r.value === "none";
      let note: string | null = null;
      if (!none) {
        if (r.via_group) note = DATA_SCOPE_MSG.via(labelOf(r.via_group));
        else if (!superuser) note = DATA_SCOPE_MSG.viaOwn;
      }
      return { key: r.key, label: r.label, valueLabel: r.value_label, note, muted: none };
    }),
  };
}
