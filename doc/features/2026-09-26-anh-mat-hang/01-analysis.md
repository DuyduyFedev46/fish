# Ảnh mặt hàng trên Shop — Phân tích nghiệp vụ
> BA · 2026-09-26 · Trạng thái: ĐÃ DUYỆT (2026-09-26, Duy) — gộp vào S38 (Đợt 3)

## 1. Yêu cầu gốc
"hình như mấy cái mặt hàng thiếu hình ảnh rồi, ko có ảnh ko show đc cho KH" (Duy, PO, 2026-09-26).

**Làm rõ hiện trạng.** Mặt hàng không phải "bị mất" ảnh: hệ thống **chưa từng có** chỗ lưu ảnh.
- `Item` (`backend/apps/catalog/models/items.py`) không có trường ảnh. Chỉ có `code`, `name`, `item_group`, `item_type`, `shelf_life_in_days`, `is_active`, `description`.
- Shop API công khai (`backend/apps/catalog/items/shop_api.py`, `_item_public`) chỉ trả mã, tên, nhóm, loại, đơn vị, giá, tồn khả dụng. Trường `description` cũng **không** được trả ra Shop.
- `requirements` không có thư viện xử lý ảnh hay kho lưu trữ ngoài. `settings` không có cấu hình MEDIA hay GCS.
- Shop (`frontend/`, Next.js static export trên Firebase `cangca-loc`) không hiển thị ảnh ở lưới danh mục (`CatalogGrid.tsx`), trang chi tiết (`app/shop/item/page.tsx`), giỏ/checkout hay tra cứu đơn (`OrderLookup.tsx`). `next.config` đặt `images.unoptimized: true`, tức Next không tự resize ảnh.
- Production chạy Cloud Run (đĩa tạm, mất khi restart), nên **không lưu được file upload trên container**. Project `keolai-63ec1` đã có Cloud Storage.
- `.gitignore` chặn cả `*.png *.jpg *.jpeg *.webp *.gif *.svg *.ico` (Duy yêu cầu 2026-09-25). Vì vậy ảnh sản phẩm, **kể cả ảnh mặc định (placeholder)**, không được nằm trong repo.
- Story S38 (Đợt 3, `doc/features/2026-09-24-erp-console-noi-that/02-stories.md`) đã có chữ "ảnh" trong câu story, nhưng **không có AC nào về ảnh**. Hiện chưa ai phân tích phần này.

## 2. Tóm tắt
**Chủ vựa** (có thể thêm Quản lý) cần **gắn ảnh cho từng mặt hàng và combo** để **khách trên Shop nhìn thấy hàng thật trước khi đặt và trả tiền trước qua VietQR**. Mô hình B2C, khách không tài khoản, trả trước (URD §5, §6.8), nên ảnh là yếu tố tạo niềm tin chính.

## 3. Bối cảnh trong hệ thống
- **Quy trình:** P-01 Danh mục, giá, combo (actor chính: Chủ). P-05 Bán hàng Shop, chỉ phần hiển thị, không đổi luồng đặt/giữ chỗ/thanh toán.
- **Rule hiện có liên quan:**
  - BR-DM-04/05/06: combo là `Item` loại BUNDLE, có giá riêng, tồn được tính ra từ thành phần.
  - BR-DM-07: sửa công thức không hồi tố lên đơn. Cách làm tương tự cho ảnh, xem BR-DM-13 bên dưới.
  - BR-PQ-10: không xoá chứng từ. Ảnh là thuộc tính của master data, không phải chứng từ.
  - BR-PQ-04: AuditLog bắt buộc cho quyền Tầng 2.
  - BR-PQ-12/13: kiểm soát quyền ở API, không ở giao diện.
  - spec §1.4: `Item` CRUD chỉ `chu`; `quan_ly`, `nv_kho` chỉ R; `nv_giao` không có quyền.
- **Quyết định ràng buộc:**
  - decisions.md 2026-09-10 (Social): đăng bài tay, dẫn link vào Shop. Link Shop sẽ được chia sẻ trên Facebook/Zalo nên ảnh xem trước khi chia sẻ link có giá trị, nhưng xem §9.
  - decisions.md (Hướng kiến trúc): ưu tiên Django Admin cho back-office trước khi tự làm CRUD.
  - Quy ước Duy 2026-09-25: không đưa ảnh lên git.
  - URD §6.8: Landing và Shop tách biệt.
