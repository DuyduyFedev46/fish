// Nhãn tiếng Việt của lệnh AI (Lô 15 QA: "Tạo mới batch", `inventory.batch.inspect`, `sales.order.confirm` lộ ra giao diện).
//
// VÌ SAO LÀM Ở FE: BE chỉ trả `title`, mà `title` do registry tự sinh khi lệnh chưa có `AiMeta.title`: hoặc là "<Hành động> <tên model tiếng Anh>"
// ("Tạo mới batch", "Xem danh sách salesorder"), hoặc là dòng đầu docstring của view (cả câu dài, có mã BR, có đường dẫn API).
// Chưa có trường nhãn riêng, nên FE giữ bảng nhãn theo id lệnh (registry BE, `apps/ai/registry`). Có lệnh mới mà chưa có trong
// bảng thì vẫn ra nhãn tiếng Việt nhờ ghép "hành động + đối tượng"; không bao giờ hiện mã lệnh thô.
// Đề nghị BE (không chặn): thêm `AiMeta.title` tiếng Việt cho mọi lệnh, khi đó bảng này chỉ còn là dự phòng.
//
// Thứ tự chọn nhãn (`commandLabel`): `title` BE nếu ngắn, có dấu tiếng Việt và không lẫn tên model/đường dẫn/mã BR (nhãn do người
// viết tay thì tôn trọng) → bảng theo id → ghép hành động + đối tượng → "Thao tác AI". Không có dữ liệu cá nhân ở đây.

/** Nhãn đầy đủ theo id lệnh, dùng khi `title` BE không dùng được (câu dài, có mã BR, hay tên model tiếng Anh). */
const COMMAND_LABELS: Record<string, string> = {
  "common.guidance": "Xem hướng dẫn bước tiếp theo",
  "content.category.create": "Tạo chuyên mục",
  "content.category.list": "Xem danh sách chuyên mục",
  "content.category.partial_update": "Cập nhật chuyên mục",
  "content.entry.counts": "Đếm bài viết theo trạng thái",
  "content.entry.create": "Tạo nháp bài viết",
  "content.entry.discard_changes": "Huỷ thay đổi nháp bài viết",
  "content.entry.list": "Xem danh sách bài viết",
  "content.entry.partial_update": "Cập nhật nháp bài viết",
  "content.entry.publish": "Xuất bản bài viết",
  "content.entry.restore_version": "Khôi phục phiên bản bài viết",
  "content.entry.retrieve": "Xem chi tiết bài viết",
  "content.entry.return_action": "Trả bài viết về nháp",
  "content.entry.submit": "Gửi duyệt bài viết",
  "content.entry.unpublish": "Gỡ bài viết khỏi web",
  "content.entry.version_detail": "Xem một phiên bản bài viết",
  "content.entry.versions": "Xem các phiên bản bài viết",
  "delivery.deliverers": "Xem người giao đang rảnh",
  "delivery.deliverynote.assign": "Giao hoặc đổi người giao",
  "delivery.deliverynote.set_status": "Cập nhật trạng thái phiếu giao",
  "inventory.batch.cancel_expired": "Huỷ phần tồn lô quá hạn",
  "inventory.batch.close": "Chốt lô cá",
  "inventory.batch.inspect": "Kiểm tra lô cá",
  "inventory.batch.publish": "Mở bán lô cá",
  "inventory.batch.return_to_supplier": "Trả lô quá hạn cho nhà cung cấp",
  "inventory.returntostock.approve": "Duyệt phiếu hàng hoàn",
  "inventory.returntostock.cancel": "Huỷ phiếu hàng hoàn",
  "inventory.stockreconciliation.approve": "Duyệt phiếu kiểm kê",
  "inventory.stockreconciliation.replace_lines": "Sửa số đếm phiếu kiểm kê",
  "inventory.stockreconciliation.return_to_draft": "Trả phiếu kiểm kê về nháp",
  "inventory.stockreconciliation.submit": "Gửi duyệt phiếu kiểm kê",
  "purchasing.purchasereceipt.cancel": "Huỷ phiếu nhập",
  "purchasing.purchasereceipt.receive_batches": "Nhập lô mua tại cảng",
  "purchasing.purchasereceipt.submit": "Xác nhận phiếu nhập",
  "reports.batch_pnl": "Xem lãi lỗ một lô",
  "reports.batch_pnl_list": "Xem lãi lỗ theo lô",
  "reports.dashboard_summary": "Xem tổng quan",
  "reports.period_pnl": "Xem lãi lỗ theo kỳ",
  "sales.paymenttransaction.resolve": "Xử lý khoản chuyển khoản lệch",
  "sales.refund.confirm": "Xác nhận đã hoàn tiền",
  "sales.refund.create_refund": "Lập phiếu hoàn tiền",
  "sales.refund.mark_failed": "Báo hoàn tiền thất bại",
  "sales.refund.retry": "Thử lại hoàn tiền",
  "sales.salesorder.cancel": "Huỷ đơn hàng đã thanh toán",
  "sales.salesorder.confirm": "Xác nhận đơn hàng",
  "sales.salesorder.confirm_payment": "Xác nhận thanh toán tay",
};

