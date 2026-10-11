// Mã giảm giá (SHOP-3b-02, 02b §3.9, BR-DM-22): kiểm form, thân gửi, khoá trường khi mã đã chạy, đọc lỗi của BE, quyền và menu.
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { canView, menuItems, PERM, type Viewer } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { catalogAbility } from "./permissions";
import type { Voucher } from "./types";
import {
  draftOfVoucher,
  emptyVoucherDraft,
  hasLongDigitRun,
  isoToVnInput,
  lockedFields,
  serverFieldMessages,
  unfavorableChanges,
  validateDisable,
  validateVoucher,
  voucherDiscountText,
  voucherInputOf,
  voucherPatchOf,
  voucherServerErrors,
  type VoucherDraft,
} from "./voucherModel";

const NOW = Date.parse("2026-10-20T03:00:00Z");

const RUNNING: Voucher = {
  id: 7,
  code: "CAVE10",
  name: "Khai trương",
  kind: "PERCENT",
  value: "10",
  max_discount: "50000",
  min_order_amount: "300000",
  starts_at: "2026-10-15T01:00:00Z",
  ends_at: "2026-10-31T16:59:00Z",
  total_uses: 100,
  used_count: 30,
  held_count: 2,
  status: "running",
  is_active: true,
  disabled_reason: "",
  disabled_note: "",
  customer_terms: "Áp dụng cho đơn đặt trên web.",
  created_at: "2026-10-01T00:00:00Z",
};
const SCHEDULED: Voucher = { ...RUNNING, id: 8, status: "scheduled", starts_at: "2026-11-01T01:00:00Z", ends_at: "2026-11-30T16:59:00Z", used_count: 0, held_count: 0 };

const GOOD: VoucherDraft = {
  code: "cave 10",
  name: "Khai trương",
  kind: "PERCENT",
  value: "10",
  maxDiscount: "50.000",
  minOrderAmount: "300.000",
  startsAt: "2026-10-15T08:00",
  endsAt: "2026-10-31T23:59",
  totalUses: "100",
  customerTerms: "",
};

describe("validateVoucher", () => {
  it("nháp đúng thì không lỗi; mã tự IN HOA, bỏ khoảng trắng", () => {
    expect(validateVoucher(GOOD)).toEqual({});
    expect(voucherInputOf(GOOD).code).toBe("CAVE10");
  });

  it("mã sai dạng, mã chứa dãy 9 chữ số", () => {
    expect(validateVoucher({ ...GOOD, code: "AB" }).code).toBeTruthy();
    expect(validateVoucher({ ...GOOD, code: "KM-10" }).code).toBeTruthy();
    expect(validateVoucher({ ...GOOD, code: "A0900000001" }).code).toBeTruthy();
    expect(hasLongDigitRun("gọi 0900 000 001")).toBe(true);
    expect(hasLongDigitRun("đơn từ 300.000")).toBe(false);
  });

  it("phần trăm cần mức giảm tối đa; số tiền thì không", () => {
    expect(validateVoucher({ ...GOOD, maxDiscount: "" }).maxDiscount).toBeTruthy();
    expect(validateVoucher({ ...GOOD, value: "101" }).value).toBeTruthy();
    expect(validateVoucher({ ...GOOD, value: "0" }).value).toBeTruthy();
    expect(validateVoucher({ ...GOOD, kind: "AMOUNT", value: "50.000", maxDiscount: "" })).toEqual({});
    expect(voucherInputOf({ ...GOOD, kind: "AMOUNT", value: "50.000", maxDiscount: "" }).max_discount).toBeNull();
  });

  it("giờ kết thúc phải sau giờ bắt đầu; lượt từ 1; điều kiện không có số điện thoại", () => {
    expect(validateVoucher({ ...GOOD, endsAt: "2026-10-15T08:00" }).endsAt).toBeTruthy();
    expect(validateVoucher({ ...GOOD, startsAt: "" }).startsAt).toBeTruthy();
    expect(validateVoucher({ ...GOOD, totalUses: "0" }).totalUses).toBeTruthy();
    expect(validateVoucher({ ...GOOD, customerTerms: "Gọi 0900000001 để hỏi" }).customerTerms).toBeTruthy();
    expect(validateVoucher({ ...GOOD, customerTerms: "x".repeat(301) }).customerTerms).toBeTruthy();
  });
});

describe("giờ GMT+7 (không theo giờ máy)", () => {
  it("giờ nhập 08:00 VN gửi đi là 01:00Z; 23:59 VN là 16:59Z", () => {
    const body = voucherInputOf(GOOD);
    expect(body.starts_at).toBe("2026-10-15T01:00:00.000Z");
    expect(body.ends_at).toBe("2026-10-31T16:59:00.000Z");
  });
  it("ISO hiển thị lại ra đúng giờ VN trong ô nhập", () => {
    expect(isoToVnInput("2026-10-15T01:00:00Z")).toBe("2026-10-15T08:00");
    expect(isoToVnInput("2026-10-31T16:59:00Z")).toBe("2026-10-31T23:59");
    expect(draftOfVoucher(RUNNING).startsAt).toBe("2026-10-15T08:00");
  });
});

