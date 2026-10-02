// ED-08: phần thuần của màn "AI của tôi" — nhãn mức, mức bị khoá, ghi chú khoá, ô ngưỡng, thay đổi chưa lưu.
import { describe, expect, it } from "vitest";
import type { MyConfig, MyConfigCommandItem } from "../types";
import { isDirty, levelChoiceLabel, levelChoices, limitErrors, limitProblem, lockNote } from "./view";

const cmd = (over: Partial<MyConfigCommandItem>): MyConfigCommandItem =>
  ({
    id: "x.write",
    title: "Việc ghi",
    kind: "write",
    level: "C",
    source: "default",
    max_level: "B",
    red_zone: false,
    supports_limits: true,
    limits: null,
    locked_reason: null,
    ...over,
  }) as MyConfigCommandItem;

const config = (commands: MyConfigCommandItem[], allowed = ["OFF", "C", "B"]): MyConfig =>
  ({
    ai_enabled: true,
    version: 1,
    killed: false,
    updated_at: "2026-10-01T10:00:00+07:00",
    global_mode: "on",
    write_levels_allowed: allowed,
    groups: [{ group: "sales", label: "Bán hàng", read_level: "A", write_level: "C", commands }],
  }) as MyConfig;

describe("levelChoiceLabel", () => {
  it("A và B có chữ cái, Hỏi trước và Tắt thì không", () => {
    expect(levelChoiceLabel("A")).toBe("A · Tự đọc");
    expect(levelChoiceLabel("B")).toBe("B · Tự ghi");
    expect(levelChoiceLabel("OFF")).toBe("Tắt");
    expect(levelChoiceLabel("C")).toBe("Hỏi trước khi làm");
  });
});

describe("levelChoices", () => {
  it("lệnh ghi hiện đủ Tắt/Hỏi trước/Tự ghi", () => {
    const c = cmd({});
    const out = levelChoices(config([c]), c, "C");
    expect(out.map((o) => o.level)).toEqual(["OFF", "C", "B"]);
    expect(out.find((o) => o.selected)?.level).toBe("C");
    expect(out.every((o) => !o.locked)).toBe(true);
  });
  it("Chủ chưa mở mức B thì B vẫn hiện nhưng bị khoá", () => {
    const c = cmd({});
    const out = levelChoices(config([c], ["OFF", "C"]), c, "C");
    expect(out.find((o) => o.level === "B")?.locked).toBe(true);
  });
  it("vùng đỏ chưa chọn B thì B khoá", () => {
    const c = cmd({ red_zone: true });
    expect(levelChoices(config([c]), c, "C").find((o) => o.level === "B")?.locked).toBe(true);
  });
  it("lệnh đọc chỉ có Tắt và Tự đọc", () => {
    const c = cmd({ kind: "read", max_level: "A", level: "A" });
    expect(levelChoices(config([c]), c, "A").map((o) => o.level)).toEqual(["OFF", "A"]);
  });
});

describe("lockNote", () => {
  it("lệnh đọc không có ghi chú", () => {
    expect(lockNote(config([]), cmd({ kind: "read" }))).toBeNull();
  });
  it("ưu tiên lời của BE", () => {
    const c = cmd({ locked_reason: { code: "X", text: "Đang bị khoá." } as MyConfigCommandItem["locked_reason"] });
    expect(lockNote(config([c]), c)).toBe("Đang bị khoá.");
  });
  it("không khoá thì không ghi chú; vùng đỏ chưa mở thì nói Chủ chưa cho phép", () => {
    const free = cmd({});
    expect(lockNote(config([free]), free)).toBeNull();
    const red = cmd({ red_zone: true, max_level: "B" });
    expect(lockNote(config([red], ["OFF", "C"]), red)).toBe("Chủ chưa cho phép.");
  });
  it("không hoàn tác được thì luôn hỏi trước", () => {
    const c = cmd({ max_level: "C" });
    expect(lockNote(config([c]), c)).toMatch(/hỏi trước/);
  });
});

describe("ô ngưỡng", () => {
  it("rỗng được, số hợp lệ, chữ thì lỗi", () => {
    expect(limitProblem("")).toBeNull();
    expect(limitProblem(" 150.5 ")).toBeNull();
    expect(limitProblem("abc")).not.toBeNull();
    expect(limitProblem("-3")).not.toBeNull();
  });
  it("chỉ kiểm lệnh đang ở mức B", () => {
    const c = cmd({});
    const cfg = config([c]);
    expect(limitErrors(cfg, { "x.write": "C" }, { "x.write": { kg: "abc" } })).toEqual({});
    expect(limitErrors(cfg, { "x.write": "B" }, { "x.write": { kg: "abc" } })).toHaveProperty(["x.write.kg"]);
  });
});

describe("isDirty", () => {
  it("giống bản đang lưu thì không bẩn; đổi mức hoặc ngưỡng thì bẩn", () => {
    const c = cmd({});
    const cfg = config([c]);
    expect(isDirty(cfg, {}, {}, {}, {})).toBe(false);
    expect(isDirty(cfg, { "x.write": "OFF" }, {}, {}, {})).toBe(true);
    expect(isDirty(cfg, {}, { "x.write": { kg: "5" } }, {}, { "x.write": { kg: "" } })).toBe(true);
  });
});
