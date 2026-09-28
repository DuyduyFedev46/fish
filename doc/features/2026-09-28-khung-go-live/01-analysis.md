# Khung go-live pháp lý trên web (footer người bán, trang chính sách, đồng ý dữ liệu cá nhân) — Phân tích nghiệp vụ
> PO (thay BA, bản ngắn) · 2026-09-28 · Nguồn: `doc/ops/go-live-phap-ly.md` · Trạng thái: **ĐÃ DUYỆT** (Duy 28/09, chốt scope qua câu hỏi)

## 1. Yêu cầu gốc và phạm vi Duy chốt (28/09)
- Làm **sau** hồ sơ `2026-09-28-cms-viet-bai`.
- **Nội dung** các trang chính sách soạn bằng CMS (loại **Trang**). Code chỉ làm **khung**:
  1. Footer thông tin người bán, **lấy từ cấu hình**, không viết cứng trong code.
  2. Link tới các trang chính sách ở footer.
  3. Ô đồng ý xử lý dữ liệu cá nhân ở checkout Shop: **bắt buộc tick**, lưu **thời điểm** và **phiên bản chính sách** đã
     đồng ý, không lưu dữ liệu cá nhân thừa.
  4. Thông báo "vựa sẽ gọi xác nhận" sau khi đặt (liên quan hồ sơ `2026-09-28-cskh-xac-nhan-in-tem`).
- Thủ tục pháp lý (thông báo website, tên miền, hồ sơ dữ liệu cá nhân…) **không phải code**: liệt kê thành checklist việc
  của Duy (§6).

## 2. Đối chiếu checklist go-live

| Mục checklist | Phần code (hồ sơ này) | Phần không phải code |
|---|---|---|
| 2 Công khai thông tin | Footer người bán (GL-01), link trang chính sách (GL-02) | Nội dung trang: `legal-vn` soạn, Duy duyệt, đăng bằng CMS |
| 3 Điều kiện giao dịch chung | Link footer (GL-02) | Nội dung trang, khớp BR-HT |
| 6 Bảo vệ dữ liệu cá nhân | Ô đồng ý ở checkout (GL-03), tra bằng chứng đồng ý (GL-05) | Chính sách quyền riêng tư, hồ sơ đánh giá tác động xử lý |
| 6b Chuyển dữ liệu ra nước ngoài | — | Hồ sơ hoặc đổi region (quyết định của Duy) |
| 9 Kênh khiếu nại | SĐT, email người bán ở footer (GL-01) | — |
| 1, 4, 5, 7, 8 | — (xem §6; HSTS ở mục 8 là việc code nhỏ, để hồ sơ khác) | Xem §6 |

## 3. Tác nhân & quyền
- **Khách** (không đăng nhập): thấy footer, đọc trang chính sách, tick đồng ý khi đặt hàng.
- **Chủ, Quản lý** (`chu`, `quan_ly`): soạn và đăng trang chính sách (quyền ND-01/02 của CMS); xem bằng chứng đồng ý của
  đơn (GL-05).
- **NV kho, NV giao:** không thấy bằng chứng đồng ý.
- **Duy / dev:** đặt giá trị thông tin người bán trong cấu hình môi trường (không có màn sửa trên console đợt này).

## 4. Business rule mới (đề xuất mã, ghi vào spec khi nghiệm thu)

| Mã | Nội dung | Nhãn |
|---|---|---|
| **BR-BH-17** | Tạo đơn trên Shop phải kèm đồng ý xử lý dữ liệu cá nhân: khách chủ động tick (không tick sẵn), gửi kèm **phiên bản** chính sách bảo mật đang có hiệu lực. Hệ thống lưu thời điểm (giờ server) và phiên bản vào đơn. Phiên bản khách gửi khác phiên bản đang hiệu lực thì từ chối, yêu cầu đồng ý lại. Không có chính sách bảo mật đã đăng thì Shop không nhận đơn (khi `PRIVACY_CONSENT_REQUIRED` bật). | D (28/09) + PA |
| **BR-ND-18** | Thông tin người bán công khai (tên, loại hình, số GCN ĐKDN/MST, địa chỉ, SĐT, email) lấy từ cấu hình môi trường, trả qua một API công khai chỉ gồm các field đó. Không viết cứng trong mã nguồn, không commit giá trị thật vào repo. | D (28/09) + NĐ 248 |
| **BR-ND-19** | Footer mọi trang công khai có link tới các trang chính sách do CMS đánh dấu hiện ở footer. | D (28/09) |

Giữ: BR-ND-16 (trang bắt buộc go-live không gỡ được, tra phiên bản có hiệu lực), bất biến 9.

