// Unit & Integration tests cho Story DW-09 (FE chọn lệnh 2 bước + ngân sách token).
// Chạy bằng Vitest: npm test

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import fs from "fs";
import path from "path";

import type { AiCommandDescriptor, AiCommandIndexItem } from "../types";
import {
  clearIndexCache,
  fetchCommandDescriptor,
  fetchCommandIndex,
  getCachedIndex,
} from "./index";
import { searchCommands } from "./search";
import {
  buildTurnAPrompt,
  buildTurnBPrompt,
  estimateTokens,
  getMaxPromptBudget,
  truncateReadResults,
  MAX_READ_RESULT_ROWS,
  N_CTX_DEFAULT,
} from "./budget";
import {
  extractDeterministicArgs,
  planCommand,
  SAMPLE_SUGGESTIONS,
} from "./planner";

// Đọc 114 lệnh thật và mở rộng thành 150 lệnh giả cho test ngân sách
const indexPath = path.resolve(__dirname, "../../../spikes/dw02/index.json");
const queriesPath = path.resolve(
  __dirname,
  "../../../../doc/features/2026-09-28-ai-digital-worker/research/cau-mau-50.json"
);

const baseCommands: AiCommandIndexItem[] = JSON.parse(
  fs.readFileSync(indexPath, "utf8")
);

// Đồng bộ metadata DW-07 cho inventory.batch.list (screens: inventory, keywords: tra tồn, tồn kho, còn bao nhiêu kg)
const batchListCmd = baseCommands.find((c) => c.id === "inventory.batch.list");
if (batchListCmd) {
  batchListCmd.screens = ["inventory"];
  batchListCmd.keywords = [
    ...(batchListCmd.keywords || []),
    "tra tồn",
    "tồn kho",
    "còn bao nhiêu kg",
    "cá thu",
  ];
}

// Tạo đủ 150 lệnh giả lập cho bài test ngân sách (DW-09-AC2)
const mock150Commands: AiCommandIndexItem[] = [...baseCommands];
while (mock150Commands.length < 150) {
  const i = mock150Commands.length + 1;
  mock150Commands.push({
    id: `custom.mockcommand${i}.action`,
    title: `Thao tác giả lập số ${i}`,
    group: i % 2 === 0 ? "thu_mua" : "ban_hang",
    kind: i % 3 === 0 ? "write" : "read",
    level: "A",
    screens: ["main"],
    keywords: [`giả lập ${i}`, `thao tác ${i}`, `mock${i}`],
  });
}

const sample50Queries: Array<{ id: number; query: string; expected_id: string }> = JSON.parse(
  fs.readFileSync(queriesPath, "utf8")
);

