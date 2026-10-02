// ED-41: phần thuần của màn "Chính sách AI".
import { describe, expect, it } from "vitest";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { AiPolicy, AiPolicyRedZoneItem, AiPolicyUserSummary } from "../types";
import { capErrors, capFormOf, capProblem, capsEqual, capsToSave, countChips, formOf, isPolicyDirty, policySubtitle, redZoneDescription, userInitial } from "./view";

const rz = (over: Partial<AiPolicyRedZoneItem>): AiPolicyRedZoneItem => ({
  perm: "x.y",
  label: "X",
  open: false,
  commands: [],
  can_do: "Câu của BE.",
  cannot_do: "",
  legal_note: "",
  delay_minutes: 0,
  ...over,
});

describe("trần lệnh", () => {
  it("đọc từ caps của BE, thiếu thì rỗng", () => {
    expect(capFormOf({ [RECEIVE_BATCHES_COMMAND_ID]: { kg: "200", vnd: 30000000, daily: 20 } })).toEqual({ kg: "200", vnd: "30000000", daily: "20" });
    expect(capFormOf(undefined)).toEqual({ kg: "", vnd: "", daily: "" });
  });
  it("rỗng được; kg nhận thập phân; đồng và số lần chỉ nhận số nguyên", () => {
    expect(capProblem("kg", "")).toBeNull();
    expect(capProblem("kg", "12.5")).toBeNull();
    expect(capProblem("vnd", "12.5")).not.toBeNull();
    expect(capProblem("daily", "-1")).not.toBeNull();
    expect(capProblem("kg", "abc")).not.toBeNull();
  });
  it("capErrors gom lỗi theo ô", () => {
    expect(capErrors({ kg: "x", vnd: "5", daily: "" })).toEqual({ kg: expect.any(String) });
    expect(capErrors({ kg: "", vnd: "", daily: "" })).toEqual({});
  });
  it("capsToSave: rỗng thành null, số thành chuỗi/số chuẩn", () => {
    expect(capsToSave({ kg: " 200.50 ", vnd: "", daily: "20" })).toEqual({ kg: "200.5", vnd: null, daily: 20 });
  });
  it("capsEqual so theo giá trị số", () => {
    expect(capsEqual({ kg: "200", vnd: "", daily: "" }, { kg: "200.0", vnd: "", daily: "" })).toBe(true);
    expect(capsEqual({ kg: "200", vnd: "", daily: "" }, { kg: "", vnd: "", daily: "" })).toBe(false);
  });
});

describe("isPolicyDirty", () => {
  const policy = { version: 1, global_mode: "on", env: "staging", production_ready: false, red_zone: [rz({ perm: "a" })], caps: {}, users: [] } as AiPolicy;
  it("không đổi thì sạch; đổi chế độ, công tắc hay trần thì bẩn", () => {
    const base = formOf(policy);
    expect(isPolicyDirty(base, formOf(policy))).toBe(false);
    expect(isPolicyDirty(base, { ...base, mode: "off" })).toBe(true);
    expect(isPolicyDirty(base, { ...base, redZone: { a: true } })).toBe(true);
    expect(isPolicyDirty(base, { ...base, caps: { kg: "1", vnd: "", daily: "" } })).toBe(true);
  });
});

describe("mô tả và nhân viên", () => {
  it("việc nhạy cảm đã biết dùng câu ngắn, việc lạ dùng câu của BE", () => {
    expect(redZoneDescription(rz({ perm: "inventory.close_batch" }))).toBe("Khoá giá vốn của lô.");
    expect(redZoneDescription(rz({ perm: "zzz" }))).toBe("Câu của BE.");
  });
  it("chữ cái đầu và số việc theo mức", () => {
    expect(userInitial("  lộc")).toBe("L");
    expect(userInitial("")).toBe("?");
    const u = { counts: { A: 1, B: 2, C: 3, OFF: 4 } } as AiPolicyUserSummary;
    expect(countChips(u).map((c) => c.text)).toEqual(["A 1", "B 2", "C 3", "Tắt 4"]);
  });
  it("dòng phụ ghi bản chạy thử khi không phải production", () => {
    expect(policySubtitle({ version: 4, env: "staging" })).toBe("Phiên bản 4 · bản chạy thử");
    expect(policySubtitle({ version: 4, env: "production" })).toBe("Phiên bản 4");
  });
});
