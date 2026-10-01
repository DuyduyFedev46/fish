// SR-AIS-02 (đọc đúng `limits` phẳng của BE, không gửi "") và SR-AIS-03 (lưu "AI của tôi" không làm mất cấu hình nhóm).
// Chạy trên mock mô phỏng ĐÚNG ngữ nghĩa BE (`backend/apps/ai/settings/services.py`): PUT thay THẾ toàn bộ
// `group_levels`, `overrides`, `limits` (vắng khoá = rỗng), nên người gọi phải gửi lại đủ giá trị đang có.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { AiCommandLevel, MyConfig, MyConfigCommandItem } from "../types";
import type { MyConfigSavePayload } from "./payload";

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "1");
});
afterEach(() => {
  vi.unstubAllEnvs();
});

async function load() {
  const api = await import("./api");
  const payload = await import("./payload");
  return { ...api, ...payload };
}

/** id lệnh → { level, source } của toàn bộ lệnh trong mọi nhóm: dấu vân tay "mức hiệu lực" của một người. */
function levelsOf(config: MyConfig): Record<string, { level: string; source: string }> {
  const out: Record<string, { level: string; source: string }> = {};
  for (const group of config.groups) for (const cmd of group.commands) out[cmd.id] = { level: cmd.level, source: cmd.source };
  return out;
}
function levelOnly(config: MyConfig): Record<string, string> {
  return Object.fromEntries(Object.entries(levelsOf(config)).map(([id, v]) => [id, v.level]));
}

describe("SR-AIS-02: limits phẳng", () => {
  it("BE trả limits phẳng {kg, vnd} (chuỗi); ô hiện đúng giá trị của người dùng", async () => {
    const { getMyConfig, readLimitInputs } = await load();
    const config = await getMyConfig();
    const receive = config.groups.flatMap((g) => g.commands).find((c) => c.id === RECEIVE_BATCHES_COMMAND_ID);
    expect(receive?.limits).toEqual({ kg: "60", vnd: "6000000" });
    expect(readLimitInputs(receive?.limits ?? null)).toEqual({ kg: "60", vnd: "6000000" });
  });

  it("lệnh không có ngưỡng (limits null) cho ô rỗng", async () => {
    const { readLimitInputs } = await load();
    expect(readLimitInputs(null)).toEqual({ kg: "", vnd: "" });
  });

  it("để trống thì KHÔNG gửi khoá (không gửi chuỗi rỗng); trống cả hai thì bỏ cả lệnh", async () => {
    const { buildLimitsForSave } = await load();
    expect(buildLimitsForSave({ a: { kg: "", vnd: "6000000" }, b: { kg: "  ", vnd: "" }, c: { kg: "5" } })).toEqual({
      a: { vnd: "6000000" },
      c: { kg: "5" },
    });
  });

  it("lưu qua API với kg để trống: 200, ngưỡng kg biến mất, vnd giữ", async () => {
    const { getMyConfig, updateMyConfig, buildMyConfigPayload, readLimitInputs } = await load();
    const config = await getMyConfig();
    const limits = Object.fromEntries(
      config.groups.flatMap((g) => g.commands).filter((c) => c.limits).map((c) => [c.id, readLimitInputs(c.limits)])
    );
    limits[RECEIVE_BATCHES_COMMAND_ID] = { ...limits[RECEIVE_BATCHES_COMMAND_ID], kg: "" };
    const updated = await updateMyConfig(buildMyConfigPayload(config, { overrides: {}, limits }));
    const receive = updated.groups.flatMap((g) => g.commands).find((c) => c.id === RECEIVE_BATCHES_COMMAND_ID);
    expect(receive?.limits).toEqual({ vnd: "6000000" });
  });

  it("BE từ chối chuỗi rỗng ở ngưỡng (mock giống BE: số không hợp lệ -> 400)", async () => {
    const { getMyConfig, updateMyConfig } = await load();
    const config = await getMyConfig();
    await expect(
      updateMyConfig({
        base_version: config.version,
        groups: {},
        overrides: {},
        limits: { [RECEIVE_BATCHES_COMMAND_ID]: { kg: "" } },
        acknowledge_responsibility: true,
      })
    ).rejects.toMatchObject({ status: 400 });
  });
});

