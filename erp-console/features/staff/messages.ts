// Thông báo của màn Nhân viên (kết quả thao tác, trạng thái) — MỘT chỗ, component không viết chuỗi tại chỗ.
// Lỗi nghiệp vụ KHÔNG ở đây: UI hiện nguyên văn `detail` BE trả (BR-PQ-08/17/18, BR-GH-08, BR-PQ-01).

export const STAFF_MSG = {
  groupsChanged: (who: string, added: string, removed: string) => {
    const parts = [added ? `thêm ${added}` : "", removed ? `bỏ ${removed}` : ""].filter(Boolean);
    return `Đã đổi nhóm của ${who}${parts.length ? `: ${parts.join("; ")}` : " (không có thay đổi)"}.`;
  },
  profileSaved: (username: string) => `Đã lưu hồ sơ của ${username}.`,
  passwordReset: (who: string) => `Đã đặt lại mật khẩu cho ${who}.`,
  deactivated: (who: string) => `Đã cho ${who} nghỉ. Người này không còn đăng nhập được.`,
  reactivated: (who: string) => `Đã cho ${who} làm lại.`,
  created: (username: string) => `Đã tạo tài khoản ${username}.`,
  draftRestored: "Đã mở lại nội dung đang gõ dở. Mật khẩu không được lưu trong nháp — nhập lại mật khẩu.",
  noActions: "Bạn không có thao tác nào trên tài khoản này.",
  neverLoggedIn: "Chưa đăng nhập",
  statusActive: "Đang làm",
  statusInactive: "Đã nghỉ",
} as const;
