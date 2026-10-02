import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { mockStocktakeApi } from "./mock";
import {
  changedLineCount,
  checkRows,
  cleanMessage,
  detailHref,
  diffTone,
  editHref,
  idFromSearch,
  lineErrorOf,
  nextStepText,
  PATH_STEPS,
  parseCount,
  previewDiff,
  qty,
  qtyText,
  signedQty,
  signedQtyText,
  summarize,
  toLineInputs,
  toMilli,
  warehouseText,
  type FormRow,
} from "./stocktakeUi";
import { mergeLoaded } from "./components/StocktakeForm";
import type { StocktakeDetail, StocktakeListItem } from "./types";

const row = (over: Partial<FormRow> = {}): FormRow => ({
  batch: 1,
  batchCode: "L1",
  itemName: "Cá",
  warehouseName: "Kho A",
  systemMilli: 10000,
  counted: "",
  reason: "",
  ...over,
});

describe("stocktakeUi: đọc số kg", () => {
  it("nhận dấu phẩy và dấu chấm, đổi ra phần nghìn", () => {
    expect(toMilli("12,5")).toBe(12500);
    expect(toMilli("12.500")).toBe(12500);
    expect(toMilli("")).toBeNull();
    expect(toMilli("abc")).toBeNull();
  });
  it("parseCount: trống / hợp lệ / âm / chữ / quá 3 chữ số lẻ", () => {
    expect(parseCount("  ")).toEqual({ kind: "empty" });
    expect(parseCount("12,5")).toEqual({ kind: "ok", milli: 12500, wire: "12.500" });
    expect(parseCount("0")).toEqual({ kind: "ok", milli: 0, wire: "0.000" });
    expect(parseCount("-1")).toMatchObject({ kind: "error", message: "Số đếm phải từ 0 kg trở lên." });
    expect(parseCount("1a")).toMatchObject({ kind: "error" });
    expect(parseCount("1,2345")).toMatchObject({ kind: "error" });
  });
  it("hiển thị kg dấu phẩy, chênh lệch có dấu trừ thật", () => {
    expect(qty(18500)).toBe("18,5");
    expect(qtyText("18.500")).toBe("18,5");
    expect(qtyText(null)).toBe("—");
    expect(signedQty(-250)).toBe("−0,25");
    expect(signedQty(300)).toBe("+0,3");
    expect(signedQty(0)).toBe("0");
    expect(signedQtyText("-0.400")).toBe("−0,4");
    expect(diffTone(-1)).toBe("crit");
    expect(diffTone(1)).toBe("warn");
    expect(diffTone(0)).toBe("");
  });
});

describe("stocktakeUi: kiểm dòng trước khi gửi", () => {
  it("đếm nhiều hơn sổ mà không ghi lý do thì lỗi ở ô lý do (BR-KK-04); đếm ít hơn không cần lý do", () => {
    const over = checkRows([row({ counted: "11" })], false);
    expect(over.errors[0].reason).toMatch(/ghi lý do/);
    expect(checkRows([row({ counted: "11", reason: "Nhập thiếu phiếu" })], false).hasError).toBe(false);
    expect(checkRows([row({ counted: "9" })], false).hasError).toBe(false);
  });
  it("số âm báo lỗi; trùng lô báo lỗi ở dòng sau", () => {
    expect(checkRows([row({ counted: "-1" })], false).errors[0].counted).toMatch(/từ 0 kg/);
    const dup = checkRows([row({ counted: "1" }), row({ counted: "2" })], false);
    expect(dup.errors[1].counted).toMatch(/đã có ở dòng trên/);
  });
  it("Lưu nháp cho phép dòng trống, Gửi duyệt đòi đủ", () => {
    const rows = [row({ batch: 1, counted: "10" }), row({ batch: 2 })];
    expect(checkRows(rows, false).hasError).toBe(false);
    expect(checkRows(rows, true).errors[1].counted).toMatch(/Nhập số đếm/);
    expect(checkRows(rows, false)).toMatchObject({ countedRows: 1, emptyRows: 1 });
  });
  it("lý do quá 500 ký tự báo lỗi", () => {
    expect(checkRows([row({ counted: "9", reason: "x".repeat(501) })], false).errors[0].reason).toMatch(/500/);
  });
  it("chỉ gửi dòng đã đếm, đúng thứ tự, số kèm 3 chữ số lẻ", () => {
    const rows = [row({ batch: 5, counted: "1,5" }), row({ batch: 6 }), row({ batch: 7, counted: "0", reason: " ghi " })];
    expect(toLineInputs(rows)).toEqual([
      { batch: 5, counted_qty: "1.500", reason: "" },
      { batch: 7, counted_qty: "0.000", reason: "ghi" },
    ]);
  });
  it("xem trước chênh lệch và tóm tắt", () => {
    expect(previewDiff(row({ counted: "9,75" }))).toBe(-250);
    expect(previewDiff(row())).toBeNull();
    const sum = summarize([row({ batch: 1, counted: "9" }), row({ batch: 2, counted: "10,5" }), row({ batch: 3, counted: "10" })]);
    expect(sum).toMatchObject({ short: 1, over: 1, match: 1, shortMilli: 1000, overMilli: 500, netMilli: -500 });
  });
});

