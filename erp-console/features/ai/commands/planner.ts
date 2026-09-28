// Quy trình chọn lệnh 2 bước kết hợp BM25 + Model (DW-09, 02b §5).
// Lượt A: Chọn lệnh từ <= 5 ứng viên (bỏ qua nếu top-1 vượt top-2 >= margin).
// Lượt B: Điền tham số từ schema (hoặc chuyển form_only nếu schema > 450 tokens hoặc form_only=true).

import type { AiCommandDescriptor, AiCommandIndexItem } from "../types";
import {
  buildTurnAPrompt,
  buildTurnBPrompt,
  isQueryTooLong,
  N_CTX_DEFAULT,
} from "./budget";
import { searchCommands, type SearchCandidate } from "./search";

export type PlanResult =
  | {
      type: "no_match";
      message: string;
      attempts: number;
      suggestions?: string[];
    }
  | {
      type: "query_too_long";
      message: string;
    }
  | {
      type: "form_only";
      command: AiCommandIndexItem;
      descriptor?: AiCommandDescriptor;
      prefilledArgs: Record<string, unknown>;
    }
  | {
      type: "execute_ready";
      command: AiCommandIndexItem;
      args: Record<string, unknown>;
    }
  | {
      type: "budget_error";
      error: string;
    };

export type PlannerOptions = {
  screen?: string;
  nCtx?: number;
  attempts?: number;
  history?: string[];
  screenContext?: Record<string, unknown>;
  descriptorFetcher?: (id: string) => Promise<AiCommandDescriptor>;
  modelCaller?: (prompt: string) => Promise<string>;
};

/**
 * Trích xuất tham số tất định từ câu nói tự nhiên (DW-09-AC3, 02b §5.4).
 * Ví dụ: "nhập 50kg cá thu CA-001" -> { qty: 50, item_code: "CA-001" }
 */
export function extractDeterministicArgs(query: string): Record<string, unknown> {
  const args: Record<string, unknown> = {};

  // 1. Trích xuất khối lượng (kg / kí / ký)
  const kgMatch = query.match(/(\d+(?:[.,]\d+)?)\s*(?:kg|kí|ký|cân)/i);
  if (kgMatch) {
    const val = parseFloat(kgMatch[1].replace(",", "."));
    if (!isNaN(val)) {
      args.qty = val;
    }
  }

  // 2. Trích xuất mã mặt hàng (CA-001, NG-002, ...)
  const itemMatch = query.match(/\b([A-Z]{2,4}-\d{3,4})\b/i);
  if (itemMatch) {
    args.item_code = itemMatch[1].toUpperCase();
  }

  // 3. Trích xuất mã lô (LO-20260928-001, ...)
  const batchMatch = query.match(/\b(LO-\d{8}-\d+)\b/i);
  if (batchMatch) {
    args.batch_id = batchMatch[1].toUpperCase();
  }

  return args;
}

export const SAMPLE_SUGGESTIONS = [
  "Tra cứu tồn kho cá thu",
  "Xem chi tiết lô cá ngừ mới nhập",
  "Tạo đơn bán hàng cho khách",
  "Xem báo cáo lãi lỗ theo lô",
];

/**
 * Điều phối lập kế hoạch chọn lệnh 2 bước (DW-09).
 */
export async function planCommand(
  query: string,
  commands: AiCommandIndexItem[],
  options?: PlannerOptions
): Promise<PlanResult> {
  const attempts = options?.attempts ?? 1;
  const nCtx = options?.nCtx ?? N_CTX_DEFAULT;

  if (isQueryTooLong(query)) {
    return {
      type: "query_too_long",
      message: "Câu hỏi của bạn quá dài (> 120 tokens). Vui lòng diễn đạt ngắn gọn hơn.",
    };
  }

  // Bước (a): Tìm kiếm ứng viên BM25 (không dùng model)
  const searchRes = searchCommands(query, commands, {
    screen: options?.screen,
    margin: 0.2, // margin từ spike DW-02
  });

  // DW-09-AC4: Không ứng viên nào đạt điểm tối thiểu
  if (!searchRes.hasMatch || searchRes.candidates.length === 0) {
    if (attempts >= 3) {
      return {
        type: "no_match",
        message: "Hệ thống chưa tìm thấy thao tác phù hợp sau nhiều lần thử. Bạn có thể thử các mẫu sau:",
        attempts,
        suggestions: SAMPLE_SUGGESTIONS,
      };
    }
    return {
      type: "no_match",
      message: "Tôi chưa hiểu rõ yêu cầu của bạn. Bạn có thể nói rõ hơn thao tác cần thực hiện không?",
      attempts,
    };
  }

  let selectedCommand: AiCommandIndexItem | null = null;

  // DW-09-AC1: Nếu top-1 vượt top-2 quá margin -> bỏ qua Lượt A
  if (searchRes.skipTurnA && searchRes.top1) {
    selectedCommand = searchRes.top1;
  } else {
    // Chạy Lượt A với Model hoặc Mock
    const promptRes = buildTurnAPrompt(
      searchRes.candidates.map((c) => c.command),
      query,
      options?.history,
      nCtx
    );

    if (!promptRes.valid) {
      return {
        type: "budget_error",
        error: promptRes.error || "BUDGET_EXCEEDED",
      };
    }

    if (options?.modelCaller) {
      const modelResp = await options.modelCaller(promptRes.prompt);
      // Tìm candidate được model chọn
      const matched = searchRes.candidates.find((c) =>
        modelResp.includes(c.command.id)
      );
      selectedCommand = matched ? matched.command : searchRes.top1;
    } else {
      // LLMock fallback
      selectedCommand = searchRes.top1;
    }
  }

  if (!selectedCommand) {
    return {
      type: "no_match",
      message: "Không xác định được lệnh phù hợp.",
      attempts,
    };
  }

  // Lấy descriptor của lệnh nếu có fetcher
  let descriptor: AiCommandDescriptor | undefined;
  if (options?.descriptorFetcher) {
    try {
      descriptor = await options.descriptorFetcher(selectedCommand.id);
    } catch {
      // Bỏ qua lỗi mạng / descriptor chưa có
    }
  }

  const prefilled = extractDeterministicArgs(query);

  // DW-09-AC3: form_only=true hoặc schema > 450 tokens -> mở form điền sẵn, không chạy Lượt B
  const isFormOnly =
    selectedCommand.form_only ||
    descriptor?.form_only ||
    (descriptor && descriptor.schema_tokens_est > 450);

  if (isFormOnly) {
    return {
      type: "form_only",
      command: selectedCommand,
      descriptor,
      prefilledArgs: prefilled,
    };
  }

  // Lượt B: Điền tham số theo schema
  if (descriptor) {
    const turnBRes = buildTurnBPrompt(
      selectedCommand,
      descriptor,
      query,
      options?.screenContext,
      nCtx
    );

    if (!turnBRes.valid) {
      return {
        type: "budget_error",
        error: turnBRes.error || "BUDGET_EXCEEDED",
      };
    }

    if (options?.modelCaller) {
      try {
        const respText = await options.modelCaller(turnBRes.prompt);
        const parsed = JSON.parse(respText);
        return {
          type: "execute_ready",
          command: selectedCommand,
          args: { ...prefilled, ...parsed },
        };
      } catch {
        // Fallback prefilled nếu model trả JSON hỏng
        return {
          type: "execute_ready",
          command: selectedCommand,
          args: prefilled,
        };
      }
    }
  }

  return {
    type: "execute_ready",
    command: selectedCommand,
    args: prefilled,
  };
}
