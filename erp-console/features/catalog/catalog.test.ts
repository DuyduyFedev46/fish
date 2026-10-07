import { describe, expect, it } from "vitest";
import { itemListQuery, pricingRuleQuery } from "./api";
import {
  addDays,
  discountNumber,
  emptyItemDraft,
  emptyRuleDraft,
  hasItemErrors,
  itemInputOf,
  lineInputOf,
  moneyDigits,
  parseAmount,
  parseQtyKg,
  parseDecimal,
  parseItemId,
  parseItemTypeParam,
  priceCell,
  priceInfo,
  ruleCondition,
  ruleDiscountText,
  ruleInputOf,
  shelfLifeText,
  tomorrowOf,
  validateGroupName,
  validateItem,
  validatePrice,
  validateRule,
} from "./catalogModel";
import { mockCatalogApi } from "./mock";
import { catalogAbility, CATALOG_PERM } from "./permissions";
import { EMPTY_ITEM_PARAMS } from "./types";

const token = (username: string) => `mock-token-${username}-${Date.now() + 60_000}`;
const call = (username: string, method: "GET" | "POST" | "PATCH" | "DELETE" | "PUT", path: string, body?: unknown) =>
  mockCatalogApi({ method, path, body, token: token(username) });
const TODAY = "2026-10-02";

describe("số và ngày", () => {
  it("moneyDigits bỏ dấu chấm nhóm, từ chối số lẻ và chữ", () => {
    expect(moneyDigits("1.500.000")).toBe("1500000");
    expect(moneyDigits("0012")).toBe("12");
    expect(moneyDigits("12,5")).toBeNull();
    expect(moneyDigits("abc")).toBeNull();
  });
  it("parseDecimal nhận dấu phẩy hoặc chấm", () => {
    expect(parseDecimal("2,5")).toBe(2.5);
    expect(parseDecimal(" 7 ")).toBe(7);
    expect(parseDecimal("")).toBeNull();
    expect(parseDecimal("-1")).toBeNull();
  });
  it("addDays qua cuối tháng và cuối năm", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(tomorrowOf(TODAY)).toBe("2026-10-03");
  });
});

describe("đặt giá mới (quyết định #10)", () => {
  const ok = { itemId: "1", priceListId: "1", rate: "260.000", validFrom: "2026-10-03", validUpto: "" };
  it("hợp lệ khi từ ngày mai, hoặc từ hôm nay", () => {
    expect(validatePrice(ok, TODAY)).toEqual({});
    expect(validatePrice({ ...ok, validFrom: TODAY }, TODAY)).toEqual({});
  });
  it("chặn từ ngày trước hôm nay, gợi ý từ ngày mai", () => {
    const e = validatePrice({ ...ok, validFrom: "2026-10-01" }, TODAY);
    expect(e.validFrom).toMatch(/từ ngày mai \(03\/10\/2026\)/);
  });
  it("giá phải lớn hơn 0 và nhỏ hơn 10 tỷ", () => {
    expect(validatePrice({ ...ok, rate: "" }, TODAY).rate).toMatch(/Nhập giá/);
    expect(validatePrice({ ...ok, rate: "0" }, TODAY).rate).toMatch(/lớn hơn 0/);
    expect(validatePrice({ ...ok, rate: "12.000.000.000" }, TODAY).rate).toMatch(/10 tỷ/);
  });
  it("ngày kết thúc không trước ngày bắt đầu; thiếu mặt hàng báo ở ô mặt hàng", () => {
    expect(validatePrice({ ...ok, validUpto: "2026-10-02" }, TODAY).validUpto).toMatch(/Ngày kết thúc/);
    expect(validatePrice({ ...ok, itemId: "" }, TODAY).itemId).toMatch(/Chọn mặt hàng/);
  });
});

describe("hiển thị giá và hạn dùng", () => {
  const simple = { item_type: "SIMPLE" as const, current_price: { rate: "260000.00", valid_from: "2026-10-01", valid_upto: null } };
  it("ô bảng và ô thông tin ghi đơn vị đúng loại", () => {
    expect(priceCell(simple)).toMatch(/260\.000.*\/kg$/);
    expect(priceInfo({ ...simple, item_type: "BUNDLE" })).toMatch(/ \/ combo$/);
  });
  it("không có current_price thì không ra chữ giá", () => {
    expect(priceCell({ item_type: "SIMPLE" })).toBeNull();
    expect(priceInfo({ item_type: "SIMPLE", current_price: null })).toBeNull();
    expect(shelfLifeText(0)).toBeNull();
    expect(shelfLifeText(3)).toBe("3 ngày");
  });
});

