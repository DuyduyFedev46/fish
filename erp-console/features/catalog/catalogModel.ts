// Hàm thuần của màn Danh mục & giá (Lô 13): kiểm form, đổi nháp → thân gửi, câu chữ hiển thị. Không gọi mạng,
// không đụng DOM nên chạy được dưới vitest. Tiền là chuỗi thập phân; ngày hiệu lực là NGÀY THUẦN (YYYY-MM-DD, giờ VN).

import { ApiError } from "@/shared/lib/http";
import { dateOnly, kg, vnd } from "@/shared/lib/format";
import { errorText } from "@/shared/lib/messages";
import { CATALOG_MSG as M } from "./messages";
import type {
  BundleLineInput,
  CatalogItem,
  ItemInput,
  ItemType,
  PricingRule,
  PricingRuleInput,
  RuleApplyOn,
  RuleDiscountType,
} from "./types";

// ---------------------------------------------------------------- số và ngày

/** Ô tiền cho giá trị "1.500.000" → "1500000"; không phải chữ số nguyên → null. */
export function moneyDigits(raw: string): string | null {
  const digits = raw.replace(/\./g, "").replace(/\s/g, "");
  return /^\d+$/.test(digits) ? digits.replace(/^0+(?=\d)/, "") : null;
}

/** Ô số thập phân "2,5" hoặc "2.5" → số; trống hoặc không phải số → null. */
export function parseDecimal(raw: string): number | null {
  const text = raw.trim().replace(",", ".");
  if (!/^\d+(\.\d+)?$/.test(text)) return null;
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

/** "2026-10-02" + 1 ngày → "2026-10-03". Tính theo lịch thuần (UTC), không phụ thuộc múi giờ máy. */
export function addDays(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + days));
  const two = (n: number) => String(n).padStart(2, "0");
  return `${t.getUTCFullYear()}-${two(t.getUTCMonth() + 1)}-${two(t.getUTCDate())}`;
}

/** Đơn vị tiền cho ô nhập (lấy từ vnd() để chữ "đ" chỉ viết ở shared/lib/format.ts). */
export const CURRENCY_UNIT = vnd(0).replace(/^[\d.,\s]+/, "");

/** Ngày mai theo giờ Việt Nam, nhận `today` (từ todayInVietnam()) để kiểm thử không phụ thuộc đồng hồ. */
export function tomorrowOf(today: string): string {
  return addDays(today, 1);
}

// ---------------------------------------------------------------- đặt giá mới

export type PriceDraft = { itemId: string; priceListId: string; rate: string; validFrom: string; validUpto: string };
export type PriceErrors = Partial<Record<keyof PriceDraft, string>>;

/** Kiểm sớm trên form. "Từ ngày" trước hôm nay bị chặn ở đây, vì BE chỉ từ chối lùi ngày khi đã có đơn trong khoảng đó. */
export function validatePrice(draft: PriceDraft, today: string): PriceErrors {
  const e: PriceErrors = {};
  if (!draft.itemId) e.itemId = M.itemRequired;
  if (!draft.priceListId) e.priceListId = M.priceListRequired;
  const digits = moneyDigits(draft.rate);
  if (!draft.rate.trim()) e.rate = M.rateRequired;
  else if (digits === null || Number(digits) <= 0) e.rate = M.rateMustBePositive;
  else if (digits.length > 10) e.rate = M.rateTooLarge;
  if (!draft.validFrom) e.validFrom = M.validFromRequired;
  else if (draft.validFrom < today) e.validFrom = M.validFromPast(dateOnly(tomorrowOf(today)));
  if (draft.validUpto && draft.validFrom && draft.validUpto < draft.validFrom) e.validUpto = M.validUptoBeforeFrom;
  return e;
}

// ---------------------------------------------------------------- hiển thị giá

/** Đơn vị bán trên nhãn giá: combo bán theo "combo", còn lại theo kg. */
export function priceUnit(type: ItemType): string {
  return type === "BUNDLE" ? "combo" : "kg";
}

/** "260.000 đ/kg" — dùng trong ô bảng. */
export function priceCell(item: Pick<CatalogItem, "item_type" | "current_price">): string | null {
  if (!item.current_price) return null;
  return `${vnd(item.current_price.rate)}/${priceUnit(item.item_type)}`;
}

/** "420.000 đ / combo" — dùng trong ô thông tin chi tiết. */
export function priceInfo(item: Pick<CatalogItem, "item_type" | "current_price">): string | null {
  if (!item.current_price) return null;
  return `${vnd(item.current_price.rate)} / ${priceUnit(item.item_type)}`;
}

export function shelfLifeText(days: number): string | null {
  return days > 0 ? `${days} ngày` : null;
}

// ---------------------------------------------------------------- form mặt hàng