- **Liên quan hồ sơ khác:** UC-22 / S38 (Đợt 3, lô L18) của `2026-09-24-erp-console-noi-that`. Ghi chú N-14 ở đó: NV kho thấy menu Danh mục.

## 4. Tác nhân & quyền
| Tác nhân | Group | Làm được gì với ảnh | Quyền cần |
|---|---|---|---|
| Chủ (Lộc) | `chu` | Thêm, thay, xoá ảnh; đặt ảnh đại diện; sửa alt text | `catalog.change_item` (Tầng 1, đã có). Có tách quyền riêng hay không thì xem Q3 |
| Quản lý | `quan_ly` | Mặc định PA: **chỉ xem**, giống spec §1.4. Có thể được uỷ (Q3) | Nếu uỷ, cần một quyền Tầng 2 mới, không mở `change_item`, vì `change_item` còn cho sửa tên, hạn dùng, ẩn/hiện |
| NV kho | `nv_kho` | Xem ảnh trong console (danh mục, chi tiết đơn) | `catalog.view_item` (đã có) |
| NV giao | `nv_giao` | Xem ảnh thu nhỏ trên dòng hàng của phiếu giao được gán (🟢, để sau) | Theo scope phiếu giao hiện có |
| Khách | (không đăng nhập) | Xem ảnh trên Shop | Công khai, không cần quyền |
| Hệ thống | — | Tạo các cỡ ảnh; dùng ảnh mặc định khi thiếu | — |

**Lập luận về ranh giới (PA).** Đổi ảnh không làm tiền rời túi và không đổi con số lời lỗ. Theo đường ranh spec §1.5, việc này *có thể* uỷ cho Quản lý. Ngược lại, đây là **thay đổi công khai trước mặt khách**: một ảnh sai hoặc phản cảm hiện ngay trên Shop. Mặc định an toàn là chỉ Chủ làm, cho tới khi Duy chọn (Q3).

## 5. Use case

### UC-A1 Thêm / thay ảnh cho mặt hàng (kể cả combo)
- **Tiền điều kiện:** người dùng có quyền sửa ảnh (UC-A1 mặc định là Chủ). Mặt hàng tồn tại. Có thể đang ẩn (`is_active=False`), vì cho phép chuẩn bị ảnh trước khi mở bán.
- **Luồng chính:**
  1. Mở mặt hàng. Giai đoạn đầu mở qua Django Admin, sau đó qua console S38 (Q4).
  2. Chọn tệp ảnh từ điện thoại hoặc máy tính.
  3. Hệ thống kiểm tra: đúng loại ảnh cho phép, không vượt dung lượng tối đa, nội dung thật sự là ảnh (không chỉ tin đuôi file) (BR-DM-10).
  4. Hệ thống gỡ metadata (vị trí GPS, thông tin máy) và tạo các cỡ hiển thị cho lưới, trang chi tiết và ảnh thu nhỏ (BR-DM-10).
  5. Người dùng nhập alt text. Để trống thì mặc định bằng tên mặt hàng (BR-DM-11).
  6. Nếu mặt hàng chưa có ảnh đại diện, ảnh này tự thành ảnh đại diện (BR-DM-09).
  7. Lưu. Hệ thống ghi AuditLog `item_image_add` hoặc `item_image_replace`, gồm ai, khi nào, mặt hàng, ảnh trước → sau (BR-DM-12).
  8. Shop hiển thị ảnh mới trong thời gian tối đa X phút (Q9, mặc định: ngay khi tải lại trang).
- **Luồng thay thế:**
  - 2a. Nhiều ảnh (nếu Q2 chọn nhiều ảnh): chọn nhiều tệp một lần; người dùng sắp thứ tự và chọn ảnh đại diện.
  - 6a. Đã có ảnh đại diện: người dùng chọn "đặt làm ảnh đại diện" cho ảnh mới, hoặc giữ ảnh cũ.
