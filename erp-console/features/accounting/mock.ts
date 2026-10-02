// Mock hoá đơn mua và chi phí phụ — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Dữ liệu bịa, không có thông tin khách.
// Kho dữ liệu nằm trong bộ nhớ trang (tải lại = về seed). features/purchasing/mock.ts đọc kho này qua
// `mockInvoicesOfReceipt` / `mockCostsOfBatches` để chi tiết phiếu nhập thấy cùng hoá đơn và chi phí với các tab.
// Quyền theo BE: hoá đơn đọc = view_purchaseinvoice (Chủ, Quản lý), ghi = add_purchaseinvoice (Chủ);
// chi phí đọc = view_purchasecost và có giá vốn (Chủ), ghi = add_purchasecost (Chủ).
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import type { Me } from "@/features/auth/types";
import { beDetail } from "@/shared/lib/beErrors.mock";
import type { PurchaseCostAllocation, PurchaseCostInput, PurchaseCostRow, PurchaseInvoiceInput, PurchaseInvoiceRow } from "./types";

const DAY = 86_400_000;
const PAGE_SIZE = 20;
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { code, detail } });
/** Cột amount của BE: 12 chữ số nguyên (nhỏ hơn 10^12). */
const MAX_COST_AMOUNT = 1_000_000_000_000;
const LANDED_OVERFLOW_PART = 400_000_000_000;
const can = (me: Me, perm: string) => me.permissions.includes(perm);
const canReadCosts = (me: Me) => can(me, "purchasing.view_purchasecost") && me.can_view_cost;

/** Tên nhà cung cấp mock (khớp MOCK_SUPPLIERS ở features/purchasing/mock.ts; Lô 12 gộp một nguồn). */
const SUPPLIER_NAME: Record<number, string> = {
  1: "Đầu mối Cảng cá Phan Thiết",
  2: "Vựa cá Lagi (Anh Ba)",
  3: "Hợp tác xã Đánh bắt Vũng Tàu",
  4: "Ghe Tư Hải",
  5: "Vựa Bà Năm",
  6: "Tàu Phước Lộc 07",
};

const dayKey = (daysAgo: number) => todayInVietnam(new Date(Date.now() - daysAgo * DAY));

// [id, nhà cung cấp, phiếu nhập hoặc null, số tiền, ngày hoá đơn (trước), trả tiền sau (ngày) hoặc null = chưa trả]
type InvoiceSeed = [number, number, number | null, number, number, number | null];
const INVOICE_SEEDS: InvoiceSeed[] = [
  [42, 3, null, 2_400_000, 2, null],
  [40, 6, 97, 3_577_200, 5, 0],
  [39, 1, null, 1_150_000, 12, null],
  [38, 5, 96, 3_818_400, 6, 0],
  [37, 4, 95, 5_738_000, 7, 1],
  [36, 6, 94, 9_150_000, 8, 0],
  [35, 5, 93, 3_672_000, 9, 0],
  [34, 4, 92, 4_375_000, 10, 0],
];

let invoices: PurchaseInvoiceRow[] | null = null;
let costs: PurchaseCostRow[] | null = null;
let nextInvoiceId = 43;
let nextCostId = 6;

function invoiceRow(input: { id: number; supplier: number; receipt: number | null; amount: string; invoice_date: string; is_paid: boolean; paid_at: string | null }): PurchaseInvoiceRow {
  return {
    id: input.id,
    code: `#${input.id}`,
    supplier: input.supplier,
    supplier_name: SUPPLIER_NAME[input.supplier] ?? `Nhà cung cấp ${input.supplier}`,
    receipt: input.receipt,
    receipt_code: input.receipt ? `PR-${input.receipt}` : null,
    amount: `${input.amount}.00`,
    is_paid: input.is_paid,
    is_paid_label: input.is_paid ? "Đã trả tiền" : "Chưa trả tiền",
    invoice_date: input.invoice_date,
    paid_at: input.paid_at,
    created_by: 1,
  };
}

function allInvoices(): PurchaseInvoiceRow[] {
  if (!invoices) {
    invoices = INVOICE_SEEDS.map(([id, supplier, receipt, amount, ago, paidAfter]) =>
      invoiceRow({
        id,
        supplier,
        receipt,
        amount: String(amount),
        invoice_date: dayKey(ago),
        is_paid: paidAfter !== null,
        paid_at: paidAfter !== null ? new Date(Date.now() - (ago - paidAfter) * DAY - 3_600_000).toISOString() : null,
      }),
    );
  }
  return invoices;
}

// [id, loại, số tiền, cách chia, ngày (trước), ghi chú, [lô, tiền]...]
type CostSeed = [number, string, number, string, number, string, [number, number][]];
const COST_SEEDS: CostSeed[] = [
  [5, "ICE", 380_000, "BY_QTY", 2, "Đá cây ướp 2 thùng xốp từ cảng về kho.", [[10, 220_000], [11, 160_000]]],
  [4, "OTHER", 95_000, "BY_QTY", 3, "", [[9, 95_000]]],
  [3, "LOADING", 300_000, "BY_QTY", 5, "Bốc vác 2 người, 1 buổi sáng.", [[6, 120_000], [7, 180_000]]],
  [2, "TRANSPORT", 1_200_000, "BY_VALUE", 7, "Xe lạnh Phan Thiết - kho.", [[3, 500_000], [4, 400_000], [5, 300_000]]],
  [1, "ICE", 450_000, "BY_QTY", 9, "", [[1, 270_000], [2, 180_000]]],
];

