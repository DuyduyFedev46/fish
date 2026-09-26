# Cá Về — ERP console (Next.js)

Console vận hành nội bộ cho Chủ, Quản lý, NV kho, NV giao. Next.js 14, **static export** (`out/`)
→ Firebase Hosting site `cangca-erp`. Gọi Django API (`cangca-api`) bằng token DRF.
S8 đã chuyển xong Tổng quan, Đơn, Kho & lô từ bản HTML cũ. Bản HTML cũ đã xoá khỏi repo khi deploy lần 1 (2026-09-25, D2). Muốn xem lại bản cũ thì dùng
Firebase Hosting → site `cangca-erp` → Release history → Rollback.

## Sơ đồ thư mục

```
erp-console/
  app/                    CHỈ route, rất mỏng: mỗi page.tsx import rồi render 1 màn từ features/ hoặc shared/
    layout.tsx            khung HTML gốc: font, script sáng/tối, <AuthProvider>
    page.tsx              "/" → chuyển tới đăng nhập hoặc trang mặc định của vai
    login/  no-role/      màn đăng nhập, màn "chưa được phân quyền"
    set-password/         S48 màn "Đặt mật khẩu mới" — màn DUY NHẤT mở được khi còn mật khẩu tạm
    (console)/            nhóm route cần đăng nhập + có Group (layout = ConsoleGate → Shell)
      overview/ orders/ deliveries/ my-deliveries/ inventory/ purchasing/
      stocktake/ reports/ catalog/ staff/        mỗi thư mục = 1 mục menu
      account/            "Tài khoản của tôi" (S46/S47) — mọi người có Group, không nằm trong menu quyền
  features/               code theo MODULE TÍNH NĂNG; chỉ tạo module khi có code
    auth/                 đăng nhập, phiên, /api/auth/me/, AuthProvider, ViewGuard, ConsoleGate,
                          S46 đăng xuất/tự đổi mật khẩu, S47 màn "Tài khoản của tôi", S48 bắt đổi mật khẩu tạm
      api.ts mock.ts types.ts session.ts components/ README.md
    staff/                S41/S42 Nhân viên: danh sách, tạo, sửa, đổi nhóm, cho nghỉ/làm lại, đặt lại mật khẩu
      api.ts mock.ts types.ts messages.ts components/ README.md
    overview/             S8 Tổng quan: KPI, 8 đơn gần nhất, cận hạn, tồn theo lô
    orders/               S10 danh sách + chi tiết đơn (GET /api/sales/orders/), S11 Chủ xác nhận đã nhận tiền,
                          S12 hàng chờ thanh toán lệch (/orders/payments/, menu con), S13 phiếu hoàn cho khoản không có hoá đơn,
                          S14 huỷ đơn đã thanh toán, S15 phiếu hoàn từ đơn có hoá đơn, S16 phiếu hoàn chờ chuyển
                          (/orders/refunds/, menu con — xác nhận/thất bại/thử lại)
    inventory/            S8 Kho & lô + tab "Hoạt động" (sổ kho) của cột phải — S25 mở rộng
                          (mỗi module: api.ts mock.ts types.ts components/ README.md)
  shared/                 dùng chung, KHÔNG phụ thuộc features/
    lib/                  http.ts (apiFetch + Token + mock), token.ts, nav.ts (menu ↔ quyền, hằng PERM/GROUP),
                          messages.ts (MỌI thông điệp lỗi/thông báo FE tự sinh), groups.ts (mã + nhãn nhóm),
                          beErrors.mock.ts (mã lỗi + detail của BE chép từ contract — chỉ mock import),
                          drafts.ts + useDraft.ts (giữ nháp), format.ts (tiền, kg, giờ),
                          useResource.ts (cache đọc dùng chung: 1 request cho nhiều màn),
                          dashboardSummary.ts (+ .mock.ts = seed) — contract /api/dashboard/summary/ dùng chung 3 module S8,
                          search.ts (tìm phía máy, bỏ dấu), status.ts (màu/icon trạng thái đơn, lô),
                          passwordRules.ts (gợi ý quy tắc mật khẩu hiện trước khi gửi — BE vẫn kiểm thật)
    ui/                   PasswordInput (Ô MẬT KHẨU DÙNG CHUNG cho mọi form: nút mắt ≥44px, gợi ý quy tắc, lỗi "không khớp"),
                          Shell (3 cột), RightRail, Icon, Sheet (hộp thoại/tấm trượt đáy), StateBox (tải/lỗi/rỗng), ResourceView (3 trạng thái
                          cho useResource), Toolbar (ô tìm + Làm mới), StatusChip, EmptyRow, Placeholder,
                          ThemeToggle, themeScript.ts, NotFoundScreen, Skeleton, Figure,
                          SideSheet + Toast + overlay.module.css (tấm bên có chuyển động ra, thông báo nổi — UI5 đưa lên dùng chung),
                          useDrawerFocus.ts (ngăn kéo menu/cột phải: focus vào trong, giữ Tab, trả focus khi đóng),
                          tokens.css (TOKEN THIẾT KẾ theo DESIGN.md ở gốc repo — file DUY NHẤT được chứa mã màu),
                          globals.css (style chung, chỉ dùng var(--…))
  e2e/                    kịch bản Playwright (Python): trên bản build mock s7_shell.py, s8_views.py, s41_s47_staff.py,
                          s48_password.py, s10_s11_orders.py, s12_s13_queue.py; trên BACKEND THẬT s41_s47_real.py (có cả S48; so chữ UI với response thật).
                          Quy ước: không `wait_for_timeout` — chờ điều kiện (URL, phần tử, localStorage, `aria-busy`,
                          `__caveMock.pending() === 0` trước khi đổi dữ liệu mock)
```

