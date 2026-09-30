# Cá Về — hướng dẫn cho agent lập trình (Gemini CLI, Antigravity và các agent khác)

Vựa cá B2C: mua lô tại cảng → bán online → quản lý kho và giá vốn theo lô. Chủ dự án là **Duy** (PO),
trao đổi bằng tiếng Việt. Nghiệp vụ và bất biến nằm ở skill `caveve-domain`: **đọc skill này trước khi
đụng vào bất kỳ code nào.**

> **TẠM DỪNG (Duy chốt 2026-09-30):** từ P8, đội Claude Code tự hiện thực, QA và commit. Gemini CLI /
> Antigravity **không** chạy `/lam-tiep` hay `/lam-tinh-nang`. Nếu được gọi, báo Duy một dòng "AGY đang tạm
> dừng theo AGENTS.md" rồi dừng, trừ khi Duy nói rõ trong lượt đó rằng bật lại AGY.

## Chia việc (Duy chốt 2026-09-28, tạm dừng từ 30/09)

| Ai | Làm gì | Đầu ra |
|---|---|---|
| **Claude Code** (phân tích cùng Duy) | BA → PO → Tech Lead (+ pháp lý) | `01-analysis.md`, `02-stories.md`, `02b-tech-design.md`, `02c-giao-viec.md` |
| **Bạn** (Gemini CLI / Antigravity) | Hiện thực: BE ∥ FE → QA → commit | code, `03-dev-notes.md`, `04-qa-report.md` |
| **Duy** | Duyệt ở từng điểm dừng, quyết định deploy | — |

Hồ sơ mỗi tính năng nằm ở `doc/features/<YYYY-MM-DD>-<slug>/`. **Bạn chỉ làm tính năng có
`02c-giao-viec.md` ở trạng thái `SẴN SÀNG CODE`**. File đó ghi lô nào làm trước, story nào, được sửa
file nào, lệnh kiểm chứng và điều kiện xong. Thiếu file này, hoặc `02-stories.md`/`02b-tech-design.md`
chưa `ĐÃ DUYỆT` → dừng và báo Duy, không tự viết yêu cầu hay tự thiết kế.

Workflow chạy việc: `/lam-tiep` (làm phase kế tiếp theo **`doc/ke-hoach-tong.md`** — thứ tự các phase, điều
kiện bắt đầu, việc của Duy) hoặc `/lam-tinh-nang <slug>` (một hồ sơ cụ thể). File ở `.agents/workflows/` cho
Antigravity, `.gemini/commands/` cho Gemini CLI.

## Agent

Định nghĩa ở `.agents/agents/` (Antigravity) — `.gemini/agents` là đường dẫn trỏ tới cùng thư mục
(Gemini CLI). Subagent không gọi được subagent khác: phiên chính là điều phối viên, giao việc, kiểm
kết quả.

| Agent | Việc | Được sửa |
|---|---|---|
| `be-dev` | story BE theo TDD | `backend/`, `adapter/`, mục BE của `03-dev-notes.md` |
| `fe-dev` | story FE, bám contract API, có mock | `frontend/`, `erp-console/`, mục FE của `03-dev-notes.md` |
| `qa-tester` | kiểm từng AC, phân quyền, rò giá vốn, rò dữ liệu cá nhân, hồi quy | test mới + `04-qa-report.md`, không sửa code sản phẩm |

Skill dùng chung ở `.agents/skills/` (trỏ về `.claude/skills/`, một nguồn duy nhất cho mọi công cụ;
chưa có thì chạy `sh scripts/lien-ket-skill.sh` một lần để tạo liên kết):
`caveve-domain`, `django-drf-patterns`, `nextjs-shop-patterns`, `tdd-workflow`, `e2e-playwright`,
`caveve-ui` và các skill UI nó chỉ định.

## Luật bắt buộc (vi phạm = dừng lại hỏi Duy)

- **Không lật quyết định** trong `doc/decisions.md` hay trong hồ sơ đã duyệt. Code không khớp thiết kế,
  hoặc thiết kế sai → ghi vào `03-dev-notes.md` mục "Lệch thiết kế" và dừng lô đó, không tự quyết.
- **Không rò giá vốn** (bất biến 1): serializer tách theo quyền, test bằng token từng Group.
- **Không rò dữ liệu cá nhân khách** (tên, SĐT, địa chỉ — bất biến 9, lỗi **Critical**): API công khai
  không trả, không ghi log, không đưa vào prompt AI, test/doc/commit chỉ dùng dữ liệu giả.
- **Không xoá chứng từ** (chỉ huỷ bằng trạng thái). Migration chỉ thêm, không đổi nghĩa field cũ.
- **Không deploy**, không `gcloud`/`firebase deploy`, không đụng DB staging/production. Deploy chỉ khi Duy
  nói rõ, theo `doc/ops/moi-truong.md`.