describe("SR-AIS-03: lưu không làm mất cấu hình nhóm", () => {
  /** Dựng người dùng có nhóm "Thu mua" đặt OFF cả đọc lẫn ghi (như `qa_pin`), rồi trả cấu hình đọc lại. */
  async function userWithPurchasingOff() {
    const api = await load();
    const base = await api.getMyConfig();
    await api.updateMyConfig({
      base_version: base.version,
      groups: { purchasing: { read: "OFF", write: "OFF" } },
      overrides: {},
      limits: {},
      acknowledge_responsibility: true,
    });
    return { ...api, before: await api.getMyConfig() };
  }

  it("nền: nhóm Thu mua OFF làm mọi lệnh của nhóm OFF", async () => {
    const { before } = await userWithPurchasingOff();
    const purchasing = before.groups.find((g) => g.group === "purchasing");
    expect(purchasing && purchasing.commands.length).toBeGreaterThan(0);
    for (const cmd of purchasing?.commands ?? []) expect(cmd.level).toBe("OFF");
  });

  it("đổi 1 lệnh rồi lưu bằng buildMyConfigPayload: mọi lệnh khác giữ nguyên mức, nhóm vẫn OFF", async () => {
    const { before, getMyConfig, updateMyConfig, buildMyConfigPayload } = await userWithPurchasingOff();
    const target = "sales.salesorder.list";
    const payload = buildMyConfigPayload(before, { overrides: { [target]: "OFF" }, limits: {} });
    expect(payload.groups).toMatchObject({ purchasing: { read: "OFF", write: "OFF" } });
    await updateMyConfig(payload);
    const after = await getMyConfig();
    const was = levelOnly(before);
    const now = levelOnly(after);
    for (const id of Object.keys(was)) {
      if (id === target) continue;
      expect(now[id], id).toBe(was[id]);
    }
    expect(now[target]).toBe("OFF");
    const purchasing = after.groups.find((g) => g.group === "purchasing");
    expect(purchasing?.read_level).toBe("OFF");
    expect(purchasing?.write_level).toBe("OFF");
  });

  it("không đổi gì rồi lưu: không lệnh nào đổi mức (đặc biệt không OFF -> C/A)", async () => {
    const { before, getMyConfig, updateMyConfig, buildMyConfigPayload } = await userWithPurchasingOff();
    await updateMyConfig(buildMyConfigPayload(before, { overrides: {}, limits: {} }));
    expect(levelOnly(await getMyConfig())).toEqual(levelOnly(before));
  });

  it("ghi lại đủ cả nhóm chưa cấu hình: giá trị gửi bằng đúng giá trị mặc định nên mức không đổi", async () => {
    const { getMyConfig, updateMyConfig, buildMyConfigPayload } = await load();
    const before = await getMyConfig();
    const payload = buildMyConfigPayload(before, { overrides: {}, limits: {} });
    expect(payload.groups).toEqual({
      purchasing: { read: "A", write: "C" },
      sales: { read: "A", write: "C" },
      customer_service: { read: "A", write: "C" },
    });
    await updateMyConfig(payload);
    expect(levelOnly(await getMyConfig())).toEqual(levelOnly(before));
  });

  it("mức ghi B mà môi trường không cho B: gửi hạ về C để BE không từ chối cả lần lưu", async () => {
    const { buildMyConfigPayload } = await load();
    const config = {
      ai_enabled: true,
      version: 1,
      killed: false,
      updated_at: "",
      global_mode: "on",
      write_levels_allowed: ["OFF", "C"],
      groups: [{ group: "purchasing", label: "Thu mua", read_level: "A", write_level: "B", commands: [] }],
    } as unknown as MyConfig;
    expect(buildMyConfigPayload(config, { overrides: {}, limits: {} }).groups).toEqual({ purchasing: { read: "A", write: "C" } });
  });

  it("tái hiện lỗi cũ: lưu KHÔNG kèm groups thì BE đặt lại group_levels = {} và lệnh OFF thành C", async () => {
    const { before, getMyConfig, updateMyConfig } = await userWithPurchasingOff();
    // Ép kiểu: kiểu `MyConfigSavePayload` bắt buộc `groups`; ở đây cố tình bỏ nó như màn cũ.
    await updateMyConfig({ base_version: before.version, overrides: {}, limits: {}, acknowledge_responsibility: true } as unknown as MyConfigSavePayload);
    const after = levelOnly(await getMyConfig());
    const purchasingWrite = before.groups.find((g) => g.group === "purchasing")?.commands.find((c) => c.kind === "write");
    expect(levelOnly(before)[purchasingWrite?.id ?? ""]).toBe("OFF");
    expect(after[purchasingWrite?.id ?? ""]).toBe("C");
  });
});

