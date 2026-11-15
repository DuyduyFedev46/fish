#!/usr/bin/env python3
"""
Kiểm phạm vi sửa của Gemini CLI: chỉ được đụng giao diện Shop web (Duy chốt 2026-11-11, xem GEMINI.md).

    python3 scripts/check_shop_ui_scope.py            # xét commit trên nhánh so với main + file đã stage
    python3 scripts/check_shop_ui_scope.py --base X   # so với nhánh/commit khác thay cho main

Exit 0: mọi file nằm trong vùng được sửa. Exit 1: in từng file ngoài vùng, phải gỡ trước khi commit.
Chỉ dùng thư viện chuẩn Python 3, chạy từ gốc repo.
"""
import argparse
import subprocess
import sys

# Vùng được sửa (tiền tố đường dẫn, tính từ gốc repo).
ALLOWED_PREFIXES = (
    "frontend/app/",
    "frontend/components/",
    "frontend/features/",
    "frontend/lib/",
    "frontend/scripts/test-",
    "frontend/e2e/shop_",
    "doc/features/2026-11-11-shop-ui-gemini/",
)

# Nằm trong vùng trên nhưng vẫn cấm.
BLOCKED_EXACT = {
    "frontend/e2e/shop_e2e_lib.py",  # cổng, mật khẩu QA, đường dẫn dùng chung cho cả bộ e2e
    "frontend/e2e/shop_seed.py",     # dữ liệu seed dùng chung với đội Claude
}


def git_lines(*args):
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_files(base):
    merge_base = git_lines("merge-base", base, "HEAD")[0]
    committed = git_lines("diff", "--name-only", f"{merge_base}..HEAD")
    staged = git_lines("diff", "--name-only", "--cached")
    return sorted(set(committed) | set(staged))


def is_allowed(path):
    if path in BLOCKED_EXACT:
        return False
    if "/.env" in path or path.startswith(".env"):
        return False
    return path.startswith(ALLOWED_PREFIXES)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main")
    args = parser.parse_args()

    files = changed_files(args.base)
    outside = [f for f in files if not is_allowed(f)]
    if outside:
        print("NGOÀI PHẠM VI Shop UI (gỡ khỏi commit hoặc hỏi Duy):")
        for f in outside:
            print(f"  {f}")
        sys.exit(1)
    print(f"OK: {len(files)} file, tất cả nằm trong phạm vi Shop UI.")


if __name__ == "__main__":
    main()