- **Ngoại lệ:**
  - E1. Sai định dạng (SVG, GIF động, PDF, file đổi đuôi, HEIC nếu không hỗ trợ): từ chối với thông điệp tiếng Việt kèm mã BR-DM-10. Không lưu gì.
  - E2. Vượt dung lượng: từ chối, báo giới hạn cụ thể.
  - E3. Ảnh quá nhỏ (dưới cạnh tối thiểu): từ chối, hoặc chỉ cảnh báo "ảnh sẽ bị mờ" (Q6).
  - E4. Mất mạng hoặc tải lên nửa chừng (Lộc hay dùng 4G ở cảng/kho): không để lại ảnh hỏng trên Shop. Mặt hàng giữ nguyên ảnh cũ. Không ghi AuditLog.
  - E5. Kho lưu trữ ngoài lỗi hoặc hết hạn mức: từ chối, báo "chưa lưu được ảnh, thử lại". Shop vẫn hiện ảnh cũ.
  - E6. Hai người sửa ảnh cùng một mặt hàng cùng lúc (nếu Quản lý được uỷ): người lưu sau không được âm thầm ghi đè thứ tự hoặc ảnh đại diện của người trước. Theo cơ chế khoá sửa chung đã có ở nền console.
  - E7. Người không có quyền gọi API upload: 403. Kiểm ở API, không chỉ ẩn nút (BR-PQ-12).
- **Hậu điều kiện:** mặt hàng có ảnh đại diện hợp lệ ở các cỡ hiển thị. AuditLog có 1 dòng. Không đụng tồn, lô, giá, đơn.

### UC-A2 Xoá ảnh / gỡ ảnh đại diện
- **Tiền điều kiện:** như UC-A1, và mặt hàng có ít nhất 1 ảnh.
- **Luồng chính:**
  1. Chọn ảnh, bấm "Gỡ ảnh" và xác nhận.
  2. Nếu đó là ảnh đại diện và còn ảnh khác, ảnh kế tiếp theo thứ tự thành ảnh đại diện.
  3. Nếu không còn ảnh nào, Shop hiện ảnh mặc định (BR-DM-09).
  4. Ghi AuditLog `item_image_remove` (BR-DM-12).
- **Ngoại lệ:**
  - E1. Mặt hàng đang bán (có lô Đang bán): vẫn cho gỡ, nhưng cảnh báo "Khách sẽ thấy ảnh mặc định".
  - E2. Người không có quyền: 403.
- **Hậu điều kiện:** ảnh không còn hiện trên Shop. File gốc được giữ hay dọn thì theo BR-DM-14.

### UC-A3 Khách xem ảnh trên Shop
- **Tiền điều kiện:** mặt hàng `is_active` và có giá niêm yết hiệu lực. Đây là điều kiện đang có ở `ShopCatalogView`, **ảnh không phải điều kiện hiển thị** (BR-DM-09).
- **Luồng chính:**
  1. Lưới danh mục (`CatalogGrid`): ảnh đại diện cỡ nhỏ, tỉ lệ thống nhất (mặc định vuông 1:1), tải lười (lazy load).
  2. Trang chi tiết: ảnh đại diện cỡ lớn. Nếu có nhiều ảnh thì có thể lướt xem. Combo hiện ảnh của combo; danh sách thành phần có thể kèm ảnh thu nhỏ (🟢).
  3. Giỏ / checkout: ảnh thu nhỏ trên từng dòng.
  4. Tra cứu đơn: ảnh thu nhỏ trên dòng hàng. Đây là ảnh **hiện hành**, không phải ảnh lúc đặt (BR-DM-13).
- **Luồng thay thế:**
  - 1a. Mặt hàng chưa có ảnh: hiện ảnh mặc định trung tính (logo hoặc biểu tượng theo nhóm hàng) kèm alt text là tên hàng. Không được để khung vỡ hoặc trống.
- **Ngoại lệ:**
  - E1. URL ảnh lỗi (bị xoá, kho lưu trữ gián đoạn): trình duyệt hiện ảnh mặc định. Trang và nút đặt hàng vẫn dùng được.
  - E2. Mạng 3G yếu: ảnh không được làm chậm hiển thị giá và tồn. Tổng dung lượng ảnh trên lưới có trần (Q7).
- **Hậu điều kiện:** không có. Chỉ đọc.

