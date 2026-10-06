// SR-HIDE-AI-01 AC5: cờ BẬT (vitest.config đặt =1) → giao diện AI hiện như cũ.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Chạy effect ngay lúc render để bắt được lệnh gọi mạng (renderToStaticMarkup mặc định không chạy effect).
vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");
  return { ...actual, default: actual, useEffect: (fn: () => void | (() => void)) => void fn() };
});
vi.mock("next/link", () => ({ default: () => null }));
const getAiStatus = vi.hoisted(() => vi.fn(() => new Promise(() => {})));
vi.mock("@/features/ai/api", () => ({ getAiStatus }));

vi.mock("@/features/auth/components/AuthProvider", () => ({ useAuth: () => ({ me: { ai_features_enabled: true } }) }));
import { AI_FEATURES_ENABLED } from "@/shared/lib/features";
import { menuItems, visibleNav, PERM, type Viewer } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { AiBlockFrame } from "@/shared/ui/detail/AiBlockFrame";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { escalatableStep } from "@/features/guidance/escalation";
import GuidanceEscalate from "@/features/guidance/components/GuidanceEscalate";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

const OWNER: Viewer = { groups: [ROLE.owner], can_view_profit: true, permissions: Object.values(PERM), home: "dashboard", ai_features_enabled: true };

beforeEach(() => {
  getAiStatus.mockClear();
});

describe("cờ AI bật", () => {
  it("cờ đọc đúng từ env", () => expect(AI_FEATURES_ENABLED).toBe(true));

  it("Chủ thấy đủ 4 mục AI; menu trái có Chính sách AI và Báo cáo AI", () => {
    const keys = visibleNav(OWNER).map((n) => n.key);
    for (const k of ["ai-policy", "ai-report", "ai-settings", "ai-actions"]) expect(keys).toContain(k);
    expect(menuItems(OWNER).map((n) => n.href)).toEqual(expect.arrayContaining(["/ai/policy/", "/ai/report/"]));
  });

  it("AiDocBlockGate hỏi status (cổng ai_enabled giữ nguyên)", () => {
    renderToStaticMarkup(createElement(AiDocBlockGate, { targetModel: "sales.salesorder", targetId: "1" }));
    expect(getAiStatus).toHaveBeenCalledTimes(1);
  });

  it("AiBlockFrame, khe aiSlot và trang AI hiện", () => {
    expect(renderToStaticMarkup(createElement(AiBlockFrame, { proposals: [], onReject: () => {}, onConfirm: () => {} }))).toContain("Trợ lý AI");
    expect(renderToStaticMarkup(createElement(DetailPage, { header: "H", aiSlot: createElement("i"), children: "trái" }))).toContain("<aside");
    expect(renderToStaticMarkup(createElement(AiFeatureGuard, null, createElement("p", null, "MAN-AI")))).toContain("MAN-AI");
  });

  it("SR-HIDE-AI-02: cờ bật → 'Nhờ người xử lý' hiện như cũ", () => {
    const step = { key: "confirm_payment", label: "X", actor: "user", allowed: false, who: ["Chủ"], missing: [], deadline: null, why: null, command: null, ai: null } as never;
    expect(escalatableStep({ next_steps: [step] }, { ai_features_enabled: true })).not.toBeNull();
    const html = renderToStaticMarkup(createElement(GuidanceEscalate, { step, docType: "sales.salesorder", docId: 1, noticeHost: null }));
    expect(html).toContain("Nhờ");
  });
});
