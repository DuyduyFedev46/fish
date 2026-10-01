// Màn 404 / lỗi chung / không có quyền: nút về trang chính đi theo `homeHref` (G9), màn lỗi khớp board W6h.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: (p: { href: string; className?: string; children?: unknown }) => createElement("a", { href: p.href, className: p.className }, p.children as never),
}));

import { ErrorScreen } from "@/shared/ui/states/ErrorScreen";
import { NoPermission } from "@/shared/ui/states/NoPermission";
import { NotFoundScreen } from "@/shared/ui/states/NotFoundScreen";

describe("nút về trang chính", () => {
  it("mặc định: Về Tổng quan -> /overview/", () => {
    for (const el of [createElement(NotFoundScreen), createElement(ErrorScreen), createElement(NoPermission)]) {
      const out = renderToStaticMarkup(el);
      expect(out).toContain('href="/overview/"');
      expect(out).toContain("Về Tổng quan");
    }
  });

  it("người giao hàng: Về Việc giao của tôi -> /my-deliveries/, không còn link Tổng quan", () => {
    const home = { homeHref: "/my-deliveries/" };
    for (const el of [createElement(NotFoundScreen, home), createElement(ErrorScreen, home), createElement(NoPermission, home)]) {
      const out = renderToStaticMarkup(el);
      expect(out).toContain('href="/my-deliveries/"');
      expect(out).toContain("Về Việc giao của tôi");
      expect(out).not.toContain("/overview/");
      expect(out).not.toContain("Về Tổng quan");
    }
  });
});

describe("ErrorScreen theo board W6h", () => {
  const out = renderToStaticMarkup(createElement(ErrorScreen, { onRetry: () => undefined }));

  it("icon lỗi đỏ, tiêu đề, câu hướng dẫn kèm giờ dd/mm/yyyy hh:mm", () => {
    expect(out).toContain("state-ic-err");
    expect(out).toContain(">error<");
    expect(out).toContain("Có lỗi xảy ra");
    expect(out).toMatch(/Nếu vẫn lỗi, báo kỹ thuật kèm giờ <span class="num">\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}<\/span>/);
  });

  it("thứ tự nút: Về (phụ) rồi Thử lại (chính, bên phải)", () => {
    expect(out.indexOf("Về Tổng quan")).toBeGreaterThan(-1);
    expect(out.indexOf("Về Tổng quan")).toBeLessThan(out.indexOf("Thử lại"));
    expect(out).toContain("btn primary");
  });

  it("không có onRetry thì không có nút Thử lại; không in nội dung lỗi kỹ thuật", () => {
    const bare = renderToStaticMarkup(createElement(ErrorScreen));
    expect(bare).not.toContain("Thử lại");
    expect(bare).not.toMatch(/stack|TypeError|undefined/i);
  });
});
