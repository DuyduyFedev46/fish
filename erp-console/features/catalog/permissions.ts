// Quyền Django của màn Danh mục & giá (Lô 13). BE là lớp chặn thật (BusinessModelPermissions); FE chỉ ẩn nút cho gọn.
// Chủ có đủ; Quản lý chỉ xem (kể cả giá); NV kho chỉ xem mặt hàng và nhóm hàng, không thấy giá hay ưu đãi (T9).

export const CATALOG_PERM = {
  viewItem: "catalog.view_item",
  addItem: "catalog.add_item",
  changeItem: "catalog.change_item",
  changeItemImage: "catalog.change_item_image",
  viewItemPrice: "catalog.view_itemprice",
  addItemPrice: "catalog.add_itemprice",
  viewPriceList: "catalog.view_pricelist",
  viewPricingRule: "catalog.view_pricingrule",
  addPricingRule: "catalog.add_pricingrule",
  changePricingRule: "catalog.change_pricingrule",
  viewItemGroup: "catalog.view_itemgroup",
  addItemGroup: "catalog.add_itemgroup",
  changeItemGroup: "catalog.change_itemgroup",
  addBundleLine: "catalog.add_bundleline",
} as const;

/** Quyền người đang xem có, gom theo việc màn cần quyết định. */
export type CatalogAbility = {
  viewPrices: boolean;
  viewRules: boolean;
  viewGroups: boolean;
  addItem: boolean;
  changeItem: boolean;
  changeImage: boolean;
  setPrice: boolean;
  addRule: boolean;
  changeRule: boolean;
  addGroup: boolean;
  changeGroup: boolean;
};

export function catalogAbility(perms: readonly string[]): CatalogAbility {
  const has = (p: string) => perms.includes(p);
  return {
    viewPrices: has(CATALOG_PERM.viewItemPrice),
    viewRules: has(CATALOG_PERM.viewPricingRule),
    viewGroups: has(CATALOG_PERM.viewItemGroup),
    addItem: has(CATALOG_PERM.addItem),
    changeItem: has(CATALOG_PERM.changeItem),
    changeImage: has(CATALOG_PERM.changeItemImage),
    setPrice: has(CATALOG_PERM.addItemPrice),
    addRule: has(CATALOG_PERM.addPricingRule),
    changeRule: has(CATALOG_PERM.changePricingRule),
    addGroup: has(CATALOG_PERM.addItemGroup),
    changeGroup: has(CATALOG_PERM.changeItemGroup),
  };
}