- **Không commit `.env`, khoá, mật khẩu** — repo đang công khai.
- **Không báo "xong" / "test xanh"** khi chưa chạy lệnh kiểm chứng trong lượt đó và dán kết quả.
- **QA không chấm PASS bằng đọc code** (review 30/09 phát hiện nhiều AC FE PASS mà thực tế sai): AC FE cần
  Playwright hoặc ảnh chụp trình duyệt; mỗi AC nghiệp vụ có ca ngoài đường thuận (xem `.agents/agents/qa-tester.md`).

## Lệnh kiểm chứng

```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd adapter && pytest                                    # khi có sửa adapter
cd frontend && npm ci && npx tsc --noEmit && npm run build
cd erp-console && npm ci && npx tsc --noEmit && npm run build && npm test   # npm ci phải sạch, không --legacy-peer-deps
# Test admin cần static: DJANGO_DEBUG=1 .venv/bin/python manage.py collectstatic --noinput (một lần)
```

## Git

- Làm trên nhánh chứa hồ sơ (hiện là `wip/autosave`, xem `02c-giao-viec.md`). `git pull` trước khi bắt đầu.
- Commit **sau khi lô đã QA APPROVED**, message tiếng Việt có mã story, rồi `git push`. Không force-push.
- Trước khi commit: `git status` không có `.env`, DB, ảnh chụp test, bí mật.

## Môi trường

Staging (SePay sandbox) và Production (SePay live) — chi tiết ở `doc/ops/moi-truong.md`. Build frontend
luôn truyền `NEXT_PUBLIC_*` trực tiếp vì `.env.local` đè lên `.env.production`.

## Đặt tên (P8b, Duy chốt 01/10)

Định danh trong code (hàm, biến, class, module, thư mục, file, test, script, route API, khoá JSON, biến env, Group,
`data-testid`, id lệnh AI, khoá lưu trình duyệt) là **tiếng Anh chuẩn, không viết tắt tiếng Việt**. Chữ hiển thị cho người
dùng, comment, docstring và tài liệu vẫn tiếng Việt. Viết tắt chỉ dùng khi là chuẩn quốc tế: `VN`, `VND`, `pnl`, `id`, `url`.
Không đưa mã lô giao việc (`lo7`, `l8`, `p8_lo5`) vào tên; mã lô/story ghi trong docstring.

| Khái niệm | Dùng | Không dùng |
|---|---|---|
| Vai (Group) | `owner` `manager` `warehouse_staff` `delivery_staff` `customer_service` | `chu` `quan_ly` `nv_kho` `nv_giao` `cskh` |
| Người giao trên một phiếu | `courier` | `nv_giao` |
| Việc gọi xác nhận đơn | `confirmation` | `cskh` (module, route, khoá JSON, env) |
| Nhập lô | `receive_batches`, `ReceiveBatches*` | `nhap_lo`, `NhapLo*` |
| Lệnh AI: nhóm / mức nhạy cảm | `purchasing` `sales` `customer_service` / `high` `medium` `low` | `thu_mua` `ban_hang` / `cao` `trung_binh` `thap` |
| Giờ Việt Nam | `VN_TIME_ZONE`, `todayInVietnam()`, `today_in_vietnam()` | `VN_TZ`, `todayVn`, `vn_today` |
| Bản rà soát QA / bổ sung | `review_*` / `extra`, `followup` | `ra_soat_*` / `bosung` |

Giữ nguyên (không đổi): migration đã chạy, `AuditLog.action` đã ghi, dòng phiên bản cấu hình AI cũ, URL công khai Shop
`/bai-viet/` `/trang/` `?chuyen-muc=`, dữ liệu demo (username `kho1`, `chu_vua`..., slug, mã hàng), keyword AI có dấu, chuỗi `cangca`.
Bảng đầy đủ: `doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md` mục 1.

**Kiểm bằng máy** (Python 3 stdlib, chạy từ gốc repo, dưới 10 giây, không cần venv):
`python3 scripts/check_naming.py`. Exit 1 khi file MỚI có định danh tiếng Việt, hoặc số vi phạm của một file TĂNG so với
`scripts/naming_baseline.json`; in file, dòng, token. Script không xét chuỗi hiển thị, comment, docstring. Danh sách từ chặn và
allowlist ở `scripts/naming_blocklist.txt`. Chạy lệnh này trước khi báo xong mọi việc có sửa code.

Mọi agent (Gemini CLI / Antigravity) chạy `python3 scripts/check_naming.py` cùng với bộ lệnh kiểm chứng ở mục "Lệnh kiểm chứng",
trong đúng lượt báo xong; phải exit 0. Cách dùng `--update`, `git mv`, `naming: allow - <lý do>`: xem skill `tdd-workflow`, mục "Đặt tên".
