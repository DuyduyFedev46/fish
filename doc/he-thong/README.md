# Tài liệu hệ thống Cá Về

> Cập nhật 11/10/2026 (rà tài liệu legacy, `doc/ops/ra-soat-tai-lieu-legacy-2026-10-11.md`).
> Bộ này mô tả hệ thống **đang chạy trong code**. Khi tài liệu cũ và code lệch nhau thì code đúng, và bộ này viết theo code.

## Đọc gì trước

| Bạn là | Đọc theo thứ tự |
|---|---|
| Người mới vào dự án | [tong-quan.md](tong-quan.md), rồi [nghiep-vu.md](nghiep-vu.md), rồi [bang-thuat-ngu.md](bang-thuat-ngu.md) |
| Dev backend | [tong-quan.md](tong-quan.md), [backend.md](backend.md), [nghiep-vu.md](nghiep-vu.md) (mục bất biến) |
| Dev ERP / Shop | [tong-quan.md](tong-quan.md), [erp-console.md](erp-console.md) hoặc [frontend.md](frontend.md) |
| PO / BA / QA | [nghiep-vu.md](nghiep-vu.md), [quy-trinh-doi.md](quy-trinh-doi.md) |

## Mục lục

| File | Nội dung |
|---|---|
| [tong-quan.md](tong-quan.md) | Hệ thống làm gì, 4 bề mặt (Shop, ERP, API, adapter), sơ đồ kiến trúc, môi trường staging và production |
| [nghiep-vu.md](nghiep-vu.md) | Luồng chính từ nhập lô tới báo cáo lãi lỗ, trạng thái chứng từ, các bất biến không được phá |
| [backend.md](backend.md) | Các Django app, model và endpoint chính, phân quyền 3 tầng và 5 nhóm, job nền, AI, lệnh quản trị, cách chạy test |
| [erp-console.md](erp-console.md) | ERP nội bộ (Next.js): cấu trúc `features/` và `shared/`, mock, build tĩnh, e2e |
| [frontend.md](frontend.md) | Shop cho khách (Next.js): trang, luồng thanh toán, mock, build tĩnh, e2e |
| [quy-trinh-doi.md](quy-trinh-doi.md) | Cách đội Claude làm việc, hồ sơ tính năng, quy ước commit và push |
| [bang-thuat-ngu.md](bang-thuat-ngu.md) | Thuật ngữ nghiệp vụ tiếng Việt và tên tương ứng trong code |

## Tài liệu gốc (nguồn sự thật, bộ này chỉ tóm tắt và trỏ tới)

| File | Dùng khi |
|---|---|
| `doc/URD.md` | Yêu cầu người dùng |
| `doc/business-process-spec.md` | Quy trình P-01 đến P-10, business rule `BR-*`, ngoại lệ, câu hỏi mở |
| `doc/decisions.md` | Quyết định đã chốt. Không tự lật |
| `doc/ke-hoach-tong.md` | Thứ tự các phase P1 đến P9 (bảng dừng ở 01/10; đợt sau đó xem hồ sơ trong `doc/features/`) |
| `doc/thuat-ngu-va-trang-thai.md` | Tên chuẩn chứng từ, trạng thái, nhãn (Duy duyệt 07/10) |
| `doc/design/shop/`, `doc/design/erp/` | Thiết kế Shop (làm lại 10/10) và ERP: luật giao diện, component, màn |
| `doc/ops/moi-truong.md` | URL, secret (tên, không có giá trị), lệnh deploy, nhật ký deploy |
| `doc/ops/go-live-phap-ly.md` | Checklist pháp lý trước khi mở bán thật |
| `doc/features/<ngày>-<slug>/` | Hồ sơ từng tính năng (phân tích, story, thiết kế kỹ thuật, ghi chú dev, báo cáo QA) |
| `.claude/skills/caveve-domain/SKILL.md` | Bản đồ nghiệp vụ và bất biến ngắn gọn cho agent |
| `DESIGN.md`, `PRODUCT.md` (gốc repo) | Hệ thiết kế giao diện, bối cảnh người dùng |

`doc/archive/` chứa tài liệu giai đoạn đầu đã lưu trữ (`BUILD-PLAN.md`, `doctype-mapping.md`…). Nhiều chỗ đã cũ, chỉ đọc để hiểu lịch sử, không dùng làm contract.

## Giữ bộ này không cũ

- Khi một lô làm đổi app, endpoint, quyền, job hay lệnh build, sửa luôn file tương ứng ở đây trong cùng commit.
- Không ghi số test cứng. Ghi lệnh để chạy test.
- Không ghi secret, mật khẩu, chuỗi kết nối DB hay dữ liệu khách thật. Repo đang công khai.
