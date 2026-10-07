// Chữ của màn Nhật ký hoạt động (ED-41 / W3f): MỘT chỗ, component không viết chuỗi tại chỗ.

export const AUDIT_MSG = {
  caption: "Nhật ký hoạt động, mới nhất trước",
  noun: "dòng nhật ký",
  kindLabel: "Lọc theo loại người làm",
  actionLabel: "Lọc theo thao tác",
  allActions: "Mọi thao tác",
  actorSelectLabel: "Lọc theo người làm",
  allActors: "Mọi người",
  searchLabel: "Tìm theo mã chứng từ",
  searchPlaceholder: "Tìm mã chứng từ…",
  shown: (n: number, total: number) => `Đang hiện ${n} / ${total} dòng`,

  colTime: "Giờ",
  colActor: "Người làm",
  colApprover: "Người duyệt",
  colAction: "Thao tác",
  colObject: "Chứng từ",
  colNote: "Ghi chú",
  colChanges: "Thay đổi",
  colProposal: "Đề xuất",

  aiTag: "AI",
  noValue: "—",
  system: "Hệ thống",

  emptyTitle: "Chưa có dòng nhật ký nào",
  emptyHint: "Mọi thao tác trên hệ thống sẽ được ghi lại và hiện ở đây.",
  emptyFiltered: "Không có dòng nào khớp bộ lọc",
  emptyFilteredHint: "Thử bỏ bớt bộ lọc hoặc chọn thao tác khác.",
  loadMore: "Tải thêm",
  loadingMore: "Đang tải…",
  loadMoreFailed: "Không tải thêm được. Thử lại.",
  retry: "Thử lại",
  filterError: "Bộ lọc chưa dùng được. Sửa lại rồi thử.",
  readOnly: "Nhật ký chỉ để xem: không sửa, không xoá.",
} as const;
