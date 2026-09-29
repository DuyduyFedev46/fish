import { describe, it, expect } from "vitest";
import { mockOrdersApi } from "./mock";
import type { OrderDetail } from "./types";

function tokenFor(username: string): string {
  return `mock-token-${username}-${Date.now() + 1000}`;
}

describe("GL-05: Orders privacy consent tests", () => {
  it("GL-05-AC1: Chu (loc) has sales.view_privacy_consent and sees privacy_consent info for order with consent", () => {
    // Trong mock: order chẵn (id=102) có consent
    const res = mockOrdersApi({
      method: "GET",
      path: "/api/sales/orders/102/",
      token: tokenFor("loc"),
    });
    expect(res.status).toBe(200);
    const body = res.body as OrderDetail;
    expect("privacy_consent" in body).toBe(true);
    expect(body.privacy_consent).not.toBeNull();
    expect(body.privacy_consent?.policy_entry_id).toBe(1);
    expect(body.privacy_consent?.policy_version).toBe(1);
    expect(body.privacy_consent?.policy_version_id).toBe(1);
  });

  it("GL-05-AC1: Quản lý (ql1) has sales.view_privacy_consent and sees privacy_consent info for order with consent", () => {
    const res = mockOrdersApi({
      method: "GET",
      path: "/api/sales/orders/102/",
      token: tokenFor("ql1"),
    });
    expect(res.status).toBe(200);
    const body = res.body as OrderDetail;
    expect("privacy_consent" in body).toBe(true);
    expect(body.privacy_consent).not.toBeNull();
    expect(body.privacy_consent?.policy_entry_id).toBe(1);
  });

  it("GL-05-AC2: Chu sees privacy_consent as null for order without consent (old order)", () => {
    // Trong mock: order lẻ (id=101) không có consent
    const res = mockOrdersApi({
      method: "GET",
      path: "/api/sales/orders/101/",
      token: tokenFor("loc"),
    });
    expect(res.status).toBe(200);
    const body = res.body as OrderDetail;
    expect("privacy_consent" in body).toBe(true);
    expect(body.privacy_consent).toBeNull();
  });

  it("GL-05-AC3: nv_kho (kho1) lacks sales.view_privacy_consent and does not have privacy_consent key", () => {
    const res = mockOrdersApi({
      method: "GET",
      path: "/api/sales/orders/102/",
      token: tokenFor("kho1"),
    });
    expect(res.status).toBe(200);
    const body = res.body as OrderDetail;
    expect("privacy_consent" in body).toBe(false);
  });

  it("GL-05-AC3: nv_giao (giao1) lacks sales.view_privacy_consent and does not have privacy_consent key", () => {
    // Đơn trong scope của giao1 nếu có hoặc ngoài scope 404
    const res = mockOrdersApi({
      method: "GET",
      path: "/api/sales/orders/101/",
      token: tokenFor("giao1"),
    });
    if (res.status === 200) {
      const body = res.body as OrderDetail;
      expect("privacy_consent" in body).toBe(false);
    } else {
      expect(res.status).toBe(404);
    }
  });
});
