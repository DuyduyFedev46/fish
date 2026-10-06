// Mock CS-18 theo contract THẬT của BE (03-dev-notes.md, Lô 5 BE mục 2): /api/confirmation/scripts/ và khoá `scripts` của chi tiết hàng chờ.
// - GET: cần delivery.view_callscript (Chủ, Quản lý, CSKH); người có change_callscript (Chủ) thấy cả kịch bản đã tắt, người khác chỉ thấy đang bật.
// - POST: add_callscript (Chủ). 400 nếu tình huống sai/đã có, nội dung rỗng hoặc quá 2000 ký tự, hoặc có chuỗi từ 9 chữ số (code BR-GH-19).
// - PATCH /{situation}/: change_callscript (Chủ); 404 nếu chưa có kịch bản tình huống đó. Không có DELETE (405).
// - Chi tiết hàng chờ: FIRST_ORDER nếu khách chưa có đơn xử lý khác, ngược lại RETURNING; COMBO nếu có dòng combo; GENERAL luôn thêm. Chỉ kịch bản đang bật.
// Mock chỉ cần "khách quen" cho vài phiếu để thử: xem RETURNING_NOTE_IDS. Dữ liệu là chữ bịa, không có số điện thoại.
import { mockRequireUser } from "@/features/auth/mock";
import type { MockRequest } from "@/shared/lib/http";
import { PERM } from "@/shared/lib/nav";
import { SCRIPT_MAX, SCRIPT_SITUATIONS } from "./callScripts";
import { hasLongDigitRun } from "./confirmationUi";
import type { CallScript, CallScriptSituation, ConfirmationQueueDetail, QueueScript } from "./types";

type MockMe = ReturnType<typeof mockRequireUser>;

const LABELS = Object.fromEntries(SCRIPT_SITUATIONS.map((s) => [s.value, s.label])) as Record<CallScriptSituation, string>;

/** Phiếu mock coi là khách quen (có đơn khác đã xử lý). */
const RETURNING_NOTE_IDS = new Set([28, 36]);

function seed(): CallScript[] {
  return [
    {
      situation: "FIRST_ORDER",
      situation_label: LABELS.FIRST_ORDER,
      content: "Chào anh/chị, em gọi từ Cá Về. Em xác nhận đơn hàng vừa đặt: đúng mặt hàng, đúng địa chỉ giao. Đây là đơn đầu tiên nên em dặn thêm: hàng giao tươi, anh/chị cất tủ mát ngay khi nhận.",
      is_active: true,
    },
    {
      situation: "COMBO",
      situation_label: LABELS.COMBO,
      content: "Đơn có combo: nhắc khách combo gồm nhiều loại, mỗi loại đóng gói riêng, kiểm tra đủ túi khi nhận.",
      is_active: false,
    },
    {
      situation: "GENERAL",
      situation_label: LABELS.GENERAL,
      content: "Rã đông: chuyển ngăn mát qua đêm, không ngâm nước nóng. Bảo quản: dùng trong 24 giờ sau khi rã đông, không cấp đông lại.",
      is_active: true,
    },
  ];
}

let store: CallScript[] = seed();

/** Đưa kho kịch bản về dữ liệu ban đầu (test). */
export function resetMockCallScripts(): void {
  store = seed();
}

function perms(me: MockMe): Set<string> {
  return new Set(me?.permissions ?? []);
}

const FORBIDDEN = { status: 403, body: { detail: "Bạn không có quyền thực hiện thao tác này.", code: "PERMISSION_DENIED" } };

function invalid(detail: string, code = "INVALID_INPUT") {
  return { status: 400, body: { detail, code } };
}

function bodyOf(req: MockRequest): Record<string, unknown> {
  return req.body && typeof req.body === "object" ? (req.body as Record<string, unknown>) : {};
}

function contentProblem(raw: unknown): string | null {
  if (typeof raw !== "string" || !raw.trim()) return "Nội dung kịch bản không được để trống.";
  if (raw.trim().length > SCRIPT_MAX) return `Nội dung kịch bản tối đa ${SCRIPT_MAX} ký tự.`;
  return null;
}

export function mockListCallScripts(req: MockRequest): { status: number; body: unknown } {
  const p = perms(mockRequireUser(req));
  if (!p.has(PERM.viewCallScript)) return FORBIDDEN;
  const all = p.has(PERM.changeCallScript);
  const order = SCRIPT_SITUATIONS.map((s) => s.value);
  // Bản sao: phản hồi như JSON qua mạng, không chia sẻ tham chiếu với kho mock (sửa kho không làm đổi dữ liệu màn đang giữ).
  const results = store
    .filter((s) => all || s.is_active)
    .map((s) => ({ ...s }))
    .sort((a, b) => order.indexOf(a.situation) - order.indexOf(b.situation));
  return { status: 200, body: { results } };
}

export function mockCreateCallScript(req: MockRequest): { status: number; body: unknown } {
  const p = perms(mockRequireUser(req));
  if (!p.has(PERM.addCallScript)) return FORBIDDEN;
  const body = bodyOf(req);
  const situation = body.situation as CallScriptSituation;
  if (!LABELS[situation]) return invalid("Tình huống không đúng.");
  if (store.some((s) => s.situation === situation)) return invalid("Tình huống này đã có kịch bản. Sửa kịch bản đã có.");
  const problem = contentProblem(body.content);
  if (problem) return invalid(problem);
  if (hasLongDigitRun(String(body.content))) return invalid("Kịch bản không được chứa số điện thoại hay dãy số dài.", "BR-GH-19");
  const row: CallScript = { situation, situation_label: LABELS[situation], content: String(body.content).trim(), is_active: body.is_active !== false };
  store.push(row);
  return { status: 201, body: { ...row } };
}

export function mockUpdateCallScript(req: MockRequest): { status: number; body: unknown } {
  const p = perms(mockRequireUser(req));
  if (!p.has(PERM.changeCallScript)) return FORBIDDEN;
  const situation = /\/scripts\/([A-Z_]+)\/?/.exec(req.path)?.[1];
  const row = store.find((s) => s.situation === situation);
  if (!row) return { status: 404, body: { detail: "Không tìm thấy kịch bản.", code: "NOT_FOUND" } };
  const body = bodyOf(req);
  if ("content" in body) {
    const problem = contentProblem(body.content);
    if (problem) return invalid(problem);
    if (hasLongDigitRun(String(body.content))) return invalid("Kịch bản không được chứa số điện thoại hay dãy số dài.", "BR-GH-19");
    row.content = String(body.content).trim();
  }
  if (typeof body.is_active === "boolean") row.is_active = body.is_active;
  return { status: 200, body: { ...row } };
}

/** Khoá `scripts` của chi tiết hàng chờ gọi (CS-18-AC1/AC2): rỗng khi người xem không có quyền xem kịch bản. */
export function scriptsForQueueItem(item: Pick<ConfirmationQueueDetail, "note_id" | "lines_summary">, me: MockMe): QueueScript[] {
  if (!perms(me).has(PERM.viewCallScript)) return [];
  const wanted: CallScriptSituation[] = [RETURNING_NOTE_IDS.has(item.note_id) ? "RETURNING" : "FIRST_ORDER"];
  if (/combo/i.test(item.lines_summary)) wanted.push("COMBO");
  wanted.push("GENERAL");
  return wanted
    .map((w) => store.find((s) => s.situation === w && s.is_active))
    .filter((s): s is CallScript => Boolean(s))
    .map((s) => ({ situation: s.situation, situation_label: s.situation_label, content: s.content }));
}
