# CMS viết bài (bài viết + trang nội dung trên web công khai) — Phân tích nghiệp vụ
> BA · 2026-09-28 · Trạng thái: **CHỜ DUYỆT**

## 1. Yêu cầu gốc

> "thêm CMS để viết bài nha"

Nguồn: Duy (PO), 2026-09-28. Duy trả lời trước các câu làm rõ:
- **Loại bài:** "ko quan tâm lắm, mình có nền tảng họ thích tạo bài gì kệ họ". Vì vậy đây là CMS chung, không khoá
  vào một loại nội dung (công thức nấu, tin mùa vụ, giới thiệu hàng, chính sách…).
- **Ai viết, ai đăng:** Duy không có ưu tiên. BA đề xuất mặc định, quyền gán qua vai trò (hồ sơ
  `2026-09-28-vai-tro-tu-dinh-nghia`). Duy vừa nói thêm là màn phân quyền vai trò **chỉ cần chọn CRUD**.
- **AI hỗ trợ viết:** "Chưa, chỉ viết tay".

## 2. Tóm tắt

**Chủ và người được Chủ giao quyền** cần **soạn, đăng, sửa và gỡ bài viết có ảnh trên web công khai của Cá Về,
kèm nút dẫn sang mua đúng mặt hàng trên Shop**, để **có nội dung kéo khách từ Google và từ link chia sẻ trên
Facebook/Zalo về Shop**, và để **tự cập nhật các trang chính sách bắt buộc trước go-live** mà không phải nhờ dev sửa
code.

## 3. Bối cảnh trong hệ thống

