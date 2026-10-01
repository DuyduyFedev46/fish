// Chip: giá trị lạ hiện đúng mã gốc trong chip xám (ED-02-AC4); giá trị trống hiện "—" không chip.
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ENUMS } from "@/shared/lib/enums";
import { Chip } from "@/shared/ui/Chip";

const html = (value: string | null | undefined) =>
  renderToStaticMarkup(createElement(Chip, { table: ENUMS.salesOrderStatus, value }));

describe("Chip", () => {
  it("giá trị biết: nhãn + tông màu", () => {
    expect(html("BOOKED")).toBe('<span class="stat-chip warn">Giữ chỗ</span>');
  });
  it("giá trị lạ: chip trung tính ghi đúng mã gốc, không phải 'Không rõ'", () => {
    const out = html("NEW_FANCY_STATE");
    expect(out).toBe('<span class="stat-chip mute">NEW_FANCY_STATE</span>');
    expect(out).not.toContain("Không rõ");
  });
  it("null, undefined, rỗng: dấu gạch ngang, không chip", () => {
    for (const v of [null, undefined, ""]) {
      const out = html(v);
      expect(out).toContain("—");
      expect(out).not.toContain("stat-chip");
    }
  });
});
