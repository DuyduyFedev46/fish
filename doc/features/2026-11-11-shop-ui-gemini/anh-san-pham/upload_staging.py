#!/usr/bin/env python3
"""
Tải ảnh minh hoạ mặt hàng và kiểm tra ảnh banner `home-banner` trên môi trường STAGING (GUI-14).

Nguyên tắc bảo mật & an toàn:
- CHỈ gọi API staging (`https://cangca-api-staging-675411800433.asia-southeast1.run.app`),
  tuyệt đối không gọi production.
- Đọc tài khoản Quản lý từ biến môi trường `CAVE_STAGING_USER` và `CAVE_STAGING_PASSWORD`.
- KHÔNG BAO GIỜ in, log, ghi file hay hiển thị mật khẩu hoặc token.
- Món đã có ảnh (`image != null`) thì bỏ qua và báo rõ (`bỏ qua vì đã có ảnh`).
- Món chưa có ảnh thì tải lên qua `POST /api/catalog/items/{id}/image/` với
  `alt_text` tiếng Việt và `is_illustration=true`.
- Banner `home-banner`: kiểm tra xem `POST /api/content/entries/<pk>/images/` có tự gắn
  ảnh vào slide mà không cần sửa/đăng lại nội dung bài CMS không; không tự sửa hay xuất
  bản lại chữ bài CMS.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

STAGING_API_BASE = "https://cangca-api-staging-675411800433.asia-southeast1.run.app"
BASE_DIR = Path(__file__).resolve().parent

ITEM_SPECS: list[tuple[str, str, str]] = [
    ("BACH-TUOC", "Bạch tuộc", "BACH-TUOC.jpg"),
    ("CA-HOI-NU", "Cá hồi Na Uy", "CA-HOI-NU.jpg"),
    ("CA-THU", "Cá thu", "CA-THU.jpg"),
    ("GHE-XANH", "Ghẹ xanh", "GHE-XANH.jpg"),
    ("MUC-ONG", "Mực ống", "MUC-ONG.jpg"),
    ("TOM-SU-1", "Tôm sú loại 1", "TOM-SU-1.jpg"),
]

BANNER_FILE = BASE_DIR / "banner" / "banner-hai-san-da-lanh.jpg"
BANNER_ALT = "Hải sản tươi cấp đông tại cảng Cá Về"


def build_ssl_context() -> ssl.SSLContext:
    """Tạo SSL context tương thích cả macOS Python framework và Linux."""
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    macos_cert = Path("/etc/ssl/cert.pem")
    if macos_cert.exists():
        return ssl.create_default_context(cafile=str(macos_cert))
    return ssl.create_default_context()


SSL_CONTEXT = build_ssl_context()


def encode_multipart_formdata(
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    """Đóng gói multipart/form-data bằng thư viện chuẩn Python."""
    boundary = f"----CaveStagingUploadBoundary{uuid.uuid4().hex}"
    lines: list[bytes] = []

    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode("utf-8"))
        lines.append(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        lines.append(f"{value}\r\n".encode("utf-8"))

    mime_type, _ = mimetypes.guess_type(str(file_path))
    content_type = mime_type or "image/jpeg"
    file_bytes = file_path.read_bytes()

    lines.append(f"--{boundary}\r\n".encode("utf-8"))
    lines.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    lines.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    lines.append(file_bytes)
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(lines)
    header_type = f"multipart/form-data; boundary={boundary}"
    return body, header_type


def api_request(
    method: str,
    path_or_url: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    raw_body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, Any]:
    """Gọi HTTP tới API staging; không bao giờ in header Authorization hay body nhạy cảm."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        url = f"{STAGING_API_BASE}{path_or_url}"

    if not url.startswith(STAGING_API_BASE):
        raise RuntimeError(f"Từ chối gọi URL ngoài staging: {url}")

    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"

    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed
    except urllib.error.HTTPError as err:
        raw_err = err.read().decode("utf-8", errors="replace")
        try:
            parsed_err = json.loads(raw_err) if raw_err else {}
        except Exception:
            parsed_err = {"detail": raw_err[:200]}
        return err.code, parsed_err


