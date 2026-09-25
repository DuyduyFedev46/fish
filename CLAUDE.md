# Cá Về — hướng dẫn cho Claude

Vựa cá B2C (mua lô tại cảng → bán online → quản lý kho/giá vốn). Người dùng là **Duy**
(PO), trao đổi bằng tiếng Việt. Nghiệp vụ & bất biến: skill `caveve-domain`.

## Workflow đội dự án — tự nhận diện, Duy không gõ lệnh

Duy chỉ nhờ bằng lời thường. **Mọi yêu cầu làm thay đổi sản phẩm** (thêm/sửa chức năng,
sửa lỗi, đổi giao diện, đổi quy tắc, viết yêu cầu/story, test thử, review, deploy) →
**gọi skill `feature` trước khi làm gì khác**, để nó chọn luồng và báo Duy một dòng:

```
ĐẦY ĐỦ  (tính năng mới / đổi nghiệp vụ)  BA → [Duy duyệt] → PO → [Duy duyệt] → BE ∥ FE → UI review → QA → Review → [Duy duyệt] → Deploy
NHANH   (lỗi rõ / chỉnh nhỏ)             AC ngắn → BE/FE → QA → tổng kết
CHỈ BA · CHỈ PO · CHỈ QA · REVIEW · DEPLOY · TIẾP TỤC (việc đang dở)
```
Không chạy workflow cho câu hỏi thuần giải thích/tra cứu, hoặc việc vận hành không đổi
code (xem log, seed dữ liệu, đổi mật khẩu) — làm trực tiếp.

**Model (Duy chốt 2026-09-26):** lập kế hoạch dùng **Opus**, gồm điều phối viên (phiên chính), `ba-analyst` và `po-owner`. Code và test dùng **Sonnet**, gồm `be-dev`, `fe-dev` và `qa-tester`. Model khai ở frontmatter `model:` của từng agent; khi gọi Agent thì không ghi đè.

| Vai | Subagent | Skill nạp sẵn | Đầu ra |
|---|---|---|---|
| BA | `ba-analyst` | requirement-elicitation | `doc/features/<ngày>-<slug>/01-analysis.md` |
| PO | `po-owner` | user-story-writing | `02-stories.md` (+ nghiệm thu) |
| BE | `be-dev` | django-drf-patterns, tdd-workflow | code `backend/` `adapter/` + `03-dev-notes.md` |
| FE | `fe-dev` | nextjs-shop-patterns, caveve-ui, impeccable, emil-design-eng, baseline-ui, fixing-accessibility | code `frontend/` `erp-console/` + `03-dev-notes.md` |
| QA | `qa-tester` | e2e-playwright, tdd-workflow | `04-qa-report.md` |

Nguồn gốc các skill (đã viết lại cho dự án): obra/superpowers, github/spec-kit,
bmad-code-org/BMAD-METHOD, wshobson/agents, Jeffallan/claude-skills,
vercel-labs/agent-skills, anthropics/skills, phuryn/pm-skills, alirezarezvani/claude-skills.
Skill UI/UX cài nguyên bản (giữ LICENSE): pbakaus/impeccable, emilkowalski/skills, nextlevelbuilder/ui-ux-pro-max-skill,
ibelick/ui-skills, vercel web-design-guidelines. Hướng thiết kế + chọn skill: `caveve-ui`.

## Luật chung
- **Git:** mỗi khi xong một tính năng (một lô đã QA APPROVED) thì commit và `git push origin main` lên github.com/DuyduyFedev46/fish. Đây là quy ước Duy đặt ngày 2026-09-25. Repo đang công khai nên không bao giờ commit `.env` hay bí mật.
- Không deploy khi Duy chưa yêu cầu.
- Không báo "xong"/"test xanh" khi chưa chạy lệnh kiểm chứng trong lượt đó.
- Không rò giá vốn, không xoá chứng từ, không lật quyết định trong `doc/decisions.md`.