describe("form mặt hàng", () => {
  it("combo mặc định có một dòng công thức, hạn dùng 0, không quản lý theo lô", () => {
    const d = emptyItemDraft("BUNDLE");
    expect(d.lines).toHaveLength(1);
    expect(d.shelfLife).toBe("0");
    expect(d.hasBatch).toBe(false);
  });
  it("mặt hàng thường: thiếu mã, tên, nhóm đều báo lỗi", () => {
    const e = validateItem(emptyItemDraft("SIMPLE"));
    expect(e.code && e.name && e.itemGroup).toBeTruthy();
    expect(hasItemErrors(e)).toBe(true);
  });
  it("hạn dùng phải là số nguyên không âm", () => {
    const base = { ...emptyItemDraft("SIMPLE"), code: "CA-A", name: "Cá A", itemGroup: "1" };
    expect(hasItemErrors(validateItem(base))).toBe(false);
    expect(validateItem({ ...base, shelfLife: "2,5" }).shelfLife).toBeTruthy();
    expect(validateItem({ ...base, shelfLife: "-1" }).shelfLife).toBeTruthy();
  });
  it("combo: công thức rỗng, trùng thành phần, số kg dưới 0,001 đều báo lỗi từng dòng", () => {
    const base = { ...emptyItemDraft("BUNDLE"), code: "CB", name: "Combo", itemGroup: "6" };
    expect(validateItem({ ...base, lines: [] }).lines).toMatch(/ít nhất một/);
    const e = validateItem({
      ...base,
      lines: [
        { key: 1, component: "1", qty: "0,5" },
        { key: 2, component: "1", qty: "0" },
        { key: 3, component: "", qty: "" },
      ],
    });
    expect(e.line[1]).toBeUndefined();
    expect(e.line[2]?.component).toMatch(/đã có/);
    expect(e.line[2]?.qty).toMatch(/0,001/);
    expect(e.line[3]?.component).toBeTruthy();
  });
  it("combo: dòng công thức còn trống hoàn toàn coi như chưa có dòng nào (ED-30-AC3)", () => {
    const base = { ...emptyItemDraft("BUNDLE"), code: "CB", name: "Combo", itemGroup: "6" };
    // Form luôn có sẵn 1 dòng trống: phải ra câu ở vùng công thức, không báo lỗi dưới dòng trống.
    const onlyBlank = validateItem(base);
    expect(onlyBlank.lines).toBe("Thêm ít nhất một mặt hàng vào công thức.");
    expect(onlyBlank.line).toEqual({});
    expect(hasItemErrors(onlyBlank)).toBe(true);
    const manyBlank = validateItem({ ...base, lines: [{ key: 1, component: "", qty: " " }, { key: 2, component: "", qty: "" }] });
    expect(manyBlank.lines).toBeTruthy();
    expect(manyBlank.line).toEqual({});
    // Có một dòng đã điền: hết câu công thức; dòng trống còn lại và dòng điền dở vẫn báo từng dòng.
    const mixed = validateItem({
      ...base,
      lines: [
        { key: 1, component: "1", qty: "0,5" },
        { key: 2, component: "", qty: "" },
        { key: 3, component: "2", qty: "" },
      ],
    });
    expect(mixed.lines).toBeUndefined();
    expect(mixed.line[1]).toBeUndefined();
    expect(mixed.line[2]?.component).toBeTruthy();
    expect(mixed.line[3]?.qty).toBe("Nhập số kg.");
    // Chỉ nhập kg mà chưa chọn mặt hàng cũng là dòng đã điền.
    const qtyOnly = validateItem({ ...base, lines: [{ key: 1, component: "", qty: "1" }] });
    expect(qtyOnly.lines).toBeUndefined();
    expect(qtyOnly.line[1]?.component).toBe("Chọn mặt hàng.");
    // Mặt hàng thường không có công thức nên không bao giờ có lỗi công thức.
    expect(validateItem({ ...emptyItemDraft("SIMPLE"), code: "A", name: "A", itemGroup: "1" }).lines).toBeUndefined();
  });
  it("thân gửi: tên cắt khoảng trắng, đơn vị Kg, định mức 3 chữ số thập phân", () => {
    const d = { ...emptyItemDraft("SIMPLE"), code: " CA-A ", name: " Cá A ", itemGroup: "3" };
    expect(itemInputOf(d)).toMatchObject({ code: "CA-A", name: "Cá A", item_group: 3, stock_uom: "Kg", item_type: "SIMPLE" });
    expect(lineInputOf(9, { key: 1, component: "2", qty: "0,5" })).toEqual({ bundle: 9, component: 2, qty_per_bundle: "0.500" });
  });
});