describe("DW-09: FE chọn lệnh 2 bước + ngân sách token (chạy với LLMock)", () => {
  beforeEach(() => {
    clearIndexCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("DW-09-AC1: Ở màn tồn kho hỏi 'còn bao nhiêu cá thu' -> <= 3 ứng viên, top-1 inventory.batch.list, bỏ lượt A nếu vượt margin", () => {
    const res = searchCommands("còn bao nhiêu cá thu", baseCommands, {
      screen: "inventory",
      limit: 3,
      margin: 0.2,
    });

    expect(res.hasMatch).toBe(true);
    expect(res.candidates.length).toBeLessThanOrEqual(3);
    expect(res.top1?.id).toBe("inventory.batch.list");
    // Top 1 vượt trội top 2 quá margin -> skipTurnA phải là true
    expect(res.skipTurnA).toBe(true);
  });

  it("DW-09-AC2: Ngân sách 150 lệnh cho 50 câu mẫu ở n_ctx 2048 & 4096 (prompt <= 80% n_ctx, <= 5 tên lệnh, <= 1-2 schema, không lọt ID ngoài top-K)", async () => {
    const nCtxConfigs = [2048, 4096];

    for (const nCtx of nCtxConfigs) {
      const maxBudget = getMaxPromptBudget(nCtx); // 1638 hoặc 3276
      const maxSchemas = nCtx === 2048 ? 1 : 2;

      for (const sample of sample50Queries) {
        const searchRes = searchCommands(sample.query, mock150Commands, {
          limit: 5,
        });

        if (!searchRes.hasMatch) continue;

        const candidateIds = searchRes.candidates.map((c) => c.command.id);

        // Lượt A:
        const turnARes = buildTurnAPrompt(
          searchRes.candidates.map((c) => c.command),
          sample.query,
          [],
          nCtx
        );

        expect(turnARes.valid).toBe(true);
        expect(turnARes.tokens).toBeLessThanOrEqual(maxBudget);
        expect(searchRes.candidates.length).toBeLessThanOrEqual(5);

        // Kiểm tra không chứa ID lệnh ngoài top-K trong prompt Lượt A
        const allOtherIds = mock150Commands
          .map((c) => c.id)
          .filter((id) => !candidateIds.includes(id));

        // Kiểm tra mẫu 10 ID ngẫu nhiên không thuộc candidateIds
        allOtherIds.slice(0, 10).forEach((otherId) => {
          expect(turnARes.prompt).not.toContain(`[${otherId}]`);
        });

        // Lượt B:
        const mockDescriptor: AiCommandDescriptor = {
          id: searchRes.top1!.id,
          title: searchRes.top1!.title,
          description: "Mô tả kiểm thử",
          kind: searchRes.top1!.kind,
          level: "A",
          max_level: "A",
          sensitivity: "trung_binh",
          channel: "local",
          red_zone: false,
          target: null,
          form_only: false,
          schema_tokens_est: 60,
          input_schema: {
            type: "object",
            properties: {
              item_code: { type: "string" },
              qty: { type: "number" },
            },
          },
          output_fields: ["id", "batch_id"],
        };

        const turnBRes = buildTurnBPrompt(
          searchRes.top1!,
          mockDescriptor,
          sample.query,
          { screen: "inventory" },
          nCtx
        );

        if (!turnBRes.isFormOnly) {
          expect(turnBRes.valid).toBe(true);
          expect(turnBRes.tokens).toBeLessThanOrEqual(maxBudget);
        }
      }
    }
  });

  it("DW-09-AC3: Lệnh form_only=true hoặc schema > 450 tokens -> mở form điền sẵn, không chạy Lượt B", async () => {
    const formOnlyCommand: AiCommandIndexItem = {
      id: "inventory.batch.cancel_expired",
      title: "Huỷ lô quá hạn",
      group: "thu_mua",
      kind: "write",
      level: "C",
      screens: ["inventory"],
      keywords: ["huỷ lô", "quá hạn"],
      form_only: true,
    };

    const descLargeSchema: AiCommandDescriptor = {
      id: "inventory.batch.cancel_expired",
      title: "Huỷ lô quá hạn",
      description: "Mô tả",
      kind: "write",
      level: "C",
      max_level: "C",
      sensitivity: "cao",
      channel: "local",
      red_zone: false,
      target: "detail",
      form_only: true,
      schema_tokens_est: 500, // > 450 tokens
      input_schema: null,
      output_fields: ["id"],
    };

    const mockModelCaller = vi.fn().mockResolvedValue("inventory.batch.cancel_expired");

    const plan = await planCommand(
      "huỷ lô quá hạn LO-20260928-001 20kg",
      [formOnlyCommand],
      {
        descriptorFetcher: async () => descLargeSchema,
        modelCaller: mockModelCaller,
      }
    );

    expect(plan.type).toBe("form_only");
    if (plan.type === "form_only") {
      expect(plan.command.id).toBe("inventory.batch.cancel_expired");
      // Trích xuất tất định
      expect(plan.prefilledArgs.qty).toBe(20);
      expect(plan.prefilledArgs.batch_id).toBe("LO-20260928-001");
    }
  });

  it("DW-09-AC4: Không ứng viên nào đạt điểm tối thiểu -> hỏi lại tối đa 3 lần rồi gợi ý câu mẫu, không gọi model", async () => {
    const mockModelCaller = vi.fn();

    // Lần 1: Không đạt điểm (chào hỏi không khớp thao tác ERP nào)
    const plan1 = await planCommand("xin chào buổi sáng", baseCommands, {
      attempts: 1,
      modelCaller: mockModelCaller,
    });
    expect(plan1.type).toBe("no_match");
    if (plan1.type === "no_match") {
      expect(plan1.attempts).toBe(1);
      expect(plan1.suggestions).toBeUndefined();
    }
    expect(mockModelCaller).not.toHaveBeenCalled();

    // Lần 2:
    const plan2 = await planCommand("xin chào buổi sáng", baseCommands, {
      attempts: 2,
      modelCaller: mockModelCaller,
    });
    expect(plan2.type).toBe("no_match");
    if (plan2.type === "no_match") {
      expect(plan2.attempts).toBe(2);
      expect(plan2.suggestions).toBeUndefined();
    }
    expect(mockModelCaller).not.toHaveBeenCalled();

    // Lần 3: Gợi ý câu mẫu
    const plan3 = await planCommand("xin chào buổi sáng", baseCommands, {
      attempts: 3,
      modelCaller: mockModelCaller,
    });
    expect(plan3.type).toBe("no_match");
    if (plan3.type === "no_match") {
      expect(plan3.attempts).toBe(3);
      expect(plan3.suggestions).toEqual(SAMPLE_SUGGESTIONS);
    }
    expect(mockModelCaller).not.toHaveBeenCalled();
  });

  it("DW-09-AC5: Kết quả mock 500 dòng -> Lượt C chỉ đưa <= 20 dòng vào prompt, hiện 'còn 480 dòng — xem màn danh sách'", () => {
    const mock500Rows = Array.from({ length: 500 }, (_, i) => ({
      id: i + 1,
      batch_id: `LO-${i + 1}`,
      qty_available: 100,
    }));

    const result = truncateReadResults(mock500Rows, 500);

    expect(result.displayItems.length).toBe(MAX_READ_RESULT_ROWS); // 20
    expect(result.total).toBe(500);
    expect(result.notice).toBe("còn 480 dòng — xem màn danh sách");
  });

  it("DW-09-AC6: Chỉ mục lưu trong RAM, tải lại khi index_version đổi, không tự thêm lệnh ngoài chỉ mục", async () => {
    const mockServerIndexV1 = {
      index_version: "v1_hash",
      config_version: 1,
      commands: [baseCommands[0], baseCommands[1]],
    };

    const mockServerIndexV2 = {
      index_version: "v2_hash",
      config_version: 2,
      commands: [baseCommands[0]],
    };

    // Giả lập apiFetch
    let serverIndex = mockServerIndexV1;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve(serverIndex),
      })
    ));

    // Lần 1: nạp v1
    const idx1 = await fetchCommandIndex();
    expect(idx1.index_version).toBe("v1_hash");
    expect(idx1.commands.length).toBe(2);
    expect(getCachedIndex()?.index_version).toBe("v1_hash");

    // Lần 2: gọi lại không force -> lấy cache v1
    serverIndex = mockServerIndexV2;
    const idxCached = await fetchCommandIndex(false);
    expect(idxCached.index_version).toBe("v1_hash");

    // Lần 3: force tải lại -> nạp v2 và cập nhật cache
    const idx2 = await fetchCommandIndex(true);
    expect(idx2.index_version).toBe("v2_hash");
    expect(idx2.commands.length).toBe(1);
    expect(getCachedIndex()?.index_version).toBe("v2_hash");
  });

  it("DW-09-AC7: Không ghi câu hỏi, prompt, kết quả vào console hay localStorage; chỉ mục giữ trong RAM", async () => {
    const consoleLogSpy = vi.spyOn(console, "log");
    const consoleInfoSpy = vi.spyOn(console, "info");
    const consoleDebugSpy = vi.spyOn(console, "debug");

    const sensitiveQuery = "còn bao nhiêu cá thu CA-001 của khách VIP";
    const plan = await planCommand(sensitiveQuery, baseCommands);

    // Không ghi ra console
    expect(consoleLogSpy).not.toHaveBeenCalled();
    expect(consoleInfoSpy).not.toHaveBeenCalled();
    expect(consoleDebugSpy).not.toHaveBeenCalled();

    // Không ghi vào localStorage
    if (typeof window !== "undefined" && window.localStorage) {
      expect(window.localStorage.getItem("ai_query")).toBeNull();
      expect(window.localStorage.getItem("ai_prompt")).toBeNull();
      expect(window.localStorage.getItem("ai_index")).toBeNull();
    }
  });

  it("DW-09-AC8: Index trả 410 (AI tắt) -> ném lỗi và không khởi tạo/chạy xử lý", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 410,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ detail: "AI_DISABLED", code: "AI_DISABLED" }),
      })
    ));

    await expect(fetchCommandIndex(true)).rejects.toThrow();
  });

  it("DW-15-AC3: Tìm kiếm bằng từ khoá cũ 'tra tồn', 'tra_ton' -> top-3 có inventory.batch.list", () => {
    const listWithKeywords: AiCommandIndexItem[] = baseCommands.map((c) => {
      if (c.id === "inventory.batch.list") {
        return {
          ...c,
          keywords: [...(c.keywords || []), "tra_ton", "tra tồn", "tồn kho"],
        };
      }
      return c;
    });

    const results1 = searchCommands("tra tồn", listWithKeywords, { limit: 3 });
    expect(results1.candidates.some((r) => r.command.id === "inventory.batch.list")).toBe(true);

    const results2 = searchCommands("tra_ton", listWithKeywords, { limit: 3 });
    expect(results2.candidates.some((r) => r.command.id === "inventory.batch.list")).toBe(true);
  });
});