**Quy tắc**
- Module không import vào bên trong module khác; chỉ dùng `shared/` hoặc `features/auth`.
- Không dùng barrel `index.ts`; import thẳng file bằng alias `@/` (vd `@/shared/lib/http`).
- Mọi call API qua `apiFetch` (`shared/lib/http.ts`). Mỗi hàm API của module truyền kèm mock:
  `apiFetch(path, { mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockX : undefined })`.
  Viết nguyên biểu thức đó tại chỗ để bản build thật loại bỏ hẳn code mock.
- Màn có quyền: page.tsx bọc `<ViewGuard view="...">`; thiếu quyền thì màn không mount, không gọi API.
  Menu ↔ quyền khai một chỗ ở `shared/lib/nav.ts`. Backend vẫn là lớp chặn thật.
- **Không viết cứng thông điệp lỗi / mã lỗi / tên quyền trong component.** Lỗi nghiệp vụ: hiện nguyên văn `detail` BE,
  logic chỉ dựa vào `code`. Câu FE tự sinh (mất mạng, 5xx, kiểm tại máy, thông báo) → `shared/lib/messages.ts`
  (hoặc `features/<x>/messages.ts`). Tên quyền → `PERM` (`shared/lib/nav.ts`); mã nhóm → `GROUP` / `groups.ts`.
- **Giao diện theo `DESIGN.md` (gốc repo)**, sản phẩm/người dùng ở `PRODUCT.md`. Chỉ dùng token trong `shared/ui/tokens.css`:
  không mã hex/rgba, không `style={{…}}` trong component (`grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' app features shared` ngoài tokens.css phải ra 0).
- Mỗi màn dữ liệu có đủ 3 trạng thái (`shared/ui/StateBox.tsx`). Mobile-first: 360px không cuộn ngang, nút ≥ 44px.
- **Mật khẩu (S48):** mọi ô mật khẩu dùng `shared/ui/PasswordInput`. Form đặt mật khẩu mới có ô "Nhập lại"; lệch thì báo
  "Hai mật khẩu không khớp" và KHÔNG gọi API. Mật khẩu không bao giờ nằm trong nháp (`useDraft`) hay localStorage.

**Thêm một module:** tạo `features/<x>/{api.ts,mock.ts,types.ts,components/<X>Screen.tsx,README.md}`,
rồi trong `app/(console)/<x>/page.tsx` thay `<Placeholder view="..." />` bằng màn của module (giữ `<ViewGuard>`). Mẫu: `features/overview/`.
Dữ liệu đọc dùng chung nhiều màn → `useResource(key, loader)` (`shared/lib/useResource.ts`), vẽ trạng thái bằng `<ResourceView>`.
Nội dung cột phải (Hoạt động, Trợ lý) ghép ở `app/(console)/layout.tsx` (tầng app được import mọi module).

## File cấu hình ở gốc

