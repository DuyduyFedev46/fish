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
  // Duy chốt 2026-09-26: chuyển thừa ngay lần đầu → phần thừa vào hàng chờ (OVERPAID) để Chủ hoàn. BE đang làm.
  amountMore: (diff: string) => `Nhiều hơn tổng đơn ${vnd(diff)} — phần thừa vào hàng chờ thanh toán để hoàn cho khách.`,
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
  resultOverpaid: (extra: string) => ` Khách chuyển thừa ${vnd(extra)} — đã đưa vào hàng chờ để hoàn.`,
  openQueue: "Mở hàng chờ thanh toán",
  resultOrphan: "Đơn đã tự huỷ nên không khôi phục. Khoản tiền nằm trong hàng chờ thanh toán lệch để Chủ xử lý hoàn.",
  resultOther: (status: string) => `Đã ghi nhận. Trạng thái đơn hiện tại: ${status}.`,
  duplicate: "Mã giao dịch này đã được ghi trước đó — hệ thống không xử lý lần hai. Tình trạng hiện tại:",
} as const;

// ---- S12/S13: hàng chờ thanh toán lệch + phiếu hoàn cho khoản không có hoá đơn ----
export const QUEUE_MSG = {
  // Tab con trong "Đơn & tiền"
  tabsLabel: "Đơn & tiền",
  tabOrders: "Đơn hàng",
  tabQueue: "Hàng chờ thanh toán",

  // Danh sách
  intro: "Mọi khoản tiền về lệch với đơn: thiếu, thừa, về sau khi đơn tự huỷ hoặc không khớp đơn nào. Mở từng khoản để gắn vào đơn, xác nhận khi khách đã bù, hoặc lập phiếu hoàn.",
  listTitle: "Khoản tiền lệch",
  filterStatus: "Tình trạng xử lý",
  filterType: "Loại lệch",
  openTab: "Đang chờ",
  resolvedTab: "Đã xử lý",
  shown: (n: number, total: number) => (n >= total ? `${total} khoản` : `Đang hiện ${n} / ${total} khoản`),
  loadMore: "Tải thêm khoản",
  loadingMore: "Đang tải thêm…",
  loading: "Đang tải hàng chờ thanh toán…",
  emptyOpenTitle: "Không còn khoản tiền lệch nào",
  emptyOpenHint: "Mọi khoản tiền về đều đã khớp đơn hoặc đã được xử lý. Bấm làm mới để kiểm tra khoản vừa về.",
  emptyResolvedTitle: "Chưa có khoản nào đã xử lý",
  emptyResolvedHint: "Khoản lệch được gắn đơn, xác nhận hoặc hoàn tiền xong sẽ nằm ở đây để đối chiếu.",
  noMatchTitle: "Không có khoản nào thuộc loại này",
  noMatchHint: "Chọn loại lệch khác hoặc xem mọi loại.",
  showAllTypes: "Xem mọi loại",
  noOrder: "Chưa gắn đơn",
  pendingRefund: "Có phiếu hoàn chờ chuyển",

  // Chi tiết
  sheetTitle: (txn: string) => `Khoản tiền ${txn}`,
  receivedAt: "Nhận lúc",
  txn: "Mã giao dịch",
  source: "Nguồn",
  content: "Nội dung CK",
  noContent: "Không có nội dung",
  orderPart: "Đơn liên quan",
  orderNone: "Tiền này không khớp đơn nào. Tìm đơn khách định trả để gắn vào, hoặc lập phiếu hoàn nếu không tìm ra.",
  orderTotal: "Tổng đơn",
  orderPaid: "Đã nhận",
  orderMissing: "Còn thiếu",
  orderOver: "Thừa",
  openOrder: (code: string) => `Xem đơn ${code}`,
  refundsPart: "Phiếu hoàn của khoản này",
  refundNoRef: "Chờ Chủ chuyển khoản trả khách",
  resolutionPart: "Đã xử lý",
  resolvedBy: "Người xử lý",
  resolvedAt: "Lúc",
  note: "Ghi chú",
  noActions: "Không còn thao tác nào cho khoản này.",
  stale: "Chưa tải lại được khoản này. Đóng tấm và làm mới danh sách để xem thao tác còn lại.",
  resolutionHow: "Cách xử lý",
  pendingRefundHint: "Khoản này vẫn nằm trong hàng chờ tới khi phiếu hoàn được xác nhận đã chuyển.",

  // Nút theo available_actions
  actAttach: "Gắn vào đơn",
  actConfirm: "Xác nhận đơn (khách đã bù)",
  actRefund: "Lập phiếu hoàn",
  back: "Quay lại",

  // Gắn vào đơn (ATTACH_TO_ORDER)
  attachTitle: (txn: string) => `Gắn ${txn} vào đơn`,
  attachSearch: "Tìm đơn theo mã, tên khách hoặc SĐT",
  attachSearchPh: "Mã đơn, tên khách, SĐT…",
  attachScopeBooked: "Đang giữ chỗ",
  attachScopeAll: "Mọi đơn",
  attachScope: "Phạm vi tìm",
  attachLoading: "Đang tìm đơn…",
  attachEmpty: "Không có đơn khớp. Thử mã đơn, SĐT hoặc chọn \"Mọi đơn\".",
  attachPick: "Chọn một đơn trong danh sách để gắn.",
  attachLegend: "Chọn đơn để gắn",
  attachSameAmount: "Bằng số tiền",
  attachQuestion: (amount: string, code: string) => `Gắn ${vnd(amount)} vào đơn ${code}?`,
  attachConsequence1: "Khoản tiền được ghi vào đơn này. Đủ tổng đơn thì đơn chuyển Đang xử lý: xuất hoá đơn, trừ kho theo lô đang giữ và tạo phiếu giao.",
  attachConsequence2: "Đơn đã tự huỷ thì không gắn được — khi đó chỉ còn cách hoàn tiền.",
  attachSubmit: (code: string) => `Gắn vào đơn ${code}`,
  attaching: "Đang gắn…",

  // Xác nhận khi khách đã bù (CONFIRM_ORDER)
  confirmTitle: (code: string) => `Xác nhận đơn ${code}`,
  confirmQuestion: (code: string) => `Khách đã chuyển bù đủ cho đơn ${code}?`,
  confirmShort: (missing: string) => `Theo số liệu hiện có, đơn còn thiếu ${vnd(missing)}. Hệ thống sẽ từ chối nếu tổng tiền đã nhận chưa đủ.`,
  confirmConsequence1: "Đơn chuyển Đang xử lý: xuất hoá đơn, trừ kho theo lô đang giữ và tạo phiếu giao.",
  confirmConsequence2: "Mọi khoản chuyển thiếu của đơn này cùng được đóng (Đã xử lý · Xác nhận đơn).",
  confirmSubmit: "Xác nhận đơn đã đủ tiền",
  confirming: "Đang xác nhận…",

  // Chung cho hai bước trên
  noteLabel: "Ghi chú",
  noteOptional: "(không bắt buộc)",
  noteHelpAttach: "Vd: Khách ghi sai nội dung chuyển khoản.",
  noteHelpConfirm: "Vd: Khách đã chuyển bù FT… lúc 10:20.",
  consequenceFinal: "Không hoàn tác bằng nút này.",
  consequenceAudit: "Nhật ký ghi tên bạn, giờ và ghi chú.",

  // Lập phiếu hoàn (S13)
  refundTitle: (txn: string) => `Lập phiếu hoàn · ${txn}`,
  refundQuestion: (amount: string) => `Lập phiếu hoàn ${vnd(amount)} cho khách?`,
  refundQuestionNoAmount: "Lập phiếu hoàn cho khách?",
  refundAmount: "Số tiền hoàn",
  refundAmountHelp: (max: string) => `Tối đa còn được hoàn: ${vnd(max)}.`,
  refundOverMax: (max: string) => `Nhiều hơn số còn được hoàn (${vnd(max)}). Máy chủ sẽ từ chối — sửa lại số tiền.`,
  refundReason: "Lý do hoàn",
  refundReasonHelp: "Ghi vào phiếu hoàn và nhật ký để đối chiếu sau này.",
  refundReasonMissing: "Nhập lý do hoàn, vd \"Tiền về sau khi đơn tự huỷ\".",
  refundReasonDefault: {
    ORPHAN: "Tiền về sau khi đơn tự huỷ",
    UNDERPAID: "Khách chuyển thiếu, không chuyển bù",
    UNMATCHED: "Tiền không khớp đơn nào",
    OVERPAID: "Khách chuyển thừa",
  } as Record<string, string>,
  refundConsequence1: "Tạo phiếu hoàn Chờ hoàn. Tiền CHƯA rời tài khoản: bạn chuyển khoản trả khách rồi xác nhận phiếu kèm mã giao dịch.",
  refundConsequence2: "Khoản này vẫn nằm trong hàng chờ tới khi phiếu hoàn được xác nhận đã chuyển.",
  refundConsequence3: "Khoản này không có hoá đơn nên không trừ vào doanh thu hay lãi lỗ.",
  refundSubmit: (amount: string) => `Lập phiếu hoàn ${vnd(amount)}`,
  refundSubmitNoAmount: "Lập phiếu hoàn",
  refunding: "Đang lập phiếu…",

  // Kết quả (theo response BE)
  resultAttached: (code: string, status: string) => `Đã gắn vào đơn ${code}. Đơn hiện: ${status}.`,
  resultAttachedOpen: (code: string, status: string) =>
    `Đã gắn vào đơn ${code} (đơn hiện: ${status}). Tiền chưa đủ nên khoản này vẫn chờ xử lý.`,
  resultConfirmed: (code: string, status: string, closed: number) =>
    `Đã xác nhận đơn ${code}. Đơn hiện: ${status}.${closed > 1 ? ` Đã đóng ${closed} khoản chuyển thiếu của đơn.` : ""}`,
  resultDelivery: (code: string) => ` Phiếu giao ${code}.`,
  resultRefund: (amount: string) => `Đã lập phiếu hoàn ${vnd(amount)} (Chờ hoàn). Chuyển khoản trả khách rồi xác nhận phiếu.`,
  resultRefundDup: (amount: string) => `Phiếu hoàn ${vnd(amount)} đã được lập trước đó — hệ thống không tạo phiếu thứ hai.`,
  refundableLeft: "Còn được hoàn",
  resultOther: (status: string) => `Đã ghi nhận. Tình trạng khoản tiền: ${status}.`,
} as const;