// ---- QA lần 1: B1 (ô ngưỡng không được biến mất) và B2 (môi trường chỉ cho C mà vẫn còn override B) ----

function command(extra: Partial<MyConfigCommandItem>): MyConfigCommandItem {
  return {
    id: RECEIVE_BATCHES_COMMAND_ID,
    title: "Nhập lô mua tại cảng",
    kind: "write",
    level: "C",
    source: "default",
    choices: ["OFF", "C", "B"],
    max_level: "B",
    locked_reason: null,
    red_zone: false,
    limits: null,
    ...extra,
  };
}

function configOf(allowed: AiCommandLevel[], commands: MyConfigCommandItem[]): MyConfig {
  return {
    ai_enabled: true,
    version: 3,
    killed: false,
    updated_at: "",
    global_mode: "on",
    write_levels_allowed: allowed,
    groups: [{ group: "purchasing", label: "Thu mua", read_level: "A", write_level: "C", commands }],
  } as MyConfig;
}

describe("B1: ô ngưỡng theo cờ supports_limits, không theo việc limits đang có khoá", () => {
  it("lệnh khai ngưỡng (supports_limits true) luôn có cả ô kg và vnd, kể cả khi limits null hoặc thiếu khoá", async () => {
    const { limitFieldsOf } = await import("./levels");
    expect(limitFieldsOf(command({ supports_limits: true, limits: null }))).toEqual(["kg", "vnd"]);
    expect(limitFieldsOf(command({ supports_limits: true, limits: { vnd: "6000000" } }))).toEqual(["kg", "vnd"]);
    expect(limitFieldsOf(command({ supports_limits: true, limits: { kg: "60", vnd: "6000000" } }))).toEqual(["kg", "vnd"]);
  });

  it("lệnh không khai ngưỡng (supports_limits false) không có ô nào", async () => {
    const { limitFieldsOf } = await import("./levels");
    expect(limitFieldsOf(command({ supports_limits: false, limits: null }))).toEqual([]);
  });

  it("tương thích BE chưa có cờ: theo khoá limits đang có; limits null thì không có ô", async () => {
    const { limitFieldsOf } = await import("./levels");
    expect(limitFieldsOf(command({ limits: { vnd: "6000000" } }))).toEqual(["vnd"]);
    expect(limitFieldsOf(command({ limits: { kg: "60", vnd: "1" } }))).toEqual(["kg", "vnd"]);
    expect(limitFieldsOf(command({ limits: null }))).toEqual([]);
  });

  it("xoá cả hai ô rồi lưu qua mock: BE trả limits null nhưng supports_limits vẫn true nên ô còn để nhập lại", async () => {
    const { getMyConfig, updateMyConfig, buildMyConfigPayload } = await load();
    const { limitFieldsOf } = await import("./levels");
    const config = await getMyConfig();
    const before = config.groups.flatMap((g) => g.commands).find((c) => c.id === RECEIVE_BATCHES_COMMAND_ID);
    expect(before?.supports_limits).toBe(true);
    const updated = await updateMyConfig(
      buildMyConfigPayload(config, { overrides: {}, limits: { [RECEIVE_BATCHES_COMMAND_ID]: { kg: "", vnd: "" } } })
    );
    const after = updated.groups.flatMap((g) => g.commands).find((c) => c.id === RECEIVE_BATCHES_COMMAND_ID);
    expect(after?.limits).toBeNull();
    expect(after && limitFieldsOf(after)).toEqual(["kg", "vnd"]);
  });

  it("mock: chỉ lệnh nhập lô khai ngưỡng, các lệnh khác supports_limits false", async () => {
    const { getMyConfig } = await load();
    const commands = (await getMyConfig()).groups.flatMap((g) => g.commands);
    expect(commands.filter((c) => c.supports_limits).map((c) => c.id)).toEqual([RECEIVE_BATCHES_COMMAND_ID]);
  });
});