describe("stocktakeUi: nạp lô theo kho", () => {
  const batch = (id: number) => ({ id, batch_id: `L${id}`, item_name: "Cá", warehouse: 1, warehouse_name: "Kho A", qty_available: "10.000" });
  it("giữ dòng đã gõ, bỏ dòng chưa chạm, không trùng lô", () => {
    const cur = [row({ batch: 1, counted: "5" }), row({ batch: 2 })];
    const merged = mergeLoaded(cur, [batch(1), batch(3)]);
    expect(merged.map((r) => r.batch)).toEqual([1, 3]);
    expect(merged[0].counted).toBe("5");
    expect(mergeLoaded(merged, [batch(1), batch(3)]).map((r) => r.batch)).toEqual([1, 3]);
  });
});

describe("stocktakeUi: lỗi của BE và đường dẫn", () => {
  it("bỏ mã nghiệp vụ trong ngoặc", () => {
    expect(cleanMessage("Lô L1 đếm nhiều hơn sổ, cần ghi lý do (BR-KK-04).")).toBe("Lô L1 đếm nhiều hơn sổ, cần ghi lý do.");
  });
  it("lineErrorOf lấy line_index và làm sạch câu", () => {
    const err = new ApiError("Dòng sai (BR-KK-04)", 400, "BR-KK-04", { line_index: 2 });
    expect(lineErrorOf(err)).toEqual({ index: 2, message: "Dòng sai" });
    expect(lineErrorOf(new ApiError("x", 400, "X", {}))).toBeNull();
    expect(lineErrorOf(new Error("x"))).toBeNull();
  });
  it("idFromSearch chỉ nhận số nguyên dương; đường dẫn chỉ mang id", () => {
    expect(idFromSearch("12")).toBe(12);
    expect(idFromSearch("0")).toBeNull();
    expect(idFromSearch("1e3")).toBeNull();
    expect(idFromSearch(null)).toBeNull();
    expect(detailHref(3)).toBe("/stocktake/detail/?id=3");
    expect(editHref(3)).toBe("/stocktake/edit/?id=3");
  });
  it("cột Kho: một ô một giá trị", () => {
    expect(warehouseText([])).toBe("—");
    expect(warehouseText(["A"])).toBe("A");
    expect(warehouseText(["A", "B", "C"])).toBe("A +2 kho");
  });
  it("câu Tiếp theo theo trạng thái và quyền", () => {
    const base = { status: "SUBMITTED", available_actions: ["approve"], short_count: 1, over_count: 1, net_difference: "-0.500" } as unknown as StocktakeListItem;
    expect(changedLineCount(base)).toBe(2);
    expect(nextStepText(base)).toMatch(/2 lô/);
    // BR-KK-09: nói đúng cơ chế (áp chênh lệch đã ghi), không hứa "theo số thực đếm".
    expect(nextStepText(base)).toContain("chênh lệch đã ghi lúc đếm (−0,5 kg)");
    expect(nextStepText(base)).not.toMatch(/theo số (thực )?đếm/);
    expect(nextStepText({ ...base, available_actions: [] })).toMatch(/Chờ Chủ hoặc Quản lý duyệt/);
    expect(nextStepText({ ...base, status: "DRAFT", available_actions: ["edit_lines", "submit"] })).toMatch(/gửi duyệt/);
    expect(nextStepText({ ...base, status: "DRAFT", available_actions: [] })).toMatch(/người lập phiếu/);
    expect(nextStepText({ ...base, status: "APPROVED" })).toBeNull();
  });
  it("StatusPath có đủ Nháp, Chờ duyệt, Đã duyệt (#6)", () => {
    expect(PATH_STEPS.map((s) => s.label)).toEqual(["Nháp", "Chờ duyệt", "Đã duyệt"]);
  });
});

const token = (user: string) => `mock-token-${user}-${Date.now() + 100000}`;
const call = (user: string, path: string) => mockStocktakeApi({ method: "GET", path, token: token(user) });

const post = (user: string, path: string) => mockStocktakeApi({ method: "POST", path, body: {}, token: token(user) });
const det = (user: string, id: number) => call(user, `/api/inventory/reconciliations/${id}/`).body as StocktakeDetail;