## 5. Tác động dữ liệu
- **`SalesOrder`** thêm 2 field: `privacy_consent_at` (thời điểm), `privacy_policy_version` (FK tới phiên bản đã đăng của
  trang chính sách bảo mật, `PROTECT`). **Lý do:** bằng chứng đồng ý theo Luật BVDLCN 2025 (checklist mục 6) và để tra
  "khách đồng ý bản chính sách nào". **Không** phải dữ liệu cá nhân mới; **không** lưu IP, trình duyệt hay dấu vết khác
  (thu tối thiểu, bất biến 9). Đơn cũ để trống.
- Cấu hình mới (env): `SELLER_NAME`, `SELLER_BUSINESS_TYPE`, `SELLER_REG_NO`, `SELLER_TAX_CODE`, `SELLER_ADDRESS`,
  `SELLER_PHONE`, `SELLER_EMAIL`, `PRIVACY_CONSENT_REQUIRED`, `SHOP_CONFIRM_CALL_NOTICE`, `SHOP_CONFIRM_CALL_HOURS`.
  Giá trị thật chỉ đặt trên Cloud Run production. Staging dùng thông tin giả. Lưu ý: nếu Lộc đăng ký hộ kinh doanh thì
  tên và địa chỉ người bán là dữ liệu cá nhân của Lộc, pháp luật buộc công khai, nhưng **không** đưa vào repo công khai.

## 6. Checklist việc của Duy (không phải code)

| # | Việc | Căn cứ (go-live) | Chặn gì |
|---|---|---|---|
| D1 | Chốt **chủ thể pháp lý** của Lộc (doanh nghiệp hay hộ kinh doanh), có MST và số GCN đăng ký | mục 1, 7 | Giá trị cấu hình GL-01; thông báo website |
| D2 | Mua **tên miền riêng** và trỏ về Hosting (`*.web.app` không dùng để thông báo được) | mục 1 | Thông báo website |
| D3 | **Thông báo website TMĐT** với Sở Công Thương qua Hệ thống quản lý hoạt động TMĐT (xác nhận địa chỉ cổng nộp) | mục 1 | Go-live |
| D4 | Nhờ `legal-vn` soạn 4 trang: chính sách bảo mật / xử lý dữ liệu cá nhân, điều kiện giao dịch chung, đổi trả & hoàn tiền (khớp BR-HT), thông tin người bán; Duy duyệt rồi đăng bằng CMS | mục 2, 3, 6 | GL-03 trên production |
| D5 | **Hồ sơ đánh giá tác động xử lý dữ liệu cá nhân** | mục 6 | Go-live |
| D6 | **Chuyển dữ liệu ra nước ngoài** (server Singapore): lập hồ sơ, hoặc quyết định chuyển DB về region/nhà cung cấp tại Việt Nam | mục 6b | Go-live |
| D7 | Cung cấp giá trị thật cho cấu hình người bán (D1 + địa chỉ, SĐT, email nhận khiếu nại) để dev đặt vào Cloud Run production | mục 2, 9 | GL-01 trên production |
| D8 | **Backup** DB production (job `pg_dump` còn nợ trong `moi-truong.md`) để bảo đảm thời hạn lưu dữ liệu đơn | mục 4 | Go-live |
| D9 | Xác nhận với kế toán cách kê khai thuế, hoá đơn điện tử | mục 7 | — |
| D10 | Đặt lịch **báo cáo năm** trước 15/02 hằng năm | mục 5 | — |
| D11 | Duyệt việc thêm HSTS cho API (việc code nhỏ, hồ sơ riêng hoặc luồng NHANH) | mục 8 | — |

## 7. Ngoài phạm vi
- Màn cho Chủ tự sửa thông tin người bán trên console (đợt này sửa bằng cấu hình).
- Quyền của khách xem, sửa, xoá dữ liệu (ẩn danh hoá): hồ sơ riêng.
- Banner cookie: chưa có cookie theo dõi hay analytics nên chưa cần.
- Đường dẫn đẹp cho trang chính sách (`/chinh-sach-bao-mat`): để sau cùng SEO của CMS.

## 8. Câu hỏi mở
| # | Câu hỏi | Mặc định PO |
|---|---|---|
| G1 | Chưa có chính sách bảo mật đã đăng thì Shop có nhận đơn không? | **Không nhận** khi `PRIVACY_CONSENT_REQUIRED=true` (mặc định true ở production và staging, chỉ tắt trong test/dev). Nghĩa là trước khi bật API production phải đăng trang chính sách. |
| G2 | Hiện thông báo "vựa sẽ gọi xác nhận" từ khi nào? | Cờ `SHOP_CONFIRM_CALL_NOTICE`, mặc định **tắt**; bật khi hồ sơ CSKH đi vào vận hành. |