const COST_TYPE_LABEL: Record<string, string> = { ICE: "Đá", TRANSPORT: "Vận chuyển", LOADING: "Bốc vác", OTHER: "Khác" };
const METHOD_LABEL: Record<string, string> = { BY_QTY: "Theo số kg", BY_VALUE: "Theo giá trị" };

function costRow(input: { id: number; cost_type: string; amount: string; allocation_method: string; incurred_date: string; note: string; allocations: { batch: number; amount: string }[] }): PurchaseCostRow {
  const allocations: PurchaseCostAllocation[] = input.allocations.map((a, i) => ({
    id: input.id * 100 + i + 1,
    purchase_cost: input.id,
    batch: a.batch,
    allocated_amount: `${a.amount}.00`,
  }));
  return {
    id: input.id,
    cost_type: input.cost_type,
    cost_type_label: COST_TYPE_LABEL[input.cost_type] ?? input.cost_type,
    amount: `${input.amount}.00`,
    allocation_method: input.allocation_method,
    allocation_method_label: METHOD_LABEL[input.allocation_method] ?? input.allocation_method,
    incurred_date: input.incurred_date,
    note: input.note,
    created_by: 1,
    created_at: new Date().toISOString(),
    allocations,
    batch_count: allocations.length,
  };
}

function allCosts(): PurchaseCostRow[] {
  if (!costs) {
    costs = COST_SEEDS.map(([id, type, amount, method, ago, note, parts]) =>
      costRow({ id, cost_type: type, amount: String(amount), allocation_method: method, incurred_date: dayKey(ago), note, allocations: parts.map(([batch, a]) => ({ batch, amount: String(a) })) }),
    );
  }
  return costs;
}

// ---- Cho features/purchasing/mock.ts ----

/** Hoá đơn của một phiếu nhập, mới nhất trước. */
export function mockInvoicesOfReceipt(receiptId: number): PurchaseInvoiceRow[] {
  return allInvoices().filter((i) => i.receipt === receiptId);
}

/** Chi phí có phần chia vào các lô cho trước, kèm tổng phần rơi vào các lô đó. */
export function mockCostsOfBatches(batchIds: number[]): { cost: PurchaseCostRow; allocated: number; batchCount: number }[] {
  const wanted = new Set(batchIds);
  const out: { cost: PurchaseCostRow; allocated: number; batchCount: number }[] = [];
  for (const cost of allCosts()) {
    const mine = cost.allocations.filter((a) => wanted.has(a.batch));
    if (mine.length === 0) continue;
    out.push({ cost, allocated: mine.reduce((sum, a) => sum + Number(a.allocated_amount), 0), batchCount: mine.length });
  }
  return out;
}

// ---- Danh sách và ghi ----

function paginate<T>(rows: T[], path: string): MockResponse {
  const page = Math.max(1, Number(new URLSearchParams(path.split("?")[1] ?? "").get("page")) || 1);
  const start = (page - 1) * PAGE_SIZE;
  return {
    status: 200,
    body: {
      count: rows.length,
      next: start + PAGE_SIZE < rows.length ? `?page=${page + 1}` : null,
      previous: page > 1 ? `?page=${page - 1}` : null,
      results: rows.slice(start, start + PAGE_SIZE),
    },
  };
}

const params = (path: string) => new URLSearchParams(path.split("?")[1] ?? "");
const MONTH = /^\d{4}-\d{2}$/;

/** GET /api/purchasing/invoices/ (R11). */
export function mockInvoiceList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.view_purchaseinvoice")) return FORBIDDEN;
  const q = params(req.path);
  let rows = [...allInvoices()];
  const paid = q.get("is_paid");
  if (paid) {
    if (!["0", "1", "true", "false"].includes(paid)) return err(400, "INVALID_FILTER", "Tham số is_paid chỉ nhận 1 hoặc 0.");
    const want = paid === "1" || paid === "true";
    rows = rows.filter((r) => r.is_paid === want);
  }
  const supplier = q.get("supplier");
  if (supplier) {
    if (!/^\d+$/.test(supplier)) return err(400, "INVALID_FILTER", "Tham số supplier phải là số.");
    rows = rows.filter((r) => r.supplier === Number(supplier));
  }
  const month = q.get("month");
  if (month) {
    if (!MONTH.test(month)) return err(400, "INVALID_FILTER", "Tham số month phải có dạng YYYY-MM.");
    rows = rows.filter((r) => r.invoice_date.startsWith(month));
  }
  rows.sort((a, b) => (a.invoice_date < b.invoice_date ? 1 : a.invoice_date > b.invoice_date ? -1 : b.id - a.id));
  return paginate(rows, req.path);
}

const required = "Trường này là bắt buộc.";

