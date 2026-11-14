// FISH-66 S5, S6: kiểm thử đơn vị cho itemFilesModel.ts (kiểm file ở máy, tách bảng M3, sắp xếp |Chênh %|, đếm cờ giá, câu chữ M5/T4).
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import {
  countPriceFlags,
  extractAlreadyAppliedCounts,
  extractRowErrors,
  formatActionBarSummary,
  formatConfirmSubmitLabel,
  formatConfirmTitle,
  formatImportSuccessToast,
  formatPriceDiffAmount,
  formatPriceDiffPercent,
  formatPriceHeaderSummary,
  groupReadonlyWarnings,
  groupValidFromSummary,
  shopStateLabel,
  sortPriceRows,
  splitPreviewSections,
  validateImportFile,
} from "./itemFilesModel";
import {
  IMPORT_ALREADY_APPLIED,
  IMPORT_INVALID_ROWS,
  type ImportPreviewRow,
  type ImportSummary,
} from "./itemFilesTypes";

const SAMPLE_ROWS: ImportPreviewRow[] = [
  {
    row: 3,
    code: "CA-01",
    action: "update",
    name: "Cá thu cắt khúc",
    item_group: "Cá biển",
    changes: [{ field: "name", label: "Tên", old: "Cá thu", new: "Cá thu cắt khúc" }],
    price: null,
    is_active_after: true,
    shop_state: "selling",
  },
  {
    row: 4,
    code: "TOM-02",
    action: "update",
    name: "Tôm sú",
    item_group: "Tôm",
    changes: [],
    price: {
      old: "278000",
      new: "265000",
      valid_from: "2026-11-15",
      change_amount: "-13000",
      change_percent: "-4.7",
      flags: [],
    },
    is_active_after: true,
    shop_state: "selling",
  },
  {
    row: 17,
    code: "CA-07",
    action: "update",
    name: "Cá thu một nắng",
    item_group: "Cá biển",
    changes: [],
    price: {
      old: "185000",
      new: "18500",
      valid_from: "2026-11-14",
      change_amount: "-166500",
      change_percent: "-90.0",
      flags: ["check_zeros", "large_change"],
    },
    is_active_after: true,
    shop_state: "selling",
  },
  {
    row: 23,
    code: "MUC-03",
    action: "update",
    name: "Mực lá",
    item_group: "Mực",
    changes: [],
    price: {
      old: "240000",
      new: "320000",
      valid_from: "2026-11-10",
      change_amount: "80000",
      change_percent: "33.3",
      flags: ["large_change", "backdated"],
    },
    is_active_after: false,
    shop_state: "hidden",
  },
  {
    row: 30,
    code: "GHE-01",
    action: "update",
    name: "Ghẹ xanh",
    item_group: "Cua ghẹ",
    changes: [{ field: "is_active", label: "Đang kinh doanh", old: "Có", new: "Không" }],
    price: null,
    is_active_after: false,
    shop_state: "will_hide",
  },
  {
    row: 201,
    code: "MUC-09",
    action: "create",
    name: "Mực ống",
    item_group: "Mực",
    changes: [],
    price: {
      old: null,
      new: "180000",
      valid_from: "2026-11-14",
      change_amount: null,
      change_percent: null,
      flags: [],
    },
    is_active_after: true,
    shop_state: "will_show",
  },
];

const SAMPLE_SUMMARY: ImportSummary = {
  total_rows: 200,
  created: 1,
  updated: 1,
  price_changed: 4,
  visibility_changed: 1,
  unchanged: 195,
  will_show_on_shop: 1,
  will_hide_from_shop: 1,
};

describe("validateImportFile", () => {
  it("chấp nhận file .xlsx trong giới hạn dung lượng", () => {
    const f = new File(["pk"], "hang-ban.xlsx");
    expect(validateImportFile(f, { max_rows: 1000, max_bytes: 1024 })).toBeNull();
  });

  it("chặn file khác .xlsx (.csv, .xls, .xlsm)", () => {
    expect(validateImportFile(new File(["a"], "data.csv"))).toContain("Chỉ nhận file .xlsx");
    expect(validateImportFile(new File(["a"], "data.xls"))).toContain("Chỉ nhận file .xlsx");
    expect(validateImportFile(new File(["a"], "data.xlsm"))).toContain("Chỉ nhận file .xlsx");
  });

  it("chặn file vượt quá max_bytes", () => {
    const big = new File([new Uint8Array(2048)], "lon.xlsx");
    expect(validateImportFile(big, { max_rows: 1000, max_bytes: 1024 })).toContain("File quá");
  });
});

