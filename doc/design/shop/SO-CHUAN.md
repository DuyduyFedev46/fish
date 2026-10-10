# Số chuẩn component Shop (dùng chung cho mọi bảng component và COMPONENTS.md)

## Màu (token DESIGN.md + 1 token mới)
canvas #FBFBFC · surface #FFFFFF · surface-2 #F4F4F6 · surface-3 #EBEBEF · border #E4E4E9 · border-strong #D4D4DB · border-input #8C8C98
ink #17171C · ink-2 #4E4E58 · ink-3 #686874
accent #1F66D1 · accent-hover #1A57B5 · accent-text #1A5BC0 · accent-soft #EBF2FE · focus #1F66D1
brand-deep #0E3A73 (MỚI: banner, footer, nút "Tìm" header máy tính) · on-brand-muted #D6E4FA (chữ phụ trên nền accent/brand-deep)
good #157F3D / good-soft #E9F7EE · warn #A85A07 / warn-soft #FDF3E3 · crit #C0312B / crit-hover #A82823 / crit-soft #FCEDEC
overlay rgba(23,23,28,0.48) · overlay-light rgba(23,23,28,0.24) (dropdown gợi ý)

## Chữ (Inter 400/500/600; số dùng tabular-nums)
display 24/600/1.25 -0.015em (máy tính tiêu đề trang 24, landing tới 60)
title 17/600/1.3 · section 15/600 · body 14/400/1.5 (máy tính 14–15) · label 13/500 · caption 12/500 · micro 11/600 (chỉ badge số)
giá thẻ 16–17/600 · giá trang chi tiết 24/600 accent-text · đơn vị giá 12–14/500 ink-2
input 16px (bắt buộc, chống zoom iOS)

## Khoảng cách
4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 (lề điện thoại 16; container máy tính max-width 1200, padding 0 24)

## Bo góc
6 (badge/tag) · 8 (button thường, input, stepper) · 10 (card điện thoại, khối) · 12 (card máy tính, banner, section) · 14 (dialog) · 16 (sheet trên) · 999 (pill: chip, CTA chính, badge số)

## Chiều cao
Button: lg 48 (CTA chính, pill) · md 44 (mặc định) · sm 36 (chỉ máy tính, thanh phụ). Icon button 44×44.
Input 44 (textarea 2 dòng ~64). Chip 40 (điện thoại, có vùng chạm 44) · chip trên nền brand 32. Stepper 44 (giỏ 40).
Header điện thoại 56 · header trang chủ điện thoại (H1) ~140 · header máy tính tầng chính ~76 + dải trên 40 + menu 48 · BottomNav 64 · thanh mua đáy ~72 + safe-area.

## Bóng
sm 0 1px 2px rgba(23,23,28,.12) (segmented đang chọn) · bar 0 -4px 16px rgba(23,23,28,.08) (thanh dính đáy) · pop 0 12px 32px rgba(23,23,28,.12) (dropdown, giỏ mini) · modal 0 24px 64px rgba(23,23,28,.28) (dialog máy tính)

## Chuyển động
nhấn: scale .97, 120ms cubic-bezier(.23,1,.32,1) · đổi Thêm→stepper: fade+scale .96→1, 180ms · sheet/thanh đáy: translateY(100%)→0, 240–260ms cubic-bezier(.32,.72,0,1) · toast: 200ms vào, tự ẩn 3s · màu/viền: 150ms ease-out · skeleton nhấp nháy 1.4s · reduced-motion: bỏ scale/translate, giữ đổi màu. Không transition: all.

## Focus
:focus-visible outline 2px focus, offset 2px · trên nền accent/brand: outline trắng offset -4px · input focus: viền accent + ring 3px accent-soft.

## Bổ sung (chốt khi gom bảng component, 07/10)
brand-deep-hover #0A2C59 · crit-border #F2C9C6 · good-border #BFE5CC · shadow-card-hover 0 6px 20px rgba(23,23,28,.06) + viền border-strong
QtyStepper ở mức tối thiểu: thẻ & giỏ → icon thùng rác, bấm mở Dialog xác nhận bỏ món; trang chi tiết → nút trừ disabled.
Giá trên thẻ màu ink; giá trang chi tiết & tổng tiền màu accent-text. Badge Hết hàng: surface-3/ink-2.