export type LineDraft = { key: number; component: string; qty: string };
export type ItemDraft = {
  code: string;
  name: string;
  itemGroup: string;
  itemType: ItemType;
  shelfLife: string;
  hasBatch: boolean;
  hasExpiry: boolean;
  isActive: boolean;
  description: string;
  lines: LineDraft[];
};

export const ITEM_LIMITS = { code: 40, name: 200, description: 1000 } as const;

export function emptyItemDraft(type: ItemType): ItemDraft {
  return {
    code: "",
    name: "",
    itemGroup: "",
    itemType: type,
    shelfLife: type === "BUNDLE" ? "0" : "3",
    hasBatch: type !== "BUNDLE",
    hasExpiry: type !== "BUNDLE",
    isActive: true,
    description: "",
    lines: type === "BUNDLE" ? [{ key: 1, component: "", qty: "" }] : [],
  };
}

export type ItemErrors = {
  code?: string;
  name?: string;
  itemGroup?: string;
  shelfLife?: string;
  description?: string;
  /** Lỗi chung của công thức (chưa có dòng nào). */
  lines?: string;
  /** Lỗi theo từng dòng, khoá = `key` của dòng. */
  line: Record<number, { component?: string; qty?: string }>;
};

export function validateItem(draft: ItemDraft): ItemErrors {
  const e: ItemErrors = { line: {} };
  const code = draft.code.trim();
  if (!code) e.code = M.codeRequired;
  else if (code.length > ITEM_LIMITS.code) e.code = M.codeTooLong;
  const name = draft.name.trim();
  if (!name) e.name = M.nameRequired;
  else if (name.length > ITEM_LIMITS.name) e.name = M.nameTooLong;
  if (!draft.itemGroup) e.itemGroup = M.groupRequired;
  if (!/^\d{1,5}$/.test(draft.shelfLife.trim())) e.shelfLife = M.shelfLifeInvalid;
  if (draft.description.length > ITEM_LIMITS.description) e.description = M.descriptionTooLong;
  if (draft.itemType === "BUNDLE") {
    if (draft.lines.length === 0) e.lines = M.linesRequired;
    const seen = new Set<string>();
    for (const line of draft.lines) {
      const le: { component?: string; qty?: string } = {};
      if (!line.component) le.component = M.lineComponentRequired;
      else if (seen.has(line.component)) le.component = M.lineComponentDuplicate;
      else seen.add(line.component);
      const qty = parseDecimal(line.qty);
      if (!line.qty.trim()) le.qty = M.lineQtyRequired;
      else if (qty === null || qty < 0.001) le.qty = M.lineQtyMin;
      if (le.component || le.qty) e.line[line.key] = le;
    }
  }
  return e;
}

export function hasItemErrors(e: ItemErrors): boolean {
  return !!(e.code || e.name || e.itemGroup || e.shelfLife || e.description || e.lines || Object.keys(e.line).length);
}

export function itemInputOf(draft: ItemDraft): ItemInput {
  return {
    code: draft.code.trim(),
    name: draft.name.trim(),
    item_group: Number(draft.itemGroup),
    item_type: draft.itemType,
    stock_uom: "Kg",
    shelf_life_in_days: Number(draft.shelfLife.trim()),
    has_batch_no: draft.hasBatch,
    has_expiry_date: draft.hasExpiry,
    is_active: draft.isActive,
    description: draft.description.trim(),
  };
}

/** Thân gửi cho một dòng công thức: định mức luôn 3 chữ số thập phân như BE lưu. */
export function lineInputOf(bundleId: number, line: LineDraft): BundleLineInput {
  const qty = parseDecimal(line.qty) ?? 0;
  return { bundle: bundleId, component: Number(line.component), qty_per_bundle: qty.toFixed(3) };
}

// ---------------------------------------------------------------- form ưu đãi

export type RuleDraft = {
  name: string;
  applyOn: RuleApplyOn;
  item: string;
  minQty: string;
  minAmount: string;
  discountType: RuleDiscountType;
  discountValue: string;
  validFrom: string;
  validUpto: string;
  isActive: boolean;
};
export type RuleErrors = Partial<Record<keyof RuleDraft, string>>;

export function emptyRuleDraft(): RuleDraft {
  return { name: "", applyOn: "ITEM", item: "", minQty: "", minAmount: "", discountType: "PERCENT", discountValue: "", validFrom: "", validUpto: "", isActive: true };
}

/** Số của ô "Mức giảm": kiểu tiền là số nguyên có dấu chấm nhóm nghìn, kiểu phần trăm có thể lẻ ("7,5"). */
export function discountNumber(draft: Pick<RuleDraft, "discountType" | "discountValue">): number | null {
  if (draft.discountType === "AMOUNT") {
    const digits = moneyDigits(draft.discountValue);
    return digits === null ? null : Number(digits);
  }
  return parseDecimal(draft.discountValue);
}

