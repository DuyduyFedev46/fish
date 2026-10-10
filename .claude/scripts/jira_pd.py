#!/usr/bin/env python3
"""Cập nhật idea trên Jira Product Discovery (project FISH) cho điều phối viên.

Thông tin đăng nhập đọc từ ~/.jira-env (JIRA_EMAIL, JIRA_API_TOKEN), nằm ngoài repo.
Chạy:
  python3 -I .claude/scripts/jira_pd.py find <thư mục doc/features hoặc chữ trong tên>
  python3 -I .claude/scripts/jira_pd.py create "[ERP] - Tên ngắn" --folder 2026-10-12-slug \
          [--labels tinh-nang,agent-be] [--roadmap Now] [--status PLAN] [--desc-file mo-ta.txt]
  python3 -I .claude/scripts/jira_pd.py move FISH-21 STAGING "QA lô cuối APPROVED, commit abc123"
  python3 -I .claude/scripts/jira_pd.py comment FISH-21 "Lô 2/5 APPROVED, commit abc123"
  python3 -I .claude/scripts/jira_pd.py desc FISH-21 mo-ta.txt
  python3 -I .claude/scripts/jira_pd.py template            # in khung 6 phần để điền
"""
import argparse
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = "https://dtduy46work.atlassian.net"
PROJECT = "FISH"
REPO_DOCS = "https://github.com/DuyduyFedev46/fish/tree/main/doc/features/"
STATUSES = ["PLAN", "DISCOVERY", "SHAPE", "REVIEW SHAPE", "BUILD", "STAGING", "DONE", "PARKED", "CANCELLED"]
TEMPLATE = [
    ("1. RÕ BÀI TOÁN LỚN", [("1", "Mô tả thực trạng hoặc nhu cầu mới trong vận hành, kinh doanh"),
                             ("2", "Vấn đề đang cản trở, khó khăn. Số liệu lượng hoá"),
                             ("3", "Mô tả cụ thể tính năng yêu cầu là gì"),
                             ("4", "Mục đích, hiệu quả kỳ vọng khi giải quyết vấn đề"),
                             ("5", "Cam kết chỉ số đánh giá")]),
    ("2. RÕ MỤC TIÊU", [("6", "Phương án đề xuất (Proposed)"), ("7", "Chia nhỏ mục tiêu theo giai đoạn"),
                         ("8", "Lý do cần thực hiện (WHY)"), ("9", "Triển khai trên hệ thống nào? (WHERE)"),
                         ("10", "Ai sử dụng? (WHO)")]),
    ("3. RÕ THỜI HẠN", [("11", "Tính năng này được thực hiện khi nào?"),
                         ("12", "Thời gian mong muốn golive + lý do"), ("13", "Lộ trình Pilot/All")]),
    ("4. RÕ KẾT QUẢ ĐẦU RA", [("14", "Các bước nghiệp vụ mong muốn"), ("15", "Kết quả cụ thể mong đợi")]),
    ("5. RÕ NGƯỜI PHỤ TRÁCH", [("18", "Phòng ban / vai liên quan"), ("19", "Người quyết định cuối cùng"),
                                ("20", "Người đại diện hệ thống")]),
    ("6. RÕ NGÂN SÁCH", [("21", "Nguồn ngân sách"), ("22", "Loại ngân sách")]),
]


def _auth():
    path = os.path.expanduser("~/.jira-env")
    if not os.path.exists(path):
        sys.exit("Thiếu ~/.jira-env (JIRA_EMAIL, JIRA_API_TOKEN). Nhờ Duy tạo lại token.")
    env = dict(line.strip().split("=", 1) for line in open(path) if "=" in line)
    return base64.b64encode(f"{env['JIRA_EMAIL']}:{env['JIRA_API_TOKEN']}".encode()).decode()


def _context():
    for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


AUTH = None
CTX = _context()


def call(method, path, body=None):
    global AUTH
    AUTH = AUTH or _auth()
    req = urllib.request.Request(SITE + path, method=method)
    req.add_header("Authorization", "Basic " + AUTH)
    req.add_header("Accept", "application/json")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req, data, context=CTX) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode()


def fields():
    _, meta = call("GET", f"/rest/api/3/issue/createmeta/{PROJECT}/issuetypes")
    type_id = meta["issueTypes"][0]["id"]
    _, meta = call("GET", f"/rest/api/3/issue/createmeta/{PROJECT}/issuetypes/{type_id}?maxResults=200")
    return type_id, {f["name"]: f for f in meta["fields"]}


