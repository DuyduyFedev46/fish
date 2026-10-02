// Phần THUẦN của màn "Chính sách AI" (ED-41 / W4c): nhập liệu trần lệnh, kiểm, so thay đổi, mô tả việc nhạy cảm.
// Quy tắc ghi caps vẫn ở ./caps.ts (buildCapsForSave); file này chỉ lo chữ người dùng nhập <-> thứ gửi lên.

import { ENUMS } from "@/shared/lib/enums";
import type { AiPolicy, AiPolicyRedZoneItem, AiPolicyUserSummary, PolicyCaps } from "../types";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { ReceiveBatchesCap } from "./caps";

export type GlobalMode = AiPolicy["global_mode"];

export const MODE_CARDS: { value: GlobalMode; title: string; text: string }[] = [
  { value: "on", title: ENUMS.aiGlobalMode.on.label, text: "Theo mức từng người chọn." },
  { value: "c_only", title: ENUMS.aiGlobalMode.c_only.label, text: "Việc thay đổi dữ liệu đều hỏi trước." },
  { value: "off", title: ENUMS.aiGlobalMode.off.label, text: "Dừng mọi việc AI." },
];

/** Mô tả ngắn từng việc nhạy cảm theo bản thiết kế; việc BE thêm mới thì dùng câu `can_do` của BE. */
const RED_ZONE_SHORT: Record<string, string> = {
  "inventory.close_batch": "Khoá giá vốn của lô.",
  "sales.confirm_refund": "Xác nhận đã trả tiền lại cho khách.",
  "sales.confirm_payment_manual": "Khớp tiền ngân hàng vào đơn.",
};

export function redZoneDescription(rz: AiPolicyRedZoneItem): string {
  return RED_ZONE_SHORT[rz.perm] ?? rz.can_do;
}

// ---- Trần lệnh "Nhập lô mua tại cảng" ----

export type CapForm = { kg: string; vnd: string; daily: string };

const textOf = (v: string | number | null | undefined): string => (v === null || v === undefined ? "" : String(v));

export function capFormOf(caps: Readonly<PolicyCaps> | null | undefined): CapForm {
  const c = caps?.[RECEIVE_BATCHES_COMMAND_ID] ?? {};
  return { kg: textOf(c.kg), vnd: textOf(c.vnd), daily: textOf(c.daily) };
}

/** Rỗng = không giới hạn. kg nhận số thập phân; đồng và số lần nhận số nguyên không âm. */
export function capProblem(field: keyof CapForm, value: string): string | null {
  const v = value.trim();
  if (!v) return null;
  if (field === "kg") return /^\d+(\.\d+)?$/.test(v) ? null : "Nhập số không âm, ví dụ 200.";
  return /^\d+$/.test(v) ? null : "Nhập số nguyên không âm, ví dụ 20.";
}

export function capErrors(form: CapForm): Partial<Record<keyof CapForm, string>> {
  const out: Partial<Record<keyof CapForm, string>> = {};
  (["kg", "vnd", "daily"] as const).forEach((f) => {
    const p = capProblem(f, form[f]);
    if (p) out[f] = p;
  });
  return out;
}

/** Thứ gửi lên BE: kg/vnd là chuỗi số (hoặc null), daily là số (hoặc null). Gọi sau khi capErrors rỗng. */
export function capsToSave(form: CapForm): ReceiveBatchesCap {
  const kg = form.kg.trim();
  const vnd = form.vnd.trim();
  const daily = form.daily.trim();
  return { kg: kg ? String(Number(kg)) : null, vnd: vnd ? String(Number(vnd)) : null, daily: daily ? Number(daily) : null };
}

const sameNumber = (a: string, b: string): boolean => {
  const x = a.trim();
  const y = b.trim();
  if (!x || !y) return x === y;
  return Number(x) === Number(y);
};

export function capsEqual(a: CapForm, b: CapForm): boolean {
  return sameNumber(a.kg, b.kg) && sameNumber(a.vnd, b.vnd) && sameNumber(a.daily, b.daily);
}

export type PolicyForm = { mode: GlobalMode; redZone: Record<string, boolean>; caps: CapForm };

export function formOf(policy: AiPolicy): PolicyForm {
  const redZone: Record<string, boolean> = {};
  for (const rz of policy.red_zone) redZone[rz.perm] = rz.open;
  return { mode: policy.global_mode, redZone, caps: capFormOf(policy.caps) };
}

export function isPolicyDirty(base: PolicyForm, now: PolicyForm): boolean {
  if (base.mode !== now.mode) return true;
  for (const perm of Object.keys({ ...base.redZone, ...now.redZone })) {
    if ((base.redZone[perm] ?? false) !== (now.redZone[perm] ?? false)) return true;
  }
  return !capsEqual(base.caps, now.caps);
}

// ---- Danh sách nhân viên ----

export function userInitial(name: string): string {
  const t = name.trim();
  return t ? t.charAt(0).toLocaleUpperCase("vi-VN") : "?";
}

/** Số việc theo mức, thứ tự như bản thiết kế: A, B, C, Tắt. */
export function countChips(u: AiPolicyUserSummary): { key: string; text: string; title: string }[] {
  return [
    { key: "A", text: `A ${u.counts.A}`, title: `${ENUMS.aiLevel.A.label}: ${u.counts.A} việc` },
    { key: "B", text: `B ${u.counts.B}`, title: `${ENUMS.aiLevel.B.label}: ${u.counts.B} việc` },
    { key: "C", text: `C ${u.counts.C}`, title: `${ENUMS.aiLevel.C.label}: ${u.counts.C} việc` },
    { key: "OFF", text: `Tắt ${u.counts.OFF}`, title: `${ENUMS.aiLevel.OFF.label}: ${u.counts.OFF} việc` },
  ];
}

/** Dòng phụ ở đầu trang: "Phiên bản 4 · bản chạy thử". */
export function policySubtitle(policy: Pick<AiPolicy, "version" | "env">): string {
  return policy.env === "production" ? `Phiên bản ${policy.version}` : `Phiên bản ${policy.version} · bản chạy thử`;
}
