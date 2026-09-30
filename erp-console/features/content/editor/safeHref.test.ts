import { describe, expect, it } from "vitest";
import { isExternalLink, isSafeHref } from "./safeHref";

// SR-23 F2: cùng bộ 40 payload với Shop (`frontend/scripts/test-safe-href.mjs`): 34 ca isSafeHref + 6 ca isExternalLink.
// Nếu sửa một bên phải sửa bên kia; không import chéo giữa hai app nên luật và test được chép song song.
// Chuỗi tạo bằng escape (\u...) để file không chứa ký tự điều khiển thật.

const LONG_OK = "/bai-viet?slug=" + "a".repeat(1900);
const TOO_LONG = "https://caveve.vn/" + "a".repeat(2000);

const SAFE_HREF_CASES: Array<[string, unknown, boolean]> = [
  // hợp lệ
  ["https", "https://caveve.vn/shop", true],
  ["http", "http://example.com/item", true],
  ["mailto", "mailto:hotro@caveve.vn", true],
  ["tel", "tel:0900000000", true],
  ["đường dẫn nội bộ", "/shop", true],
  ["đường dẫn nội bộ có query", "/bai-viet?slug=ca-thu", true],
  ["neo trong trang", "#muc-2", true],
  ["https viết hoa + khoảng trắng đầu/cuối (được trim)", "  HTTPS://caveve.vn  ", true],
  ["nội bộ dưới 2000 ký tự", LONG_OK, true],
  // nguy hiểm
  ["javascript:", "javascript:alert(1)", false],
  ["JAVASCRIPT: viết hoa", "JAVASCRIPT:alert(1)", false],
  ["JaVaScRiPt: xen kẽ hoa thường", "jAvAsCrIpT:alert(document.cookie)", false],
  ["vbscript: có khoảng trắng đầu", " vbscript:msgbox(1)", false],
  ["data:", "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==", false],
  ["protocol-relative //", "//evil.example/phish", false],
  ["/\\ (gạch chéo rồi gạch ngược)", "/\\evil.example", false],
  ["\\\\ gạch ngược ở đầu", "\\\\evil.example", false],
  ["\\host gạch ngược đơn ở đầu (trình duyệt hiểu là //host)", "\\evil.example", false],
  ["tab xen giữa giao thức", "java\tscript:alert(1)", false],
  ["xuống dòng xen giữa giao thức", "java\nscript:alert(1)", false],
  ["ký tự NUL đầu chuỗi", "\u0000javascript:alert(1)", false],
  ["ký tự điều khiển 0x01 đầu chuỗi", "\u0001javascript:alert(1)", false],
  ["khoảng trắng bên trong URL", "https://caveve.vn/a b", false],
  ["ký tự điều khiển C1 (0x85)", "https://caveve.vn/\u0085x", false],
  ["file:", "file:///etc/passwd", false],
  ["ftp:", "ftp://example.com/a", false],
  ["blob:", "blob:https://caveve.vn/abc", false],
  ["không có giao thức, không có gạch chéo", "abc", false],
  ["quá 2000 ký tự", TOO_LONG, false],
  ["chuỗi rỗng", "", false],
  ["chỉ khoảng trắng", "   ", false],
  ["undefined", undefined, false],
  ["null", null, false],
  ["số (không phải chuỗi)", 123, false],
];

const EXTERNAL_LINK_CASES: Array<[string, unknown, boolean]> = [
  ["https là link ngoài", "https://caveve.vn/x", true],
  ["HTTP viết hoa là link ngoài", "HTTP://caveve.vn/x", true],
  ["đường dẫn nội bộ không phải link ngoài", "/shop", false],
  ["mailto không mở tab mới", "mailto:a@b.vn", false],
  ["tel không mở tab mới", "tel:0900000000", false],
  ["undefined", undefined, false],
];

describe("isSafeHref (SR-23 F2, cùng payload với Shop)", () => {
  it.each(SAFE_HREF_CASES)("%s", (_label, input, expected) => {
    expect(isSafeHref(input as string | undefined)).toBe(expected);
  });
});

describe("isExternalLink (SR-23 F2, cùng payload với Shop)", () => {
  it.each(EXTERNAL_LINK_CASES)("%s", (_label, input, expected) => {
    expect(isExternalLink(input as string | undefined)).toBe(expected);
  });
});