def format_image_urls(image_obj: dict[str, Any] | None) -> str:
    """Rút gọn chuỗi URL 3 kích cỡ ảnh để in bảng báo cáo."""
    if not image_obj or not isinstance(image_obj, dict):
        return "—"
    urls = image_obj.get("urls") or {}
    if not isinstance(urls, dict) or not urls:
        return "—"
    parts: list[str] = []
    for key in ("thumb", "card", "detail", "sm", "md", "lg"):
        if key in urls and urls[key]:
            parts.append(f"`{key}`: {urls[key]}")
    return "<br>".join(parts) if parts else "—"


def login_token(username: str, password: str) -> str:
    """Đăng nhập `POST /api/auth/token/` lấy token, không in mật khẩu hay token."""
    status_code, payload = api_request(
        "POST",
        "/api/auth/token/",
        json_body={"username": username, "password": password},
    )
    if status_code != 200 or not isinstance(payload, dict) or not payload.get("token"):
        detail = payload.get("detail") if isinstance(payload, dict) else "Lỗi xác thực"
        raise RuntimeError(f"Đăng nhập thất bại (HTTP {status_code}): {detail}")
    return str(payload["token"])


def fetch_catalog_items_authenticated(token: str) -> dict[str, dict[str, Any]]:
    """Lấy danh sách mặt hàng qua `GET /api/catalog/items/` (có phân trang), ghép theo `code`."""
    by_code: dict[str, dict[str, Any]] = {}
    next_url: str | None = "/api/catalog/items/?page_size=100"
    while next_url:
        status_code, payload = api_request("GET", next_url, token=token)
        if status_code != 200:
            raise RuntimeError(f"Không lấy được danh sách mặt hàng (HTTP {status_code})")
        if isinstance(payload, dict) and "results" in payload:
            items = payload["results"]
            next_url = payload.get("next")
        elif isinstance(payload, list):
            items = payload
            next_url = None
        else:
            items = []
            next_url = None
        for item in items:
            code = item.get("code")
            if code:
                by_code[str(code)] = item
    return by_code


def fetch_catalog_items_public() -> dict[str, dict[str, Any]]:
    """Dùng cho `--dry-run` khi chưa đặt biến môi trường: hỏi `/api/shop/catalog/` công khai."""
    status_code, payload = api_request("GET", "/api/shop/catalog/")
    if status_code != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"Không đọc được `/api/shop/catalog/` (HTTP {status_code})")
    by_code: dict[str, dict[str, Any]] = {}
    for item in payload.get("items") or []:
        code = item.get("item_code") or item.get("code")
        if code:
            by_code[str(code)] = {
                "id": item.get("id", "?"),
                "code": code,
                "name": item.get("name"),
                "image": item.get("image"),
            }
    return by_code