describe("B2: trần môi trường là C thì không gửi override B và không hiện OFF", () => {
  const WRITE_ENV_C: AiCommandLevel[] = ["OFF", "C"];
  const WRITE_ENV_B: AiCommandLevel[] = ["OFF", "C", "B"];

  it("override B bị hạ về C khi môi trường chỉ cho C; override khác giữ nguyên", async () => {
    const { buildMyConfigPayload } = await load();
    const config = configOf(WRITE_ENV_C, [command({ level: "B", source: "override" })]);
    const payload = buildMyConfigPayload(config, {
      overrides: { [RECEIVE_BATCHES_COMMAND_ID]: "B", "sales.salesorder.list": "OFF" },
      limits: {},
    });
    expect(payload.overrides).toEqual({ [RECEIVE_BATCHES_COMMAND_ID]: "C", "sales.salesorder.list": "OFF" });
  });

  it("môi trường cho B thì override B giữ nguyên", async () => {
    const { buildMyConfigPayload } = await load();
    const config = configOf(WRITE_ENV_B, [command({ level: "B", source: "override" })]);
    expect(buildMyConfigPayload(config, { overrides: { [RECEIVE_BATCHES_COMMAND_ID]: "B" }, limits: {} }).overrides).toEqual({
      [RECEIVE_BATCHES_COMMAND_ID]: "B",
    });
  });

  it("lệnh bị khoá (vùng đỏ chưa mở) hoặc trần lệnh là C: override B cũng hạ về C để BE không báo lỗi", async () => {
    const { buildMyConfigPayload } = await load();
    const locked = command({ id: "sales.salesorder.confirm_payment", red_zone: true, max_level: "C", locked_reason: { code: "BR-AI-18", text: "x" } });
    const capped = command({ id: "sales.refund.create_refund", max_level: "C" });
    const config = configOf(WRITE_ENV_B, [locked, capped]);
    expect(
      buildMyConfigPayload(config, { overrides: { [locked.id]: "B", [capped.id]: "B" }, limits: {} }).overrides
    ).toEqual({ [locked.id]: "C", [capped.id]: "C" });
  });

  it("ô chọn: mức B không còn chọn được thì hiển thị mức hiệu lực C, không phải OFF", async () => {
    const { displayLevel, commandChoices } = await import("./levels");
    const cmd = command({ level: "B", source: "override" });
    const config = configOf(WRITE_ENV_C, [cmd]);
    expect(commandChoices(config, cmd, "B")).toEqual(["OFF", "C"]);
    expect(displayLevel(config, cmd, "B")).toBe("C");
    // môi trường cho B thì vẫn B
    const configB = configOf(WRITE_ENV_B, [cmd]);
    expect(commandChoices(configB, cmd, "B")).toContain("B");
    expect(displayLevel(configB, cmd, "B")).toBe("B");
  });

  it("nhóm đặt B mà lệnh theo nhóm: hiển thị C khi môi trường chỉ cho C", async () => {
    const { displayLevel } = await import("./levels");
    const cmd = command({ level: "B", source: "group" });
    expect(displayLevel(configOf(WRITE_ENV_C, [cmd]), cmd, cmd.level)).toBe("C");
  });

  it("lệnh đọc không bị ảnh hưởng: OFF và A giữ nguyên", async () => {
    const { displayLevel } = await import("./levels");
    const cmd = command({ kind: "read", level: "OFF", choices: ["OFF", "A"], max_level: "A" });
    const config = configOf(WRITE_ENV_C, [cmd]);
    expect(displayLevel(config, cmd, "OFF")).toBe("OFF");
    expect(displayLevel(config, cmd, "A")).toBe("A");
  });
});

