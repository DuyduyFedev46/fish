// DataTable (02b §4): cột `locked` (giá vốn, lãi lỗ) chỉ vào DOM khi `canViewCost`; 4 trạng thái; mờ khi stale.
// Vẽ bằng react-dom/server (không cần DOM giả).
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: (p: { href: string; className?: string; children?: unknown }) => createElement("a", { href: p.href, className: p.className }, p.children as never),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => undefined }) }));

import { DataTable, type Column } from "@/shared/ui/list/DataTable";

type Row = { id: number; code: string; total: string; cost: string };
const rows: Row[] = [
  { id: 1, code: "SO-A", total: "540.000 đ", cost: "CVON-111" },
  { id: 2, code: "SO-B", total: "120.000 đ", cost: "CVON-222" },
];
const columns: Column<Row>[] = [
  { key: "code", header: "Mã đơn", render: (r) => r.code },
  { key: "total", header: "Tổng tiền", num: true, render: (r) => r.total },
  { key: "cost", header: "Giá vốn", num: true, locked: true, render: (r) => r.cost },
];

function html(over: Record<string, unknown> = {}) {
  return renderToStaticMarkup(
    createElement(DataTable<Row>, {
      columns,
      rows,
      rowKey: (r: Row) => r.id,
      noun: "đơn hàng",
      empty: { title: "Chưa có đơn hàng nào", hint: "Đơn mới sẽ hiện ở đây." },
      caption: "Danh sách đơn",
      canViewCost: true,
      ...over,
    }),
  );
}

describe("DataTable: cột giá vốn (locked)", () => {
  it("canViewCost=false: tiêu đề và mọi ô của cột khoá không có trong DOM", () => {
    const out = html({ canViewCost: false });
    expect(out).not.toContain("Giá vốn");
    expect(out).not.toContain("CVON-111");
    expect(out).not.toContain("CVON-222");
    expect(out).not.toContain("cột giới hạn quyền xem");
    expect(out).toContain("Tổng tiền");
    expect(out).toContain("540.000 đ");
  });

  it("canViewCost=true: có tiêu đề, icon khoá và giá trị", () => {
    const out = html({ canViewCost: true });
    expect(out).toContain("Giá vốn");
    expect(out).toContain(">lock<");
    expect(out).toContain("cột giới hạn quyền xem");
    expect(out).toContain("CVON-111");
  });

  it("render của cột khoá không bị gọi khi không có quyền", () => {
    const spy = vi.fn((r: Row) => r.cost);
    html({ canViewCost: false, columns: [columns[0], { key: "cost", header: "Giá vốn", locked: true, render: spy }] });
    expect(spy).not.toHaveBeenCalled();
  });

  it("trạng thái tải/trống cũng không có cột khoá khi không có quyền", () => {
    expect(html({ canViewCost: false, rows: null, loading: true })).not.toContain("Giá vốn");
    expect(html({ canViewCost: false, rows: [] })).not.toContain("Giá vốn");
  });
});

describe("DataTable: trạng thái", () => {
  it("đang tải: giữ tiêu đề cột, có khung xương và thông báo cho trình đọc", () => {
    const out = html({ rows: null, loading: true });
    expect(out).toContain("Mã đơn");
    expect(out).toContain("lt-skel");
    expect(out).toContain("Đang tải dữ liệu");
    expect(out).toContain('aria-busy="true"');
  });

  it("lỗi: hiện thông điệp và nút Thử lại", () => {
    const out = html({ rows: [], error: "Không tải được danh sách đơn.", onRetry: () => undefined });
    expect(out).toContain("Không tải được danh sách đơn.");
    expect(out).toContain("Thử lại");
  });

  it("trống: tiêu đề + 1 câu; có từ khoá thì thành 'Không tìm thấy … khớp với'", () => {
    expect(html({ rows: [] })).toContain("Chưa có đơn hàng nào");
    const q = html({ rows: [], query: "xyz", onClearQuery: () => undefined });
    expect(q).toContain("Không tìm thấy đơn hàng khớp với “xyz”");
    expect(q).toContain("Xoá tìm kiếm");
  });

  it("stale=true làm mờ dữ liệu cũ; mặc định không mờ khi có mạng", () => {
    expect(html({ stale: true })).toContain("lt-card is-stale");
    expect(html()).not.toContain("is-stale");
  });

  it("dòng có rowHref: ô đầu là liên kết", () => {
    const out = html({ rowHref: (r: Row) => `/orders/${r.id}/` });
    expect(out).toContain('href="/orders/1/"');
    expect(out).toContain("lt-click");
  });
});

describe("DataTable: khung xương ẩn cột như bảng thật (17b F4)", () => {
  const cols: Column<Row>[] = [
    { key: "code", header: "Mã đơn", render: (r) => r.code },
    { key: "total", header: "Tổng tiền", num: true, hideBelow: 720, render: (r) => r.total },
    { key: "cost", header: "Giá vốn", num: true, locked: true, hideBelow: 980, render: (r) => r.cost },
  ];
  const tdClasses = (out: string, rowClass: string) => {
    const row = out.split("<tr").find((s) => s.includes(rowClass)) ?? "";
    return [...row.matchAll(/<td[^>]*?class="([^"]*)"/g)].map((m) => m[1]);
  };

  it("ô khung xương mang đúng class ẩn cột (lt-hb-*) như ô dữ liệu", () => {
    const skel = tdClasses(html({ columns: cols, rows: null, loading: true }), "lt-skel");
    const real = tdClasses(html({ columns: cols, rowHref: (r: Row) => `/x/${r.id}/` }), "lt-click");
    expect(skel.some((c) => c.includes("lt-hb-720"))).toBe(true);
    expect(skel.some((c) => c.includes("lt-hb-980"))).toBe(true);
    expect(skel.map((c) => c.match(/lt-hb-\d+/)?.[0] ?? "")).toEqual(real.map((c) => c.match(/lt-hb-\d+/)?.[0] ?? ""));
  });

  it("không quyền giá vốn: khung xương cũng bỏ cột khoá (cùng số ô với bảng thật)", () => {
    const out = html({ columns: cols, rows: null, loading: true, canViewCost: false });
    const skelRow = out.split("<tr").find((s) => s.includes("lt-skel")) ?? "";
    expect((skelRow.match(/<td/g) ?? []).length).toBe(2);
  });
});
