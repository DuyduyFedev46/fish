import { describe, it, expect, vi, beforeEach } from "vitest";
import { callCommand } from "../commands/call";
import { fetchAiActions, undoAiAction, mockAiActions, mockUndoAiAction } from "./api";

describe("DW-19 & DW-21 Frontend Actions & Undo Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        const urlStr = String(url);
        if (urlStr.includes("/api/ai/commands/")) {
          const body = typeof init?.body === "string" ? JSON.parse(init.body) : (init?.body || {});
          if (body?.args?._defer) {
            return Promise.resolve({
              ok: true,
              status: 200,
              headers: new Headers({ "content-type": "application/json" }),
              json: () =>
                Promise.resolve({
                  outcome: "scheduled",
                  level: "B",
                  action_id: "mock-action-scheduled-12345",
                  execute_after: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
                  undo_until: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
                  downgrade_reason: null,
                }),
            });
          }
          if (body?.args?._level === "B") {
            return Promise.resolve({
              ok: true,
              status: 200,
              headers: new Headers({ "content-type": "application/json" }),
              json: () =>
                Promise.resolve({
                  outcome: "done",
                  level: "B",
                  action_id: "mock-action-b-uuid-12345",
                  result: { ok: true },
                  undo_until: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
                  downgrade_reason: null,
                }),
            });
          }
        }

        if (urlStr.includes("/api/ai/actions/") && urlStr.endsWith("/undo/")) {
          const parts = urlStr.replace(/\/+$/, "").split("/");
          const id = parts[parts.length - 2];
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: () =>
              Promise.resolve({
                outcome: "undone",
                action_id: id,
              }),
          });
        }

        if (urlStr.includes("/api/ai/actions/")) {
          const urlObj = new URL(urlStr, "http://localhost:8000");
          const statusParam = urlObj.searchParams.get("status");
          let results = [...mockAiActions.results];
          if (statusParam) {
            results = results.filter((r) => r.status === statusParam);
          }
          return Promise.resolve({
            ok: true,
            status: 200,
            headers: new Headers({ "content-type": "application/json" }),
            json: () =>
              Promise.resolve({
                count: results.length,
                next: null,
                previous: null,
                results,
              }),
          });
        }

        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({}),
        });
      })
    );
  });

  it("DW-19-AC1: callCommand trả về undo_until khi lệnh ghi đạt mức B (outcome === done)", async () => {
    const res = await callCommand("purchasing.purchasereceipt.nhap_lo", {
      args: { _level: "B" },
    });
    expect(res.outcome).toBe("done");
    expect(res.level).toBe("B");
    expect(res.action_id).toBeDefined();
    expect(res.undo_until).toBeDefined();
    expect(new Date(res.undo_until!).getTime()).toBeGreaterThan(Date.now());
  });

  it("DW-21-AC1: callCommand trả về execute_after và undo_until khi lệnh xếp lịch (outcome === scheduled)", async () => {
    const res = await callCommand("inventory.batch.close.defer", {
      args: { _defer: true },
    });
    expect(res.outcome).toBe("scheduled");
    expect(res.level).toBe("B");
    expect(res.action_id).toBeDefined();
    expect(res.execute_after).toBeDefined();
    expect(res.undo_until).toBeDefined();
    expect(new Date(res.execute_after!).getTime()).toBeGreaterThan(Date.now());
  });

  it("DW-21-AC4: mockUndoAiAction huỷ lịch việc SCHEDULED -> CANCELLED & undoAiAction gọi API thành công", async () => {
    const scheduledItem = mockAiActions.results.find((a) => a.id === "b2c3d4e5-f6a7-8901-bcde-f12345678901");
    expect(scheduledItem).toBeDefined();
    scheduledItem!.status = "SCHEDULED";

    const mockRes = mockUndoAiAction("b2c3d4e5-f6a7-8901-bcde-f12345678901");
    expect(mockRes.status).toBe(200);
    expect(mockRes.body.outcome).toBe("undone");
    expect(scheduledItem!.status).toBe("CANCELLED");

    const res = await undoAiAction("b2c3d4e5-f6a7-8901-bcde-f12345678901");
    expect(res.outcome).toBe("undone");
    expect(res.action_id).toBe("b2c3d4e5-f6a7-8901-bcde-f12345678901");
  });

  it("DW-19-AC3: mockUndoAiAction hoàn tác việc DONE mức B -> UNDONE & undoAiAction gọi API thành công", async () => {
    const doneItem = mockAiActions.results.find((a) => a.id === "c3d4e5f6-a7b8-9012-cdef-123456789012");
    expect(doneItem).toBeDefined();
    doneItem!.status = "DONE";

    const mockRes = mockUndoAiAction("c3d4e5f6-a7b8-9012-cdef-123456789012");
    expect(mockRes.status).toBe(200);
    expect(mockRes.body.outcome).toBe("undone");
    expect(doneItem!.status).toBe("UNDONE");

    const res = await undoAiAction("c3d4e5f6-a7b8-9012-cdef-123456789012");
    expect(res.outcome).toBe("undone");
    expect(res.action_id).toBe("c3d4e5f6-a7b8-9012-cdef-123456789012");
  });

  it("DW-21: fetchAiActions lọc đúng danh sách theo status filter", async () => {
    const scheduledRes = await fetchAiActions({ status: "SCHEDULED" });
    scheduledRes.results.forEach((item) => {
      expect(item.status).toBe("SCHEDULED");
    });

    const pendingRes = await fetchAiActions({ status: "PENDING" });
    pendingRes.results.forEach((item) => {
      expect(item.status).toBe("PENDING");
    });
  });
});