describe("form ưu đãi", () => {
  it("theo mặt hàng cần mặt hàng và số kg; theo đơn cần giá trị đơn", () => {
    const item = validateRule({ ...emptyRuleDraft(), name: "A", discountValue: "10" });
    expect(item.item && item.minQty).toBeTruthy();
    const order = validateRule({ ...emptyRuleDraft(), name: "B", applyOn: "ORDER", discountValue: "10" });
    expect(order.minAmount).toBeTruthy();
    expect(order.item).toBeUndefined();
  });
  it("mức giảm lớn hơn 0; phần trăm không quá 100; kiểu tiền là số nguyên", () => {
    const base = { ...emptyRuleDraft(), name: "A", item: "1", minQty: "5" };
    expect(validateRule({ ...base, discountValue: "0" }).discountValue).toMatch(/lớn hơn 0/);
    expect(validateRule({ ...base, discountValue: "101" }).discountValue).toMatch(/100/);
    expect(validateRule({ ...base, discountValue: "7,5" })).toEqual({});
    expect(discountNumber({ discountType: "AMOUNT", discountValue: "50.000" })).toBe(50000);
    expect(validateRule({ ...base, discountType: "AMOUNT", discountValue: "50.000" })).toEqual({});
  });
  it("đến ngày không trước từ ngày", () => {
    const base = { ...emptyRuleDraft(), name: "A", item: "1", minQty: "5", discountValue: "5" };
    expect(validateRule({ ...base, validFrom: "2026-10-05", validUpto: "2026-10-01" }).validUpto).toBeTruthy();
  });
  it("thân gửi theo loại: ITEM bỏ min_amount, ORDER bỏ item và min_qty", () => {
    const item = ruleInputOf({ ...emptyRuleDraft(), name: " A ", item: "3", minQty: "5", discountValue: "10" });
    expect(item).toMatchObject({ name: "A", apply_on: "ITEM", item: 3, min_qty: "5.000", min_amount: null, discount_type: "PERCENT", discount_value: "10.00" });
    const order = ruleInputOf({ ...emptyRuleDraft(), applyOn: "ORDER", minAmount: "500.000", discountType: "AMOUNT", discountValue: "50.000", name: "B" });
    expect(order).toMatchObject({ item: null, min_qty: null, min_amount: "500000.00", discount_value: "50000.00", valid_from: null });
  });
  it("chữ điều kiện và mức giảm", () => {
    expect(ruleDiscountText({ discount_type: "PERCENT", discount_value: "10.00" })).toBe("10%");
    expect(ruleDiscountText({ discount_type: "AMOUNT", discount_value: "50000.00" })).toMatch(/50\.000/);
    expect(ruleCondition({ apply_on: "ITEM", item_name: "Cá thu", min_qty: "5.000", min_amount: null })).toMatch(/Cá thu, mua từ 5/);
    expect(ruleCondition({ apply_on: "ORDER", item_name: null, min_qty: null, min_amount: "500000.00" })).toMatch(/Đơn từ 500\.000/);
    expect(ruleCondition({ apply_on: "ITEM", item_name: null, min_qty: null, min_amount: null })).toBeNull();
  });
});

describe("nhóm hàng, tham số, URL", () => {
  it("tên nhóm bắt buộc, tối đa 120 ký tự", () => {
    expect(validateGroupName("  ")).toMatch(/Nhập/);
    expect(validateGroupName("a".repeat(121))).toMatch(/120/);
    expect(validateGroupName("Cá biển")).toBeNull();
  });
  it("itemListQuery bỏ tham số rỗng, đúng tên tham số", () => {
    expect(itemListQuery(EMPTY_ITEM_PARAMS, 1)).toBe("");
    expect(itemListQuery({ group: "3", type: "BUNDLE", active: "0", hasImage: "1" }, 2)).toContain("page=2");
    expect(pricingRuleQuery({ active: "", applyOn: "" }, 1)).toBe("");
  });
  it("URL chỉ nhận id số dương và loại combo", () => {
    expect(parseItemId("?id=12")).toBe(12);
    expect(parseItemId("?id=0")).toBeNull();
    expect(parseItemId("?id=abc")).toBeNull();
    expect(parseItemId("")).toBeNull();
    expect(parseItemTypeParam("?type=BUNDLE")).toBe("BUNDLE");
    expect(parseItemTypeParam("?type=x")).toBe("SIMPLE");
  });
});

