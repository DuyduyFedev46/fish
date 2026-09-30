import { describe, expect, it } from "vitest";
import { safeNext } from "./nav";

// L7-1: `next` sau đăng nhập chỉ nhận đường dẫn nội bộ. Giá trị vào là chuỗi ĐÃ giải mã (URLSearchParams.get),
// nên `/%5Cevil.example` trong URL tới đây là `/\evil.example`.
describe("safeNext (chống open redirect sau đăng nhập)", () => {
  it.each<[string, string | null]>([
    ["protocol-relative //", "//evil.example"],
    ["gạch chéo rồi gạch ngược", "/\\evil.example"],
    ["/%5Cevil.example sau khi giải mã", decodeURIComponent("/%5Cevil.example")],
    ["tab giữa hai gạch chéo", "/\t/evil.example"],
    ["%09 sau khi giải mã", decodeURIComponent("/%09/evil.example")],
    ["xuống dòng", "/\n/evil.example"],
    ["ký tự điều khiển C1", "/\u0085/evil.example"],
    ["tab ở đầu chuỗi", "\t//evil.example"],
    ["https tuyệt đối", "https://evil.example"],
    ["javascript:", "javascript:alert(1)"],
    ["chỉ gạch ngược", "\\evil.example"],
    ["quá 2000 ký tự", "/" + "a".repeat(2000)],
    ["chuỗi rỗng", ""],
    ["null", null],
  ])("từ chối: %s", (_label, input) => {
    expect(safeNext(input)).toBeNull();
  });

  it.each(["/orders/?id=1", "/print/label/?note=1&print_no=1", "/", "/inventory/?status=EXPIRED"])(
    "giữ nguyên: %s",
    (input) => {
      expect(safeNext(input)).toBe(input);
    },
  );
});
