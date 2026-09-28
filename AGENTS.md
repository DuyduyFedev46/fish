# Cá Về — hướng dẫn cho agent lập trình (Gemini CLI, Antigravity và các agent khác)

Vựa cá B2C: mua lô tại cảng → bán online → quản lý kho và giá vốn theo lô. Chủ dự án là **Duy** (PO),
trao đổi bằng tiếng Việt. Nghiệp vụ và bất biến nằm ở skill `caveve-domain`: **đọc skill này trước khi
đụng vào bất kỳ code nào.**

## Chia việc (Duy chốt 2026-09-28)

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

## Lệnh kiểm chứng

```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd adapter && pytest                                    # khi có sửa adapter
cd frontend && npx tsc --noEmit && npm run build
cd erp-console && npx tsc --noEmit && npm run build
```

## Git

- Làm trên nhánh chứa hồ sơ (hiện là `wip/autosave`, xem `02c-giao-viec.md`). `git pull` trước khi bắt đầu.
- Commit **sau khi lô đã QA APPROVED**, message tiếng Việt có mã story, rồi `git push`. Không force-push.
- Trước khi commit: `git status` không có `.env`, DB, ảnh chụp test, bí mật.

## Môi trường

Staging (SePay sandbox) và Production (SePay live) — chi tiết ở `doc/ops/moi-truong.md`. Build frontend
luôn truyền `NEXT_PUBLIC_*` trực tiếp vì `.env.local` đè lên `.env.production`.