/** POST /api/purchasing/invoices/. */
export function mockInvoiceCreate(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.add_purchaseinvoice")) return FORBIDDEN;
  const body = (req.body ?? {}) as Partial<PurchaseInvoiceInput>;
  const bad: Record<string, string[]> = {};
  if (!body.supplier || !SUPPLIER_NAME[body.supplier]) bad.supplier = [required];
  if (!body.invoice_date) bad.invoice_date = [required];
  if (body.amount === undefined || body.amount === null || body.amount === "") bad.amount = [required];
  else if (!/^\d+(\.\d{1,2})?$/.test(String(body.amount))) bad.amount = ["Nhập một số hợp lệ, không âm."];
  if (Object.keys(bad).length > 0) return { status: 400, body: bad };
  const row = invoiceRow({
    id: nextInvoiceId++,
    supplier: body.supplier as number,
    receipt: body.receipt ?? null,
    amount: String(body.amount).replace(/\.\d+$/, ""),
    invoice_date: body.invoice_date as string,
    is_paid: body.is_paid !== false,
    paid_at: body.is_paid !== false ? body.paid_at ?? new Date().toISOString() : null,
  });
  allInvoices().unshift(row);
  return { status: 201, body: row };
}

/** GET /api/purchasing/costs/ (R12): cả chứng từ là giá vốn nên người không phải Chủ nhận 403 trước khi tới dữ liệu. */
export function mockCostList(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!canReadCosts(me)) return FORBIDDEN;
  const q = params(req.path);
  let rows = [...allCosts()];
  const types = q.get("cost_type");
  if (types) {
    const list = types.split(",").map((t) => t.trim()).filter(Boolean);
    if (list.some((t) => !COST_TYPE_LABEL[t])) return err(400, "INVALID_FILTER", "Tham số cost_type có giá trị không hợp lệ.");
    rows = rows.filter((r) => list.includes(r.cost_type));
  }
  const month = q.get("month");
  if (month) {
    if (!MONTH.test(month)) return err(400, "INVALID_FILTER", "Tham số month phải có dạng YYYY-MM.");
    rows = rows.filter((r) => r.incurred_date.startsWith(month));
  }
  rows.sort((a, b) => (a.incurred_date < b.incurred_date ? 1 : a.incurred_date > b.incurred_date ? -1 : b.id - a.id));
  return paginate(rows, req.path);
}

/** POST /api/purchasing/costs/: kiểm tổng phần chia như BE (BR-GV-04). */
export function mockCostCreate(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!can(me, "purchasing.add_purchasecost")) return FORBIDDEN;
  const body = (req.body ?? {}) as Partial<PurchaseCostInput>;
  if (!body.cost_type || !COST_TYPE_LABEL[body.cost_type]) return err(400, "BR-GV-01", "Loại chi phí không hợp lệ.");
  const amount = Number(body.amount);
  // Lô bổ sung A #14: BE trả kèm khoá `amount` / `allocations` để form hiện lỗi dưới đúng ô (beErrors.mock.ts chép nguyên văn câu của BE).
  if (body.amount === undefined || body.amount === null || String(body.amount).trim() === "" || !Number.isFinite(amount)) {
    const detail = "Số tiền chi phí không hợp lệ.";
    return { status: 400, body: { code: "INVALID_AMOUNT", detail, amount: [detail] } };
  }
  if (amount < 0) return err(400, "BR-GV-01", "Số tiền chi phí không được âm.");
  if (amount >= MAX_COST_AMOUNT) {
    const detail = beDetail("COST_AMOUNT_TOO_LARGE");
    return { status: 400, body: { code: "COST_AMOUNT_TOO_LARGE", detail, amount: [detail] } };
  }
  if (!body.incurred_date) return { status: 400, body: { incurred_date: [required] } };
  const parts = body.allocations ?? [];
  if (parts.length === 0) return err(400, "BR-GV-04", "Phải chỉ định ít nhất một lô nhận phân bổ.");
  const sum = parts.reduce((s, a) => s + Number(a.amount), 0);
  if (sum !== amount) return err(400, "BR-GV-04", "Tổng số tiền phân bổ truyền vào không khớp số tiền chi phí.");
  // Giá vốn mỗi kg của lô phải dưới 10 chữ số phần nguyên. Mock không biết số kg từng lô nên giả định lô cỡ 40 kg: một phần chia từ 4×10^11 trở lên là tràn.
  if (parts.some((a) => Number(a.amount) >= LANDED_OVERFLOW_PART)) {
    const detail = beDetail("COST_LANDED_OVERFLOW");
    return { status: 400, body: { code: "COST_LANDED_OVERFLOW", detail, allocations: [detail] } };
  }
  const row = costRow({
    id: nextCostId++,
    cost_type: body.cost_type,
    amount: String(body.amount),
    allocation_method: body.allocation_method ?? "BY_QTY",
    incurred_date: body.incurred_date,
    note: body.note ?? "",
    allocations: parts.map((a) => ({ batch: a.batch, amount: String(a.amount) })),
  });
  allCosts().unshift(row);
  return { status: 201, body: row };
}
