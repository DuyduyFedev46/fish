import { describe, it, expect, beforeEach } from "vitest";
import {
  getMockCskhQueue,
  mockClaimCskhTask,
  mockRecordCskhCall,
  mockSearchCskh,
  mockUnconfirm,
  mockChangeRecipient,
  MOCK_CSKH_ITEMS,
} from "./mock";
import {
  mockGetDeliveryLabel,
  mockPostDeliveryLabelPrint,
} from "../deliveries/mock";

describe("CSKH Feature Tests (CS-04, CS-05, CS-06, CS-11)", () => {
  beforeEach(() => {
    // Reset state on mock items if modified
    const item31 = MOCK_CSKH_ITEMS.find((i) => i.note_id === 31);
    if (item31) {
      item31.note_status = "CONFIRMING";
      item31.confirm_state = "PENDING";
      item31.claimed_by = null;
      item31.claimed_until = null;
    }
  });

  describe("CS-05: Hàng chờ CSKH & Tìm kiếm", () => {
    it("CS-05-AC1: Hàng chờ mặc định lọc CONFIRMING, sắp xếp theo paid_at tăng dần", () => {
      const res = getMockCskhQueue();
      expect(res.results.length).toBeGreaterThan(0);
      for (let i = 0; i < res.results.length - 1; i++) {
        const tA = new Date(res.results[i].paid_at!).getTime();
        const tB = new Date(res.results[i + 1].paid_at!).getTime();
        expect(tA).toBeLessThanOrEqual(tB);
      }
    });

    it("CS-05-AC2: Tab CALLBACK chỉ trả các phiếu có confirm_state=CALLBACK", () => {
      const res = getMockCskhQueue({ state: "CALLBACK" });
      expect(res.results.length).toBeGreaterThan(0);
      for (const item of res.results) {
        expect(item.confirm_state).toBe("CALLBACK");
      }
    });

    it("CS-05-AC3: Khoá mềm claim đơn trong 5 phút và chặn tranh chấp 409 CLAIMED", () => {
      const firstClaim = mockClaimCskhTask({}, 31);
      expect(firstClaim.status).toBe(200);
      if ("claimed_by" in firstClaim.body) {
        expect(firstClaim.body.claimed_by.display_name).toBe("CSKH Thử");
      }

      // Giả lập người khác (id khác) claim trong thời gian khoá
      const item31 = MOCK_CSKH_ITEMS.find((i) => i.note_id === 31)!;
      item31.claimed_by = { id: 99, display_name: "CSKH Khác" };
      item31.claimed_until = new Date(Date.now() + 4 * 60 * 1000).toISOString();

      const secondClaim = mockClaimCskhTask({}, 31);
      expect(secondClaim.status).toBe(409);
      if ("code" in secondClaim.body) {
        expect(secondClaim.body.code).toBe("CLAIMED");
        expect(secondClaim.body.detail).toContain("CSKH Khác");
      }
    });

    it("CS-05-AC5: Tìm kiếm SĐT trả đủ thông tin cho đơn trong scope, che SĐT cho đơn ngoài scope", () => {
      const res = mockSearchCskh({}, "0900000123");
      expect(res.status).toBe(200);
      if ("results" in res.body) {
        expect(res.body.results.length).toBeGreaterThan(0);
        const item = res.body.results[0];
        expect(item.in_scope).toBe(true);
        expect(item.customer_name).toBe("Khách Thử A");
        expect(item.phone).toBe("0900000123");
      }
    });

    it("CS-05-AC6: Tìm kiếm SĐT một phần (< 9 số) trả 400 INVALID_QUERY", () => {
      const res = mockSearchCskh({}, "090012");
      expect(res.status).toBe(400);
      if ("code" in res.body) {
        expect(res.body.code).toBe("INVALID_QUERY");
      }
    });
  });

  describe("CS-06: Ghi kết quả cuộc gọi & Huỷ xác nhận", () => {
    it("CS-06-AC1: Ghi CONFIRMED chuyển phiếu sang PREPARING", () => {
      const res = mockRecordCskhCall({}, 31, {
        result: "CONFIRMED",
        note: "Giao sau 17h",
        request_id: "req-test-uuid-1",
      });
      expect(res.status).toBe(201);
      if ("note_status" in res.body) {
        expect(res.body.note_status).toBe("PREPARING");
        expect(res.body.confirm_state).toBeNull();
      }
    });

    it("CS-06-AC4: Ghi CALLBACK chuyển confirm_state sang CALLBACK kèm callback_at", () => {
      const futureTime = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
      const res = mockRecordCskhCall({}, 30, {
        result: "CALLBACK",
        callback_at: futureTime,
        note: "Khách bận, gọi lại sau 2h",
        request_id: "req-test-uuid-2",
      });
      expect(res.status).toBe(201);
      if ("confirm_state" in res.body) {
        expect(res.body.confirm_state).toBe("CALLBACK");
      }
    });

    it("CS-06-AC6: BR-GH-19 chặn ghi SĐT hoặc STK (≥ 9 chữ số) vào ghi chú", () => {
      const res1 = mockRecordCskhCall({}, 31, {
        result: "CONFIRMED",
        note: "Giao cho số 0901234567 nhé",
        request_id: "req-test-uuid-3",
      });
      expect(res1.status).toBe(400);
      if ("code" in res1.body) {
        expect(res1.body.code).toBe("BR-GH-19");
      }

      const res2 = mockRecordCskhCall({}, 31, {
        result: "CONFIRMED",
        note: "SĐT liên hệ: 0900.111.222",
        request_id: "req-test-uuid-4",
      });
      expect(res2.status).toBe(400);
      if ("code" in res2.body) {
        expect(res2.body.code).toBe("BR-GH-19");
      }
    });

    it("CS-06-AC8: Huỷ xác nhận đưa phiếu từ PREPARING về CONFIRMING/PENDING", () => {
      const item31 = MOCK_CSKH_ITEMS.find((i) => i.note_id === 31)!;
      item31.note_status = "PREPARING";

      const res = mockUnconfirm({}, 31, { reason: "Bấm nhầm đơn" });
      expect(res.status).toBe(200);
      if ("note_status" in res.body) {
        expect(res.body.note_status).toBe("CONFIRMING");
        expect(res.body.confirm_state).toBe("PENDING");
      }
    });
  });

  describe("CS-11: In tem giao hàng 100x150 mm", () => {
    it("CS-11-AC2: Phiếu CONFIRMING không in được tem (BR-GH-09)", () => {
      const res = mockGetDeliveryLabel({}, 30);
      expect(res.status).toBe(400);
      if ("code" in res.body) {
        expect(res.body.code).toBe("BR-GH-09");
      }
    });

    it("CS-11-AC4: Dữ liệu tem KHÔNG chứa giá bán, tổng tiền hay giá vốn", () => {
      const res = mockGetDeliveryLabel({}, 31);
      expect(res.status).toBe(200);
      if ("barcode_value" in res.body) {
        const bodyObj = res.body as Record<string, unknown>;
        expect(bodyObj).not.toHaveProperty("price");
        expect(bodyObj).not.toHaveProperty("amount");
        expect(bodyObj).not.toHaveProperty("total_amount");
        expect(bodyObj).not.toHaveProperty("unit_cost");
        expect(bodyObj).not.toHaveProperty("purchase_rate");
        expect(bodyObj.paid_text).toBe("ĐÃ THANH TOÁN – không thu thêm");
      }
    });

    it("CS-11-AC5: SĐT trên tem bắt buộc phải được che dạng mask", () => {
      const res = mockGetDeliveryLabel({}, 31);
      expect(res.status).toBe(200);
      if ("recipient_phone_masked" in res.body) {
        expect(res.body.recipient_phone_masked).toBe("09xx xxx 123");
        expect(res.body.recipient_phone_masked).not.toBe("0900000123");
      }
    });

    it("CS-11-AC1: In tem thành công sinh lượt in và đánh dấu printed", () => {
      const res = mockPostDeliveryLabelPrint({}, 31);
      expect([200, 201]).toContain(res.status);
      if ("print_no" in res.body) {
        expect(res.body.print_no).toBeGreaterThanOrEqual(1);
      }
    });
  });

  describe("Bất biến hệ thống", () => {
    it("Bất biến 1 (X-AC3): Không có khoá giá vốn nào trong mock hàng chờ CSKH", () => {
      const costForbidden = [
        "unit_cost",
        "purchase_rate",
        "landed_cost",
        "landed_unit_cost",
        "total_cost",
        "cogs",
        "profit",
      ];
      for (const item of MOCK_CSKH_ITEMS) {
        for (const key of costForbidden) {
          expect(item).not.toHaveProperty(key);
        }
      }
    });
  });
});