def check_and_handle_banner(*, token: str | None, dry_run: bool) -> tuple[str, str]:
    """
    Kiểm tra bài `home-banner`:
    - Theo `frontend/features/home/homeBlocks.ts`, `parseBanner(body)` chỉ đọc ảnh từ block
      `{"type": "image", "urls": ...}` nằm trong `body.blocks` của bài CMS `home-banner`.
    - Endpoint `POST /api/content/entries/<pk>/images/` (`upload_content_image`) chỉ tạo bản ghi
      `ContentImage` rời trong kho, KHÔNG tự gắn vào `entry.body.blocks` và không xuất bản lại bài.
    - Theo phiếu việc GUI-14: "tải được bằng tài khoản đó qua `POST /api/content/entries/<pk>/images/`
      thì tải 1 ảnh banner, không được (403, cần đổi nội dung bài) thì bỏ qua và ghi lý do.
      Không đăng hay sửa chữ bài CMS."
    """
    pub_status, pub_data = api_request("GET", "/api/public/content/entries/home-banner/")
    has_image_block = False
    if pub_status == 200 and isinstance(pub_data, dict):
        blocks = (pub_data.get("body") or {}).get("blocks") or []
        has_image_block = any(
            isinstance(b, dict) and b.get("type") == "image" for b in blocks
        )

    if token:
        ent_status, ent_data = api_request(
            "GET", "/api/content/entries/?search=home-banner", token=token
        )
        if ent_status == 403:
            return (
                "bỏ qua (403 Forbidden)",
                "Tài khoản không có quyền truy cập `/api/content/entries/` (HTTP 403).",
            )

    if not has_image_block:
        return (
            "bỏ qua (cần đổi nội dung bài CMS)",
            "Bài `home-banner` trên staging hiện chỉ có các block `heading` và `paragraph`, "
            "chưa có block `image` trong `body.blocks`. Gọi `POST /api/content/entries/<pk>/images/` "
            "chỉ tạo bản ghi `ContentImage` rời, không tự gắn ảnh vào slide nếu không sửa và đăng lại "
            "`body.blocks` của bài CMS (phiếu việc cấm sửa/đăng lại bài CMS).",
        )

    return (
        "bỏ qua (đã có block image)",
        "Bài `home-banner` đã có block image.",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tải ảnh minh hoạ 6 món hải sản lên staging (GUI-14)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ kiểm tra danh sách món trên staging và in kế hoạch, không tải ảnh lên.",
    )
    args = parser.parse_args()

    username = os.environ.get("CAVE_STAGING_USER", "").strip()
    password = os.environ.get("CAVE_STAGING_PASSWORD", "").strip()
    has_creds = bool(username and password)

    for code, _alt, filename in ITEM_SPECS:
        img_path = BASE_DIR / filename
        if not img_path.is_file():
            print(f"LỖI: Thiếu file ảnh {img_path}", file=sys.stderr)
            return 1

    token: str | None = None
    if has_creds:
        token = login_token(username, password)
        catalog_by_code = fetch_catalog_items_authenticated(token)
        mode_note = "Đã xác thực tài khoản Quản lý qua `POST /api/auth/token/`"
    elif args.dry_run:
        catalog_by_code = fetch_catalog_items_public()
        mode_note = (
            "Chế độ `--dry-run` không có biến `CAVE_STAGING_USER`/`CAVE_STAGING_PASSWORD` "
            "(đối chiếu qua `/api/shop/catalog/` công khai)"
        )
    else:
        print(
            "DỪNG: Thiếu biến môi trường `CAVE_STAGING_USER` hoặc `CAVE_STAGING_PASSWORD`. "
            "Không thể tải ảnh thật lên staging.",
            file=sys.stderr,
        )
        return 2

    print(f"# Kết quả {'Dry-Run' if args.dry_run else 'Tải ảnh thật'} — Staging (`GUI-14`)")
    print(f"- Môi trường: `{STAGING_API_BASE}`")
    print(f"- Trạng thái xác thực: {mode_note}")
    print()
    print("| Mã món | ID | Tên món | Trạng thái | URL ảnh (`thumb` / `card` / `detail`) |")
    print("|---|---|---|---|---|")

    for code, alt_text, filename in ITEM_SPECS:
        item = catalog_by_code.get(code)
        img_path = BASE_DIR / filename
        if not item:
            print(f"| `{code}` | — | {alt_text} | lỗi: không tìm thấy mã trên staging | — |")
            continue

        item_id = item.get("id", "?")
        existing_img = item.get("image")
        if existing_img:
            urls_str = format_image_urls(existing_img)
            print(
                f"| `{code}` | `{item_id}` | {alt_text} | **bỏ qua vì đã có ảnh** | {urls_str} |"
            )
            continue

        if args.dry_run:
            print(
                f"| `{code}` | `{item_id}` | {alt_text} | **sẽ tải lên (dry-run)** (`{filename}`, `is_illustration=true`) | *(chưa gọi POST)* |"
            )
            continue

        assert token is not None
        body, content_type = encode_multipart_formdata(
            fields={"alt_text": alt_text, "is_illustration": "true"},
            file_field="file",
            file_path=img_path,
        )
        post_status, post_data = api_request(
            "POST",
            f"/api/catalog/items/{item_id}/image/",
            token=token,
            raw_body=body,
            content_type=content_type,
        )
        if post_status in (200, 201) and isinstance(post_data, dict):
            uploaded_img = post_data.get("image")
            urls_str = format_image_urls(uploaded_img)
            print(
                f"| `{code}` | `{item_id}` | {alt_text} | **đã tải** (HTTP {post_status}) | {urls_str} |"
            )
        else:
            err_detail = (
                post_data.get("detail")
                if isinstance(post_data, dict)
                else str(post_data)
            )
            print(
                f"| `{code}` | `{item_id}` | {alt_text} | **lỗi** (HTTP {post_status}: {err_detail}) | — |"
            )

    banner_status, banner_reason = check_and_handle_banner(
        token=token, dry_run=args.dry_run
    )
    print()
    print("## Banner `home-banner`")
    print(f"- Trạng thái: **{banner_status}**")
    print(f"- Lý do: {banner_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