describe("B2: thông báo lỗi lưu nêu rõ lệnh nào", () => {
  it("BR-AI-19 có errors theo id lệnh: nêu tên lệnh và lý do", async () => {
    const { describeSaveError } = await import("./levels");
    const { ApiError } = await import("@/shared/lib/http");
    const config = configOf(["OFF", "C", "B"], [command({})]);
    const err = new ApiError("Dữ liệu cấu hình không hợp lệ.", 400, "BR-AI-19", {
      errors: { [RECEIVE_BATCHES_COMMAND_ID]: "vượt trần của Chủ", "groups.purchasing.write": "Mức ghi không hợp lệ" },
    });
    const text = describeSaveError(err, config, null);
    expect(text).toContain("Nhập lô mua tại cảng");
    expect(text).toContain("vượt trần của Chủ");
    expect(text).toContain("Thu mua");
    expect(text).not.toContain(RECEIVE_BATCHES_COMMAND_ID);
  });

  it("BR-AI-19 chỉ một lỗi và câu chung trùng lý do: nêu một lần, kèm tên lệnh", async () => {
    const { describeSaveError } = await import("./levels");
    const { ApiError } = await import("@/shared/lib/http");
    const config = configOf(["OFF", "C", "B"], [command({})]);
    const err = new ApiError("vượt trần của Chủ", 400, "BR-AI-19", { errors: { [RECEIVE_BATCHES_COMMAND_ID]: "vượt trần của Chủ" } });
    expect(describeSaveError(err, config, null)).toBe("Nhập lô mua tại cảng: vượt trần của Chủ.");
  });

  it("qua mock thật: lệnh ngoài quyền gửi lên -> 400 BR-AI-19, thông báo nêu id lệnh sai (mock trải errors như BE)", async () => {
    const { getMyConfig, updateMyConfig, buildMyConfigPayload } = await load();
    const { describeSaveError } = await import("./levels");
    const config = await getMyConfig();
    const payload = buildMyConfigPayload(config, { overrides: { "sales.salesorder.list": "B" }, limits: {} });
    // lệnh đọc không có mức B: payload hạ về C, nên cố tình ghi đè trực tiếp để gây 400 BR-AI-19 từ mock
    payload.overrides["sales.salesorder.list"] = "B";
    const error = await updateMyConfig(payload).catch((e) => e);
    expect(error.code).toBe("BR-AI-19");
    expect(describeSaveError(error, config, payload)).toContain("Xem danh sách đơn bán: Mức không hợp lệ");
  });

  it("BR-AI-27 không kèm errors: nêu các lệnh trong thân đã gửi đang ở mức B", async () => {
    const { describeSaveError } = await import("./levels");
    const { ApiError } = await import("@/shared/lib/http");
    const config = configOf(["OFF", "C", "B"], [command({})]);
    const err = new ApiError("Môi trường hiện tại không hỗ trợ mức tự thực thi B.", 400, "BR-AI-27");
    const text = describeSaveError(err, config, {
      base_version: 3,
      groups: {},
      overrides: { [RECEIVE_BATCHES_COMMAND_ID]: "B" },
      limits: {},
      acknowledge_responsibility: true,
    });
    expect(text).toContain("Môi trường hiện tại không hỗ trợ mức tự thực thi B.");
    expect(text).toContain("Nhập lô mua tại cảng");
  });

  it("lỗi khác hoặc không phải ApiError: giữ nguyên thông điệp", async () => {
    const { describeSaveError } = await import("./levels");
    const { ApiError } = await import("@/shared/lib/http");
    const config = configOf(["OFF", "C"], []);
    expect(describeSaveError(new ApiError("Cấu hình đã thay đổi ở phiên khác.", 409, "AI_CONFIG_CONFLICT"), config, null)).toBe(
      "Cấu hình đã thay đổi ở phiên khác."
    );
    expect(describeSaveError(new Error("x"), config, null)).toBe("x");
    expect(describeSaveError("lạ", config, null)).toBe("Lỗi khi lưu cấu hình.");
  });
});