| File | Để làm gì |
|---|---|
| `package.json` | Tên app, thư viện cần (next, react) và các lệnh `npm run dev/build`. `sideEffects` báo cho bộ đóng gói biết chỉ file CSS có tác dụng phụ, để bỏ được code không dùng |
| `next.config.mjs` | Cấu hình Next.js: xuất web tĩnh ra `out/`, URL có dấu `/` cuối, luôn định nghĩa cờ mock khi build |
| `tsconfig.json` | Cấu hình TypeScript; khai alias `@/` = thư mục gốc erp-console |
| `firebase.json` | Firebase Hosting: đưa thư mục `out/` lên site `cangca-erp` |
| `.firebaserc` | Project Google Cloud mặc định cho lệnh firebase (`keolai-63ec1`) |
| `.env.example` | Mẫu biến môi trường: địa chỉ API và bật/tắt mock. Chép thành `.env.local` khi chạy máy mình |
| `.gitignore` | Những thứ không đưa vào git: `node_modules/`, `.next/`, `out/`, `.env.local` |
| `next-env.d.ts` | Next.js tự sinh để TypeScript hiểu kiểu của Next; không sửa tay |

## Dữ liệu mock và dữ liệu demo (D1 — Duy chốt 2026-09-24)

Có HAI thứ khác nhau, đều bật/tắt được:

| | Là gì | Bật | Tắt |
|---|---|---|---|
| **Mock của console** | Console không gọi mạng; mỗi module trả JSON giả theo contract (`features/*/mock.ts`). Dùng khi BE chưa có endpoint hoặc chạy máy không có Django | `NEXT_PUBLIC_USE_MOCK=1` lúc `npm run dev` / `npm run build` | bỏ biến hoặc `NEXT_PUBLIC_USE_MOCK=0` (mặc định). Bản build thật **không chứa** code mock (webpack bỏ hẳn) |
| **Dữ liệu demo trên backend thật** | Mặt hàng, lô, đơn, hoá đơn mẫu nằm trong DB thật (kể cả production) | `cd backend && .venv/bin/python manage.py seed_demo` (chạy lại không nhân đôi) | `manage.py seed_demo --remove` (thêm `--dry-run` để xem trước). Chỉ gỡ bản ghi do `seed_demo` tạo ra, không đụng dữ liệu thật; gỡ xong thêm lại được bằng `seed_demo`. DB đã seed bằng bản cũ: `seed_demo --remove --adopt-legacy --dry-run` rồi bỏ `--dry-run` |

`.env.local` (chép từ `.env.example`) giữ lựa chọn khi chạy máy mình. Deploy: **không** set `NEXT_PUBLIC_USE_MOCK`.

## Lệnh

```bash
cd erp-console
npm install                                   # lần đầu
NEXT_PUBLIC_USE_MOCK=1 npm run dev            # BẬT mock, không cần backend → http://localhost:3100
npm run dev                                   # TẮT mock (mặc định): gọi NEXT_PUBLIC_API_BASE (mặc định http://localhost:8000)
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev    # nối Django chạy máy mình
npx tsc --noEmit && npm run build             # kiểm kiểu + build tĩnh ra out/
```

Tài khoản mock (mật khẩu `demo1234`): `loc` (Chủ), `ql1` (Quản lý), `kho1` (NV kho + NV giao),
`giao1` (NV giao), `giao2` (còn phiếu Đang giao), `ql9` (Quản lý + quyền lẻ `manage_staff`), `sa1` (superuser + Quản lý),
`admin` (superuser, chưa phân quyền), `nghi1` (đã nghỉ), `kho5` (NV kho, còn mật khẩu tạm → phải đặt mật khẩu mới, S48).
Mock lưu người dùng trong localStorage; `__caveMock.resetUsers()` về seed. Tài khoản Chủ tạo / đặt lại mật khẩu trong mock
cũng bị bắt đổi mật khẩu ở lần đăng nhập đầu (như BE).

**Build để deploy** (chỉ khi Duy duyệt): phải set URL API thật lúc build, vì đây là web tĩnh:
```bash
NEXT_PUBLIC_API_BASE=https://<url Cloud Run cangca-api> npm run build
firebase deploy --only hosting               # chạy trong erp-console/, đẩy out/ lên cangca-erp
```
Không build với `NEXT_PUBLIC_USE_MOCK=1` khi deploy.