describe("mock Kiểm kê: luồng Nháp, Chờ duyệt, Đã duyệt (Lô bổ sung A #6, #20)", () => {
  it("người nhập số tự duyệt được phiếu của mình: không còn chặn BR-KK-02/08", () => {
    // KK-14 (Chờ duyệt) do nhân viên kho nhập: Chủ và Quản lý đều có nút Duyệt; Quản lý nhập số phiếu 15 rồi gửi duyệt thì tự duyệt được.
    expect(det("loc", 14).available_actions).toContain("approve");
    expect(det("ql1", 14).available_actions).toContain("approve");
    expect(det("ql1", 14)).not.toHaveProperty("approve_blocked_reason");
    const sent = post("ql1", "/api/inventory/reconciliations/15/submit/");
    expect(sent.status).toBe(200);
  });
  it("Nháp: có Sửa số đếm và Gửi duyệt, chưa có Duyệt; Chờ duyệt: có Duyệt và Trả về nháp, hết Sửa", () => {
    const draft = det("loc", 15);
    expect(draft.status).toBe("DRAFT");
    expect(draft.status_label).toBe("Nháp");
    expect(draft.available_actions).toEqual(["edit_lines", "submit"]);
    const waiting = det("loc", 14);
    expect(waiting.status).toBe("SUBMITTED");
    expect(waiting.status_label).toBe("Chờ duyệt");
    expect(waiting.available_actions).toEqual(["return_to_draft", "approve"]);
  });
  it("nhân viên kho: gửi duyệt và trả về nháp được, không có Duyệt (thiếu quyền)", () => {
    expect(det("kho1", 14).available_actions).toEqual(["return_to_draft"]);
    expect(post("kho1", "/api/inventory/reconciliations/14/approve/").status).toBe(403);
  });
  it("duyệt phiếu chưa gửi: 400 RECON_NOT_SUBMITTED kèm câu của BE", () => {
    const res = post("loc", "/api/inventory/reconciliations/15/approve/");
    expect(res.status).toBe(400);
    expect(res.body).toMatchObject({ code: "RECON_NOT_SUBMITTED", detail: "Phiếu kiểm kê chưa gửi duyệt. Hãy gửi duyệt trước khi duyệt." });
  });
  it("trả về nháp phiếu không ở Chờ duyệt: 400 RECON_NOT_SUBMITTED", () => {
    const res = post("loc", "/api/inventory/reconciliations/15/return-to-draft/");
    expect(res.status).toBe(400);
    expect(res.body).toMatchObject({ code: "RECON_NOT_SUBMITTED", detail: "Chỉ trả về nháp được phiếu đang chờ duyệt." });
  });
  it("gửi duyệt phiếu rỗng: 400 RECON_EMPTY; phiếu đã gửi: RECON_NOT_DRAFT", () => {
    expect(post("loc", "/api/inventory/reconciliations/17/submit/").body).toMatchObject({ code: "RECON_EMPTY" });
    expect(post("loc", "/api/inventory/reconciliations/14/submit/").body).toMatchObject({ code: "RECON_NOT_DRAFT" });
  });
  it("gửi duyệt rồi: chuyển sang Chờ duyệt", () => {
    const res = post("loc", "/api/inventory/reconciliations/15/submit/");
    expect((res.body as StocktakeDetail).status).toBe("SUBMITTED");
    expect((res.body as StocktakeDetail).available_actions).toEqual(["return_to_draft", "approve"]);
  });
  it("trả về nháp rồi: Nháp, sửa số đếm lại được", () => {
    const res = post("loc", "/api/inventory/reconciliations/14/return-to-draft/").body as StocktakeDetail;
    expect(res.status).toBe("DRAFT");
    expect(res.available_actions).toEqual(["edit_lines", "submit"]);
  });
  it("giao1 và cs2 bị 403", () => {
    expect(call("giao1", "/api/inventory/reconciliations/").status).toBe(403);
    expect(call("cs2", "/api/inventory/reconciliations/").status).toBe(403);
  });
  it("phản hồi không có trường giá vốn", () => {
    const body = JSON.stringify([call("loc", "/api/inventory/reconciliations/14/").body, call("loc", "/api/inventory/batches/?warehouse=1&has_stock=1").body]);
    expect(body).not.toMatch(/cost|price|unit_cost/i);
  });
});

describe("module Kiểm kê: không giá vốn, không dữ liệu khách trong mã nguồn", () => {
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const name of readdirSync(dir)) {
      const p = join(dir, name);
      if (statSync(p).isDirectory()) walk(p);
      else if (/\.(ts|tsx)$/.test(name) && !name.endsWith(".test.ts")) files.push(p);
    }
  };
  walk(__dirname);
  it("không đọc trường giá vốn và không đụng localStorage/console ngoài mock", () => {
    for (const f of files) {
      // Bỏ dòng chú thích: chú thích được phép nhắc tên (vd "không ghi vào localStorage").
      const text = readFileSync(f, "utf8").split("\n").filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join("\n");
      expect(text, f).not.toMatch(/unit_cost|avg_cost|cost_price|\bcost\b/);
      if (!f.endsWith("mock.ts")) {
        expect(text, f).not.toMatch(/localStorage|sessionStorage|console\.(log|info|warn|error)/);
      }
      expect(text, f).not.toMatch(/customer_name|\bphone\b|\baddress\b/);
    }
  });
  it("không có câu hứa tồn đổi \"theo số (thực) đếm\" (BR-KK-09: duyệt áp chênh lệch đã ghi)", () => {
    for (const f of files) {
      expect(readFileSync(f, "utf8"), f).not.toMatch(/theo số (thực )?đếm/);
    }
  });
});