describe("tách phần và sắp xếp bảng Đổi giá ở M3", () => {
  it("tách đúng 4 bảng: Đổi giá, Ẩn/hiện, Món mới, Món sửa", () => {
    const { priceRows, visibilityRows, newItemRows, updatedFieldRows } = splitPreviewSections(SAMPLE_ROWS);
    expect(priceRows.map((r) => r.code)).toEqual(["TOM-02", "CA-07", "MUC-03", "MUC-09"]);
    expect(visibilityRows.map((v) => v.code)).toEqual(["GHE-01"]);
    expect(newItemRows.map((r) => r.code)).toEqual(["MUC-09"]);
    expect(updatedFieldRows.map((u) => `${u.code}:${u.field}`)).toEqual(["CA-01:name"]);
  });

  it("sắp mặc định theo |Chênh %| giảm dần, món mới chưa có giá cũ xuống cuối", () => {
    const { priceRows } = splitPreviewSections(SAMPLE_ROWS);
    const byPct = sortPriceRows(priceRows, "percent");
    expect(byPct.map((r) => r.code)).toEqual(["CA-07", "MUC-03", "TOM-02", "MUC-09"]);

    const byRow = sortPriceRows(priceRows, "row");
    expect(byRow.map((r) => r.code)).toEqual(["TOM-02", "CA-07", "MUC-03", "MUC-09"]);
  });

  it("đếm cờ giá và tạo dòng tóm tắt đầu bảng Đổi giá", () => {
    const { priceRows } = splitPreviewSections(SAMPLE_ROWS);
    const flags = countPriceFlags(priceRows);
    expect(flags.total).toBe(4);
    expect(flags.checkZeros).toBe(1);
    expect(flags.largeChange).toBe(2);
    expect(flags.backdated).toBe(1);
    expect(flags.flaggedRows.map((r) => r.code)).toEqual(["CA-07", "MUC-03"]);
    expect(formatPriceHeaderSummary(priceRows)).toBe(
      "4 giá mới · 1 cần kiểm lại số 0 · 2 chênh lớn · 1 lùi ngày",
    );
  });
});

describe("định dạng hiển thị chênh lệch giá, ngày áp dụng, câu chữ M5 và T4", () => {
  it("định dạng mũi tên ▲/▼ và dấu +/− cho Chênh lệch và Chênh %", () => {
    expect(formatPriceDiffAmount("80000")).toBe("▲ +80.000 đ");
    expect(formatPriceDiffAmount("-166500")).toBe("▼ −166.500 đ");
    expect(formatPriceDiffAmount(null)).toBe("—");

    expect(formatPriceDiffPercent("33.3")).toBe("▲ +33,3%");
    expect(formatPriceDiffPercent("-90.0")).toBe("▼ −90,0%");
    expect(formatPriceDiffPercent(null)).toBe("—");
  });

  it("nhãn trạng thái trên Shop và gộp ngày áp dụng giá cho M5", () => {
    expect(shopStateLabel("selling")).toBe("Đang bán");
    expect(shopStateLabel("will_show")).toBe("Sẽ hiện");
    expect(shopStateLabel("will_hide")).toBe("Sẽ ẩn");
    expect(shopStateLabel("hidden")).toBe("Đang ẩn");

    const { priceRows } = splitPreviewSections(SAMPLE_ROWS);
    expect(groupValidFromSummary(priceRows)).toBe(
      "10/11/2026 (1 món), 14/11/2026 (2 món), 15/11/2026 (1 món)",
    );
  });

  it("tiêu đề hộp xác nhận M5, nút chính và toast T4", () => {
    expect(formatActionBarSummary(SAMPLE_SUMMARY)).toBe("4 giá mới · 1 món mới · 1 món sửa · 1 đổi ẩn/hiện");
    expect(formatConfirmTitle(SAMPLE_SUMMARY)).toBe("Nhập 4 giá mới, 1 món mới, 1 món sửa?");
    expect(formatConfirmSubmitLabel(SAMPLE_SUMMARY)).toBe("Xác nhận nhập 4 giá mới");
    expect(
      formatConfirmSubmitLabel({
        ...SAMPLE_SUMMARY,
        price_changed: 0,
      }),
    ).toBe("Xác nhận nhập 3 thay đổi");
    expect(
      formatImportSuccessToast({
        created: 1,
        updated: 0,
        price_changed: 2,
      }),
    ).toBe("Đã nhập: 1 món mới, 2 giá mới.");
  });

  it("gộp cảnh báo cột chỉ đọc và đọc lỗi dòng / 409 IMPORT_ALREADY_APPLIED", () => {
    const grouped = groupReadonlyWarnings([
      { row: 12, code: "CA-03", column: "Giá bán hiện hành", message: "m" },
      { row: 5, code: "CA-01", column: "Giá bán hiện hành", message: "m" },
    ]);
    expect(grouped).toHaveLength(1);
    expect(grouped[0].rows).toEqual([5, 12]);
    expect(grouped[0].text).toContain("2 dòng có sửa ở cột Giá bán hiện hành");
    expect(grouped[0].text).toContain("Dòng: 5, 12.");

    const rowErr = new ApiError("File có 2 lỗi", 400, IMPORT_INVALID_ROWS, {
      error_count: 2,
      error_row_count: 2,
      errors_truncated: false,
      errors: [
        { row: 9, code: "B", column: "Giá mới", message: "Lỗi 2" },
        { row: 3, code: "A", column: "Tên", message: "Lỗi 1" },
      ],
    });
    const extracted = extractRowErrors(rowErr);
    expect(extracted?.error_count).toBe(2);
    expect(extracted?.errors.map((e) => e.row)).toEqual([3, 9]);

    const dupErr = new ApiError("Đã ghi", 409, IMPORT_ALREADY_APPLIED, {
      created: 1,
      updated: 2,
      price_changed: 3,
      visibility_changed: 0,
    });
    expect(extractAlreadyAppliedCounts(dupErr)).toEqual({
      created: 1,
      updated: 2,
      price_changed: 3,
      visibility_changed: 0,
    });
  });
});