### UC-A4 Nhân viên xem ảnh trong ERP console
- **Tiền điều kiện:** có `catalog.view_item` (danh mục) hoặc quyền xem đơn / phiếu giao.
- **Luồng chính:** ảnh thu nhỏ trong danh sách mặt hàng (S38) và trong dòng hàng của chi tiết đơn / phiếu soạn. Mục đích là giúp NV kho soạn đúng hàng.
- **Ngoại lệ:** giống UC-A3 E1.
- **Hậu điều kiện:** không có.
- **Ghi chú:** 🟢. Màn danh mục trong console chưa có (Đợt 3). Ảnh trong chi tiết đơn là tiện ích, không chặn.

### UC-A5 Nhập ảnh ban đầu cho toàn bộ danh mục (lần đầu)
- **Tiền điều kiện:** có danh sách mặt hàng đang bán và bộ ảnh (Lộc chụp, hoặc ảnh minh hoạ có quyền dùng, Q8).
- **Luồng chính:** Chủ, hoặc người Duy chỉ định, gắn ảnh lần lượt theo UC-A1. Hệ thống có danh sách "**mặt hàng đang bán mà chưa có ảnh**" để biết còn thiếu mặt hàng nào.
- **Ngoại lệ:** ảnh minh hoạ không rõ nguồn hoặc bản quyền: không dùng (Q8).
- **Hậu điều kiện:** mọi mặt hàng hiện trên Shop đều có ảnh, hoặc được chấp nhận dùng ảnh mặc định.

## 6. Business rule
| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| **BR-DM-09** | Mỗi mặt hàng (SIMPLE và BUNDLE) có **tối đa N ảnh**, trong đó đúng **1 ảnh đại diện** khi có ít nhất 1 ảnh. **Thiếu ảnh không chặn bán**: Shop dùng ảnh mặc định. Combo có ảnh riêng, không tự lấy ảnh thành phần. | PA (N chờ Q2) | Mới |
| **BR-DM-10** | Chỉ nhận ảnh raster **JPEG / PNG / WebP** (HEIC tuỳ Q5). **Cấm SVG** (có thể chứa script), GIF động, PDF. Kiểm nội dung thật, không tin đuôi file. Dung lượng tệp gốc ≤ **10 MB** (tham số cấu hình, không hard-code). Hệ thống **gỡ metadata EXIF/GPS**, và **chỉ phát ra Shop các cỡ đã xử lý**, không phát tệp gốc. | PA | Mới |
| **BR-DM-11** | Mỗi ảnh có **alt text tiếng Việt**, mặc định bằng tên mặt hàng. Dùng cho người đọc màn hình và SEO. | PA | Mới |
| **BR-DM-12** | Thêm, thay, gỡ ảnh và đổi ảnh đại diện **ghi AuditLog** (ai, khi nào, mặt hàng, trước → sau). Lý do: đây là thay đổi hiển thị công khai. Rule này mở rộng BR-PQ-04, vốn chỉ bắt buộc cho quyền Tầng 2. | PA | Mới |
| **BR-DM-13** | Ảnh **không đóng băng theo đơn**: tra cứu đơn cũ hiện ảnh hiện hành. Khác với giá và công thức (BR-BH-08, BR-DM-07). Lý do: ảnh không phải dữ liệu tiền. Việc này khớp hiện trạng, vì dòng đơn cũng không lưu bản chụp tên hàng mà trỏ thẳng về `Item`. | PA | Mới |
| **BR-DM-14** | Ảnh bị thay hoặc gỡ **không xoá cứng ngay**: file giữ lại **30 ngày** (tham số) để khôi phục và đối chiếu AuditLog, sau đó được dọn. Ảnh **không phải chứng từ** nên không áp BR-PQ-10. | PA | Mới |
| **BR-DM-15** | Ảnh công khai **không được lộ thông tin giá mua hay nhà cung cấp** (bảng giá tại cảng, hoá đơn, tên đầu mối trong khung hình). Đây là quy tắc vận hành / hướng dẫn chụp, máy không kiểm được. | PA | Mới |
| **BR-DM-16** | Ảnh và asset **không nằm trong repo git và không nằm trên đĩa container**. Chúng nằm ở kho lưu trữ ngoài bền vững. Ảnh mặc định cũng theo quy ước này (hoặc vẽ bằng CSS/icon, không phải tệp ảnh). | D (quy ước 2026-09-25) + ràng buộc hạ tầng | Mới |
| BR-PQ-10 | Master data chưa có giao dịch mới được xoá. Không đổi. | D | Giữ |
| spec §1.4 | `Item` CRUD chỉ `chu`. Có thể sửa nếu Q3 chọn uỷ ảnh cho Quản lý. | PA | Giữ (chờ Q3) |

