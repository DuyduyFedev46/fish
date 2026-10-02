// Mock module AI — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Mock endpoint theo contract 02b-tech-design.md mục 6:
//   GET  /api/ai/status/                        (S05 — luôn 200, ai_enabled đọc cờ mock)
// Mock nhật ký (S03) đã chuyển sang features/audit/mock.ts.
//
// Cờ: localStorage "cave_erp_mock_ai"="on" → ai_enabled (MẶC ĐỊNH TẮT — để e2e cũ vẫn thấy khung chờ
// "Trợ lý đang được nối, sắp có" và không phát sinh request). Bật nhanh trong DevTools:
//   window.__caveMock.ai("on" | "off")   — bật/tắt cờ AI (localStorage)
//   window.__caveMock.aiConsent(true)    — đặt cờ đã đồng ý tải model
//   window.__caveMock.aiBudget("ok" | "warning" | "blocked") — hạn mức chi phí giả (chỉ Chủ thấy, khi AI bật)

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { setAiConsent } from "./consent";
import { ROLE } from "@/shared/lib/roles";

const AI_ON_KEY = "cave_erp_mock_ai";
/** Trạng thái hạn mức giả cho e2e: "warning" | "blocked" (mặc định "ok"). Không chứa dữ liệu cá nhân. */
const AI_BUDGET_KEY = "cave_erp_mock_ai_budget";

function budgetStatus(): { spent_vnd: number; limit_vnd: number; status: string } {
  let v: string | null = null;
  try {
    v = typeof window === "undefined" ? null : window.localStorage.getItem(AI_BUDGET_KEY);
  } catch {
    v = null;
  }
  if (v === "warning") return { spent_vnd: 170000, limit_vnd: 200000, status: "warning" };
  if (v === "blocked") return { spent_vnd: 200000, limit_vnd: 200000, status: "blocked" };
  return { spent_vnd: 0, limit_vnd: 200000, status: "ok" };
}

/** Cờ AI toàn cục của mock (server thật: Chủ tắt AI → mọi `step.ai` = null). Dùng cả ở features/guidance/mock. */
export function aiEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(AI_ON_KEY) === "on";
  } catch {
    return false;
  }
}

// ================= S05 — /api/ai/status/ =================

/** GET /api/ai/status/ — luôn 200; `model` từ env override (S17 chưa chốt → null); budget chỉ chu. */
export function mockStatus(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const name = process.env.NEXT_PUBLIC_AI_MODEL_NAME;
  const url = process.env.NEXT_PUBLIC_AI_MODEL_GGUF_URL;
  const enabled = aiEnabled();
  // Như BE: AI tắt → không có model, không có budget; AI bật → budget chỉ có với Chủ.
  return {
    status: 200,
    body: {
      ai_enabled: enabled,
      cloud_enabled: false,
      model: enabled && name && url ? { name, version: "dev", gguf_url: url } : null,
      budget: enabled && me.groups.includes(ROLE.owner) ? budgetStatus() : null,
    },
  };
}

// ---- Công cụ thử trong DevTools (chỉ có ở mock) ----
if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    ai: (mode: "on" | "off") => {
      try {
        if (mode === "on") window.localStorage.setItem(AI_ON_KEY, "on");
        else window.localStorage.removeItem(AI_ON_KEY);
      } catch {
        /* storage chặn → giữ nguyên */
      }
      return aiEnabled();
    },
    aiConsent: (v: boolean) => setAiConsent(v),
    aiBudget: (v: "ok" | "warning" | "blocked") => {
      try {
        if (v === "ok") window.localStorage.removeItem(AI_BUDGET_KEY);
        else window.localStorage.setItem(AI_BUDGET_KEY, v);
      } catch {
        /* storage chặn → giữ nguyên */
      }
      return v;
    },
  };
}
