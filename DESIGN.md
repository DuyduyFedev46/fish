---
name: Cá Về
description: Design system dùng chung cho ERP console, Shop và app. Tinh gọn kiểu Linear/Notion, một màu nhấn xanh biển.
colors:
  # Light
  canvas: "#FBFBFC"
  sidebar: "#F4F4F6"
  surface: "#FFFFFF"
  surface-2: "#F4F4F6"
  surface-3: "#EBEBEF"
  border: "#E4E4E9"
  border-strong: "#D4D4DB"
  border-input: "#8C8C98"
  ink: "#17171C"
  ink-2: "#4E4E58"
  ink-3: "#686874"
  accent: "#1F66D1"
  accent-hover: "#1A57B5"
  accent-text: "#1A5BC0"
  accent-soft: "#EBF2FE"
  on-accent: "#FFFFFF"
  focus: "#1F66D1"
  good: "#157F3D"
  good-soft: "#E9F7EE"
  warn: "#A85A07"
  warn-soft: "#FDF3E3"
  crit: "#C0312B"
  crit-hover: "#A82823"
  crit-soft: "#FCEDEC"
  on-crit: "#FFFFFF"
  # Dark (ngang hàng light, không đảo màu máy móc)
  dark-canvas: "#111113"
  dark-sidebar: "#151518"
  dark-surface: "#1A1A1E"
  dark-surface-2: "#222227"
  dark-surface-3: "#2B2B31"
  dark-border: "#2A2A30"
  dark-border-strong: "#3A3A42"
  dark-border-input: "#6B6B77"
  dark-ink: "#EDEDF0"
  dark-ink-2: "#AEAEB8"
  dark-ink-3: "#9696A1"
  dark-accent: "#2F6FDB"
  dark-accent-hover: "#285FC4"
  dark-accent-text: "#7FB0FA"
  dark-accent-soft: "#1A2740"
  dark-focus: "#5B95F2"
  dark-good: "#5CC98A"
  dark-good-soft: "#15271D"
  dark-warn: "#E3AA4B"
  dark-warn-soft: "#2A2114"
  dark-crit: "#F2807A"
  dark-crit-hover: "#F59590"
  dark-crit-soft: "#2E1817"
  dark-on-crit: "#1A0B0A"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
  caption:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
  data:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
  code:
    fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "14px"
  full: "999px"
spacing:
  "0.5": "2px"
  "1": "4px"
  "1.5": "6px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
  "12": "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.md}"
    height: "44px"
    padding: "0 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "44px"
    padding: "0 14px"
  button-danger:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.crit}"
    rounded: "{rounded.md}"
    height: "44px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "44px"
    padding: "0 12px"
  nav-item:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    height: "36px"
    padding: "0 10px"
  nav-item-active:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.accent-text}"
  tag:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    height: "22px"
    padding: "0 8px"
    typography: "{typography.caption}"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
---

# Design System: Cá Về

Nguồn token chạy thật: `erp-console/shared/ui/tokens.css` (ERP). Shop (`frontend/`) và app sau này **chép cùng giá trị**
từ file này, không tự đặt màu mới. Đổi token thì đổi ở đây trước, rồi đồng bộ các `tokens.css`.
Bối cảnh sản phẩm và người dùng: `PRODUCT.md`. Cách chọn skill UI: `.claude/skills/caveve-ui/SKILL.md`.

## Overview

Công cụ làm việc, không phải trang quảng cáo. Hướng **Linear/Notion tinh gọn** (Duy chốt 2026-09-24): nền xám trung tính
rất nhạt, bề mặt trắng, viền mảnh 1 px, một màu nhấn **xanh biển** cho hành động chính và trạng thái đang chọn.
Thứ bậc tạo bằng cỡ chữ, độ đậm và ba mức xám của chữ (`ink`, `ink-2`, `ink-3`), không bằng khung dày hay bóng nặng.
Con số (tiền, kg) là nhân vật chính: chữ số cùng độ rộng (`tabular-nums`), căn phải trong bảng.

