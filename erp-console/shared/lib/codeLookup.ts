// ⌘K nhảy theo MÃ chứng từ (ED-07, Lô 17b H1). Hàm thuần: nhận dạng mẫu mã, dựng đường dẫn, và điều phối việc tra qua `CodeFinder`
// (do features/lookup nối với từng module). Chuỗi KHÔNG đúng mẫu mã (tên khách, SĐT, từ thường) thì `parseCodeRef` trả null và KHÔNG có
// request nào được gửi: ô ⌘K không được dùng để dò tên/SĐT (02b T5, bất biến 9).
//
// Mẫu mã:
//   SO261007-4F2A1C   đơn          → GET /api/sales/orders/?q=<mã>, lấy dòng khớp đúng rồi mở /orders/detail/?id=
//   GH-…              phiếu giao   → GET /api/delivery/notes/?code=<mã> (có phạm vi: giao1 tra mã của giao2 → không thấy)
//   <MÃ-LÔ>           lô           → GET /api/inventory/batches/<mã>/ (đã chấp nhận mã lô)
//   PR-n KK-n RT-n    phiếu nhập · kiểm kê · hàng hoàn → mở thẳng trang chi tiết theo id (trang tự xử lý 404/403)
//   #n                phiếu hoàn tiền (mã `#id` ở hàng chờ hoàn tiền) → /orders/refunds/detail/?id=

export type CodeRef =
  | { kind: "order"; code: string }
  | { kind: "note"; code: string }
  | { kind: "batch"; code: string }
  | { kind: "id"; code: string; href: string };

const ID_ROUTES: Record<string, string> = {
  PR: "/purchasing/detail/?id=",
  KK: "/stocktake/detail/?id=",
  RT: "/returns/detail/?id=",
};

/** Mã dạng chuẩn hoá (chữ hoa) hoặc null khi không giống mã nào. */
export function parseCodeRef(raw: string): CodeRef | null {
  const code = raw.trim().toUpperCase();
  if (!code || code.length > 40 || /\s/.test(code) || /[^\x21-\x7E]/.test(code)) return null;
  // Dãy dài giống SĐT (liền nhau, hoặc chỉ gồm số và dấu nối "09-1234-5678"): không bao giờ là mã.
  if (/\d{9,}/.test(code) || (/^[\d\-./]+$/.test(code) && code.replace(/\D/g, "").length >= 9)) return null;
  const num = /^(PR|KK|RT)-(\d{1,9})$/.exec(code);
  if (num) return { kind: "id", code, href: `${ID_ROUTES[num[1]]}${Number(num[2])}` };
  const refund = /^#(\d{1,9})$/.exec(code);
  if (refund) return { kind: "id", code, href: `/orders/refunds/detail/?id=${Number(refund[1])}` };
  if (/^SO\d{6}-[A-Z0-9]{4,8}$/.test(code)) return { kind: "order", code };
  if (/^GH-[A-Z0-9][A-Z0-9-]{2,}$/.test(code)) return { kind: "note", code };
  // Mã lô: các đoạn chữ-số nối bằng "-", có ít nhất một chữ số và một chữ cái (vd CA-THU-260928-VT01, LO-0912, L0914-CT01).
  if (/^(?=.*\d)(?=.*[A-Z])[A-Z0-9]{1,12}(?:-[A-Z0-9]{1,12})+$/.test(code)) return { kind: "batch", code };
  return null;
}

/** Mỗi hàm trả id của chứng từ khớp ĐÚNG mã, hoặc null khi không có/không thuộc phạm vi. Ném lỗi khi mạng/quyền hỏng. */
export type CodeFinder = {
  order: (code: string, signal?: AbortSignal) => Promise<number | null>;
  note: (code: string, signal?: AbortSignal) => Promise<number | null>;
  batch: (code: string, signal?: AbortSignal) => Promise<number | null>;
};

export type CodeLookupResult = { status: "found"; href: string } | { status: "none"; code: string };

export async function resolveCodeRef(ref: CodeRef, finder: CodeFinder, signal?: AbortSignal): Promise<CodeLookupResult> {
  if (ref.kind === "id") return { status: "found", href: ref.href };
  const id = await finder[ref.kind](ref.code, signal);
  if (id === null) return { status: "none", code: ref.code };
  const base = ref.kind === "order" ? "/orders/detail/?id=" : ref.kind === "note" ? "/deliveries/detail/?id=" : "/inventory/detail/?id=";
  return { status: "found", href: `${base}${id}` };
}

export const CODE_NOT_FOUND = (code: string) => `Không tìm thấy chứng từ khớp với ${code}`;
