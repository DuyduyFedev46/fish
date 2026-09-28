// Ngân sách token và kiểm soát tràn context (DW-09, 02b §5.3, §5.4).
// Quy tắc cốt lõi: mọi prompt <= 80% n_ctx, tối đa 5 tên ứng viên (lượt A),
// tối đa 1 schema (2048) / 2 schema (4096) ở lượt B, cắt kết quả đọc <= 20 dòng.

import type { AiCommandDescriptor, AiCommandIndexItem } from "../types";

export const N_CTX_DEFAULT = 2048;
export const MAX_SCHEMA_TOKENS = 450;
export const MAX_QUERY_TOKENS = 120;
export const MAX_CANDIDATES_TURN_A = 5;
export const MAX_READ_RESULT_ROWS = 20;

/** Ước lượng số token của một chuỗi văn bản (ký tự / 2.5 hoặc từ ngữ). */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.max(1, Math.ceil(text.length / 2.5));
}

/** Lấy trần ngân sách an toàn (80% n_ctx) theo BR-AI-13. */
export function getMaxPromptBudget(nCtx: number = N_CTX_DEFAULT): number {
  return Math.floor(nCtx * 0.8);
}

/** Kiểm tra câu hỏi người dùng có vượt 120 token không. */
export function isQueryTooLong(query: string): boolean {
  return estimateTokens(query) > MAX_QUERY_TOKENS;
}

export type TurnAPromptResult = {
  prompt: string;
  tokens: number;
  valid: boolean;
  error?: string;
};

/**
 * Xây dựng prompt Lượt A — Chọn 1 trong số <= 5 ứng viên (02b §5.3).
 * Chỉ đưa tên và mô tả ngắn của <= 5 ứng viên top-K; tuyệt đối không đưa lệnh ngoài top-K.
 */
export function buildTurnAPrompt(
  candidates: AiCommandIndexItem[],
  query: string,
  history: string[] = [],
  nCtx: number = N_CTX_DEFAULT
): TurnAPromptResult {
  const maxBudget = getMaxPromptBudget(nCtx);

  if (isQueryTooLong(query)) {
    return {
      prompt: "",
      tokens: estimateTokens(query),
      valid: false,
      error: "QUERY_TOO_LONG",
    };
  }

  // Cắt tối đa 5 ứng viên
  const topCandidates = candidates.slice(0, MAX_CANDIDATES_TURN_A);

  const sysPrompt = "Bạn là trợ lý ERP Cá Về. Hãy chọn 1 lệnh phù hợp nhất từ danh sách ứng viên sau:";
  const candidateLines = topCandidates.map(
    (c, idx) => `${idx + 1}. [${c.id}] ${c.title} (Nhóm: ${c.group}, Thao tác: ${c.kind})`
  );

  // Xử lý sliding window cho history
  let activeHistory = [...history];
  let candidateBlock = candidateLines.join("\n");
  let promptText = "";

  const assemble = (hist: string[]) => {
    const parts = [
      sysPrompt,
      "Danh sách ứng viên:",
      candidateBlock,
    ];
    if (hist.length > 0) {
      parts.push("Lịch sử gần đây:", hist.join("\n"));
    }
    parts.push(`Câu hỏi người dùng: "${query}"`);
    parts.push("Trả về ID của lệnh được chọn:");
    return parts.join("\n\n");
  };

  promptText = assemble(activeHistory);
  let tokens = estimateTokens(promptText);

  // Vượt ngân sách -> cắt dần lịch sử (sliding window)
  while (tokens > maxBudget && activeHistory.length > 0) {
    activeHistory.shift();
    promptText = assemble(activeHistory);
    tokens = estimateTokens(promptText);
  }

  return {
    prompt: promptText,
    tokens,
    valid: tokens <= maxBudget,
    error: tokens > maxBudget ? "BUDGET_EXCEEDED" : undefined,
  };
}

export type TurnBPromptResult = {
  prompt: string;
  tokens: number;
  valid: boolean;
  isFormOnly: boolean;
  error?: string;
};

/**
 * Xây dựng prompt Lượt B — Điền tham số theo JSON Schema của lệnh (02b §5.3, §5.4).
 * Nếu form_only=true hoặc schema > 450 token -> chuyển sang form_only (không chạy model lượt B).
 */
export function buildTurnBPrompt(
  command: AiCommandIndexItem,
  descriptor: AiCommandDescriptor,
  query: string,
  screenContext?: Record<string, unknown>,
  nCtx: number = N_CTX_DEFAULT
): TurnBPromptResult {
  const maxBudget = getMaxPromptBudget(nCtx);

  // DW-09-AC3: form_only=true hoặc schema > 450 tokens -> không chạy model
  if (command.form_only || descriptor.form_only || descriptor.schema_tokens_est > MAX_SCHEMA_TOKENS) {
    return {
      prompt: "",
      tokens: 0,
      valid: true,
      isFormOnly: true,
    };
  }

  if (isQueryTooLong(query)) {
    return {
      prompt: "",
      tokens: estimateTokens(query),
      valid: false,
      isFormOnly: false,
      error: "QUERY_TOO_LONG",
    };
  }

  const sysPrompt = "Bạn là trợ lý ERP Cá Về. Hãy trích xuất tham số JSON hợp lệ theo schema sau:";
  const schemaStr = descriptor.input_schema
    ? JSON.stringify(descriptor.input_schema, null, 2)
    : "{}";

  const contextStr = screenContext && Object.keys(screenContext).length > 0
    ? `Ngữ cảnh màn hình: ${JSON.stringify(screenContext)}`
    : "";

  const parts = [
    sysPrompt,
    `Lệnh: ${command.id} (${command.title})`,
    "JSON Schema đầu vào:",
    schemaStr,
  ];

  if (contextStr) {
    parts.push(contextStr);
  }

  parts.push(`Yêu cầu của người dùng: "${query}"`);
  parts.push("Chỉ trả về JSON object hợp lệ:");

  const promptText = parts.join("\n\n");
  const tokens = estimateTokens(promptText);

  return {
    prompt: promptText,
    tokens,
    valid: tokens <= maxBudget,
    isFormOnly: false,
    error: tokens > maxBudget ? "BUDGET_EXCEEDED" : undefined,
  };
}

export type TruncateResultsResult<T> = {
  displayItems: T[];
  notice?: string;
  total: number;
};

/**
 * Cắt kết quả đọc (Lượt C / hiển thị) không quá 20 dòng để tránh crash tab (DW-09-AC5, 02b §5.4).
 */
export function truncateReadResults<T>(
  items: T[],
  totalCount?: number
): TruncateResultsResult<T> {
  const total = totalCount ?? items.length;
  if (items.length <= MAX_READ_RESULT_ROWS) {
    return {
      displayItems: items,
      total,
    };
  }

  const remaining = total - MAX_READ_RESULT_ROWS;
  return {
    displayItems: items.slice(0, MAX_READ_RESULT_ROWS),
    notice: `còn ${remaining} dòng — xem màn danh sách`,
    total,
  };
}