Người dùng chuẩn đo là NV kho/NV giao cầm điện thoại ngoài trời: vùng bấm ≥ 44 px, tương phản AA ở cả light và dark,
thao tác chính nằm dưới ngón cái (menu đáy, nút chính ở cuối form). Dark mode là chế độ ngang hàng, chọn theo máy hoặc
bằng nút đổi giao diện (lưu `localStorage["cave_theme"]`).

## Colors

Chiến lược **Restrained**: 90% là xám trung tính (hơi lạnh), 1 màu nhấn, 3 màu trạng thái dùng khi có nghĩa.

### Primary

- **Xanh biển `accent` #1F66D1 / dark #2F6FDB:** nền nút chính, mục menu đang chọn (dạng `accent-soft` + `accent-text`),
  vòng focus, liên kết. Chữ trắng trên nền accent đạt 5.4:1 (light) và 4.75:1 (dark).
- `accent-text` (#1A5BC0 / dark #7FB0FA) là màu dành cho **chữ** xanh trên nền sáng/tối; không dùng `accent` làm chữ trong dark.
- `accent-soft` là nền nhạt cho trạng thái chọn và chip thông tin ("Đang xử lý").

### Neutral

| Token | Light | Dark | Dùng cho |
|---|---|---|---|
| `canvas` | #FBFBFC | #111113 | nền vùng nội dung giữa |
| `sidebar` | #F4F4F6 | #151518 | cột menu trái, cột phải, nền màn đăng nhập |
| `surface` | #FFFFFF | #1A1A1E | bảng, panel, ô nhập, hộp thoại |
| `surface-2` | #F4F4F6 | #222227 | hover, nền phụ |
| `surface-3` | #EBEBEF | #2B2B31 | đang nhấn, chip trung tính |
| `border` | #E4E4E9 | #2A2A30 | đường kẻ, viền panel |
| `border-strong` | #D4D4DB | #3A3A42 | viền nút phụ |
| `border-input` | #8C8C98 | #6B6B77 | viền ô nhập (≥ 3:1 với nền, WCAG 1.4.11) |
| `ink` | #17171C | #EDEDF0 | chữ chính |
| `ink-2` | #4E4E58 | #AEAEB8 | chữ phụ, nhãn |
| `ink-3` | #686874 | #9696A1 | chú thích, placeholder (≥ 4.6:1 trên mọi nền xám) |

### Trạng thái

| Token | Light (chữ / nền) | Dark (chữ / nền) | Nghĩa |
|---|---|---|---|
| `good` | #157F3D / #E9F7EE | #5CC98A / #15271D | đã thanh toán, hoàn tất, thành công |
| `warn` | #A85A07 / #FDF3E3 | #E3AA4B / #2A2114 | cận hạn, sắp hết giữ chỗ, cần chú ý |
| `crit` | #C0312B / #FCEDEC | #F2807A / #2E1817 | lỗi, quá hạn, hành động nguy hiểm |
| info | dùng `accent-text` / `accent-soft` | | trạng thái đang chạy, thông báo trung tính |

Mọi cặp chữ/nền ở trên đã đo ≥ 4.5:1. Nút nguy hiểm dạng đặc: light chữ trắng trên `crit` (5.6:1), dark chữ `on-crit` #1A0B0A (7.4:1).

### Named Rules

- **Một màu nhấn mỗi màn.** Xanh biển chỉ cho hành động chính, mục đang chọn, focus, liên kết. Không tô icon trang trí bằng accent hàng loạt.
- **Màu trạng thái phải có nghĩa.** Không dùng xanh lá/hổ phách/đỏ để làm đẹp. Trạng thái luôn đi kèm chữ hoặc icon, không chỉ màu.
- **Không gradient, không glow.** Logo là ô vuông màu đặc.

## Typography

- **Inter** (Google Fonts, có subset `vietnamese`, đủ "ư ơ ạ ễ ặ ỹ") cho mọi thứ: tiêu đề, nhãn, nút, dữ liệu. Một họ chữ là đủ cho công cụ vận hành.
- **JetBrains Mono** (có subset `vietnamese`) chỉ cho **mã** (mã đơn, mã lô, tên đăng nhập, mật khẩu tạm), không dùng làm trang trí.
- Số tiền, kg, giờ: Inter + `font-variant-numeric: tabular-nums` (class `.num`), căn phải trong bảng.
- Nạp bằng `<link>` Google Fonts `display=swap` ở `app/layout.tsx` (web tĩnh, không phụ thuộc mạng lúc build).
- Icon: **Material Symbols Outlined** (một bộ, một nét), cỡ 16/18/20 px, luôn `aria-hidden`.

### Hierarchy (thang cố định, tỉ lệ ~1.125, không co giãn theo màn)

| Token CSS | Cỡ | Dùng |
|---|---|---|
| `--text-2xs` | 11px | nhãn cột bảng, nhãn nhóm menu (chữ hoa, `letter-spacing: .06em`) |
| `--text-xs` | 12px | chú thích, chip, giờ |
| `--text-sm` | 13px | chữ phụ, nhãn ô nhập, menu desktop |
| `--text-base` | 14px | chữ thân, nút, ô bảng |
| `--text-md` | 15px | tiêu đề topbar, tiêu đề panel |
| `--text-lg` | 17px | tiêu đề hộp thoại, tiêu đề thẻ |
| `--text-xl` | 20px | tiêu đề màn đăng nhập, số KPI trên điện thoại |
| `--text-2xl` | 24px | số KPI desktop, tiêu đề trang lớn |
| `--text-input` | 16px | **mọi ô nhập** (iOS không tự phóng to) |

Độ đậm: 400 thân · 500 nhãn/menu/số · 600 tiêu đề, nút. Tiêu đề `letter-spacing: -0.01em`, `text-wrap: balance`.

## Layout

- **Khoảng cách** theo bước 4 px: `--space-1` 4 · `-2` 8 · `-3` 12 · `-4` 16 · `-5` 20 · `-6` 24 · `-8` 32 · `-10` 40.
  Nhóm chặt bên trong (8–12), tách nhóm rộng hơn (16–24); phía trên tiêu đề nhiều hơn phía dưới.
- **Console ERP (mobile-first):**
  - < 768 px: topbar 56 px (nút ☰, tiêu đề, đổi giao diện, cột phải) · nội dung · **menu đáy** 60 px + `safe-area-inset-bottom`, tối đa 5 mục (4 + "Thêm"). Menu trái và cột phải là ngăn kéo.
  - 768–1023 px: menu trái cố định 240 px; cột phải là ngăn kéo.
  - ≥ 1024 px: **3 cột** 240 px · nội dung · 320 px.
- Chiều cao khung dùng `100dvh`. 360 px không được cuộn ngang. Nội dung giữa rộng tối đa 1280 px.
- Safe-area: topbar/ngăn kéo/menu đáy/tấm trượt dùng `env(safe-area-inset-*)`; khung `.app` chừa trái/phải khi xoay ngang (`viewport-fit=cover`).
- **Vùng bấm** `--tap` 44 px trên điện thoại, 40 px từ 768 px (chuột).
- **z-index** cố định (`--z-*`): header bảng dính 5 · topbar 10 · scrim 30 · ngăn kéo phải 40 · ngăn kéo trái 41 · thông báo nổi (`--z-toast`) 50 · hộp thoại 60.

## Elevation & Depth

Phẳng là mặc định: panel và bảng chỉ có viền 1 px `border`, không bóng. Bóng chỉ cho thứ **nổi lên trên** nội dung.

| Token | Dùng |
|---|---|
| `--shadow-xs` | nút phụ, ô nhập (gần như không thấy, tạo độ nổi 1 px) |
| `--shadow-sm` | thẻ đăng nhập trên desktop |
| `--shadow-md` | ngăn kéo menu/cột phải trên điện thoại |
| `--shadow-lg` | hộp thoại, tấm trượt đáy |

Dark mode dùng bóng đen đậm hơn và dựa vào bậc sáng của bề mặt (`canvas` < `sidebar` < `surface` < `surface-2`) để tạo chiều sâu.

## Shapes

Bo góc nhỏ và nhất quán: `--radius-xs` 4 (thanh chỉ báo) · `-sm` 6 (mục menu, chip vuông) · `-md` 8 (nút, ô nhập) ·
`-lg` 10 (panel, bảng, thẻ KPI) · `-xl` 14 (hộp thoại, thẻ đăng nhập) · `-full` (chip trạng thái, avatar).

## Motion

Nhẹ và nhanh, chỉ để phản hồi và chuyển trạng thái, không trang trí.

| Token | Giá trị | Dùng |
|---|---|---|
| `--dur-fast` | 120ms | hover, đổi màu, nhấn nút |
| `--dur-base` | 180ms | chip, focus, hiện thông báo |
| `--dur-slow` | 240ms | ngăn kéo, tấm trượt đáy |
| `--ease-out` | cubic-bezier(0.23, 1, 0.32, 1) | mọi thứ xuất hiện |
| `--ease-drawer` | cubic-bezier(0.32, 0.72, 0, 1) | ngăn kéo, tấm trượt |

- Nút và mục bấm được: `:active { transform: scale(.97) }` (nút lớn) hoặc đổi nền `surface-3` (mục menu). Hover chỉ trong `@media (hover: hover) and (pointer: fine)` (máy cảm ứng không bị "kẹt hover").
- Nhấn giữ nút/mục menu không bôi chọn chữ (`user-select: none` chỉ trên nút, mục menu, tab).
- Chỉ animate `transform`, `opacity`, và màu nền/viền của phần tử nhỏ. Không `transition: all`.
- Hộp thoại xuất hiện từ `scale(.97)` + `opacity: 0` (không từ `scale(0)`); tấm trượt đáy từ `translateY(100%)`.
- `prefers-reduced-motion: reduce`: bỏ mọi chuyển động vị trí/tỉ lệ, giữ đổi màu tức thì.

## Components

### Buttons

- **Chính** (`.btn.primary`): nền `accent`, chữ `on-accent`, cao `--tap`, bo `--radius-md`, chữ 14/600. Mỗi form một nút chính.
- **Phụ** (`.btn`): nền `surface`, viền `border-strong`, `--shadow-xs`. Hover nền `surface-2`.
- **Nguy hiểm** (`.btn.danger`): chữ `crit`, viền `crit`; bản đặc `.btn.danger.solid` cho bước xác nhận cuối.
- **Icon** (`.iconbtn`): vuông `--tap`, không viền (ghost) trên topbar; luôn có `aria-label`.
- Đang gửi: icon `progress_activity` quay + chữ "Đang …", nút `disabled`, chặn bấm đúp.

### Inputs / Fields

- Nhãn trên ô (13/500, `ink-2`), ô cao ≥ 44 px, nền `surface`, viền `border-input`, chữ 16 px.
- Focus: viền `focus` + vòng `0 0 0 3px` màu `accent-soft`. Lỗi: viền `crit`, `aria-invalid`, câu lỗi dưới ô có icon, nói cách sửa.
- **Ô mật khẩu** luôn dùng `shared/ui/PasswordInput`: nút mắt 44×44 nằm trong ô, danh sách quy tắc cập nhật khi gõ (icon tròn → dấu tích xanh).

### Tag (`.tags > .tag`)

Nhãn nhóm quyền: thẻ vuông nhẹ cao 22 px, bo `sm`, nền `surface-2` + viền trong 1 px `border`, chữ 12/500 `ink-2`. Không dùng
màu nhấn hay màu trạng thái. (UI5 bỏ viên thuốc `.chip` cũ — không còn màn nào dùng.) Trạng thái (đang làm/đã nghỉ, có/không,
trạng thái chứng từ) dùng **chấm trạng thái** bên dưới.

### Status dot (`.status`, `shared/ui/StatusChip`)

Chấm 8 px + chữ `status_label` 13/500 (12 trong danh sách điện thoại). Chữ `ink-2`; `warn`/`crit` tô cả chữ vì cần chú ý;
`mute` là chấm rỗng (khác cả hình lẫn màu). Chữ luôn hiện, không chỉ dựa vào màu.

### KPI strip (`.kpi-band > dl.kpis > .tile`)

Dải số liệu phẳng, không hộp: kẻ mảnh trên/dưới dải, chia cột bằng đường 1 px. Nhãn 12/500 `ink-3`, số 20 px (24 px khi
vùng chứa ≥ 840 px) 600 tabular-nums, đơn vị 0.7em `ink-3`, phụ chú 12 `ink-3`. Vùng chứa < 600 px: lưới 2×2.
Chỉ tô `warn` khi cần chú ý (`.tile.attn` tô số, `.foot.attn` tô phụ chú + icon).

### Data table (`.dt-wrap > table.data`)

Phẳng trên `canvas`, không khung: hàng ~44 px ngăn bằng đường 1 px, hàng tràn 12 px hai bên để chữ thẳng tiêu đề khối.
Header 11 px chữ hoa `ink-3`, **dính** khi cuộn (`--z-sticky`). Số `.r .num` căn phải, đơn vị qua `shared/ui/Figure`.
Mã (đơn, lô) mono 12 px `ink-3`. Hover hàng nền `surface-2` (chỉ `hover:hover`).
Vùng chứa < 640 px (container query, gồm cột giữa hẹp ở 1024–1279 px) → **danh sách gọn**: dòng 1 = `m-title` + `m-fig`,
dòng 2 = mã và ô phụ (nhãn ngắn qua `data-m-label`) + `m-status` bên phải; `m-hide` ẩn ô rỗng. Không thẻ lồng thẻ.

Danh sách gọn ẩn `thead` nên mỗi ô có `data-label` (tên cột); CSS đọc nó thành nhãn **ẩn** (`::before` 1 px, cắt) để trình đọc
màn hình vẫn nghe "Mã đơn: …" — `textContent` của ô không đổi.

### Section (`.sect > .sect-h`)

Khối nội dung phẳng ở **mọi** màn danh sách (Tổng quan, Đơn, Kho & lô, Nhân sự): tiêu đề 15/600 + chú thích 12 `ink-3` +
liên kết phải (mũi tên nhích 2 px khi hover). Danh sách bên dưới không đóng khung, hàng tràn 12 px hai bên.
Ngoại lệ có chủ đích: trang cài đặt (Tài khoản của tôi) dùng nhóm hàng có khung kiểu trang cài đặt.

### Cards / Containers

- Nhóm có khung (trang cài đặt, thao tác trong tấm bên): nền `surface`, viền `border`, bo `--radius-lg`, **không bóng**.
  (Lớp `.panel` cũ đã bỏ ở UI5.)
- Không lồng khung trong khung. Thông tin nhóm trong panel ngăn bằng đường kẻ mảnh, không bằng khung.
- Thông báo (`.alert-box`): nền `*-soft`, chữ màu trạng thái, icon đầu dòng; không viền trái màu.

### Navigation

- **Menu trái**: nền `sidebar`, nhóm có nhãn chữ hoa 11 px `ink-3`; mục cao 36 px (44 px trên điện thoại), icon 18 px `ink-3`.
  Đang chọn: nền `accent-soft`, chữ + icon `accent-text`. Chân menu: avatar + tên (mở "Tài khoản của tôi") + nút đăng xuất.
- **Menu đáy** (điện thoại): 60 px + safe-area; mục đang chọn có icon đặc, chữ `accent-text` và viên nền `accent-soft` sau icon.
- **Cột phải** (Ghi chú · Trợ lý · Hoạt động): tab **chỉ chữ** (không xuống dòng ở 360 px), gạch chân 2 px `accent`;
  phím ← → Home End chuyển tab (một tab trong thứ tự Tab). Trợ lý chưa nối: khung "sắp có" (icon, tiêu đề + nhãn
  `Sắp có` nền `accent-soft`, một câu, ví dụ câu hỏi dạng chữ trơn — không đóng khung để khỏi trông như nút).
- **Ngăn kéo** (menu trái < 768 px, cột phải < 1024 px): mở thì focus vào trong (mục đang chọn), giữ Tab trong ngăn kéo,
  Esc/bấm nền/nút "Đóng menu" để đóng, đóng thì focus về nút đã mở (`shared/ui/useDrawerFocus`).

### Sổ kho (`.feed-day > ol.feed > li.fev`)

Nhóm theo ngày ("Hôm nay", "Hôm qua", dd/mm, 12/600 `ink-2`). Mỗi dòng: icon tròn 28 px **trung tính** (`surface-3`/`ink-2`)
theo loại phát sinh · dòng 1 loại phát sinh 13/500 + số kg có dấu tabular căn phải · dòng 2 mã lô mono 12 `ink-3` + giờ.
Không tô đỏ việc bán hàng bình thường; chỉ "hạch toán lỗ / huỷ" tô icon hổ phách vì cần chú ý.

### Empty / Loading / Error

- **Một kiểu cho rỗng / lỗi / 403** (bảng, cả màn, cột phải, Nhân sự): icon 22 px trong ô vuông 40 px bo `lg` nền `surface-2`
  (`surface-3` trong cột phải), tiêu đề 15/600 `ink`, một câu 13 `ink-2` (≤ 46ch), một hành động. Lỗi: ô icon `crit-soft`, câu lỗi
  làm tiêu đề, nút "Thử lại".
- Nút gửi **không tắt vì thiếu ô**: bấm thì báo ngay dưới ô trống (`aria-invalid`, câu nói cách sửa) và đưa focus vào ô đó.
  Chỉ tắt khi đang gửi (kèm "Đang …").
- Tải: màn dữ liệu dùng **khung chờ đúng hình** (`shared/ui/Skeleton`: vạch `surface-3` nhịp mờ 1.4s, đứng yên khi giảm chuyển động,
  `role="status"` + chữ ẩn "Đang tải dữ liệu…"); chỗ nhỏ vẫn dùng icon quay + chữ. Lỗi: icon + câu nói cách sửa + nút "Thử lại". Rỗng: icon trong ô vuông `surface-2`,
  tiêu đề, một câu hướng dẫn, một hành động kế tiếp. 403: nói rõ thiếu quyền gì và nhờ ai.

## Do's and Don'ts

### Do:

- Dùng token (`var(--…)`) cho mọi màu, khoảng cách, bo góc, bóng, thời lượng. `grep` mã hex trong component phải ra 0.
- Kiểm cả light và dark, cả 360 px và 1280 px trước khi báo xong.
- Căn phải và `tabular-nums` cho tiền, kg. Đơn vị "₫", "kg" cùng cỡ chữ, màu `ink-3`.
- Viết nhãn bằng động từ rõ; câu lỗi nói cách sửa.

### Don't:

- Không gradient, glow, glassmorphism, bóng đổ nặng, viền trái màu dày trên thẻ/alert.
- Không dùng mono làm trang trí; không font thiếu dấu tiếng Việt.
- Không cỡ chữ ô nhập < 16 px; không `100vh` cho khung (dùng `100dvh`).
- Không hiển thị giá vốn/lãi lỗ chỉ vì đổi giao diện; Shop không bao giờ có dữ liệu này.
- Không animate khi thao tác bằng phím tắt; không animation > 300 ms trong UI.
