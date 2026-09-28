// Mock data cho Tiếp theo · Đã làm (DW-03, DW-04, DW-05).
// Phục vụ test mock mode và E2E không phụ thuộc backend.

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import type { GuidanceData } from "./types";

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
              ai: null,
            },
          ],
      warnings: [],
      timeline: [
        {
          at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          kind: "order_placed",
          label: `Khách đặt đơn SO-DEMO-${docId} (540.000 đ)`,
          doc: "order",
          actor: { kind: "system" as const, display: "Hệ thống" },
        },
        ...(isBooked
          ? []
          : [
              {
                at: new Date(Date.now() - 20 * 60 * 1000).toISOString(),
                kind: "payment_received",
                label: "Nhận 540.000 đ · Cổng SePay · Khớp (mã GD SP-123456)",
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

  return {
    status: 404,
    body: { detail: `Chưa hỗ trợ mock loại chứng từ: ${docType}`, code: "NOT_FOUND" },
  };
}