- **Quy trình:** không thuộc P-01…P-10. Đây là mảng mới, nằm ở mặt tiền **Landing** (URD §6.8: "trang giới thiệu, tối
  ưu SEO, không có giao dịch"). Đề xuất đặt tên **P-11 Nội dung** và nhóm rule mới **BR-ND** (PA). Gián tiếp đụng:
  P-01 (liên kết mặt hàng và ảnh), P-05 (khách đi từ bài sang Shop), §1 Phân quyền.
- **Rule hiện có liên quan:** BR-PQ-04/05 (AuditLog), BR-PQ-10 (không xoá chứng từ; bài **không** phải chứng từ),
  BR-PQ-12/13 (chặn ở API), BR-DM-09…16 (ảnh mặt hàng: kiểm định dạng, gỡ EXIF, không để ảnh trong git, không lộ giá
  mua trong ảnh), bất biến 1 (giá vốn), bất biến 9 (dữ liệu cá nhân).
- **Quyết định ràng buộc:**
  - URD §6.8, decisions "Bối cảnh dự án": **Landing (SEO) và Shop (giao dịch) tách nhau.** Bài viết thuộc phía
    Landing: không có giỏ hàng hay thanh toán trong bài, chỉ có nút dẫn sang Shop.
  - decisions 2026-09-10 (Social): đăng tay trên từng nền tảng, không tích hợp API. Đo hiệu quả bằng UTM trên link
    Shop. CMS **không** tự đăng bài lên Facebook/Zalo/TikTok. Link bài được dán tay lên social.
  - decisions 2026-09-09 (kiến trúc): Django là lõi, ưu tiên công cụ có sẵn, một người maintain được.
  - Quy ước Duy 2026-09-25: không có tệp ảnh trong git (BR-DM-16).
  - Hồ sơ AI `2026-09-28-ai-digital-worker/02b-tech-design.md` §0: mọi feature mới có API thì tự thành lệnh AI, lệnh
    ghi mặc định mức C (nháp chờ duyệt). Xem §7.6.
  - Hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` (CHỜ DUYỆT): quyền cấp qua "quyền tính năng", Duy vừa nói chỉ cần chọn
    CRUD. Xem §4.

### 3.1 Hiện trạng code (kiểm tra 2026-09-28)

| Chỗ | Hiện trạng | Hệ quả cho CMS |
|---|---|---|
| `frontend/next.config.mjs` | `output: "export"`: **static export**, Firebase Hosting `cangca-loc`, không có server khi chạy. `images.unoptimized: true` | Mỗi trang bài muốn có HTML và thẻ meta riêng thì phải được **dựng lúc build**. Bài đăng sau lần build cuối sẽ không có trang tĩnh. |
| `frontend/app/shop/item/page.tsx` | Trang chi tiết dùng `/shop/item?code=X` và tải dữ liệu phía trình duyệt, vì static export không dựng được mã chưa biết lúc build | Nếu CMS làm theo cùng mẫu (`/bai-viet?slug=…`) thì Google chỉ thấy khung rỗng lúc đầu. **Facebook và Zalo không chạy JS**, nên ảnh xem trước khi chia sẻ link luôn là ảnh chung. Hồ sơ ảnh mặt hàng đã gặp đúng giới hạn này (§9 bên đó). |
| `frontend/app/page.tsx` | Landing một trang, `metadata` tĩnh, `openGraph` chung, **không có `og:image`** | Chưa có hạ tầng SEO nào khác. |
| `frontend/` | **Không có** `sitemap`, `robots.txt`, trang chính sách, footer thông tin người bán, analytics hay pixel | Sitemap và robots là việc mới. UTM hiện **không ai đọc** vì Shop chưa có analytics (§7.4). |
| `frontend/firebase.json` + `doc/ops/moi-truong.md` | Build và deploy **chạy tay trên máy dev** (`npm run build` rồi `firebase deploy`), không có CI (`.github/workflows` không có). Staging `cangca-loc-staging.web.app` và production `cangca-loc.web.app` | Phương án "build lại mỗi khi đăng bài" cần thêm một đường build/deploy tự động. Hiện chưa có. |
| `doc/ops/moi-truong.md` | **Production API đang tắt** (chế độ tiết kiệm từ 27/09), Shop production mở trang nhưng không gọi được API | Bài tải dữ liệu lúc chạy sẽ trắng trên production chừng nào API còn tắt. Bài tĩnh dựng sẵn thì vẫn đọc được. |
| `backend/apps/catalog/images/` | Ảnh mặt hàng: kiểm định dạng thật, gỡ EXIF/GPS, **cắt vuông 1:1**, 3 cỡ WebP, kho `local`/`gcs`, bucket riêng staging/production, không xoá object cũ | Dùng lại được kiểm định dạng, gỡ EXIF, kho lưu, bucket. **Không dùng lại được cắt vuông**: ảnh bài và ảnh bìa cần giữ tỉ lệ (ảnh chia sẻ chuẩn khoảng 1,91:1). Quan hệ đang là 1 ảnh / 1 mặt hàng (`ItemImage` 1-1), còn bài cần nhiều ảnh. |
| `backend/apps/catalog/admin.py` | Django Admin có đăng ký catalog | Admin chỉ dùng làm đường cứu hộ (S41-AC8). Không có trình soạn văn bản giàu định dạng. |
| `erp-console/package.json` | Chỉ có `next`, `react`, `react-dom` | Trình soạn là **phụ thuộc mới** (Tech Lead chọn). |
| `accounts.AuditLog` | Có `action`, `changes` (JSON) | Dùng được cho hành động đăng, gỡ, khôi phục. |
| `doc/ops/go-live-phap-ly.md` mục 2, 3, 6 | Chưa có trang chính sách bảo mật, điều kiện giao dịch chung, đổi trả hoàn tiền, thông tin người bán | CMS có loại **Trang** để soạn các trang này (UC-ND-07). |
| Tên miền | Chỉ có `*.web.app`. Checklist go-live mục 1 ghi `*.web.app` không phù hợp để thông báo website | SEO trên `*.web.app` rồi chuyển tên miền sau sẽ mất thứ hạng nếu không có chuyển hướng 301 (R6). |

## 4. Tác nhân & quyền

Duy chốt màn vai trò chỉ chọn CRUD. BA đề xuất hai dòng quyền tính năng trên màn đó, đều là ô CRUD (PA, 🟡 Q3):

| Quyền tính năng (PA) | C | R | U | D | Mức (theo hồ sơ vai trò) |
|---|---|---|---|---|---|
| **ND-01 Bài viết & trang (soạn)** | tạo nháp | xem mọi bài kể cả nháp | sửa nháp, sửa bản đang soạn của bài đã đăng | xoá **nháp chưa từng đăng** | T |
| **ND-02 Đăng bài** | đăng lần đầu | (theo ND-01) | đăng bản sửa, khôi phục phiên bản | **gỡ** bài khỏi web (không xoá cứng) | **N**: nội dung hiện công khai trước khách, có rủi ro pháp lý quảng cáo |
| **ND-03 Chuyên mục** | tạo | xem | đổi tên, thứ tự | ngừng dùng | T |

Lý do tách ND-02: đăng là hành động công khai, giống lý do hồ sơ ảnh mặt hàng dùng quyền riêng thay vì `change_item`.
Duy vẫn chỉ tick CRUD, không có khái niệm mới.

| Tác nhân | Vai mặc định | Làm được gì | Quyền cần |
|---|---|---|---|
| Chủ (Lộc) | `chu` | Mọi thứ | ND-01, ND-02, ND-03 (vai hệ thống tự có) |
| Quản lý | `quan_ly` | Soạn, đăng, gỡ, quản lý chuyên mục | ND-01, ND-02, ND-03 (PA 🟡 Q3) |
| NV kho, NV giao | `nv_kho`, `nv_giao` | Không có | — |
| Vai tự tạo (vd "Bán hàng", "CSKH", cộng tác viên viết bài) | do Chủ tạo | Theo ô CRUD Chủ tick. Ví dụ chỉ ND-01 thì soạn nháp, Chủ hoặc Quản lý đăng | theo vai |
| Khách, máy tìm kiếm, bot mạng xã hội | không đăng nhập | Đọc bài **đã đăng** | công khai |
| Hệ thống | — | Sinh đường dẫn, sitemap, ảnh chia sẻ, phiên bản; đưa bài lên web theo phương án kiến trúc (Q1) | — |
| AI (lệnh tự sinh) | theo người dùng | Xem §7.6 | ≤ quyền của người dùng |

**Không đổi con số lời lỗ, không làm tiền rời túi**, nên theo ranh giới spec §1.5 việc này uỷ được cho Quản lý.

## 5. Use case

### UC-ND-01 Soạn bài nháp
- **Tiền điều kiện:** đăng nhập ERP console, có ND-01 (C).
- **Luồng chính:**
  1. Mở Nội dung → "Viết bài". Chọn loại **Bài viết** (mặc định) hoặc **Trang** (UC-ND-07).
  2. Nhập tiêu đề. Hệ thống gợi ý **đường dẫn (slug)** bỏ dấu từ tiêu đề, vd `cach-ra-dong-ca-thu`. Người soạn sửa được
     trước lần đăng đầu (BR-ND-04).
  3. Soạn thân bài bằng **bộ định dạng giới hạn** (BR-ND-06): đoạn, tiêu đề phụ, đậm/nghiêng, danh sách, trích dẫn,
     liên kết, ảnh, **thẻ mặt hàng**.
  4. Chèn ảnh: chọn tệp từ điện thoại/máy tính → hệ thống kiểm tra và xử lý như ảnh mặt hàng nhưng **giữ tỉ lệ**
     (BR-ND-07). Mỗi ảnh có alt text, mặc định bằng tiêu đề bài.
  5. Chèn thẻ mặt hàng: tìm theo tên hoặc mã trong danh mục đang bán → thẻ hiện ảnh, tên, nút "Xem giá & đặt" dẫn sang
     Shop (BR-ND-09, BR-ND-10).
  6. Chọn chuyên mục (một), ảnh bìa, đoạn trích. Phần SEO (tuỳ chọn, có mặc định): tiêu đề SEO, mô tả, ảnh chia sẻ
     (BR-ND-11).
  7. Hệ thống **tự lưu nháp** định kỳ và khi rời màn. Bấm "Xem trước" để xem đúng giao diện web công khai, chỉ người
     trong ERP thấy.
- **Luồng thay thế:**
  - 1a. Nhân bản một bài có sẵn thành nháp mới (tiện cho bài cùng khuôn). Slug mới phải khác.
- **Ngoại lệ:**
  - E1. Tiêu đề trống → vẫn lưu nháp được, nhưng không đăng được (UC-ND-02).
  - E2. Slug trùng bài khác (kể cả bài đã gỡ) → báo trùng, gợi ý thêm hậu tố `-2`.
  - E3. Ảnh sai định dạng, quá dung lượng, SVG, tệp giả ảnh → từ chối kèm mã BR-DM-10 như ảnh mặt hàng; nháp giữ
    nguyên.
  - E4. Mất mạng giữa chừng (4G ở cảng) → phần chưa lưu giữ trên máy và báo "chưa lưu", không mất bài. Ảnh tải nửa
    chừng không để lại ảnh hỏng trong bài.
  - E5. Hai người cùng sửa một nháp → người lưu sau nhận "bài đã đổi, tải lại", không ghi đè im lặng (khoá lạc quan
    như ảnh mặt hàng).
  - E6. Dán nội dung từ Word/web có mã HTML lạ, script, iframe → hệ thống **bỏ phần ngoài bộ định dạng**, giữ chữ
    (BR-ND-06).
  - E7. Người không có ND-01 gọi API → 403.
- **Hậu điều kiện:** có bài trạng thái **Nháp**, chưa hiện ở web công khai. Không ghi AuditLog cho mỗi lần tự lưu.

### UC-ND-02 Đăng bài lần đầu
- **Tiền điều kiện:** bài ở trạng thái Nháp; người đăng có ND-02 (C).
- **Luồng chính:**
  1. Bấm "Đăng". Hệ thống kiểm tra đủ điều kiện (BR-ND-03): có tiêu đề, slug, thân bài, chuyên mục (với Bài viết), ảnh
     bìa có alt text, mô tả SEO (hoặc đoạn trích làm mặc định).
  2. Hệ thống hiện **danh sách tự kiểm** trước khi đăng (BR-ND-13): không ghi giá mua hay tên nhà cung cấp; không có
     tên, SĐT, địa chỉ, ảnh khách khi chưa có đồng ý; ảnh có quyền dùng; không nói công dụng chữa bệnh; giá trong bài
     (nếu có) là giá hiện hành. Người đăng tick xác nhận.
  3. Hệ thống quét tự động những gì máy bắt được (BR-ND-13): chuỗi giống số điện thoại, từ khoá giá vốn. Có thì cảnh
     báo, không chặn (🟡 Q9).
  4. Hệ thống lưu **phiên bản đã đăng số 1** (bất biến, BR-ND-05), đặt trạng thái **Đã đăng**, ghi thời điểm đăng.
  5. Ghi AuditLog `content_publish` (ai, bài nào, phiên bản số mấy).
  6. Bài lên web công khai theo phương án kiến trúc Duy chọn ở **Q1** (xuất hiện ngay, hoặc sau vài phút build). Màn
     ERP hiện rõ trạng thái "Đang đưa lên web…" → "Đã lên web" hoặc "Lỗi, thử lại".
  7. Hệ thống cập nhật sitemap (BR-ND-12).
- **Luồng thay thế:**
  - 1a. Người có ND-01 nhưng thiếu ND-02: nút "Đăng" đổi thành "Gửi duyệt". Bài chuyển **Chờ duyệt**, người có ND-02
    thấy trong danh sách. (🟡 Q4: có cần trạng thái này ở V1 không.)
- **Ngoại lệ:**
  - E1. Thiếu điều kiện ở bước 1 → liệt kê từng mục còn thiếu, bài vẫn là Nháp.
  - E2. Bước đưa lên web thất bại (build lỗi, API lỗi) → bài vẫn **Đã đăng** trong hệ thống, trạng thái lên web báo lỗi,
    có nút thử lại. Web giữ nguyên như trước, không hiện trang hỏng. Không ghi AuditLog lần hai.
  - E3. Hai người bấm đăng cùng lúc → chỉ một lần đăng thành công, người kia nhận "bài đã được đăng".
  - E4. Không có quyền → 403, kiểm ở API.
- **Hậu điều kiện:** bài có đường dẫn công khai cố định. Có 1 phiên bản đã đăng. AuditLog có 1 dòng.

### UC-ND-03 Sửa bài đã đăng
- **Tiền điều kiện:** bài Đã đăng; người sửa có ND-01 (U).
- **Luồng chính:**
  1. Mở bài, sửa. Mọi thay đổi nằm ở **bản đang soạn**. Web công khai **vẫn hiện bản đã đăng** tới khi đăng lại
     (BR-ND-05).
  2. Người có ND-02 (U) bấm "Cập nhật bài" → như UC-ND-02 bước 1–7, tạo **phiên bản đã đăng số n+1**, ghi thời điểm
     "Cập nhật lần cuối". AuditLog `content_republish`.
- **Luồng thay thế:**
  - 2a. Bỏ bản đang soạn → quay về bản đã đăng.
  - 2b. **Khôi phục phiên bản cũ**: chọn phiên bản đã đăng trước đó → nạp vào bản đang soạn → đăng lại (thành phiên bản
    mới, không sửa phiên bản cũ). AuditLog `content_restore_version`.
- **Ngoại lệ:**
  - E1. Muốn đổi slug của bài đã đăng → theo BR-ND-04 (mặc định không cho, 🟡 Q6).
  - E2. Mặt hàng gắn trong bài đã ngừng bán → không chặn sửa, hiện cảnh báo (UC-ND-05 E1).
- **Hậu điều kiện:** web hiện phiên bản mới. Các phiên bản cũ còn nguyên.

### UC-ND-04 Gỡ bài, đăng lại, xoá nháp
- **Tiền điều kiện:** có ND-02 (D) để gỡ; ND-01 (D) để xoá nháp.
- **Luồng chính (gỡ):**
  1. Bấm "Gỡ khỏi web", nhập **lý do** (bắt buộc, vd "sai giá", "khiếu nại", "hết mùa").
  2. Bài chuyển **Đã gỡ**. Đường dẫn công khai trả trang "Bài không còn" (mã 410 hoặc 404 tuỳ Tech Lead), có link về
     Shop. Bài rời sitemap.
  3. AuditLog `content_unpublish` kèm lý do.
- **Luồng thay thế:**
  - 1a. **Đăng lại** bài đã gỡ → như UC-ND-03 bước 2, dùng lại slug cũ.
  - 1b. **Xoá nháp chưa từng đăng**: xoá thật (BR-ND-02), có hỏi xác nhận. Không ghi AuditLog (🟡 Q7).
- **Ngoại lệ:**
  - E1. Bài đã từng đăng thì **không xoá cứng được**, kể cả khi đang Đã gỡ (BR-ND-02). Nút "Xoá" không có, API trả 400
    kèm mã BR.
  - E2. Gỡ gấp khi đưa lên web đang lỗi → trạng thái trong hệ thống vẫn là Đã gỡ, màn hiện "chưa gỡ được khỏi web" và
    thử lại. Đây là trường hợp **khẩn** (bài sai giá hoặc bị khiếu nại), nên gỡ phải chạy được kể cả khi build đang
    hỏng (BR-ND-15).
- **Hậu điều kiện:** bài và mọi phiên bản vẫn còn trong hệ thống.

### UC-ND-05 Khách đọc bài và sang Shop mua
- **Tiền điều kiện:** bài Đã đăng.
- **Luồng chính:**
  1. Khách vào bài từ Google, từ link chia sẻ trên Facebook/Zalo, hoặc từ danh sách bài trên Landing.
  2. Trang hiện tiêu đề, ngày đăng, ngày cập nhật, ảnh bìa, thân bài, thẻ mặt hàng. Tác giả hiển thị là "Cá Về"
     (BR-ND-14).
  3. Thẻ mặt hàng hiện ảnh và tên, cùng nút "Xem giá & đặt". Giá (nếu hiện) phải là **giá hiện hành**, lấy lúc khách
     xem (BR-ND-10).
  4. Bấm nút → sang `/shop/item?code=…` **kèm tham số UTM** (BR-ND-09). Từ đây đi luồng P-05 như cũ.
- **Luồng thay thế:**
  - 1a. Danh sách bài theo chuyên mục, mới nhất trước, có phân trang.
- **Ngoại lệ:**
  - E1. Mặt hàng trong thẻ đã ẩn, hết hàng hoặc không còn giá → thẻ hiện "Tạm hết hàng", nút dẫn về Shop chung. Không
    hiện thẻ vỡ, không chặn đọc bài.
  - E2. API tắt hoặc lỗi → phần chữ và ảnh của bài vẫn đọc được nếu Q1 chọn dựng tĩnh. Chỉ phần giá/tồn trên thẻ ẩn đi.
  - E3. Slug không tồn tại → trang 404 có link về Landing và Shop.
- **Hậu điều kiện:** không có dữ liệu nào về khách được thu ở bước đọc bài (BR-ND-14).

### UC-ND-06 Quản lý chuyên mục
- **Tiền điều kiện:** có ND-03.
- **Luồng chính:** tạo chuyên mục (tên, slug, mô tả ngắn, thứ tự). Đổi tên. Sắp thứ tự trên menu.
- **Ngoại lệ:** tên hoặc slug trùng → từ chối. **Ngừng dùng** chuyên mục còn bài Đã đăng → chặn, liệt kê bài
  (hoặc chuyển bài sang chuyên mục khác trước).
- **Hậu điều kiện:** không xoá cứng chuyên mục đã từng có bài đăng (BR-ND-02).

### UC-ND-07 Soạn trang nội dung (chính sách, giới thiệu)
- **Tiền điều kiện:** như UC-ND-01, loại **Trang**.
- **Luồng chính:**
  1. Trang không có chuyên mục, không hiện trong danh sách bài, đường dẫn cố định ngắn (vd `/chinh-sach-bao-mat`).
  2. Đăng như UC-ND-02. Trang hiện dòng "Có hiệu lực từ / cập nhật ngày …".
  3. Trang được gắn vào **footer** của Landing và Shop theo danh sách do người có ND-02 chọn.
- **Luồng thay thế:** sửa và khôi phục như UC-ND-03. Mỗi lần đăng lại là một phiên bản có ngày hiệu lực.
- **Ngoại lệ:**
  - E1. Gỡ một trang được đánh dấu **bắt buộc go-live** (chính sách bảo mật, điều kiện giao dịch, đổi trả hoàn tiền,
    thông tin người bán) → chặn, chỉ cho sửa và đăng lại (BR-ND-16).
  - E2. Nội dung trang hoàn tiền mâu thuẫn BR-HT → máy không kiểm được. Nội dung pháp lý do `legal-vn` soạn và Duy
    duyệt trước khi đăng (go-live mục 3).
- **Hậu điều kiện:** tra được **phiên bản nào có hiệu lực vào ngày nào**. Cần khi khách khiếu nại "lúc tôi đặt, chính
  sách ghi khác" và khi ô đồng ý xử lý dữ liệu ở checkout trỏ tới một phiên bản chính sách (go-live mục 6).

### UC-ND-08 Máy tìm kiếm và bot mạng xã hội đọc bài (Hệ thống)
- **Luồng chính:** web có `sitemap` liệt kê Landing, Shop, bài và trang Đã đăng, kèm ngày cập nhật. `robots` cho phép
  trên production. Mỗi bài có tiêu đề, mô tả, đường dẫn chính thức (canonical) và ảnh chia sẻ **riêng** trong HTML ban
  đầu, không cần chạy JS (BR-ND-11, BR-ND-12).
- **Ngoại lệ:**
  - E1. **Staging luôn chặn lập chỉ mục** (noindex) để không bị Google coi là nội dung trùng (BR-ND-12). Hiện chưa có
    `robots` nào, nên `cangca-loc-staging.web.app` đang có thể bị lập chỉ mục.
  - E2. Bài có cờ "không lập chỉ mục" (vd trang khuyến mãi tạm) → không vào sitemap, có noindex.
- **Hậu điều kiện:** chia sẻ link một bài lên Facebook/Zalo hiện đúng ảnh bìa và tiêu đề bài đó (nếu Q1 chọn A hoặc C).

### UC-ND-09 AI của người dùng gọi lệnh CMS (ảnh hưởng từ hồ sơ AI)
- Theo 02b hồ sơ AI §0: API ghi của CMS **tự thành lệnh** mức C. AI có thể soạn nháp chờ người duyệt nếu người dùng có
  ND-01. Duy nói "chưa, chỉ viết tay". Xem §7.6 và 🟡 Q10 cho mặc định.

## 6. Business rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| **BR-ND-01** | Nội dung có hai loại: **Bài viết** (có chuyên mục, ngày đăng, vào danh sách bài) và **Trang** (đường dẫn cố định, không chuyên mục, gắn footer). Không khoá kiểu nội dung trong bài: người soạn tự viết công thức, tin mùa vụ, giới thiệu… | Duy 28/09 + PA | Mới |
| **BR-ND-02** | Vòng đời: **Nháp → (Chờ duyệt) → Đã đăng ⇄ Đã gỡ**. Nháp **chưa từng đăng** được xoá thật. Bài, trang hay chuyên mục **đã từng đăng không xoá cứng**, chỉ gỡ hoặc ngừng dùng. Lý do: bằng chứng nội dung quảng cáo đã công khai khi có khiếu nại, và giữ đường dẫn không bị tái sử dụng. Bài không phải chứng từ nên BR-PQ-10 không áp nguyên văn. | PA | Mới |
| **BR-ND-03** | Điều kiện đăng: tiêu đề, slug, thân bài, chuyên mục (với Bài viết), ảnh bìa có alt text, mô tả SEO (hoặc đoạn trích). Thiếu thì không đăng được. | PA | Mới |
| **BR-ND-04** | Slug duy nhất trên toàn bộ nội dung (kể cả bài đã gỡ), chữ thường không dấu, gạch nối. **Khoá sau lần đăng đầu.** Nếu Q6 cho đổi thì đường dẫn cũ phải chuyển hướng vĩnh viễn sang đường dẫn mới. | PA | Mới |
| **BR-ND-05** | Mỗi lần đăng tạo một **phiên bản đã đăng** bất biến (nội dung, SEO, người đăng, thời điểm). Web chỉ hiện phiên bản đã đăng mới nhất. Sửa bài đã đăng không đổi web cho tới khi đăng lại. Khôi phục = tạo phiên bản mới từ nội dung cũ. Phiên bản đã đăng là append-only (tương tự bất biến 4). Tự lưu nháp không tạo phiên bản. | PA | Mới |
| **BR-ND-06** | Thân bài chỉ gồm **bộ định dạng giới hạn**: đoạn, tiêu đề phụ, đậm, nghiêng, danh sách, trích dẫn, liên kết, ảnh, thẻ mặt hàng. **Không** HTML tự do, script, iframe, nhúng mã bên ngoài, form. Nội dung ngoài bộ này bị bỏ khi lưu, và web công khai **lọc lại lúc hiển thị** (hai lớp). Lý do: web công khai cùng tên miền với Shop và checkout, một lỗ XSS ở bài viết là lỗ ở trang thanh toán. | PA | Mới |
| **BR-ND-07** | Ảnh bài dùng lại kiểm tra BR-DM-10 (JPEG/PNG/WebP, cấm SVG, kiểm nội dung thật, ≤ 10 MB, gỡ EXIF/GPS, chỉ phát cỡ đã xử lý) và BR-DM-16 (ngoài git, ngoài đĩa container). **Khác ảnh mặt hàng:** giữ tỉ lệ gốc, không cắt vuông; ảnh bìa có thêm một cỡ cho ảnh chia sẻ. Mỗi ảnh có alt text (BR-DM-11). Tối đa N ảnh mỗi bài (tham số, mặc định 20). Ảnh bị gỡ khỏi bài không xoá ngay, giữ ít nhất tới khi không phiên bản đã đăng nào còn dùng (BR-DM-14). | PA + D (25/09) | Mới |
| **BR-ND-08** | Liên kết ngoài trong bài mở tab mới, có đánh dấu không chuyển uy tín (nofollow) mặc định. Không chèn link rút gọn hay link tiếp thị liên kết. | PA | Mới |
| **BR-ND-09** | Thẻ mặt hàng và mọi link từ bài sang Shop gắn UTM theo quy ước: `utm_source=caveve_web`, `utm_medium=bai_viet`, `utm_campaign=<slug bài>`. Link bài dán lên social dùng `utm_source=facebook|zalo|tiktok`, `utm_medium=social`. UTM **không bao giờ chứa dữ liệu cá nhân**. | decisions 10/09 (Social, UTM) + PA | Mới |
| **BR-ND-10** | Thẻ mặt hàng lấy dữ liệu **công khai** của Shop (tên, ảnh, giá niêm yết hiện hành, còn/hết hàng), **không bao giờ** qua serializer ERP. Nếu hiện giá thì phải là giá **lúc khách xem**, không phải giá lúc đăng bài. Người soạn **không nên gõ giá cứng** trong chữ; nếu gõ thì chịu trách nhiệm cập nhật (danh sách tự kiểm BR-ND-13). | Bất biến 1 + PA | Mới |
| **BR-ND-11** | SEO mỗi bài: tiêu đề SEO (mặc định tiêu đề bài), mô tả (mặc định đoạn trích, cắt ~160 ký tự), ảnh chia sẻ (mặc định ảnh bìa), canonical theo tên miền chính thức, cờ không lập chỉ mục. Các thẻ này phải có trong **HTML ban đầu** của trang bài (điều kiện để Google đọc chắc và để Facebook/Zalo hiện ảnh xem trước). | PA | Mới |
| **BR-ND-12** | Sitemap gồm Landing, Shop, bài và trang Đã đăng không có cờ noindex, kèm ngày cập nhật. Đăng, sửa, gỡ đều làm sitemap thay đổi. **Môi trường staging luôn noindex** và không có sitemap công khai. | PA | Mới |
| **BR-ND-13** | Trước khi đăng, người đăng xác nhận **danh sách tự kiểm**: (a) không giá mua, giá vốn, tên nhà cung cấp, ảnh bảng giá tại cảng (mở rộng BR-DM-15 sang chữ); (b) không tên, SĐT, địa chỉ, ảnh mặt khách nếu chưa có đồng ý bằng văn bản; (c) ảnh và chữ có quyền dùng, ảnh minh hoạ ghi nhãn; (d) không nói công dụng chữa bệnh, không so sánh chê đối thủ, hàng đông lạnh không gọi là "tươi sống"; (e) giá, khuyến mãi nhắc trong bài đúng hiện hành. Máy quét cảnh báo được (a) một phần và chuỗi giống SĐT ở (b). Còn lại là quy tắc vận hành. Danh sách cuối do `legal-vn` rà. | PA, chờ `legal-vn` | Mới |
| **BR-ND-14** | Web công khai **không** trả tên đăng nhập, họ tên hay email của nhân viên soạn bài: tác giả hiển thị là "Cá Về" (🟡 Q8). Đọc bài không thu dữ liệu cá nhân nào của khách: không bình luận, không form, không pixel. Thêm analytics hay pixel là **bên thứ ba mới**, cần Duy duyệt và chính sách quyền riêng tư nêu rõ (bất biến 9). | Bất biến 9 + PA | Mới |
| **BR-ND-15** | Đăng, đăng lại, khôi phục, gỡ đều ghi AuditLog (ai, bài, phiên bản, lý do nếu gỡ). **Không chép thân bài vào AuditLog** (dài, và có thể chứa dữ liệu lọt vào sai). Gỡ bài phải có hiệu lực trên web **kể cả khi đường đưa bài lên web đang lỗi** (phương án Q1 phải có đường gỡ khẩn). | PA (mở rộng BR-PQ-04, theo mẫu BR-DM-12) | Mới |
| **BR-ND-16** | Trang được đánh dấu **bắt buộc go-live** (chính sách bảo mật, điều kiện giao dịch chung, đổi trả hoàn tiền, thông tin người bán theo NĐ 248) không gỡ được, chỉ sửa và đăng lại. Mỗi phiên bản có **ngày hiệu lực**, tra được phiên bản có hiệu lực tại một thời điểm. | PA theo go-live mục 2, 3, 6 | Mới |
| **BR-ND-17** | Nội dung chỉ tiếng Việt. Không bình luận, không đánh giá sao ở V1. | PRODUCT.md + PA | Mới |
| BR-DM-10, 11, 14, 15, 16 | Quy tắc ảnh mặt hàng, dùng lại cho ảnh bài (BR-ND-07). | PA / D | Giữ |
| BR-PQ-12, 13 | Chặn ở API. Test token theo vai có thêm các endpoint CMS, và test quét JSON công khai của bài không có khoá giá vốn và dữ liệu cá nhân. | D | Giữ (mở rộng phạm vi test) |
| URD §6.8 | Landing (SEO, không giao dịch) tách khỏi Shop. Bài viết thuộc Landing. | L/D | Giữ |

## 7. Tác động dữ liệu & tích hợp

Chỉ nêu cái gì đổi. Cách làm là việc của Tech Lead (`02b`).

### 7.1 Dữ liệu (thêm mới, bất biến 8: có lý do ở từng dòng)
- **Nội dung** (bài/trang): loại, tiêu đề, slug, đoạn trích, chuyên mục, ảnh bìa, trạng thái, SEO, cờ noindex, cờ bắt
  buộc go-live, người tạo, thời điểm đăng đầu/cập nhật. Lý do: UC-ND-01…07.
- **Bản đang soạn và phiên bản đã đăng** (append-only). Lý do: BR-ND-05, BR-ND-16.
- **Chuyên mục**. Lý do: UC-ND-06.
- **Ảnh bài** (nhiều ảnh mỗi bài, giữ tỉ lệ). Có nên dùng chung bảng hoặc chung module xử lý với `catalog/images`
  không là việc của Tech Lead. Lưu ý `ItemImage` hiện là 1-1 và cắt vuông.
- **Liên kết bài ↔ mặt hàng** (mặt hàng nào được gắn trong bài nào). Lý do: thẻ mặt hàng, cảnh báo khi mặt hàng ngừng
  bán, sau này đo bài nào kéo đơn.
- **Permission mới:** theo ND-01…03 (§4). Gán mặc định cho `chu` và `quan_ly` qua data migration như `0006`, và khai
  quyền tính năng vào danh mục của hồ sơ vai trò (BR-PQ-28 bên đó).
- **AuditLog:** không đổi schema. Thêm action `content_publish`, `content_republish`, `content_restore_version`,
  `content_unpublish`.
- **Không đổi:** mọi model nghiệp vụ (Item, lô, đơn, tiền). Không có field giá, không có field dữ liệu cá nhân khách.

### 7.2 API và màn hình
- **ERP console:** mục menu mới "Nội dung" (danh sách bài lọc theo trạng thái/chuyên mục, trình soạn, xem trước, lịch
  sử phiên bản, chuyên mục). Trình soạn giàu định dạng là **phụ thuộc mới** của `erp-console` (Tech Lead chọn). Phải
  dùng được trên điện thoại (PRODUCT.md: người dùng ngoài trời, điện thoại là chuẩn).
- **Django Admin:** chỉ để xem và cứu hộ (superuser), không phải nơi soạn (🟡 Q2).
- **API công khai (`AllowAny`):** danh sách và chi tiết bài/trang **đã đăng**, chuyên mục. Field liệt kê tường minh,
  không trả người tạo, không trả nháp. Thẻ mặt hàng dùng lại API Shop công khai hiện có.
- **Web công khai `frontend/`:** trang danh sách bài, trang bài, trang chuyên mục, trang nội dung, footer, sitemap,
  robots, 404/410. Có dựng tĩnh hay không tuỳ Q1.

### 7.3 Ràng buộc static export và các phương án cho Tech Lead (liên quan 🔴 Q1)

Ràng buộc: `frontend` là static export, không có server khi chạy. Build và deploy hiện chạy tay trên máy dev.
Production API đang tắt. Facebook/Zalo không chạy JS khi lấy ảnh xem trước.

| PA | Cách | Được | Mất | Thời gian bài lên web |
|---|---|---|---|---|
| **A. Dựng lại khi đăng** | Đăng/gỡ kích hoạt build `frontend` (lấy bài đã đăng từ API) rồi deploy Firebase, tự động | SEO tốt nhất, ảnh chia sẻ riêng từng bài, trang bài vẫn đọc được khi API tắt, không thêm server khi chạy | Cần dựng **đường build/deploy tự động** (hiện chưa có) với secret deploy Firebase; mỗi lần đăng tốn một lượt build; build hỏng thì bài không lên (và **gỡ khẩn** cần đường riêng, BR-ND-15); phải xử lý staging/production tách biệt | vài phút |
| **B. Tải lúc chạy** | Một trang tĩnh `/bai-viet?slug=…` tải bài qua API trong trình duyệt, như `/shop/item?code=` | Rẻ nhất, bài hiện ngay, không đổi hạ tầng | Google đọc kém hơn (phải chạy JS), **Facebook/Zalo luôn hiện ảnh chung**, sitemap phải do backend sinh, **trắng trang khi API production tắt** | ngay |
| **C. Backend dựng HTML trang bài** | Firebase Hosting chuyển `/bai-viet/**` (và `sitemap`) sang Cloud Run; backend trả HTML bài đầy đủ | SEO và ảnh chia sẻ đúng, bài hiện ngay, không cần CI | Trang bài có giao diện dựng ở một nơi thứ hai ngoài Next.js (hai bộ giao diện phải giữ giống nhau); phụ thuộc Cloud Run lúc chạy (cold start, API production đang tắt) | ngay |
| **D. Kết hợp** | B cho người đọc + C chỉ trả thẻ meta cho bot mạng xã hội/tìm kiếm | Bài hiện ngay, ảnh chia sẻ đúng | Phức tạp nhất, dễ lệch nội dung giữa hai đường | ngay |
| **E. Bỏ static export** | Chuyển `frontend` sang chạy server (SSR) | Linh hoạt nhất | Đổi kiến trúc cả Shop, đổi chi phí và cách deploy. Quá tầm yêu cầu này. BA **không đề xuất** | ngay |

Gợi ý BA (không phải quyết định kỹ thuật): nếu mục tiêu là SEO và chia sẻ link thì **A** khớp nhất với nguyên tắc
"không server khi chạy, ít phụ thuộc". **B** chỉ hợp khi bài là nội dung phụ cho người đã ở trên web. Tech Lead đánh
giá chi phí đường build tự động so với C.

### 7.4 Bên thứ ba
- **Không có bên mới bắt buộc.** Bucket ảnh GCS đã có.
- UTM chỉ có ích khi có công cụ đọc số liệu. Shop hiện **không có analytics**. Thêm Google Analytics, Meta Pixel hay
  tương tự là bên thứ ba mới, dữ liệu gửi ra nước ngoài → cần Duy duyệt, chính sách quyền riêng tư nêu rõ và banner
  đồng ý nếu có cookie theo dõi (bất biến 9, go-live mục 6/6b). **Ngoài phạm vi hồ sơ này** (🟢 Q12). Trước mắt UTM
  vẫn gắn vì rẻ và đọc được sau qua log Hosting hoặc công cụ đo phía server.
- Google Search Console (khai sitemap, xác minh tên miền): việc vận hành, không gửi dữ liệu khách.

### 7.5 Liên kết hồ sơ vai trò (`2026-09-28-vai-tro-tu-dinh-nghia`)
- Thêm mảng **"Nội dung"** vào danh mục quyền tính năng với ND-01 (T), ND-02 (N), ND-03 (T). Không có quyền nào ở mức K.
- Nếu hồ sơ vai trò chưa xong khi CMS làm, gán tạm bằng data migration cho `chu` + `quan_ly` như các quyền trước.

### 7.6 Ảnh hưởng hồ sơ AI (`2026-09-28-ai-digital-worker`)
- Theo 02b §0 dòng 1 và 3: API ghi CMS (tạo nháp, sửa, đăng, gỡ) **tự thành lệnh AI** ở trần **C** (nháp chờ duyệt).
  API đọc thì chạy ngay nhưng qua bộ lọc "bỏ chữ tự do", nên AI đọc thân bài gần như không được gì.
- Mâu thuẫn nhẹ với câu "Chưa, chỉ viết tay": nếu giữ nguyên tắc tự sinh thì người dùng vẫn có thể bảo AI "viết nháp
  bài về cá thu", và AI soạn nội dung quảng cáo. Rủi ro: câu chữ AI sinh ra có thể sai sự thật về hàng hoá hoặc chép
  nội dung có bản quyền. Nội dung đó sẽ lên web công khai nếu người duyệt bấm đăng.
- **Lệnh đăng và gỡ** là thay đổi công khai. Chúng không nằm trong vùng đỏ (không có quyền tiền), nên theo luật hiện có
  sẽ ở trần C, tức AI đề xuất và người bấm. Điều này chấp nhận được về an toàn.
- Mặc định 🟡 Q10 ở §10. Dù chọn gì, hồ sơ AI cần ghi CMS là lệnh ghi đầu tiên **tạo nội dung công khai**, và test
  "feature mới không khai gì" (02b §11.2) nên có một ca CMS.

## 8. Rủi ro Cá Về

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| R1 | **Rò giá vốn qua bài.** Người soạn là Chủ (người biết giá mua) viết "mua tại cảng 80k/kg", hoặc ảnh chụp bảng giá cảng. Thẻ mặt hàng lấy nhầm serializer ERP có `landed_unit_cost`. | **Cao** | BR-ND-10 (chỉ API Shop công khai), BR-ND-13 (tự kiểm + máy cảnh báo), test quét JSON công khai của bài không có khoá giá vốn. |
| R2 | **Rò dữ liệu cá nhân khách:** bài "khách nói gì về Cá Về" kèm tên, SĐT, ảnh chụp tin nhắn Zalo có SĐT, ảnh đơn giao có địa chỉ. | **Cao** (Critical nếu xảy ra) | BR-ND-13 (b), máy quét chuỗi giống SĐT, lời chứng thực chỉ khi có đồng ý bằng văn bản (legal-vn). |
| R3 | **XSS trên tên miền có checkout:** thân bài giàu định dạng, dán từ web, ảnh SVG. | **Cao** | BR-ND-06 (hai lớp lọc), BR-ND-07 (không SVG). |
| R4 | **Pháp lý quảng cáo thực phẩm** và bảo vệ người tiêu dùng: nói quá công dụng, gọi hàng đông lạnh là tươi sống, giá trong bài lệch giá Shop, khuyến mãi không đăng ký, dùng ảnh/chữ chép mạng. | Trung bình–Cao | BR-ND-13, gửi `legal-vn` (§11). |
| R5 | **Kiến trúc static export:** chọn B thì mục tiêu SEO/chia sẻ không đạt; chọn A thì thêm đường build tự động có secret deploy, build hỏng làm kẹt cả việc gỡ bài khẩn. | Trung bình | Q1, BR-ND-15 (đường gỡ khẩn). |
| R6 | **Tên miền:** SEO xây trên `*.web.app` rồi chuyển tên miền riêng (bắt buộc cho go-live mục 1) sẽ mất thứ hạng nếu không chuyển hướng 301. Staging chưa có noindex. | Trung bình | Canonical theo tên miền chính thức ngay từ đầu (BR-ND-11), noindex staging (BR-ND-12), Q11. |
| R7 | **Phân quyền:** ai sửa được cũng đăng được nếu gộp chung một quyền; nội dung sai hiện ngay trước khách. | Trung bình | ND-02 tách riêng, mức N (§4). |
| R8 | **Mất bằng chứng:** xoá cứng bài quảng cáo đã đăng rồi khách khiếu nại theo nội dung bài. | Trung bình | BR-ND-02, BR-ND-05, BR-ND-16. |
| R9 | **AI soạn nội dung công khai** trái ý "chỉ viết tay". | Thấp–Trung bình | §7.6, Q10. |
| R10 | Chi phí băng thông ảnh bài tăng theo lượt xem (bucket không CDN). | Thấp | Cỡ WebP nhỏ, lazy load, budget alert còn nợ (moi-truong.md). |
| — | FEFO, tồn, giữ chỗ, tiền, chứng từ | Không ảnh hưởng | CMS không đụng lô, đơn, giá. |

## 9. Ngoài phạm vi

- **Bình luận, đánh giá sao, form liên hệ trong bài** (thu dữ liệu cá nhân, cần kiểm duyệt).
- **Đa ngôn ngữ.**
- **AI viết hộ, AI sinh alt text, AI gợi ý tiêu đề** (Duy: "Chưa, chỉ viết tay"). Tác động của lệnh tự sinh xem §7.6.
- **Tự đăng lên Facebook/Zalo/TikTok** (decisions 10/09).
- **Analytics, pixel quảng cáo, bảng số liệu bài viết** (🟢 Q12).
- **Hẹn giờ đăng** (🟢 Q13).
- **Thẻ (tag)** ngoài chuyên mục (🟡 Q5: mặc định V1 chỉ có chuyên mục).
- **Video tải lên, nhúng YouTube/TikTok** (nhúng là iframe bên thứ ba, trái BR-ND-06).
- **Bán hàng trong bài** (giỏ, nút mua trực tiếp): trái URD §6.8. Bài chỉ dẫn sang Shop.
- **Soạn lại nội dung Landing hiện có** (hero, "Vì sao chọn Cá Về") bằng CMS. Có thể làm sau bằng loại Trang.
- **Mua tên miền, thông báo website với Sở Công Thương**: việc go-live, không phải CMS.
- **Nội dung pháp lý của các trang chính sách**: `legal-vn` soạn. CMS chỉ là nơi đăng.

## 10. Câu hỏi mở

| # | Mức | Câu hỏi | Phương án | Mặc định PA đề xuất |
|---|---|---|---|---|
| Q1 | 🔴 | **Bài viết dùng để làm gì là chính, và chấp nhận bài lên web chậm vài phút không?** Câu trả lời quyết định kiến trúc (§7.3). | **(a)** Kéo khách từ Google và từ link chia sẻ Facebook/Zalo (cần trang tĩnh riêng từng bài, ảnh xem trước riêng); chấp nhận bài lên web sau **vài phút** kể từ khi bấm đăng; chấp nhận thêm một đường build/deploy tự động → PA **A**. **(b)** Như (a) nhưng bài phải hiện **ngay** → PA **C** (backend dựng HTML trang bài). **(c)** Chỉ là nơi đọc thêm cho người đã vào web, không cần SEO hay ảnh chia sẻ riêng → PA **B**, rẻ nhất. | **(a)**. Social đăng tay và dẫn link là kênh chính (decisions 10/09), nên ảnh xem trước riêng từng bài là giá trị lớn nhất. Vài phút trễ không hại gì với bài viết. Bài vẫn đọc được khi API production tắt. Tech Lead xác nhận chi phí ở `02b`. |
| Q2 | 🟡 | Soạn ở đâu? | (a) ERP console; (b) Django Admin | **(a) ERP console.** Dùng được phân quyền theo vai, dùng được trên điện thoại, khớp hướng "console thay Admin". Admin chỉ để cứu hộ. |
| Q3 | 🟡 | Ô quyền trên màn vai trò: một dòng "Bài viết" CRUD (U gồm cả đăng), hay tách thêm dòng "Đăng bài"? Quản lý có sẵn quyền đăng không? | (a) Hai dòng ND-01/ND-02 (+ ND-03 chuyên mục); (b) một dòng, U = đăng | **(a)**, vẫn chỉ là ô CRUD. `chu` và `quan_ly` có cả ba. Vai tự tạo tuỳ Chủ tick. |
| Q4 | 🟡 | Có cần trạng thái **Chờ duyệt** (người chỉ có ND-01 gửi, người có ND-02 đăng) ở V1? | — | **Có**, vì chi phí nhỏ và mở đường cho cộng tác viên viết bài mà không cho đăng. |
| Q5 | 🟡 | Chuyên mục và thẻ? | — | V1 chỉ **chuyên mục** (một bài một chuyên mục), chưa có thẻ. Bài ít thì trang thẻ mỏng nội dung, không tốt cho SEO. |
| Q6 | 🟡 | Đổi đường dẫn (slug) bài đã đăng? | — | **Không cho** ở V1. Muốn đổi thì gỡ và tạo bài mới. Cho đổi thì phải kèm chuyển hướng (BR-ND-04). |
| Q7 | 🟡 | Xoá nháp chưa từng đăng có cần AuditLog/thùng rác? | — | Xoá thật, có hỏi xác nhận, không AuditLog. |
| Q8 | 🟡 | Tên tác giả hiển thị? | — | "**Cá Về**", không hiện tên nhân viên (tên nhân viên cũng là dữ liệu cá nhân). |
| Q9 | 🟡 | Máy quét thấy chuỗi giống SĐT hoặc từ khoá giá vốn thì chặn hay cảnh báo? | — | **Cảnh báo**, người đăng xác nhận lại. Chặn cứng dễ bắt nhầm (vd hotline của vựa). |
| Q10 | 🟡 | AI (lệnh tự sinh) có được gọi lệnh ghi của CMS ở V1 không? | (a) Giữ nguyên nguyên tắc 28/09: tự thành lệnh trần C, AI chỉ soạn nháp hoặc đề xuất đăng/gỡ, người bấm; nháp do AI tạo được **đánh dấu nguồn AI** và hiện nhãn cho người duyệt. (b) Chặn đường dẫn CMS khỏi AI ở V1 (thêm vào danh sách chặn của hồ sơ AI). | **(b)** cho V1. "Chưa, chỉ viết tay" là câu trả lời trực tiếp cho tính năng này, trong khi nội dung công khai do AI soạn còn chờ `legal-vn` rà nghĩa vụ ghi nhãn nội dung AI. Mở lại bằng một dòng cấu hình khi Duy muốn. Tech Lead AI xác nhận cách chặn theo đường dẫn. |
| Q11 | 🟡 | Tên miền chính thức? | — | Tạm dùng `cangca-loc.web.app` làm canonical, khi có tên miền riêng thì chuyển 301 toàn bộ. Nên có tên miền **trước** khi đẩy SEO. |
| Q12 | 🟢 | Đo bài nào kéo đơn (analytics, số liệu UTM)? | — | Để sau, cần hồ sơ riêng vì là bên thứ ba (bất biến 9). |
| Q13 | 🟢 | Hẹn giờ đăng? | — | Để sau. Với PA A cần job hẹn giờ gọi build. |
| Q14 | 🟢 | Dùng CMS để soạn lại Landing hiện có? | — | Để sau. |

## 11. Việc gửi `legal-vn` rà (không chặn phân tích, chặn **đăng bài thật** trên production)

1. Quảng cáo thực phẩm thông thường (hải sản đông lạnh) trên website của chính người bán: có phải xác nhận nội dung
   quảng cáo không; những câu chữ bị cấm (công dụng chữa bệnh, so sánh, "tươi sống" với hàng cấp đông, nguồn gốc xuất
   xứ). Căn cứ tham khảo cần kiểm: Luật Quảng cáo và văn bản sửa đổi, NĐ 15/2018 về an toàn thực phẩm (phần quảng cáo
   thực phẩm), Luật Bảo vệ quyền lợi người tiêu dùng 2023.
2. Nhắc giá, khuyến mãi trong bài: nghĩa vụ niêm yết giá đúng và thủ tục thông báo khuyến mại khi bài công bố ưu đãi
   (liên quan `PricingRule`).
3. Lời chứng thực, ảnh khách: hình thức đồng ý theo Luật BVDLCN 2025.
4. Website có mục bài viết về sản phẩm của chính mình có bị coi là "trang thông tin điện tử" cần giấy phép hay thông báo
   riêng không (NĐ 147/2024 thay NĐ 72/2013), hay chỉ cần thông báo website TMĐT (go-live mục 1).
5. Nội dung do AI tạo có nghĩa vụ ghi nhãn không (nếu Q10 chọn a).
6. Danh sách tự kiểm BR-ND-13 (bản cuối) và nội dung các trang bắt buộc go-live (UC-ND-07).
7. Bản quyền ảnh và chữ sưu tầm; nhãn "Ảnh minh hoạ" (đã có ở BR hồ sơ ảnh mặt hàng Q8).

## 12. Phân đoạn đề xuất (để PO cắt story)

| Đoạn | Nội dung | Điều kiện xong |
|---|---|---|
| **Đ0: tiền đề** | Chốt Q1 và phương án kiến trúc (`02b`). `robots` noindex cho staging (làm được ngay, độc lập). Quyền ND-01…03 gán `chu`/`quan_ly`. | Staging trả noindex; test token theo vai cho endpoint CMS |
| **Đ1: soạn và đăng** | Nội dung, chuyên mục, trình soạn trên console, ảnh bài (dùng lại xử lý ảnh, giữ tỉ lệ), vòng đời Nháp/Chờ duyệt/Đã đăng/Đã gỡ, phiên bản, khôi phục, AuditLog, danh sách tự kiểm | UC-ND-01…04, 06; test XSS (BR-ND-06); test quét JSON công khai không có giá vốn/PII |
| **Đ2: web công khai + SEO** | Trang danh sách, trang bài, chuyên mục, thẻ mặt hàng + UTM, sitemap, meta, ảnh chia sẻ, 404/410, đường gỡ khẩn | UC-ND-05, 08; chia sẻ link một bài lên Facebook hiện đúng ảnh bìa (nếu Q1 = a/b) |
| **Đ3: trang bắt buộc go-live** | Loại Trang, footer, cờ bắt buộc, ngày hiệu lực phiên bản. Nội dung do `legal-vn` soạn | UC-ND-07; bốn trang go-live mục 2, 3, 6 lên staging |
| **Đ4: nối AI** | Theo Q10 (chặn đường dẫn, hoặc gắn nguồn AI cho nháp) | Test "feature mới không khai gì" có ca CMS |

Đ3 có thể làm ngay sau Đ1 nếu go-live gấp hơn SEO.