/** Đối tượng của lệnh (đoạn giữa của id), viết thường để ghép sau động từ. Có cả `order` vì id ngắn từng xuất hiện ở nhật ký cũ. */
const SUBJECTS: Record<string, string> = {
  batch: "lô cá",
  bundleline: "dòng combo",
  category: "chuyên mục",
  deliverynote: "phiếu giao",
  entry: "bài viết",
  item: "mặt hàng",
  itemgroup: "nhóm hàng",
  itemprice: "giá bán",
  order: "đơn hàng",
  paymenttransaction: "khoản chuyển khoản",
  pricelist: "bảng giá",
  pricingrule: "ưu đãi",
  purchasecost: "chi phí mua",
  purchaseinvoice: "hoá đơn mua",
  purchasereceipt: "phiếu nhập",
  refund: "phiếu hoàn tiền",
  returntostock: "phiếu hàng hoàn",
  salesinvoice: "hoá đơn bán",
  salesorder: "đơn hàng",
  stockentry: "phiếu kho",
  stockledgerentry: "dòng sổ nhập xuất",
  stockreconciliation: "phiếu kiểm kê",
  supplier: "nhà cung cấp",
  warehouse: "kho hàng",
};

/** Động từ (đoạn cuối của id). */
const VERBS: Record<string, string> = {
  approve: "Duyệt",
  assign: "Giao việc cho",
  cancel: "Huỷ",
  close: "Chốt",
  confirm: "Xác nhận",
  create: "Tạo",
  inspect: "Kiểm tra",
  list: "Xem danh sách",
  mark_failed: "Báo thất bại",
  partial_update: "Cập nhật",
  publish: "Mở bán",
  resolve: "Xử lý",
  retrieve: "Xem chi tiết",
  retry: "Thử lại",
  submit: "Gửi duyệt",
  update: "Cập nhật",
};

const VIETNAMESE_DIACRITIC = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
/** Dấu hiệu `title` BE là câu dài, đường dẫn API, mã BR hay tên model tiếng Anh chứ không phải nhãn. */
const NOT_A_LABEL = /[`/()§]|\bGET\b|\bPOST\b|\bBR-|\bAPI\b/;

function derivedLabel(id: string): string | null {
  const parts = id.split(".");
  if (parts.length < 3) return null;
  const subject = SUBJECTS[parts[1]];
  const verb = VERBS[parts.slice(2).join("_")];
  return subject && verb ? `${verb} ${subject}` : null;
}

function usableTitle(title: string | undefined | null): string | null {
  const t = (title ?? "").trim();
  if (!t || t.length > 40 || NOT_A_LABEL.test(t) || !VIETNAMESE_DIACRITIC.test(t)) return null;
  // Tên model tiếng Anh viết liền ("Tạo mới batch", "Xem danh sách salesorder"): có từ không dấu trùng khoá đối tượng.
  const words = t.toLowerCase().split(/\s+/);
  return words.some((w) => w in SUBJECTS) ? null : t;
}

/** Nhãn tiếng Việt cho lệnh AI. `id` là mã lệnh (có thể rỗng khi dữ liệu cũ), `title` là tên BE trả. Không bao giờ trả mã thô. */
export function commandLabel(id: string | undefined | null, title?: string | null): string {
  const key = (id ?? "").trim();
  return usableTitle(title) ?? COMMAND_LABELS[key] ?? derivedLabel(key) ?? "Thao tác AI";
}
