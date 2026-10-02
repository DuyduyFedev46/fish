// Mock data cho Tiếp theo · Đã làm (DW-03, DW-04, DW-05).
// Phục vụ test mock mode và E2E không phụ thuộc backend.

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { mockExpiredBatchGuidance } from "@/features/inventory/mock";
import { aiEnabled as mockAiEnabled } from "@/features/ai/mock";
import type { GuidanceData } from "./types";

// F6-1: bước người dùng chưa được phép (viewer thiếu quyền) để màn hiện nút "Nhờ" (DW-23). Chỉ dùng cho mock/e2e.
function ownerOnlyStep(key: string, label: string, br: string, text: string) {
  return {
    key,
    label,
    actor: "user" as const,
    allowed: false,
    who: ["Chủ"],
    missing: [{ code: br, text }],
    deadline: null,
    why: { br, text },
    command: null,
    ai: null,
  };
}

export function mockGuidanceApi(req: MockRequest): MockResponse {
  const match = req.path.match(/^\/api\/guidance\/([a-z_]+)\/([^/]+)\/$/);
  if (!match) {
    return { status: 404, body: { detail: "Không tìm thấy endpoint.", code: "NOT_FOUND" } };
  }

  const [, docType, docId] = match;

  if (docType === "order") {
    const isBooked = docId === "1" || docId.toString().includes("BOOKED");
    const data: GuidanceData = {
      doc: {
        type: "order",
        id: docId,
        code: `SO-DEMO-${docId}`,
        status: isBooked ? "BOOKED" : "PAID",
        status_label: isBooked ? "Giữ chỗ" : "Đã thanh toán",
      },
      next_steps: isBooked
        ? [
            {
              key: "auto_cancel",
              label: "Hệ thống sẽ tự huỷ",
              actor: "system",
              allowed: false,
              who: ["Hệ thống"],
              missing: [],
              deadline: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
              why: {
                br: "BR-BH-04",
                text: "Hệ thống tự động huỷ đơn quá hạn giữ chỗ để nhả hàng cho khách khác",
              },
              command: null,
              ai: null,
            },
            {
              key: "confirm_payment",
              label: "Xác nhận thanh toán tay",
              actor: "user",
              allowed: true,
              who: ["Chủ"],
              missing: [],
              deadline: null,
              why: {
                br: "BR-TT-07",
                text: "Thanh toán tay cần Chủ xác nhận để đảm bảo đối soát ngân hàng",
              },
              command: "sales.salesorder.confirm_payment",
              ai: null,
            },
          ]
        : [
            {
              key: "cancel",
              label: "Huỷ đơn",
              actor: "user",
              allowed: true,
              who: ["Quản lý", "Chủ"],
              missing: [],
              deadline: null,
              why: {
                br: "BR-GH-07",
                text: "Chỉ có thể huỷ đơn khi hàng chưa giao cho khách",
              },
              command: "sales.salesorder.cancel_order",
              ai: null,
            },
            {
              key: "create_refund",
              label: "Tạo phiếu hoàn",
              actor: "user",
              allowed: true,
              who: ["Quản lý", "Chủ"],
              missing: [],
              deadline: null,
              why: {
                br: "BR-HT-04",
                text: "Chỉ tạo phiếu hoàn khi hoá đơn còn khoản có thể hoàn",
              },
              command: "sales.refund.create",
              // F6-2: giống server (resolve_step_ai) — cờ AI toàn cục tắt thì `ai: null`; bật thì mức C, KHÔNG xét đồng ý model.
              ai: mockAiEnabled() ? { level: "C", label: "Để AI làm" } : null,
            },
            ownerOnlyStep("cancel_paid", "Huỷ đơn đã thanh toán", "BR-PQ-03", "Huỷ đơn đã thanh toán chỉ Chủ được làm."),
          ],
      warnings: [],
      timeline: [
        {
          at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          kind: "order_placed",
          label: `Khách đặt đơn SO-DEMO-${docId} (540.000 ₫)`,
          doc: "order",
          actor: { kind: "system" as const, display: "Hệ thống" },
        },
        ...(isBooked
          ? []
          : [
              {
                at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
                kind: "payment_received",
                label: "Nhận 540.000 ₫ · Cổng SePay · Khớp (mã GD SP-123456)",
                doc: "order",
                actor: { kind: "system" as const, display: "Hệ thống" },
              },
              {
                at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
                kind: "invoice_issued",
                label: `Xuất hoá đơn INV-${docId}`,
                doc: "invoice",
                actor: { kind: "system" as const, display: "Hệ thống" },
              },
              {
                at: new Date(Date.now() - 19 * 60 * 1000).toISOString(),
                kind: "delivery_created",
                label: `Tạo phiếu giao DN-${docId} (Soạn hàng)`,
                doc: "delivery",
                actor: { kind: "system" as const, display: "Hệ thống" },
              },
            ]),
      ],
      related: isBooked
        ? []
        : [
            { type: "invoice", code: `INV-${docId}` },
            { type: "delivery", code: `DN-${docId}` },
          ],
    };
    return { status: 200, body: data };
  }

  if (docType === "refund") {
    const data: GuidanceData = {
      doc: {
        type: "refund",
        id: docId,
        code: `REF-${docId}`,
        status: "PENDING",
        status_label: "Chờ hoàn",
      },
      next_steps: [
        {
          key: "confirm",
          label: "Xác nhận đã hoàn",
          actor: "user",
          allowed: true,
          who: ["Chủ"],
          missing: [],
          deadline: null,
          why: {
            br: "BR-HT-03",
            text: "Cần mã giao dịch chuyển khoản trước khi xác nhận hoàn tiền",
          },
          command: "sales.refund.confirm",
          ai: null,
        },
        {
          key: "mark_failed",
          label: "Báo thất bại",
          actor: "user",
          allowed: true,
          who: ["Chủ"],
          missing: [],
          deadline: null,
          why: {
            br: "BR-HT-08",
            text: "Phiếu hoàn đã được xử lý hoặc không còn ở trạng thái chờ",
          },
          command: "sales.refund.mark_failed",
          ai: null,
        },
        ownerOnlyStep("cancel_refund", "Huỷ phiếu hoàn", "BR-HT-05", "Phiếu hoàn đã có yêu cầu chuyển tiền, chỉ Chủ được huỷ."),
      ],
      warnings: [
        {
          code: "GW-02",
          text: "Phiếu hoàn gần hạn 30 ngày (BR-AI-33)",
        },
      ],
      timeline: [
        {
          at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          kind: "refund_created",
          label: "Tạo phiếu hoàn 50.000 ₫",
          doc: "refund",
          actor: { kind: "user" as const, display: "Quản lý A" },
        },
      ],
      related: [
        { type: "invoice", code: `INV-${docId}` },
        { type: "order", code: `SO-${docId}` },
      ],
    };
    return { status: 200, body: data };
  }

  if (docType === "payment") {
    const data: GuidanceData = {
      doc: {
        type: "payment",
        id: docId,
        code: `TXN-DEMO-${docId}`,
        status: "OPEN",
        status_label: "Chờ xử lý",
      },
      next_steps: [
        {
          key: "attach_to_order",
          label: "Gắn vào đơn hàng",
          actor: "user",
          allowed: true,
          who: ["Chủ"],
          missing: [],
          deadline: null,
          why: {
            br: "BR-TT-09",
            text: "Giao dịch thanh toán cần được xử lý theo hàng chờ lệch",
          },
          command: "sales.paymenttransaction.resolve",
          ai: null,
        },
        {
          key: "refund",
          label: "Tạo phiếu hoàn",
          actor: "user",
          allowed: true,
          who: ["Chủ"],
          missing: [],
          deadline: null,
          why: {
            br: "BR-TT-10",
            text: "Tiền về cho đơn đã thanh toán cần được hoàn lại",
          },
          command: "sales.refund.create",
          ai: null,
        },
        ownerOnlyStep("confirm_manual", "Xác nhận thủ công đã nhận tiền", "BR-TT-07", "Xác nhận thanh toán tay cần Chủ."),
      ],
      warnings: [],
      timeline: [
        {
          at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
          kind: "payment_received",
          label: "Nhận giao dịch thanh toán 200.000 ₫ (mã GD SP-987654)",
          doc: "payment",
          actor: { kind: "system" as const, display: "Hệ thống" },
        },
      ],
      related: [],
    };
    return { status: 200, body: data };
  }

  if (docType === "batch") {
    // P8 Lô 5: lô Quá hạn còn tồn do mock của inventory quản (tồn đổi theo thao tác Đã huỷ / Đã trả NCC).
    const expired = mockExpiredBatchGuidance(docId, req);
    if (expired) return expired;
    const data: GuidanceData = {
      doc: {
        type: "batch",
        id: docId,
        code: `CA-DEMO-B${docId}`,
        status: "SELLING",
        status_label: "Đang bán",
      },
      next_steps: [
        {
          key: "auto_near_expiry",
          label: "Hệ thống sẽ chuyển Cận hạn",
          actor: "system",
          allowed: false,
          who: ["Hệ thống"],
          missing: [],
          deadline: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString(),
          why: {
            br: "BR-LO-06",
            text: "Lô gần hết hạn sẽ tự động chuyển trạng thái Cận hạn",
          },
          command: null,
          ai: null,
        },
        {
          key: "close",
          label: "Chốt lô",
          actor: "user",
          allowed: false,
          who: ["Chủ"],
          missing: [
            {
              code: "BR-LO-04",
              text: "Chốt lô yêu cầu tồn = 0 hoặc đã huỷ phần còn lại (BR-LO-04).",
            },
          ],
          deadline: null,
          why: {
            br: "BR-LO-04",
            text: "Lô chỉ chốt khi không còn đơn mở và phiếu chờ xử lý",
          },
          command: "inventory.batch.close",
          ai: null,
        },
      ],
      warnings: [
        {
          code: "GW-01",
          text: "Lô chưa có chi phí mua nào (có thể thiếu đá, xe)",
        },
      ],
      timeline: [
        {
          at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
          kind: "batch_created",
          label: "Nhập lô 100.000 kg",
          doc: "batch",
          actor: { kind: "system" as const, display: "Hệ thống" },
        },
        {
          at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
          kind: "batch_published",
          label: "Mở bán lô",
          doc: "batch",
          actor: { kind: "user" as const, display: "Quản lý A" },
        },
      ],
      related: [],
    };
    return { status: 200, body: data };
  }

  if (docType === "delivery") {
    // R2 `delivery`: chỉ dòng thời gian (không bước tiếp theo). Nhãn không có tên, SĐT, địa chỉ hay ghi chú (bất biến 9).
    const data: GuidanceData = {
      doc: { type: "delivery", id: docId, code: `GH-${docId}`, status: null, status_label: null },
      next_steps: [],
      warnings: [],
      timeline: [
        { at: "2026-09-28T01:05:00Z", kind: "create", label: "Hệ thống tạo phiếu giao", doc: "", actor: { kind: "system", display: "Hệ thống" } },
        { at: "2026-09-28T01:40:00Z", kind: "confirm", label: "Xác nhận đơn với khách", doc: "", actor: { kind: "user", display: "Chị Hạnh" } },
        { at: "2026-09-28T02:10:00Z", kind: "label", label: "In tem giao", doc: "", actor: { kind: "user", display: "Anh Tín" } },
      ],
      related: [],
    };
    return { status: 200, body: data };
  }

  return {
    status: 404,
    body: { detail: `Chưa hỗ trợ mock loại chứng từ: ${docType}`, code: "NOT_FOUND" },
  };
}