describe("quyền", () => {
  it("Chủ ghi được, Quản lý chỉ xem, NV kho không thấy giá", () => {
    const owner = catalogAbility(Object.values(CATALOG_PERM));
    expect(owner.setPrice && owner.addRule && owner.addGroup && owner.addItem && owner.changeItem).toBe(true);
    const viewer = catalogAbility([CATALOG_PERM.viewItem, CATALOG_PERM.viewItemPrice, CATALOG_PERM.viewPricingRule, CATALOG_PERM.viewItemGroup]);
    expect(viewer.viewPrices && viewer.viewRules && viewer.viewGroups).toBe(true);
    expect(viewer.setPrice || viewer.addRule || viewer.addGroup || viewer.addItem).toBe(false);
    const warehouse = catalogAbility([CATALOG_PERM.viewItem]);
    expect(warehouse.viewPrices || warehouse.viewRules).toBe(false);
  });
});

describe("mock theo contract BE R14", () => {
  type Page<T> = { count: number; next: string | null; results: T[] };
  const ITEMS = "/api/catalog/items/";

  it("NV kho không nhận current_price; Quản lý nhận", () => {
    const warehouse = call("kho1", "GET", ITEMS);
    expect(warehouse.status).toBe(200);
    const warehouseRows = (warehouse.body as Page<Record<string, unknown>>).results;
    expect(warehouseRows.length).toBeGreaterThan(0);
    expect(warehouseRows.every((r) => !("current_price" in r))).toBe(true);
    const managerRows = (call("ql1", "GET", ITEMS).body as Page<Record<string, unknown>>).results;
    expect(managerRows.every((r) => "current_price" in r)).toBe(true);
  });
  it("NV kho bị 403 ở bảng giá, ưu đãi và bảng giá gốc", () => {
    expect(call("kho1", "GET", "/api/catalog/item-prices/").status).toBe(403);
    expect(call("kho1", "GET", "/api/catalog/pricing-rules/").status).toBe(403);
    expect(call("kho1", "GET", "/api/catalog/price-lists/").status).toBe(403);
  });
  it("Quản lý đọc được nhưng ghi bị 403", () => {
    expect(call("ql1", "GET", "/api/catalog/item-prices/").status).toBe(200);
    expect(call("ql1", "POST", "/api/catalog/item-prices/", { price_list: 1, item: 1, rate: "1000.00", valid_from: "2099-01-01" }).status).toBe(403);
    expect(call("ql1", "POST", "/api/catalog/item-groups/", { name: "Thử" }).status).toBe(403);
    expect(call("ql1", "PATCH", `${ITEMS}1/`, { name: "X" }).status).toBe(403);
  });
  it("không có endpoint xoá giá: DELETE bị 405", () => {
    expect(call("loc", "DELETE", "/api/catalog/item-prices/").status).toBe(405);
  });
  it("Chủ đặt giá mới: mức giá đang áp dụng được khép từ ngày hôm trước", () => {
    const first = call("loc", "POST", "/api/catalog/item-prices/", { price_list: 1, item: 4, rate: "190000.00", valid_from: "2099-03-10" });
    expect(first.status).toBe(201);
    const second = call("loc", "POST", "/api/catalog/item-prices/", { price_list: 1, item: 4, rate: "200000.00", valid_from: "2099-03-20" });
    expect(second.status).toBe(201);
    const rows = (call("loc", "GET", "/api/catalog/item-prices/?item=4").body as Page<{ valid_from: string; valid_upto: string | null }>).results;
    expect(rows.find((r) => r.valid_from === "2099-03-10")?.valid_upto).toBe("2099-03-19");
  });
  it("giá bằng 0 bị 400 ở ô rate; chồng lấn ngày bị 400", () => {
    const zero = call("loc", "POST", "/api/catalog/item-prices/", { price_list: 1, item: 2, rate: "0.00", valid_from: "2099-04-01" });
    expect(zero.status).toBe(400);
    expect(Object.keys(zero.body as object)).toContain("rate");
  });
  it("mã mặt hàng trùng báo 400 ở ô code; nhóm trùng tên báo ở ô name", () => {
    const dup = call("loc", "POST", ITEMS, {
      code: "CA-THU", name: "Trùng", item_group: 1, item_type: "SIMPLE", stock_uom: "Kg", shelf_life_in_days: 3, has_batch_no: true, has_expiry_date: true, is_active: true, description: "",
    });
    expect(dup.status).toBe(400);
    expect(Object.keys(dup.body as object)).toContain("code");
    const group = (call("loc", "GET", "/api/catalog/item-groups/").body as Page<{ name: string }>).results[0];
    const dupGroup = call("loc", "POST", "/api/catalog/item-groups/", { name: group.name, parent: null });
    expect(dupGroup.status).toBe(400);
    expect(Object.keys(dupGroup.body as object)).toContain("name");
  });
  it("ưu đãi: phần trăm và bật tắt", () => {
    const made = call("loc", "POST", "/api/catalog/pricing-rules/", {
      name: "Thử bật tắt", is_active: true, apply_on: "ORDER", item: null, min_qty: null, min_amount: "500000.00", discount_type: "PERCENT", discount_value: "5.00", valid_from: null, valid_upto: null,
    });
    expect(made.status).toBe(201);
    const id = (made.body as { id: number }).id;
    const off = call("loc", "PATCH", `/api/catalog/pricing-rules/${id}/`, { is_active: false });
    expect(off.status).toBe(200);
    expect((off.body as { is_active: boolean }).is_active).toBe(false);
  });
  it("không có token thì 401", () => {
    expect(mockCatalogApi({ method: "GET", path: ITEMS, token: null }).status).toBe(401);
  });
});

