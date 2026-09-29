import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  fetchDeliveryNotes,
  fetchDeliveryNoteDetail,
  packDeliveryNote,
} from "./api";
import {
  getMockDeliveryNotes,
  getMockDeliveryNoteDetail,
  mockPackDeliveryNote,
  mockPostDeliveryLabelPrint,
  mockPostDeliveryLabelVoid,
  MOCK_DELIVERY_NOTES,
} from "./mock";

describe("Deliveries feature tests (CS-02, CS-03)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("CS-02-AC1: getMockDeliveryNotes filters by status correctly", () => {
    const confirmingRes = getMockDeliveryNotes({ status: "CONFIRMING" });
    expect(confirmingRes.results.every((n) => n.status === "CONFIRMING")).toBe(true);

    const preparingRes = getMockDeliveryNotes({ status: "PREPARING" });
    expect(preparingRes.results.every((n) => n.status === "PREPARING")).toBe(true);

    const readyRes = getMockDeliveryNotes({ status: "READY" });
    expect(readyRes.results.every((n) => n.status === "READY")).toBe(true);
  });

  it("CS-02-AC2: PREPARING note shows printed=false when label not printed", () => {
    const note = MOCK_DELIVERY_NOTES.find((n) => n.status === "PREPARING");
    expect(note).toBeDefined();
    expect(note?.label.printed).toBe(false);
  });

  it("CS-02-AC3: CONFIRMING note has available_actions empty", () => {
    const confNote = MOCK_DELIVERY_NOTES.find((n) => n.status === "CONFIRMING");
    expect(confNote).toBeDefined();
    expect(confNote?.available_actions).toEqual([]);
  });

  it("CS-03-AC1: Detail returns lines with item_name, qty_kg, batch_id, expiry_date", () => {
    const detail = getMockDeliveryNoteDetail(31);
    expect(detail.id).toBe(31);
    expect(detail.lines.length).toBeGreaterThan(0);
    const line = detail.lines[0];
    expect(line.item_name).toBeDefined();
    expect(line.qty_kg).toBeDefined();
    expect(line.batch_id).toBeDefined();
    expect(line.expiry_date).toBeDefined();
  });

  it("CS-03-AC2: mockPackDeliveryNote marks note as READY", () => {
    // Clone note 31
    const testNote = { ...MOCK_DELIVERY_NOTES.find((n) => n.id === 31)! };
    const originalStatus = testNote.status;
    expect(originalStatus).toBe("PREPARING");

    const res = mockPackDeliveryNote(31, "PREPARING");
    expect(res.already).toBe(false);
    expect(res.note.status).toBe("READY");
    expect(res.note.status_label).toBe("Chờ lấy");
  });

  it("CS-03-AC3: mockPackDeliveryNote on already READY note returns already: true", () => {
    const res = mockPackDeliveryNote(31, "PREPARING");
    expect(res.already).toBe(true);
    expect(res.note.status).toBe("READY");
  });

  it("CS-03-AC4: mockPackDeliveryNote on CONFIRMING note throws BR-GH-11", () => {
    expect(() => mockPackDeliveryNote(30, "PREPARING")).toThrow("BR-GH-11");
  });

  it("X-AC3: No cost keys in mock delivery notes", () => {
    for (const note of MOCK_DELIVERY_NOTES) {
      const keys = Object.keys(note);
      expect(keys).not.toContain("unit_cost");
      expect(keys).not.toContain("purchase_rate");
      expect(keys).not.toContain("landed_unit_cost");
      expect(keys).not.toContain("rate");
      expect(keys).not.toContain("profit");
      expect(keys).not.toContain("cost");

      for (const line of note.lines) {
        const lineKeys = Object.keys(line);
        expect(lineKeys).not.toContain("unit_cost");
        expect(lineKeys).not.toContain("purchase_rate");
        expect(lineKeys).not.toContain("rate");
      }
    }
  });

  it("API: fetchDeliveryNotes and packDeliveryNote integrate with mock / fetch", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () =>
            Promise.resolve({
              count: 1,
              results: [MOCK_DELIVERY_NOTES[0]],
            }),
        })
      )
    );

    const res = await fetchDeliveryNotes({ status: "CONFIRMING" });
    expect(res.results.length).toBe(1);
    expect(res.results[0].code).toBe("GH-HD-0030-CONF");
  });

  it("CS-14-AC1 & AC2: mockPostDeliveryLabelPrint records reprint and to_void, mockPostDeliveryLabelVoid removes from to_void", () => {
    const print1 = mockPostDeliveryLabelPrint({}, 31);
    expect(print1.status).toBe(201);
    expect((print1.body as any).print_no).toBe(1);

    const print2 = mockPostDeliveryLabelPrint({}, 31);
    expect(print2.status).toBe(200);
    expect((print2.body as any).print_no).toBe(2);
    expect((print2.body as any).is_reprint).toBe(true);

    const note31 = MOCK_DELIVERY_NOTES.find((n) => n.id === 31)!;
    expect(note31.label.to_void).toContain(1);

    const voidActive = mockPostDeliveryLabelVoid({ body: { print_no: 2 } }, 31);
    expect(voidActive.status).toBe(400);
    expect((voidActive.body as any).code).toBe("BR-GH-16");

    const void1 = mockPostDeliveryLabelVoid({ body: { print_no: 1 } }, 31);
    expect(void1.status).toBe(200);
    expect((void1.body as any).already).toBe(false);
    expect((void1.body as any).print_no).toBe(1);

    const voidAgain = mockPostDeliveryLabelVoid({ body: { print_no: 1 } }, 31);
    expect(voidAgain.status).toBe(200);
    expect((voidAgain.body as any).already).toBe(true);
  });
});

