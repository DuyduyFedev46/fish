// SR-HIDE-AI-01: cờ NEXT_PUBLIC_AI_FEATURES TẮT → menu, tìm lệnh, khối Trợ lý AI và link /ai/* biến mất, không gọi /api/ai/*.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/shared/lib/features", () => ({ AI_FEATURES_ENABLED: false }));
// Chạy effect ngay lúc render để bắt được lệnh gọi mạng (renderToStaticMarkup mặc định không chạy effect).
vi.mock("react", async () => {
  const actual = await vi.importActual<typeof import("react")>("react");
  return { ...actual, default: actual, useEffect: (fn: () => void | (() => void)) => void fn() };
});
vi.mock("next/link", () => ({ default: () => null }));
const getAiStatus = vi.hoisted(() => vi.fn(() => new Promise(() => {})));
vi.mock("@/features/ai/api", () => ({ getAiStatus }));

vi.mock("@/features/auth/components/AuthProvider", () => ({ useAuth: () => ({ me: null }) }));
import { menuItems, visibleNav, canView, PERM, type Viewer } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { AiDocBlockGate } from "@/features/ai/components/AiDocBlockGate";
import { ConfirmationAiBlock } from "@/features/confirmation/components/ConfirmationAiBlock";
import { AiBlockFrame } from "@/shared/ui/detail/AiBlockFrame";
import { DetailPage } from "@/shared/ui/detail/DetailPage";
import { escalatableStep } from "@/features/guidance/escalation";
import GuidanceEscalate from "@/features/guidance/components/GuidanceEscalate";
import { AiFeatureGuard } from "@/shared/ui/states/AiFeatureGuard";

const OWNER: Viewer = { groups: [ROLE.owner], can_view_profit: true, permissions: Object.values(PERM), home: "dashboard" };
const AI_KEYS = ["ai-policy", "ai-report", "ai-settings", "ai-actions"] as const;

beforeEach(() => {
  getAiStatus.mockClear();
});

describe("cờ AI tắt", () => {
  it("Chủ cũng không thấy mục AI nào trong nav / menu / tìm lệnh", () => {
    const keys = visibleNav(OWNER).map((n) => n.key);
    for (const k of AI_KEYS) {
      expect(keys).not.toContain(k);
      expect(canView(OWNER, k)).toBe(false);
    }
    expect(menuItems(OWNER).some((n) => n.href.startsWith("/ai/"))).toBe(false);
  });

  it("AiDocBlockGate và ConfirmationAiBlock: không vẽ gì và không gọi status", () => {
    expect(renderToStaticMarkup(createElement(AiDocBlockGate, { targetModel: "sales.salesorder", targetId: "1" }))).toBe("");
    expect(renderToStaticMarkup(createElement(ConfirmationAiBlock, { noteId: 1 }))).toBe("");
    expect(getAiStatus).not.toHaveBeenCalled();
  });

  it("AiBlockFrame không vẽ khung", () => {
    expect(renderToStaticMarkup(createElement(AiBlockFrame, { proposals: [], onReject: () => {}, onConfirm: () => {} }))).toBe("");
  });

  it("DetailPage bỏ khe AI, không để cột phải rỗng", () => {
    const html = renderToStaticMarkup(createElement(DetailPage, { header: "H", aiSlot: createElement("div", { "data-ai-block": "" }, "AI"), children: "trái" }));
    expect(html).not.toContain("data-ai-block");
    expect(html).not.toContain("<aside");
    const withTimeline = renderToStaticMarkup(createElement(DetailPage, { header: "H", aiSlot: createElement("i"), timeline: createElement("b", null, "TL"), children: "trái" }));
    expect(withTimeline).toContain("TL");
    expect(withTimeline).not.toContain("<i");
  });

  it("trang /ai/*: AiFeatureGuard không mount màn AI", () => {
    const html = renderToStaticMarkup(createElement(AiFeatureGuard, null, createElement("p", null, "MAN-AI")));
    expect(html).not.toContain("MAN-AI");
  });

  it("SR-HIDE-AI-02: /ai/* hiện 'Không tìm thấy trang này', không nhắc cấp quyền", () => {
    const html = renderToStaticMarkup(createElement(AiFeatureGuard, null, createElement("p", null, "MAN-AI")));
    expect(html).toContain("Không tìm thấy trang này");
    expect(html).not.toContain("Chủ vựa");
    expect(html).not.toContain("quyền");
  });

  it("SR-HIDE-AI-02: không còn điểm vào 'Nhờ người xử lý'", () => {
    const step = { key: "confirm_payment", label: "X", actor: "user", allowed: false, who: ["Chủ"], missing: [], deadline: null, why: null, command: null, ai: null } as never;
    expect(escalatableStep({ next_steps: [step] })).toBeNull();
    const html = renderToStaticMarkup(createElement(GuidanceEscalate, { step, docType: "sales.salesorder", docId: 1, noticeHost: null }));
    expect(html).toBe("");
  });
});
