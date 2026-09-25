// Câu FE tự sinh của module orders (S10, S11). Lỗi nghiệp vụ của BE (BR-TT-08…) KHÔNG nằm ở đây: UI hiện nguyên văn
// `detail` BE trả. Quy ước: shared/lib/messages.ts.

import { vnd } from "@/shared/lib/format";

export const ORDERS_MSG = {
  // ---- Danh sách ----
  searchPlaceholder: "Tìm mã đơn, tên khách hoặc SĐT…",
  emptyTitle: "Chưa có đơn nào",
  emptyHint: "Đơn khách đặt trên Shop sẽ hiện ở đây. Bấm làm mới để kiểm tra đơn vừa vào.",
  noMatchTitle: "Không có đơn khớp bộ lọc",
  noMatchHint: "Thử từ khoá khác, đổi trạng thái hoặc khoảng ngày, hay bỏ lọc để xem mọi đơn.",
  shown: (n: number, total: number) => (n >= total ? `${total} đơn` : `Đang hiện ${n} / ${total} đơn`),
  loadMore: "Tải thêm đơn",
  loadingMore: "Đang tải thêm…",
  loadMoreFailed: "Không tải thêm được.",
  refreshFailed: "Không làm mới được, đang hiện danh sách lần tải trước.",
  needsAttention: "Cần chú ý",
  dateRangeInvalid: "Ngày bắt đầu đang sau ngày kết thúc — sửa lại một trong hai ô.",

  // ---- Chi tiết ----
  detailLoading: "Đang tải chi tiết đơn…",
  reservedLeft: "Giữ chỗ còn",
  reservedOver: "Đã hết giờ giữ chỗ",
  reservedHint: "Khách chưa trả tiền trong thời gian này thì hệ thống tự huỷ đơn và nhả hàng.",
  noPayments: "Chưa có giao dịch nào.",
  noDelivery: "Chưa có phiếu giao.",
  noRefunds: "Không có phiếu hoàn.",
  noAllocations: "Chưa phân bổ lô.",
  noAddress: "Chưa có địa chỉ",
  noInvoice: "Chưa có hoá đơn",
  unassigned: "Chưa gán người giao",
  failedAttempts: (n: number) => `${n} lần giao thất bại`,
  timelineDerived: "Ghép tạm từ các mốc giờ của đơn, thanh toán và hoá đơn (máy chủ chưa trả dòng thời gian).",
  system: "Hệ thống",
  tlCreated: "Khách đặt đơn",
  tlPayment: (amount: string) => `Nhận ${vnd(amount)}`,
  tlInvoice: (code: string) => `Xuất hoá đơn ${code}`,

  // ---- S11: xác nhận đã nhận tiền ----
  confirmAction: "Xác nhận đã nhận tiền",
  confirmTitle: (code: string) => `Xác nhận đã nhận tiền · ${code}`,
  confirmQuestion: (amount: string, code: string) => `Xác nhận đã nhận ${vnd(amount)} cho đơn ${code}?`,
  txnLabel: "Mã giao dịch ngân hàng",
  txnHelp: "Chép từ tin nhắn hoặc sao kê ngân hàng, vd FT2626712345. Mỗi mã chỉ được ghi một lần.",
  txnMissing: "Nhập mã giao dịch ngân hàng để đối chiếu sau này.",
  txnPlaceholder: "Mã FT… trên sao kê",
  amountLabel: "Số tiền đã nhận",
  amountHelp: "Mặc định bằng tổng đơn. Sửa lại nếu khách chuyển khác số.",
  amountMissing: "Nhập số tiền khách đã chuyển.",
  amountNegative: "Số tiền không được âm. Nhập đúng số khách đã chuyển, vd 540000.",
  amountZero: "Số tiền phải từ 1 ₫ trở lên (tiền VND không có số lẻ). Nhập đúng số khách đã chuyển.",
  amountNotNumber: "Chỉ nhập chữ số, vd 540000 hoặc 540.000.",
  amountTooBig: "Số tiền quá lớn: tối đa 12 chữ số (999.999.999.999 ₫). Đối chiếu lại số trên sao kê.",
  amountLess: (diff: string) => `Ít hơn tổng đơn ${vnd(diff)}.`,
  amountMore: (diff: string) => `Nhiều hơn tổng đơn ${vnd(diff)}.`,
  consequencePaid: "Đơn chuyển sang Đang xử lý: xuất hoá đơn, trừ kho theo lô đang giữ và tạo phiếu giao.",
  consequenceUnder: "Nếu số tiền thiếu, đơn vẫn Giữ chỗ và khoản tiền vào hàng chờ thanh toán lệch.",
  consequenceOrphan: "Đơn đã tự huỷ: xác nhận KHÔNG khôi phục đơn. Khoản tiền vào hàng chờ thanh toán lệch để xử lý hoàn.",
  consequenceFinal: "Không hoàn tác bằng nút này. Ghi sai thì phải huỷ đơn và hoàn tiền.",
  consequenceAudit: "Nhật ký ghi tên bạn là người xác nhận.",
  confirmSubmit: (amount: string) => `Xác nhận đã nhận ${vnd(amount)}`,
  confirmSubmitNoAmount: "Xác nhận đã nhận tiền",
  confirming: "Đang xác nhận…",
  back: "Quay lại",

  // ---- Kết quả (theo `result` BE trả) ----
  resultPaid: (code: string, note?: string) =>
    `Đã xác nhận nhận tiền đơn ${code}. Đơn chuyển Đang xử lý${note ? `, phiếu giao ${note}` : ""}.`,
  resultUnder: (paid: string, missing: string) =>
    `Đã ghi nhận ${vnd(paid)}, còn thiếu ${vnd(missing)}. Đơn vẫn Giữ chỗ; khoản tiền nằm trong hàng chờ thanh toán lệch.`,
  resultOrphan: "Đơn đã tự huỷ nên không khôi phục. Khoản tiền nằm trong hàng chờ thanh toán lệch để Chủ xử lý hoàn.",
  resultOther: (status: string) => `Đã ghi nhận. Trạng thái đơn hiện tại: ${status}.`,
  duplicate: "Mã giao dịch này đã được ghi trước đó — hệ thống không xử lý lần hai. Tình trạng hiện tại:",
} as const;
