// BR-GH-19 ở quyết định đơn chưa xác nhận: lý do ≤ 200 ký tự, không chứa chuỗi số dài; `decision_note` đọc lại ở chi tiết phiếu.
import { describe, expect, it } from "vitest";
import { MOCK_CONFIRMATION_ITEMS, mockDecideConfirmation, mockGetConfirmationDetail } from "./mock";

const escalated = () => MOCK_CONFIRMATION_ITEMS.find((i) => i.confirm_state === "ESCALATED" && i.in_scope)!;

describe("DecideModal: BR-GH-19", () => {
  it("lý do có chuỗi số dài hoặc quá 200 ký tự bị 400 BR-GH-19, phiếu không đổi", () => {
    const item = escalated();
    for (const reason of ["Khách đưa số 0901 234 567", "x".repeat(201)]) {
      const res = mockDecideConfirmation({}, item.note_id, { decision: "DELIVER_WITHOUT_CONFIRM", reason });
      expect(res.status).toBe(400);
      expect((res.body as { code: string }).code).toBe("BR-GH-19");
      expect(item.confirm_state).toBe("ESCALATED");
    }
  });

  it("decision_note được trả lại ở chi tiết khi có, rỗng khi chưa có", () => {
    const item = escalated();
    const before = mockGetConfirmationDetail({}, item.note_id).body as { decision_note?: string };
    expect(before.decision_note ?? "").toBe("");
    const ok = mockDecideConfirmation({}, item.note_id, { decision: "DELIVER_WITHOUT_CONFIRM", reason: "Khách quen, giao luôn" });
    expect(ok.status).toBe(200);
    const after = mockGetConfirmationDetail({}, item.note_id).body as { decision_note?: string };
    expect(after.decision_note).toBe("Khách quen, giao luôn");
  });
});