## 7. Tác động dữ liệu & tích hợp
Mô tả *cái gì*, không thiết kế chi tiết.
- **Dữ liệu:** cần lưu cho mỗi mặt hàng một hoặc nhiều ảnh, gồm vị trí file ở kho ngoài, thứ tự, cờ ảnh đại diện, alt text, người và thời điểm tải lên. Chọn 1 ảnh hay nhiều ảnh (Q2) quyết định cần **thêm field vào `Item`** hay **thêm model con**. Cả hai đều là thay đổi schema, cần migration và phải nêu lý do (bất biến 8). Nếu chưa chắc, chọn cấu trúc cho phép nhiều ảnh ngay từ đầu, dù giao diện chỉ dùng 1 ảnh, để sau này đổi ý khỏi phải làm lại migration dữ liệu. Đây là ghi chú PA cho BE quyết định.
- **Backend:** thư viện xử lý ảnh và thư viện kho lưu trữ là **phụ thuộc mới** (BE chọn). Cấu hình bucket và thông tin xác thực đọc từ env (bất biến 7). Môi trường dev/test phải chạy được **không cần GCS thật**.
- **Shop API:** `ShopCatalogView` và `ShopItemDetailView` cần trả thêm URL ảnh (các cỡ) và alt text. **Không được lộ** đường dẫn tệp gốc hay metadata nội bộ.
- **Shop FE:** lưới danh mục, trang chi tiết, giỏ/checkout, tra cứu đơn. Chế độ mock (`NEXT_PUBLIC_USE_MOCK=1`) cần dữ liệu ảnh giả **không nằm trong repo**, ví dụ khung CSS.
- **Admin / console:** giai đoạn đầu dùng Django Admin để upload (theo hướng "ưu tiên Admin"). S38 thêm AC upload và xem ảnh trên console.
- **Bên ngoài:** Cloud Storage trong project `keolai-63ec1` (đã có). Có thể thêm CDN. Firebase Storage là phương án khác (Q1).
- **Chi phí (ước lượng thô, cần kiểm lại bảng giá GCP hiện hành):** vựa quy mô 1 điểm bán, vài chục mặt hàng × vài ảnh × 3 cỡ là dưới 1 GB lưu trữ, nên chi phí lưu trữ không đáng kể. Khoản đáng để ý là **băng thông ra internet**, tăng theo lượt xem Shop. Nén ảnh (WebP, cỡ nhỏ cho lưới) là biện pháp chính để kìm khoản này. Cần Duy đặt trần ngân sách / cảnh báo billing (Q1).

## 8. Rủi ro Cá Về
| Mảng | Rủi ro | Mức |
|---|---|---|
| **Giá vốn** | Không rò qua API vì ảnh không chứa field giá. **Có thể rò qua nội dung ảnh**: ảnh chụp tại cảng lọt bảng giá, hoá đơn NCC hoặc tên đầu mối (BR-DM-15). Đây là rủi ro lớn nhất riêng của Cá Về: giá mua tại cảng là lợi thế đàm phán (spec §1.7). | Trung bình |
| **Riêng tư / bảo mật** | EXIF GPS trong ảnh điện thoại lộ vị trí kho hoặc nhà Lộc. Upload SVG hoặc file giả ảnh có thể chạy script (XSS) trên domain công khai. Bucket đọc công khai mà cấu hình sai (cho ghi hoặc cho liệt kê) thì ai cũng tải hoặc ghi đè được. | Cao nếu bỏ qua BR-DM-10 |
| **Phân quyền** | Upload qua API mà chỉ ẩn nút ở console thì NV kho cũng gọi được (BR-PQ-12). Nếu uỷ Quản lý bằng cách mở `change_item`, Quản lý sẽ sửa được cả tên, hạn dùng, ẩn/hiện. | Trung bình |
| **AuditLog** | Hiện chưa có AuditLog nào cho catalog (grep `apps/catalog` không thấy). Ảnh là thay đổi công khai đầu tiên của catalog được ghi log (BR-DM-12). | Thấp |
| **Kỳ vọng khách / khiếu nại** | Ảnh minh hoạ đẹp hơn hàng đông lạnh thật dẫn tới khách từ chối nhận hàng. Lúc đó rơi vào P-08 giao thất bại và P-07 hoàn tiền, tức **tiền rời túi**. Nên có nhãn "Ảnh minh hoạ" khi không phải ảnh thật (Q8). | Trung bình |
| **Vận hành / hạ tầng** | Lưu nhầm lên đĩa Cloud Run thì ảnh mất sau mỗi lần deploy hoặc restart. Ảnh nặng làm Shop chậm trên 3G và tăng chi phí băng thông. | Cao nếu làm sai, dễ tránh |
| **FEFO / tồn / tiền** | Không ảnh hưởng: ảnh không đụng lô, tồn, giữ chỗ, giá. | — |
| **Chứng từ** | Không ảnh hưởng: ảnh là thuộc tính master data, không phải chứng từ (BR-DM-13/14). | — |