/** Cùng luật với serializer BE (apps/catalog/pricing): ITEM cần mặt hàng + số kg, ORDER cần giá trị đơn, mức giảm > 0, phần trăm ≤ 100. */
export function validateRule(draft: RuleDraft): RuleErrors {
  const e: RuleErrors = {};
  if (!draft.name.trim()) e.name = M.ruleNameRequired;
  if (draft.applyOn === "ITEM") {
    if (!draft.item) e.item = M.ruleItemRequired;
    const qty = parseDecimal(draft.minQty);
    if (!draft.minQty.trim()) e.minQty = M.minQtyRequired;
    else if (qty === null || qty <= 0) e.minQty = M.minQtyPositive;
  } else {
    const digits = moneyDigits(draft.minAmount);
    if (!draft.minAmount.trim()) e.minAmount = M.minAmountRequired;
    else if (digits === null || Number(digits) <= 0) e.minAmount = M.minAmountRequired;
  }
  const value = discountNumber(draft);
  if (!draft.discountValue.trim()) e.discountValue = M.discountRequired;
  else if (value === null || value <= 0) e.discountValue = M.discountPositive;
  else if (draft.discountType === "PERCENT" && value > 100) e.discountValue = M.discountPercentMax;
  if (draft.validFrom && draft.validUpto && draft.validUpto < draft.validFrom) e.validUpto = M.validUptoBeforeFrom;
  return e;
}

export function ruleInputOf(draft: RuleDraft): PricingRuleInput {
  const value = discountNumber(draft) ?? 0;
  const isItem = draft.applyOn === "ITEM";
  return {
    name: draft.name.trim(),
    is_active: draft.isActive,
    apply_on: draft.applyOn,
    item: isItem ? Number(draft.item) : null,
    min_qty: isItem ? (parseDecimal(draft.minQty) ?? 0).toFixed(3) : null,
    min_amount: isItem ? null : `${moneyDigits(draft.minAmount) ?? "0"}.00`,
    discount_type: draft.discountType,
    discount_value: draft.discountType === "AMOUNT" ? `${value}.00` : value.toFixed(2),
    valid_from: draft.validFrom || null,
    valid_upto: draft.validUpto || null,
  };
}

/** Điều kiện ngắn của ưu đãi cho ô bảng: "Cá thu, mua từ 5 kg" hoặc "Đơn từ 500.000 đ". */
export function ruleCondition(rule: Pick<PricingRule, "apply_on" | "item_name" | "min_qty" | "min_amount">): string | null {
  if (rule.apply_on === "ITEM") {
    if (!rule.item_name || rule.min_qty === null) return null;
    return M.ruleConditionItem(rule.item_name, kg(rule.min_qty));
  }
  return rule.min_amount === null ? null : M.ruleConditionOrder(vnd(rule.min_amount));
}

/** Mức giảm cho ô bảng: "10%" hoặc "50.000 đ". */
export function ruleDiscountText(rule: Pick<PricingRule, "discount_type" | "discount_value">): string {
  if (rule.discount_type === "PERCENT") {
    const n = Number(rule.discount_value);
    return `${Number.isFinite(n) ? String(Math.round(n * 100) / 100).replace(".", ",") : rule.discount_value}%`;
  }
  return vnd(rule.discount_value);
}

// ---------------------------------------------------------------- nhóm hàng

export function validateGroupName(raw: string): string | null {
  const name = raw.trim();
  if (!name) return M.groupNameRequired;
  if (name.length > 120) return M.groupNameTooLong;
  return null;
}

// ---------------------------------------------------------------- lỗi và URL

/** Câu hiện cho người dùng khi lưu lỗi: nguyên văn `detail` của BE nếu có, không thì câu chung. */
export function saveErrorMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 0) return err.message;
  return errorText(err);
}

/** `?id=12` → 12; thiếu hoặc không phải số nguyên dương → null. URL chỉ chứa id số. */
export function parseItemId(search: string): number | null {
  const raw = new URLSearchParams(search).get("id");
  if (!raw || !/^\d{1,12}$/.test(raw)) return null;
  const n = Number(raw);
  return n > 0 ? n : null;
}

/** `?type=BUNDLE` → "BUNDLE"; còn lại là mặt hàng thường. */
export function parseItemTypeParam(search: string): ItemType {
  return new URLSearchParams(search).get("type") === "BUNDLE" ? "BUNDLE" : "SIMPLE";
}

export function asActiveFilter(v: string): string {
  return v === "1" || v === "0" ? v : "";
}

export function asTypeFilter(v: string): "" | ItemType {
  return v === "SIMPLE" || v === "BUNDLE" ? v : "";
}
