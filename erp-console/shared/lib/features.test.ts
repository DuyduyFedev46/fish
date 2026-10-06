// W39: giao diện AI chỉ hiện khi cờ build BẬT và BE báo bật; `me` chưa tải xong = tắt.
// Test grep: ngoài features.ts, không file nguồn nào được import AI_FEATURES_ENABLED (nơi khác phải gọi aiVisible).
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

async function load(flag: string) {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_AI_FEATURES", flag);
  return import("./features");
}

afterEach(() => vi.unstubAllEnvs());

describe("aiVisible", () => {
  it("bốn tổ hợp cờ build × BE", async () => {
    const on = await load("1");
    expect(on.aiVisible({ ai_features_enabled: true })).toBe(true);
    expect(on.aiVisible({ ai_features_enabled: false })).toBe(false);
    const off = await load("0");
    expect(off.aiVisible({ ai_features_enabled: true })).toBe(false);
    expect(off.aiVisible({ ai_features_enabled: false })).toBe(false);
  });
  it("me chưa tải xong hoặc BE chưa trả cờ thì tắt", async () => {
    const on = await load("1");
    expect(on.aiVisible(null)).toBe(false);
    expect(on.aiVisible(undefined)).toBe(false);
    expect(on.aiVisible({})).toBe(false);
  });
});

function walk(dir: string, out: string[]): string[] {
  for (const name of readdirSync(dir)) {
    if (["node_modules", ".next", "out", "e2e"].includes(name)) continue;
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.(ts|tsx)$/.test(name)) out.push(full);
  }
  return out;
}

describe("một cờ AI duy nhất", () => {
  it("ngoài features.ts và test, không file nào import AI_FEATURES_ENABLED", () => {
    const root = path.resolve(__dirname, "../..");
    const offenders = walk(root, [])
      .filter((f) => !/shared[\\/]lib[\\/]features\.ts$/.test(f) && !/\.test\.tsx?$/.test(f))
      .filter((f) => /import[^;]*\bAI_FEATURES_ENABLED\b/.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });
});
