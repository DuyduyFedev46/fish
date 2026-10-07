"""Hàm dùng chung cho kịch bản e2e ERP.

1) finish(results): in tổng kết, thoát khác 0 khi còn ca FAIL (hoặc không có ca nào).
    from e2e_support import finish
    finish(results)     # results: danh sách (tên, đạt[, ghi chú]) hoặc danh sách bool
2) page_404_body(base): lấy trang 404 TỪ CHÍNH máy chủ đang chạy (base/404.html) để giả lập 404 ở trình duyệt.
   Không đọc `out/404.html` trên đĩa: nếu build ở đĩa khác bản đang phục vụ thì mã băm các tệp JS lệch và trang trắng.

Lý do có tệp này: nhiều kịch bản cũ in FAIL mà vẫn thoát 0 (hồi quy 08/10), nên chạy trong CI hay shell không biết đỏ.
Kịch bản chạy bằng `python3 e2e/<tên>.py` nên `from e2e_support import finish` tìm thấy tệp này cùng thư mục.
"""

import sys
import urllib.request


def _passed(entry):
    if isinstance(entry, (tuple, list)):
        return bool(entry[1])
    return bool(entry)


def finish(results):
    total = len(results)
    failed = [r for r in results if not _passed(r)]
    print(f"{total - len(failed)}/{total} PASS", flush=True)
    for r in failed:
        name = r[0] if isinstance(r, (tuple, list)) else str(r)
        print(f"FAIL (tổng kết) {name}", flush=True)
    sys.exit(1 if failed or total == 0 else 0)


def page_404_body(base):
    with urllib.request.urlopen(base.rstrip("/") + "/404.html", timeout=15) as r:
        return r.read().decode("utf-8")