def move(key, status, comment=None):
    if status not in STATUSES:
        sys.exit(f"Trạng thái không hợp lệ: {status}. Chọn một trong {STATUSES}")
    st, issue = call("GET", f"/rest/api/3/issue/{key}?fields=status")
    if st != 200:
        sys.exit(f"Không đọc được {key}: {st} {issue}")
    if issue["fields"]["status"]["name"] != status:
        _, tr = call("GET", f"/rest/api/3/issue/{key}/transitions")
        match = [t for t in tr["transitions"] if t["to"]["name"] == status]
        if not match:
            sys.exit(f"{key}: không có đường chuyển sang {status}")
        st, res = call("POST", f"/rest/api/3/issue/{key}/transitions", {"transition": {"id": match[0]["id"]}})
        if st != 204:
            sys.exit(f"{key}: chuyển trạng thái lỗi {st} {res}")
    if comment:
        add_comment(key, comment)
    print(f"{key} → {status}")


def add_comment(key, text):
    st, res = call("POST", f"/rest/api/2/issue/{key}/comment", {"body": text})
    if st != 201:
        sys.exit(f"{key}: comment lỗi {st} {res}")


def find(text):
    jql = f'project = {PROJECT} AND (summary ~ "{text}" OR text ~ "{text}") ORDER BY key'
    _, res = call("GET", "/rest/api/3/search/jql?" + urllib.parse.urlencode(
        {"jql": jql, "fields": "summary,status", "maxResults": 20}))
    for issue in res.get("issues", []):
        print(f"{issue['key']}\t{issue['fields']['status']['name']}\t{issue['fields']['summary']}")


def template():
    for title, rows in TEMPLATE:
        print(f"h3. {title}")
        print("||STT||Nội dung câu hỏi||Câu trả lời và phân tích||")
        for num, question in rows:
            print(f"|{num}|{question}| |")


def create(args):
    type_id, f = fields()
    payload = {"project": {"key": PROJECT}, "issuetype": {"id": type_id}, "summary": args.summary,
               "labels": [l for l in (args.labels or "").split(",") if l]}
    if args.desc_file:
        payload["description"] = open(args.desc_file).read()
    if args.folder:
        payload[f["Documents"]["fieldId"]] = REPO_DOCS + args.folder
    if args.roadmap:
        options = {a["value"]: a["id"] for a in f["Roadmap"]["allowedValues"]}
        payload[f["Roadmap"]["fieldId"]] = {"id": options[args.roadmap]}
    st, res = call("POST", "/rest/api/2/issue", {"fields": payload})
    if st != 201:
        sys.exit(f"Tạo idea lỗi {st} {res}")
    print(res["key"])
    if args.status and args.status != "PLAN":
        move(res["key"], args.status)


def main():
    parser = argparse.ArgumentParser(description="Cập nhật Jira Product Discovery FISH")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find"); p.add_argument("text")
    p = sub.add_parser("move"); p.add_argument("key"); p.add_argument("status"); p.add_argument("comment", nargs="?")
    p = sub.add_parser("comment"); p.add_argument("key"); p.add_argument("text")
    p = sub.add_parser("desc"); p.add_argument("key"); p.add_argument("file")
    sub.add_parser("template")
    p = sub.add_parser("create")
    p.add_argument("summary"); p.add_argument("--folder"); p.add_argument("--labels")
    p.add_argument("--roadmap", choices=["Now", "Next", "Later", "Won't do"])
    p.add_argument("--status", choices=STATUSES, default="PLAN"); p.add_argument("--desc-file")
    args = parser.parse_args()
    if args.cmd == "find":
        find(args.text)
    elif args.cmd == "move":
        move(args.key, args.status, args.comment)
    elif args.cmd == "comment":
        add_comment(args.key, args.text); print(f"{args.key}: đã comment")
    elif args.cmd == "desc":
        st, res = call("PUT", f"/rest/api/2/issue/{args.key}", {"fields": {"description": open(args.file).read()}})
        print(f"{args.key}: {'đã cập nhật mô tả' if st == 204 else f'lỗi {st} {res}'}")
    elif args.cmd == "template":
        template()
    elif args.cmd == "create":
        create(args)


if __name__ == "__main__":
    main()