describe("sửa mã đang chạy (BR-DM-22)", () => {
  it("khoá code, kind luôn; từ starts_at khoá thêm giờ bắt đầu và điều kiện khách", () => {
    expect([...lockedFields(SCHEDULED, NOW)].sort()).toEqual(["code", "kind"]);
    expect([...lockedFields(RUNNING, NOW)].sort()).toEqual(["code", "customerTerms", "kind", "startsAt"]);
  });

  it("đổi theo hướng có lợi thì qua, ngược hướng thì báo", () => {
    const base = draftOfVoucher(RUNNING);
    expect(unfavorableChanges(RUNNING, base)).toEqual({});
    expect(unfavorableChanges(RUNNING, { ...base, totalUses: "150", minOrderAmount: "200.000", value: "12", maxDiscount: "60.000", endsAt: "2026-11-05T23:59" })).toEqual({});
    const bad = unfavorableChanges(RUNNING, { ...base, totalUses: "50", minOrderAmount: "400.000", value: "8", maxDiscount: "40.000", endsAt: "2026-10-20T23:59" });
    expect(Object.keys(bad).sort()).toEqual(["endsAt", "maxDiscount", "minOrderAmount", "totalUses", "value"]);
  });

  it("PATCH chỉ chứa trường đổi, không có trường khoá", () => {
    const base = draftOfVoucher(RUNNING);
    expect(voucherPatchOf(RUNNING, base, NOW)).toEqual({});
    expect(voucherPatchOf(RUNNING, { ...base, totalUses: "150", name: "Khai trương mới" }, NOW)).toEqual({ name: "Khai trương mới", total_uses: 150 });
    // Trước starts_at: sửa tự do kể cả giờ bắt đầu và điều kiện khách.
    const sched = draftOfVoucher(SCHEDULED);
    const patch = voucherPatchOf(SCHEDULED, { ...sched, startsAt: "2026-11-02T08:00", customerTerms: "Mới" }, NOW);
    expect(patch).toEqual({ starts_at: "2026-11-02T01:00:00.000Z", customer_terms: "Mới" });
    expect("code" in patch || "kind" in patch).toBe(false);
  });
});

describe("lỗi của BE theo trường", () => {
  it("VALIDATION có fields dạng object", () => {
    const err = new ApiError("Thông tin mã giảm giá chưa hợp lệ.", 400, "VALIDATION", { fields: { code: "Mã này đã có. Chọn mã khác.", max_discount: ["Cần mức tối đa."] } });
    expect(voucherServerErrors(err)).toEqual({ code: "Mã này đã có. Chọn mã khác.", maxDiscount: "Cần mức tối đa." });
  });
  it("UNFAVORABLE_CHANGE và FIELD_LOCKED có fields dạng mảng: gắn câu chung vào từng ô", () => {
    const err = new ApiError("Mã đang chạy chỉ sửa được theo hướng có lợi cho khách. Tắt mã này và tạo mã mới.", 400, "UNFAVORABLE_CHANGE", { fields: ["min_order_amount"] });
    expect(voucherServerErrors(err)).toEqual({ minOrderAmount: err.message });
    expect(serverFieldMessages(err)).toEqual({ min_order_amount: err.message });
  });
  it("lỗi không phải 400 hoặc không có fields thì rỗng", () => {
    expect(voucherServerErrors(new ApiError("x", 500))).toEqual({});
    expect(voucherServerErrors(new Error("x"))).toEqual({});
    expect(voucherServerErrors(new ApiError("x", 400, "VALIDATION", {}))).toEqual({});
  });
});

describe("tắt mã", () => {
  it("bắt buộc lý do; OTHER bắt buộc ghi chú; ghi chú không có dãy 9 chữ số", () => {
    expect(validateDisable({ reason: "", note: "" }).reason).toBeTruthy();
    expect(validateDisable({ reason: "BUDGET", note: "" })).toEqual({});
    expect(validateDisable({ reason: "OTHER", note: "  " }).note).toBeTruthy();
    expect(validateDisable({ reason: "OTHER", note: "Khách phản ánh sai mức" })).toEqual({});
    expect(validateDisable({ reason: "OTHER", note: "gọi 0900000001" }).note).toBeTruthy();
    expect(validateDisable({ reason: "OTHER", note: "x".repeat(201) }).note).toBeTruthy();
  });
});

describe("hiển thị mức giảm", () => {
  it("phần trăm kèm trần, số tiền", () => {
    expect(voucherDiscountText({ kind: "PERCENT", value: "10.00", max_discount: "50000" })).toContain("10%");
    expect(voucherDiscountText({ kind: "PERCENT", value: "10", max_discount: "50000" })).toContain("50.000");
    expect(voucherDiscountText({ kind: "AMOUNT", value: "30000", max_discount: null })).toBe("30.000 đ");
  });
});

describe("quyền và menu (catalog.manage_voucher)", () => {
  const viewer = (over: Partial<Viewer>): Viewer => ({ groups: [], permissions: [], can_view_profit: false, home: "dashboard", ...over });
  const OWNER = viewer({ groups: [ROLE.owner], permissions: [PERM.viewItem, PERM.manageVoucher] });
  const MANAGER = viewer({ groups: [ROLE.manager], permissions: [PERM.viewItem, PERM.viewItemPrice] });

  it("chỉ người có quyền thấy menu và vào được màn", () => {
    expect(canView(OWNER, "vouchers")).toBe(true);
    expect(menuItems(OWNER).map((n) => n.key)).toContain("vouchers");
    expect(canView(MANAGER, "vouchers")).toBe(false);
    expect(menuItems(MANAGER).map((n) => n.key)).not.toContain("vouchers");
  });

  it("mã quyền khớp 02b §3.9 và catalogAbility", () => {
    expect(PERM.manageVoucher).toBe("catalog.manage_voucher");
    expect(catalogAbility([PERM.manageVoucher]).manageVoucher).toBe(true);
    expect(catalogAbility([PERM.viewItem]).manageVoucher).toBe(false);
  });

  it("nháp rỗng mặc định là giảm phần trăm", () => {
    expect(emptyVoucherDraft().kind).toBe("PERCENT");
  });
});
