import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { StatusPath } from "./StatusPath";
import { Timeline } from "./Timeline";
import { CONFLICT_FIELD_MESSAGE, validateDraft } from "./InfoField";
import { AiBlockFrame, type AiProposalView } from "./AiBlockFrame";

const STEPS = [
  { key: "A", label: "Nháp" },
  { key: "B", label: "Đã nhập kho" },
  { key: "C", label: "Đã có hoá đơn" },
];

describe("StatusPath", () => {
  it("đánh dấu bước đã qua / hiện tại / chưa tới và dòng Tiếp theo · Đã làm", () => {
    const html = renderToStaticMarkup(createElement(StatusPath, { steps: STEPS, current: "B", next: "Ghi hoá đơn", done: ["Tạo phiếu"] }));
    expect(html).toMatch(/data-state="done"[^>]*>.*?<span>Nháp<\/span>/);
    expect(html).toContain('data-state="current"');
    expect(html).toContain('data-state="todo"');
    expect(html).toContain("Tiếp theo");
    expect(html).toContain("Ghi hoá đơn");
    expect(html).toContain("Đã làm");
  });
  it("kết thúc xấu (đã huỷ) hiện ở cuối", () => {
    const html = renderToStaticMarkup(createElement(StatusPath, { steps: STEPS, current: "B", badEnd: { label: "Đã huỷ" } }));
    expect(html).toContain('data-state="bad"');
    expect(html).toContain("Đã huỷ");
  });
});

describe("Timeline", () => {
  it("không in mã BR, có nhãn AI, ghi rõ khi bị cắt", () => {
    const html = renderToStaticMarkup(
      createElement(Timeline, {
        entries: [{ at: "2026-10-01T03:00:00Z", label: "Xác nhận nhập kho", actor: "AI của Lộc", byAi: true }],
        truncated: true,
      })
    );
    expect(html).not.toMatch(/BR-/);
    expect(html).toContain("AI");
    expect(html).toContain("Chỉ hiện 1 việc gần nhất.");
    expect(html).toContain("10:00"); // giờ Việt Nam
  });
  it("rỗng → thông báo, không có dòng", () => {
    const html = renderToStaticMarkup(createElement(Timeline, { entries: [] }));
    expect(html).toContain("Chưa có việc nào");
    expect(html).not.toContain("data-timeline-row");
  });
});

describe("InfoField sửa tại chỗ: kiểm nhập trước khi gửi (QA B5)", () => {
  it("để trống khi bắt buộc là lỗi nhập; có chữ thì hợp lệ", () => {
    expect(validateDraft("  ", { required: true })).toBe("Nhập giá trị cho ô này.");
    expect(validateDraft("", { required: false })).toBeNull();
    expect(validateDraft("12", { required: true })).toBeNull();
  });
  it("dùng validate của màn khi đã có giá trị", () => {
    expect(validateDraft("0", { required: true, validate: (v) => (Number(v) <= 0 ? "Phải lớn hơn 0." : null) })).toBe("Phải lớn hơn 0.");
  });
});

describe("InfoField sửa tại chỗ: xung đột phiên bản (L5)", () => {
  it("có câu ngắn riêng cho xung đột, không để im lặng", () => {
    expect(CONFLICT_FIELD_MESSAGE).toMatch(/vừa sửa/);
  });
});

describe("AiBlockFrame: khung hỏi nhanh tĩnh (QA B3) và nút Đồng ý khi thiếu chi tiết (Techlead M2)", () => {
  const noop = () => {};
  const starter = { chips: ["Tóm tắt lịch sử chứng từ này", "Chứng từ này còn thiếu gì?"], value: "", onChange: noop, onFocus: noop, onAsk: noop };
  const proposal = (over: Partial<AiProposalView> = {}): AiProposalView => ({
    id: "a1", proposedBy: "AI của Lộc", proposedAt: "2026-10-01T01:00:00Z", title: "Xác nhận phiếu", changes: [], state: "PENDING", waitSeconds: 3, ...over,
  });
  const render = (props: Partial<Parameters<typeof AiBlockFrame>[0]>) =>
    renderToStaticMarkup(createElement(AiBlockFrame, { proposals: [], onReject: noop, onConfirm: noop, ...props }));

  it("chip, ô hỏi và nút gửi hiện sẵn kể cả khi không có đề xuất", () => {
    const html = render({ starter });
    expect(html).toContain("data-ai-starter");
    expect(html).toContain("Tóm tắt lịch sử chứng từ này");
    expect(html).toContain("Chứng từ này còn thiếu gì?");
    expect(html).toContain('aria-label="Hỏi AI về chứng từ này"');
    expect(html).toContain('aria-label="Gửi câu hỏi"');
    expect(html).toContain("Chưa có đề xuất nào cho chứng từ này.");
  });
  it("có khe chat (trợ lý đã mở) thì khung tĩnh nhường chỗ", () => {
    const html = render({ starter, chat: createElement("div", { "data-chat-slot": "" }) });
    expect(html).toContain("data-chat-slot");
    expect(html).not.toContain("data-ai-starter");
  });
  it("thiếu chi tiết (blocked): Đồng ý khoá, KHÔNG hiện bộ đếm kẹt 'Đồng ý (3)', Từ chối vẫn dùng được", () => {
    const html = render({ proposals: [proposal({ waitSeconds: 0, blocked: true })] });
    expect(html).not.toContain("Đồng ý (");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Đồng ý<\/button>/);
    expect(html).toMatch(/<button(?![^>]*disabled)[^>]*>Từ chối<\/button>/);
  });
  it("đang chờ BR-AI-14 thì đếm ngược", () => {
    expect(render({ proposals: [proposal({ waitSeconds: 2 })] })).toContain("Đồng ý (2)");
  });
  it("việc đã nhờ nhóm xử lý (ESCALATED) hiện nhóm nhận việc, không có nút Đồng ý", () => {
    const html = render({ proposals: [proposal({ state: "ESCALATED", assigneeGroup: "Chủ" })] });
    expect(html).toContain("Đã nhờ nhóm Chủ xử lý.");
    expect(html).not.toContain("Từ chối");
  });
});

describe("AiBlockFrame: giữ khung hỏi nhanh trong lúc trợ lý nạp (B6, L9)", () => {
  const noop = () => {};
  const starter = { chips: ["Hỏi"], value: "abc", onChange: noop, onFocus: noop, onAsk: noop };
  const chat = createElement("p", null, "Đang mở trợ lý…");
  const render = (props: Partial<Parameters<typeof AiBlockFrame>[0]>) =>
    renderToStaticMarkup(createElement(AiBlockFrame, { proposals: [], onReject: noop, onConfirm: noop, ...props }));
  it("keepStarter: ô tĩnh và panel cùng có mặt", () => {
    const html = render({ chat, starter, keepStarter: true });
    expect(html).toContain("data-ai-starter");
    expect(html).toContain("Đang mở trợ lý");
  });
  it("keepStarter: ô tĩnh luôn đứng TRƯỚC khe chat (một vị trí cố định, React không dựng lại ô nhập)", () => {
    const html = render({ chat, starter, keepStarter: true });
    expect(html.indexOf("data-ai-starter")).toBeGreaterThan(-1);
    expect(html.indexOf("data-ai-starter")).toBeLessThan(html.indexOf("Đang mở trợ lý"));
    expect(html.match(/data-ai-starter/g)).toHaveLength(1);
  });
  it("không keepStarter: panel thay khung tĩnh như cũ", () => {
    const html = render({ chat, starter });
    expect(html).not.toContain("data-ai-starter");
    expect(html).toContain("Đang mở trợ lý");
  });
});