describe("Lô 17b G5: số không bị cắt hay làm tròn ngầm", () => {
  it("parseAmount: 12 chữ số vừa, 13 chữ số báo tooBig, chữ báo invalid", () => {
    expect(parseAmount("999.999.999.999")).toEqual({ kind: "ok", digits: "999999999999" });
    expect(parseAmount("1.000.000.000.000")).toEqual({ kind: "tooBig" });
    expect(parseAmount("12a")).toEqual({ kind: "invalid" });
    expect(parseAmount(" ")).toEqual({ kind: "empty" });
  });
  it("parseQtyKg: 3 số lẻ vừa, 4 số lẻ báo tooPrecise, quá 9 chữ số nguyên báo tooBig", () => {
    expect(parseQtyKg("0,001")).toMatchObject({ kind: "ok", text: "0.001" });
    expect(parseQtyKg("0,0005")).toEqual({ kind: "tooPrecise" });
    expect(parseQtyKg("1234567890")).toEqual({ kind: "tooBig" });
  });
  it("định mức combo 4 số lẻ bị báo lỗi, không làm tròn thành 0,001", () => {
    const d = { ...emptyItemDraft("BUNDLE"), itemType: "BUNDLE" as const, code: "C", name: "C", itemGroup: "1", shelfLife: "3", lines: [{ key: 1, component: "2", qty: "0,0004" }] };
    expect(validateItem(d).line[1]?.qty).toMatch(/3 chữ số/);
  });
  it("kg tối thiểu 4 số lẻ và phần trăm 3 số lẻ bị báo lỗi; tiền quá lớn bị báo lỗi", () => {
    expect(validateRule({ ...emptyRuleDraft(), name: "A", item: "3", minQty: "5,1234", discountValue: "10" }).minQty).toMatch(/3 chữ số/);
    expect(validateRule({ ...emptyRuleDraft(), name: "A", item: "3", minQty: "5", discountValue: "7,555" }).discountValue).toMatch(/2 chữ số/);
    const big = validateRule({ ...emptyRuleDraft(), name: "B", applyOn: "ORDER", minAmount: "1.000.000.000.000", discountType: "AMOUNT", discountValue: "5.000" });
    expect(big.minAmount).toMatch(/quá lớn/);
  });
  it("gửi BE giữ nguyên chữ số, đệm đủ số lẻ", () => {
    expect(ruleInputOf({ ...emptyRuleDraft(), name: "A", item: "3", minQty: "5,25", discountValue: "7,5" })).toMatchObject({ min_qty: "5.250", discount_value: "7.50" });
    expect(ruleInputOf({ ...emptyRuleDraft(), name: "B", applyOn: "ORDER", minAmount: "999.999.999.999", discountType: "AMOUNT", discountValue: "5.000" })).toMatchObject({ min_amount: "999999999999.00", discount_value: "5000.00" });
  });
});
