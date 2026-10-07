import type { HOME_CONFIRMATION_QUEUE, RoleCode } from "@/shared/lib/roles";

// Kiểu dữ liệu module auth — khớp contract S6 (+ phần mở rộng S47 và S46 theo story, BE L6 chưa chốt).

export type GroupCode = RoleCode;

/** Trang mặc định sau đăng nhập. */
export type MeHome = "dashboard" | "my-deliveries" | typeof HOME_CONFIRMATION_QUEUE | "no-role";

export type CodeLabel = { code: string; label: string };

/** GET /api/auth/me/ */
export type Me = {
  id: number;
  username: string;
  display_name: string;
  phone: string;
  groups: string[];
  /** `app_label.codename`, = user.get_all_permissions() */
  permissions: string[];
  can_view_cost: boolean;
  can_view_profit: boolean;
  home: MeHome;
  /** S47 — nhãn tiếng Việt của `groups`. Optional: BE chưa trả thì FE dịch bằng shared/lib/groups.ts. */
  group_labels?: CodeLabel[];
  /** S47 — CHỈ quyền Tầng 2 (Meta.permissions tuỳ biến) kèm nhãn. Optional: BE chưa trả thì màn báo "chưa có". */
  capabilities?: CodeLabel[];
  /**
   * S48 — true: người này còn dùng mật khẩu tạm (Chủ vừa tạo tài khoản / đặt lại mật khẩu). Console chỉ mở màn
   * "Đặt mật khẩu mới"; BE chặn mọi API nghiệp vụ khác bằng 403 `AUTH_MUST_CHANGE_PASSWORD`. Superuser không bị ép.
   * Optional: BE chưa có S48 thì coi như false.
   */
  must_change_password?: boolean;
  /** Duy 08/10 câu 1 — superuser (kể cả không nhóm) vào ERP như Chủ: BE trả `home = "dashboard"`. `groups` vẫn là nhóm thật. */
  is_superuser?: boolean;
  /** W39 — BE báo cờ AI (`settings.AI_ENABLED`). Giao diện AI chỉ hiện khi cờ build bật VÀ giá trị này true (`aiVisible`). */
  ai_features_enabled?: boolean;
};

/** S48 — `code` của 403 khi còn mật khẩu tạm (logic dựa vào code, không dựa vào câu `detail`). */
export const MUST_CHANGE_PASSWORD_CODE = "AUTH_MUST_CHANGE_PASSWORD";

/** D-3 (Duy 08/10) — `code` của 403 khi tài khoản không thuộc nhóm nào và không phải superuser: ERP chặn hẳn ở BE. */
export const NO_ROLE_CODE = "AUTH_NO_ROLE";

/** POST /api/auth/token/ (DRF obtain_auth_token) */
export type TokenResponse = { token: string };

/** POST /api/auth/change-password/ (S46) → 200: token cũ bị xoá, dùng token mới này. */
export type ChangePasswordResponse = { token: string };