## 9. Ngoài phạm vi
- Ảnh theo **lô** (ảnh thực tế từng mẻ hàng về). Có thể hữu ích để chứng minh độ tươi, nhưng là tính năng khác.
- Video, ảnh 360°, phóng to kiểu kính lúp.
- Tự động nhận diện hoặc kiểm duyệt nội dung ảnh bằng AI; tự sinh alt text.
- **Ảnh xem trước khi chia sẻ link lên Facebook/Zalo theo từng mặt hàng (og:image).** Shop là static export và trang chi tiết dùng query `?code=`, nên thẻ meta khó đổi theo từng mặt hàng. Muốn có thì cần quyết định kiến trúc riêng. Mặc định chỉ có og:image chung cho Shop/Landing (🟢).
- Ảnh cho Landing (giới thiệu vựa), banner khuyến mãi.
- Hiển thị `description` của mặt hàng trên Shop. Field này có nhưng chưa trả ra; có thể tách thành yêu cầu riêng (xem Q11).
- Đóng băng ảnh theo đơn (BR-DM-13).

## 10. Câu hỏi mở
| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q1 | 🔴 | **Nơi lưu và ngân sách:** dùng Cloud Storage bucket trong `keolai-63ec1` (đọc công khai, có thể thêm CDN), hay Firebase Storage? Trần chi phí mỗi tháng cho ảnh là bao nhiêu, có cần bật cảnh báo billing không? | GCS bucket riêng cho ảnh sản phẩm, cùng region `asia-southeast1`. Công khai **chỉ đọc từng object**, không cho liệt kê hay ghi. Chưa cần CDN ở giai đoạn đầu. Bật cảnh báo billing ở mức nhỏ |
| Q2 | 🔴 | **Mỗi mặt hàng 1 ảnh đại diện hay nhiều ảnh?** Nếu nhiều thì tối đa mấy ảnh? | Lưu được tối đa **5 ảnh**. Đợt đầu Shop chỉ hiện **1 ảnh đại diện**; lướt nhiều ảnh ở trang chi tiết làm sau |
| Q3 | 🔴 | **Ai được upload / thay ảnh:** chỉ Chủ, hay uỷ cả Quản lý? Nếu uỷ Quản lý thì dùng quyền riêng chỉ cho ảnh, không cho sửa tên, hạn dùng, ẩn/hiện? | Chỉ Chủ (spec §1.4). Nếu uỷ thì dùng **quyền Tầng 2 riêng cho ảnh**, ghi AuditLog |
| Q4 | 🔴 | **Làm trước Đợt 3 hay gộp vào S38?** | **Tách làm ngay**, độc lập với Đợt 3: kho lưu trữ, dữ liệu ảnh, upload qua **Django Admin**, Shop API trả ảnh, Shop hiển thị ảnh. Lý do: Shop hiện không có ảnh nào, và Admin đã là nơi Chủ quản lý danh mục. S38 chỉ bổ sung AC "upload/xem ảnh trên console" sau |
| Q5 | 🟡 | Có nhận ảnh **HEIC** (mặc định của iPhone) không? | Không bắt buộc. Trình duyệt iOS thường tự đổi sang JPEG khi chọn từ thư viện ảnh; FE/BE kiểm chứng trên máy thật. Nếu không được thì báo lỗi rõ ràng (BR-DM-10 E1) |
| Q6 | 🟡 | Kích thước và tỉ lệ: ảnh quá nhỏ thì chặn hay cảnh báo? Cắt vuông 1:1 hay giữ tỉ lệ gốc? | Tỉ lệ **1:1** cắt giữa để lưới đều. Cạnh ngắn **< 600 px** thì cảnh báo, không chặn. Tệp gốc ≤ 10 MB |
| Q7 | 🟡 | Cần mấy cỡ ảnh, định dạng xuất gì? | 3 cỡ: thu nhỏ (~160 px, cho giỏ/đơn), lưới (~480 px), chi tiết (~1200 px). Xuất **WebP**, có JPEG dự phòng nếu FE cần. Mỗi ảnh lưới khoảng dưới 60 KB |
| Q8 | 🟡 | **Ảnh thật do Lộc chụp hay tạm dùng ảnh minh hoạ?** Nếu minh hoạ thì lấy nguồn nào, có ghi nhãn "Ảnh minh hoạ" không? | Ưu tiên ảnh Lộc chụp. Ảnh minh hoạ chỉ dùng nguồn có quyền sử dụng rõ ràng và **bắt buộc có nhãn "Ảnh minh hoạ"** trên Shop. Thiếu ảnh thì dùng ảnh mặc định, không lấy ảnh mạng không rõ nguồn |
| Q9 | 🟡 | Ảnh mới cần hiện trên Shop sau bao lâu? | Hiện khi khách tải lại trang. Thay ảnh thì dùng URL mới, không ghi đè URL cũ, để khỏi bị cache cũ |
| Q10 | 🟡 | Ảnh mặc định khi thiếu: logo Cá Về hay biểu tượng theo nhóm hàng (cá/tôm/mực/cua)? | Một ảnh trung tính có logo, vẽ bằng CSS/icon hoặc đặt ở bucket (không vào git, BR-DM-16) |
| Q11 | 🟢 | Có muốn hiện luôn `description` của mặt hàng trên trang chi tiết Shop không? (field đã có, chưa trả ra) | Để yêu cầu riêng |
| Q12 | 🟢 | Ảnh thu nhỏ trong chi tiết đơn / phiếu soạn của console để NV kho soạn đúng hàng? | Làm khi tới S38 hoặc khi làm chi tiết đơn |
| Q13 | 🟢 | Ảnh xem trước khi chia sẻ link lên Facebook/Zalo theo từng mặt hàng (og:image)? | Để sau; hiện chỉ dùng og:image chung (xem §9) |
| Q14 | 🟢 | Có cần báo cáo hay cảnh báo "mặt hàng đang bán chưa có ảnh" trên Tổng quan không? | Chỉ cần bộ lọc trong danh sách mặt hàng (UC-A5) |

---
## Quyết định của Duy (2026-09-26)
| # | Quyết định |
|---|---|
| Q1 | Lưu ảnh ở **GCS bucket riêng tại `asia-southeast1`** trong project `keolai-63ec1`. Mỗi ảnh công khai ở chế độ chỉ đọc; không cho liệt kê, không cho ghi. Chưa dùng CDN. Bật cảnh báo billing ở mức nhỏ. |
| Q2 | Mỗi mặt hàng **chỉ 1 ảnh**. |
| Q3 | **Chủ và Quản lý** được tải lên hoặc thay ảnh, bằng **quyền Tầng 2 riêng chỉ dành cho ảnh**. Quyền này không cho sửa tên, hạn dùng, giá hay trạng thái ẩn/hiện. |
| Q4 | **Gộp vào S38 (Đợt 3).** Đợt này chưa làm. |
| Q5–Q10 | Áp dụng các mặc định 🟡 BA đã đề xuất: cắt vuông 1:1, 3 cỡ ảnh WebP, gỡ EXIF/GPS, không nhận SVG, ảnh mặc định không nằm trong git, ảnh minh hoạ phải gắn nhãn, thay ảnh thì dùng URL mới. |
