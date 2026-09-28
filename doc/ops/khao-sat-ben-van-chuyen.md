# Khảo sát bên vận chuyển cho vựa Cá Về

- **Ngày khảo sát:** 2026-09-28
- **Người làm:** Claude (research subagent), theo yêu cầu của Duy
- **Mục đích:** chỉ để biết thị trường có bên nào đáp ứng được không. **Báo cáo này không đề xuất lật quyết định** "100% đơn do nhân viên nội bộ giao" (`doc/decisions.md`, 2026-09-09). Nó chỉ cung cấp dữ liệu.
- **Phạm vi:** lấy hàng ở kho Phan Thiết, giao nội thành và liên tỉnh trong bán kính dưới 300 km, ưu tiên giao trong ngày. Hàng đông lạnh đóng thùng xốp và đá, mỗi đơn 1–10 kg, vài chục đơn/ngày. Phải có API.

## 0. Cách làm và mức tin cậy

- **WebFetch bị proxy chặn** (`EGRESS_BLOCKED`) với ahamove.com, developers.ahamove.com và lalamove.com. Vì vậy mọi số liệu dưới đây lấy từ **đoạn trích kết quả WebSearch**. Tôi không mở được toàn văn trang.
- Quy ước mức tin cậy:
  - **Cao:** đoạn trích lấy từ trang chính chủ của bên vận chuyển hoặc từ cơ quan nhà nước.
  - **TB (trung bình):** đoạn trích từ báo chí, blog đối tác hoặc trang bên thứ ba.
  - **Thấp / chưa xác minh:** suy luận, hoặc nguồn không nói rõ khu vực Phan Thiết.
- Giá chỉ để tham khảo. Giá thật phụ thuộc vào giờ, khu vực và khuyến mãi, nên phải gọi API báo giá hoặc hỏi trực tiếp. **Không có con số nào trong báo cáo là do tôi tự đặt ra.** Ô nào không tìm được nguồn thì ghi "chưa xác minh".

## 1. Địa danh hành chính hiện hành

- Từ ngày 01/07/2025, ba tỉnh Lâm Đồng, Bình Thuận và Đắk Nông hợp nhất thành **tỉnh Lâm Đồng** mới. Chính quyền cấp huyện bị bỏ.
- Khu trung tâm TP. Phan Thiết cũ nay là **phường Phan Thiết, tỉnh Lâm Đồng**, gộp từ ba phường cũ Phú Trinh, Lạc Đạo và Bình Hưng. Các phường cũ khác của Phan Thiết được gộp vào những phường mới khác, nên địa chỉ kho cần ghi đúng tên phường mới. Mức tin cậy: Cao.
  - Nguồn: https://thuvienphapluat.vn/phap-luat/phuong-phan-thiet-tinh-lam-dong-tu-172025-duoc-sap-nhap-tu-cac-phuong-cu-nao-223910.html
  - Nguồn: https://thuvienphapluat.vn/phap-luat/ho-tro-phap-luat/phan-thiet-thuoc-tinh-nao-sau-sap-nhap-phuong-phan-thiet-duoc-sap-nhap-tu-nhung-phuong-nao-413229-268506.html
- **Hệ quả khi tích hợp:** nhiều bên vận chuyển vẫn dùng mã "Bình Thuận" hoặc "Phan Thiết" cũ trong danh mục địa chỉ và city_id. Khi nối API cần kiểm tra bộ mã địa chỉ của từng bên đã cập nhật theo 34 tỉnh chưa.

## 2. Điểm đến tiêu biểu trong bán kính 300 km

Khoảng cách tính bằng đường bộ, lấy trung tâm tới trung tâm, là số ước tính.

| Điểm đến | Khoảng cách | Thời gian lái xe | Nguồn (tin cậy) |
|---|---|---|---|
| Nội thành Phan Thiết (cũ) | < 15 km | < 30 phút | ước tính, chưa xác minh |
| TP.HCM (trung tâm) | ~183 km | 2–2,5 giờ nhờ cao tốc Dầu Giây–Phan Thiết (dài 99 km) | https://baoxeditinh.com/tu-tphcm-di-phan-thiet-bao-nhieu-km/ (TB); https://vi.wikipedia.org/wiki/%C4%90%C6%B0%E1%BB%9Dng_cao_t%E1%BB%91c_Phan_Thi%E1%BA%BFt_%E2%80%93_D%E1%BA%A7u_Gi%C3%A2y (TB) |
| Biên Hòa (Đồng Nai) | ~142 km | 3–4 giờ (đi xe khách) | https://12go.asia/vi/travel/bien-hoa/phan-thiet (TB) |
| Vũng Tàu (nay thuộc TP.HCM) | ~150–170 km | chưa xác minh | https://crystalbay.com/63-phan-thiet-di-vung-tau-bao-nhieu-km-n57483.html (TB) |
| Bảo Lộc | ~110–120 km | chưa xác minh | https://vntravel.org.vn/tag/cung-duong-bao-loc-phan-thiet.html (TB) |
| Đà Lạt | ~160 km (đường đèo) | chưa xác minh | https://cattour.vn/blog/tu-phan-thiet-di-da-lat-bao-nhieu-km-kham-pha-ve-dep-bat-tan-cua-mien-trung-viet-nam-1482.html (TB) |
| Phan Rang (nay thuộc Khánh Hòa) | ~130–150 km | khoảng 2 giờ 20 phút (xe khách) | https://cattour.vn/blog/xe-phan-thiet-phan-rang-phan-thiet-cach-phan-rang-bao-nhieu-km-2045.html (TB) |
| Nha Trang | ~220–250 km | chưa xác minh | https://langchaixua.com/du-lich-mui-ne/tu-nha-trang-di-phan-thiet-bao-nhieu-km/ (TB) |

Mọi điểm đến trong bảng đều nằm trong 300 km. Về mặt địa lý, xe chạy thẳng có thể giao trong ngày tới tất cả các điểm này.

## 3. Bảng so sánh từng bên

Các ký hiệu dùng trong bảng:
- ✅: có, kèm nguồn.
- ❌: không có, hoặc cấm.
- ❓: chưa xác minh.
- Cột "Lấy ở PT" nghĩa là bên đó có nhận lấy hàng ở Phan Thiết hay không.

### 3.1. Nhóm giao nhanh theo xe máy hoặc xe tải công nghệ

| Tiêu chí | **Ahamove** | **Lalamove** | **GrabExpress** | **beDelivery (Be)** | **Green SM Express (Xanh SM cũ)** |
|---|---|---|---|---|---|
| Lấy ở PT | ✅ Có mặt ở TP. Phan Thiết từ 09/03/2023 (Cao) [A1] | ✅ Nhận hàng từ Bình Thuận **cho xe van/tải liên tỉnh** (Cao) [L1]. Xe máy nội thành PT thì ❓ | ❓ Danh sách khu vực của GrabExpress có "Bình Thuận" nhưng nguồn là bài năm 2022 (TB) [G1] | ❓ Không thấy PT trong các nguồn [B1] | ❓ Có "Lâm Đồng" trong 19–23 tỉnh đang hoạt động, nhưng không rõ có khu Phan Thiết hay không (TB) [X1][X2] |
| Nội thành | Siêu tốc (khoảng ≤ 2 giờ sau khi tài xế nhận đơn), 2H, 4H, có ghép đơn [A2][A3] | Xe máy nội thành, nhưng ở PT thì ❓ | Siêu tốc. **Không nhận liên tỉnh** (TB) [G2] | nội thành, ở PT thì ❓ | nội thành, ở PT thì ❓ |
| Liên tỉnh < 300 km | Có dịch vụ liên tỉnh nhưng đi theo kho, mất 24–48 giờ tính từ TP.HCM. **Không thấy tuyến trong ngày xuất phát từ PT** [A4] | ✅ Xe van hoặc tải (0,5–2,5 tấn; miền Trung tới 1,25 tấn) chạy thẳng, nên về lý thuyết giao được trong ngày tới TP.HCM, Đồng Nai, Lâm Đồng, Khánh Hòa (Cao) [L1][L2]. Có dịch vụ "liên tỉnh xe máy" nhưng tuyến và cự ly tối đa thì ❓ [L3] | ❌ không có | ❓ | ❓ |
| Hàng tươi sống / đông lạnh | ⚠ **Mâu thuẫn.** Ahamove có trang "Giao thực phẩm tươi sống trong ngày" và loại đơn Fresh Food (cá, thịt, đông lạnh), nhưng các nguồn chỉ nhắc HN và HCM [A5]. Chính sách **liên tỉnh** ghi rõ "hàng đông lạnh, hàng tươi sống nằm ngoài phạm vi cung ứng" [A6] | ✅ Blog chính chủ nói có chở thịt và hải sản đông lạnh (Cao) [L4]. Chưa thấy danh mục hàng cấm chi tiết | ✅ GrabExpress Siêu tốc Thực phẩm nhận hải sản, thịt sống, cá tươi (TB) [G3]. Nhưng nguồn chỉ ghi áp dụng ở HN, HCM, Đà Nẵng [G4] | ❓ | ❓ |
| Giá tham khảo | Siêu tốc khoảng 15.709 đ cho 2 km đầu. 2H khoảng 19.636 đ cho 4 km đầu. 4H 24.000 đ cho 10 km đầu. Đây là giá chung, giá riêng PT thì ❓. Giờ 15h30–20h có thể nhân 1,5 lần [A7]. Lúc ra mắt ở PT có khuyến mãi 10.000 đ/đơn (3 đơn đầu) [A1] | Xe máy dưới 5 km: 20–30 nghìn đ (TB) [L5]. Xe van liên tỉnh: chỉ có mốc tham khảo **từ 800 nghìn đ/chuyến** cho tuyến HCM→Bình Phước [L6]. Tuyến PT→HCM thì ❓ | 16.000 đ cho 3 km đầu, sau đó 5.000 đ/km (Siêu tốc Thực phẩm, HN/HCM/ĐN; TB) [G4] | ❓ | 14.000 đ cho 2 km đầu, sau đó 5.000 đ/km (giá lúc ra mắt 12/2023; TB) [X3] |
| API | ✅ Công khai: tạo đơn, **ước tính phí**, **webhook** cập nhật trạng thái, **staging** (`partner-apistg.ahamove.com`), API lấy danh sách thành phố và dịch vụ. Muốn nhận key thì điền form (Cao) [A8] | ✅ API v3 công khai: **báo giá** (hiệu lực 5 phút), tạo đơn, **webhook** (thử lại 10 lần trong 24 giờ), **sandbox** (Cao) [L7]. ⚠ Tài liệu nêu market VN gồm `VN_SGN` và `VN_HAN`. Có hỗ trợ lấy ở PT hay không thì ❓ [L8] | ✅ GrabExpress API trên developer.grab.com (báo giá, tạo đơn, webhook, sandbox), có Việt Nam trong danh sách thị trường (TB) [G5]. Điều kiện mở cho VN thì ❓ | ❓ Không tìm thấy tài liệu API công khai [B2] | ❓ Không tìm thấy API công khai |
| Mở tài khoản | Tài khoản doanh nghiệp, điền form để nhận API key [A8] | Mở tài khoản doanh nghiệp, cấu hình webhook qua Partner Portal [L7] | ❓ | ❓ | ❓ |
| Chính sách dữ liệu cá nhân | ✅ Có công bố, ghi tuân theo NĐ 13/2023: https://ahamove.com/policy | ✅ https://www.lalamove.com/vi-vn/privacy-policy, có trang DPO | ✅ https://www.grab.com/vn/en/terms-policies/privacy-notice/ | ❓ | ❓ |
| Rủi ro chính | Chưa chắc có nhận hàng đông lạnh ở PT hay không. Không có tuyến liên tỉnh trong ngày | API có thể chưa phủ PT. Giá theo chuyến xe van thì cao với đơn 5 kg, trừ khi gom nhiều đơn một chuyến | Không đi liên tỉnh. Chưa rõ có ở PT không | Thiếu dữ liệu | Thiếu dữ liệu |

### 3.2. Nhóm chuyển phát (bưu cục, mạng lưới kho)

| Tiêu chí | **GHN** | **GHTK** | **Viettel Post** | **VNPost / EMS** | **J&T Express** | **SPX (Shopee Express)** | **BEST Express** | **Ninja Van** |
|---|---|---|---|---|---|---|---|---|
| Lấy ở PT | ✅ mạng lưới toàn quốc | ✅ toàn quốc | ✅ toàn quốc | ✅ toàn quốc | ✅ toàn quốc | ❓ chủ yếu đơn Shopee | ✅ | ❌ **Đã rút khỏi VN**, ngừng hẳn từ 30/09/2025 [N1] |
| Trong ngày < 300 km | Express nội vùng: nhận trong ngày hoặc muộn nhất sáng hôm sau, tuỳ giờ bàn giao [H2] | XFAST 3 giờ, **chỉ nội thành HN và HCM** [K2] | Hỏa tốc (VHT) 12–24 giờ, ở tỉnh ngoài danh sách chính thì tính 24 giờ. Nhanh (VCN) từ 60 giờ (TB) [V3] | ❓ | 1–5 ngày | ❓ SPX Instant chỉ dành cho đơn Shopee | ❓ | – |
| Tươi sống / đông lạnh | ❌ **Không nhận** hàng tươi sống và hàng đông lạnh (Cao) [H1] | ❌ **Không nhận** hàng tươi sống và đông lạnh. Hàng có điều kiện đặc biệt phải báo trước để GHTK xét (Cao) [K1] | ⚠ **Có nhận đông lạnh có điều kiện**: đóng thùng xốp và gel đá hoặc đá khô, **không có xe lạnh suốt tuyến**, **chỉ ở một số tỉnh**. Tuyến ngắn thì lấy trong ngày, lân cận 1–2 ngày. Không nhận cá sống, hải sản sống, thịt tươi (Cao, trang chính chủ) [V1] | ⚠ Blog nói bưu điện nhận đồ đông lạnh nếu đóng thùng xốp. Chưa có nguồn chính chủ (Thấp) [E1] | ⚠ Dịch vụ riêng **J&T Fresh** cho hàng tươi sống. Tuyến và thời gian thì ❓ [J1] | ❌ Cấm "thực phẩm yêu cầu bảo quản" ở dịch vụ thường (Cao) [S1] | ❌ Liệt kê "thực phẩm yêu cầu bảo quản" trong nhóm hạn chế (TB) [BE1] | – |
| Giá 5 kg | không tra, vì bị loại do chính sách hàng cấm | không tra, cùng lý do | ❓ nhân viên báo giá theo từng lô [V1] | ❓ | ❓ | – | – | – |
| API | ✅ api.ghn.vn: tính phí, tạo đơn, **callback trạng thái**, môi trường dev (Cao) [H3] | ✅ api.ghtk.vn: tạo đơn, tính phí, **webhook** (Cao) [K3] | ✅ partner2.viettelpost.vn: tạo đơn, tính cước, **webhook**, môi trường phát triển (Cao) [V2] | ✅ MyVNPost: tạo đơn và webhook có chữ ký RSA, phải xin whitelist IP (TB) [E2] | ❓ | ❓ | ❓ | – |
| Chính sách dữ liệu cá nhân | ✅ https://ghn.vn/pages/chinh-sach-bao-mat | ✅ https://ghtk.vn/chinh-sach-bao-mat-cua-ghtk/ | ✅ Có bản PDF ngày 01/04/2026: https://s3-north1.viettelidc.com.vn/app-vtp/about/20260401_Chinh-sach-bao-ve-du-lieu-ca-nhan-VTPost.pdf | ❓ | ❓ | ❓ | ❓ | – |
| Kết luận | Loại, vì cấm hàng | Loại, vì cấm hàng | **Ứng viên dự phòng** cho liên tỉnh (hàng đông lạnh + API), nhưng **không cam kết trong ngày** | Cần gọi xác minh | Cần gọi hỏi J&T Fresh | Loại | Loại | Loại |

### 3.3. Nhóm gửi theo xe khách hoặc nhà xe, và nền tảng vận tải

| Tiêu chí | **FUTA Express (Phương Trang)** | **Nhà xe / chành xe tuyến PT–SG** (Nam Hải Limousine, chanhxephanthiet.com…) | **VeXeRe BMS** | **Logivan / EcoTruck** |
|---|---|---|---|---|
| Lấy ở PT | ✅ có bưu cục và tuyến xe (TB) [F1] | ✅ [NX1][NX2] | Không phải bên vận chuyển. Đây là phần mềm cho nhà xe | Chuyên xe tải nguyên chuyến hoặc hàng lẻ Bắc–Nam [LG1] |
| Trong ngày | "Hỏa tốc" hợp với thực phẩm và hải sản. "Nếu trong vùng có thể giao nhận ngay trong ngày" (TB) [F1]. Tuyến PT→HCM cụ thể thì ❓ | Quảng cáo giao trong ngày, 3–4 giờ (TB) [NX1] | – | Không phù hợp đơn vài kg |
| Đông lạnh | ❓ Chưa thấy danh mục hàng cấm đề cập đến thùng xốp có đá | ✅ Các vựa hải sản ở PT đang dùng cách gửi xe để giao về HCM trong ngày (TB) [NX3] | – | – |
| Giá | ❓ Có bộ tính cước trên futaexpress.vn | ❓ | – | – |
| API | ⚠ Một đoạn trích nhắc "API FUTA Express giới hạn 1000 lời gọi/phút", nhưng **không tìm thấy tài liệu công khai**. Mức tin cậy Thấp | ❌ Không có | VeXeRe kết nối nhà xe với Grab hoặc Lalamove cho chặng cuối. **Không thấy API cho người gửi hàng** [VX1] | ❓ |
| Rủi ro | Đơn đến bến rồi còn cần chặng cuối tới nhà khách | Không có API, trạng thái đơn phải cập nhật tay | – | – |

### 3.4. Nhóm chuyên chuỗi lạnh (chỉ để tham khảo)

| Bên | Ghi chú |
|---|---|
| ABA Cooltrans | Có khoảng 300 xe lạnh, kho ở HN và HCM, trung tâm phân phối ở Thủ Đức. Có dịch vụ FTL và LTL. **Không thấy tuyến Phan Thiết**, và bên này phục vụ B2B/chuỗi siêu thị chứ không giao B2C tới từng nhà (Cao) [ABA1] |
| Minh Phú logistics, Lạnh Việt | Không tìm được thông tin về tuyến PT hay API, nên chưa xác minh |
| Chung | Nhóm này dư năng lực so với nhu cầu. Vựa đã tự đóng thùng giữ lạnh nên không cần xe lạnh |

## 4. Lưu ý dữ liệu cá nhân (bắt buộc)

- Nối API với bất kỳ bên nào ở trên đều có nghĩa là **gửi tên, SĐT và địa chỉ khách cho bên thứ ba**. Theo quy tắc dự án (CLAUDE.md và bất biến 9 trong skill `caveve-domain`), việc này **cần Duy duyệt trước**, và phải có **thoả thuận xử lý dữ liệu** với bên vận chuyển.
- Căn cứ pháp lý là **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15**, có hiệu lực từ 01/01/2026. Hướng dẫn chi tiết nằm ở NĐ 356/2025/NĐ-CP, văn bản thay NĐ 13/2023.
  - Nguồn: https://bocongan.gov.vn/chinh-sach-phap-luat/bai-viet/luat-bao-ve-du-lieu-ca-nhan-chinh-thuc-co-hieu-luc-thi-hanh-tu-ngay-01-01-2026-1767186124
  - Nguồn: https://thuvienphapluat.vn/van-ban/Bo-may-hanh-chinh/Luat-Bao-ve-du-lieu-ca-nhan-2025-so-91-2025-QH15-625628.aspx
- Những bên **có công bố chính sách bảo vệ dữ liệu cá nhân**: Ahamove, Lalamove (có trang DPO), Grab, GHN, GHTK và Viettel Post (bản 01/04/2026). Bảng mục 3 có link của từng bên.
- **Chưa bên nào công bố mẫu thoả thuận xử lý dữ liệu (DPA) cho đối tác API.** Đây là việc cần hỏi khi làm việc với họ.
- Chỉ gửi đi những trường tối thiểu: tên người nhận, SĐT, địa chỉ và ghi chú giao hàng. Không gửi lịch sử mua hàng. Không ghi payload có dữ liệu cá nhân vào log của adapter.
- Tham khảo thêm: Grab từng bị Singapore phạt vì làm lộ dữ liệu của khoảng 21.000 người dùng GrabHitch năm 2019 (https://mst.gov.vn/grab-bi-phat-vi-de-lo-du-lieu-ca-nhan-cua-hon-21000-nguoi-dung-197144621.htm).
- Báo cáo này không chứa dữ liệu khách thật nào.

## 5. Kết luận

### (a) Có bên nào đáp ứng đủ 3 điều kiện không?

Ba điều kiện là: lấy hàng ở Phan Thiết, giao trong ngày dưới 300 km, và có API.

**Chưa có bên nào được xác minh công khai là đáp ứng đủ cả 3 điều kiện, đồng thời nhận hàng đông lạnh.**

- **Lalamove** là bên gần đạt nhất. Họ nhận hàng từ Bình Thuận bằng xe van/tải liên tỉnh, chạy thẳng nên có thể giao trong ngày, có nhận hải sản đông lạnh, và có API v3 kèm sandbox và webhook. Nhưng **tài liệu API mới thấy market `VN_SGN` và `VN_HAN`**. Chưa rõ API có tạo được đơn lấy hàng ở Phan Thiết không. Giá theo chuyến xe cũng cao với đơn 5 kg.
- **Ahamove** đạt 2/3 điều kiện cho **nội thành Phan Thiết**: có mặt ở PT và có API đầy đủ. Tuy vậy chính sách của họ về hàng đông lạnh đang mâu thuẫn, và họ **không có tuyến liên tỉnh trong ngày**.

### (b) Top 3

| Hạng | Bên | Vai trò phù hợp | Lý do | Điểm yếu cần xác minh |
|---|---|---|---|---|
| 1 | **Ahamove** | Nội thành Phan Thiết | Có mặt ở PT từ 3/2023. API công khai đầy đủ nhất (ước tính phí, tạo đơn, webhook, staging). Có dịch vụ Siêu tốc khoảng ≤ 2 giờ và gói Fresh Food | Ở PT có nhận hàng đông lạnh trong thùng xốp không. Ở PT có những dịch vụ nào và giá bao nhiêu. Không đi liên tỉnh trong ngày |
| 2 | **Lalamove** | Liên tỉnh trong ngày (PT→HCM, Đồng Nai, Lâm Đồng, Khánh Hòa) | Duy nhất có xe van/tải nhận hàng ở Bình Thuận chạy thẳng liên tỉnh. Chấp nhận thực phẩm đông lạnh. Có API v3, sandbox và webhook | API có phủ PT không. Giá theo chuyến cao nên chỉ hợp khi gom nhiều đơn cùng hướng. Xe máy liên tỉnh có tuyến PT không |
| 3 | **Viettel Post** | Liên tỉnh dự phòng (không trong ngày) | Là hãng chuyển phát lớn duy nhất nói rõ nhận đông lạnh (thùng xốp và đá). API có webhook. Chính sách dữ liệu cá nhân mới cập nhật 2026 | Hỏa tốc mất 12–24 giờ, không phải trong ngày. Dịch vụ đông lạnh "chỉ ở một số tỉnh". Ở PT có hay không thì chưa rõ |

Hai bên đáng theo dõi thêm:
- **FUTA Express:** mạng lưới xe khách cho phép giao trong ngày PT→HCM, nhưng chưa có API công khai.
- **GrabExpress:** có API, nhưng chưa rõ có hoạt động ở PT không, và không đi liên tỉnh.

### (c) Khoảng trống

1. **Liên tỉnh trong ngày cho đơn lẻ vài kg, có API:** chưa bên nào phủ được.
   - Hãng chuyển phát thì cấm hàng đông lạnh, hoặc chỉ hỏa tốc 12–24 giờ.
   - Lalamove và nhà xe thì tính theo chuyến, hoặc không có API.
2. **Các tuyến Đà Lạt, Bảo Lộc (đường đèo), Phan Rang và Nha Trang:** không có nguồn nào nói rõ có dịch vụ giao trong ngày từ PT, trừ Lalamove xe van (vẫn cần xác minh).
3. **Chặng cuối ở nơi đến khi gửi xe khách** (bến xe → nhà khách) không có API liền mạch.
4. **Khung giờ tối và cao điểm:** Ahamove có hệ số giá khoảng x1,5 trong giờ 15h30–20h (giá chung). Nguồn cung tài xế ở PT vào tối muộn hoặc sáng sớm thì chưa rõ. Dịch vụ GrabExpress Siêu tốc chỉ nhận đơn từ 9h.
5. **Tết:** Ahamove năm 2026 tăng giá tới 2,2 lần (HCM) và đóng kho trong khoảng 14–20/02.
   - Nguồn: https://ahamove.com/lich-hoat-dong-tet-nguyen-dan-2026

### (d) Câu hỏi cần gọi điện xác nhận

**Ahamove** (hotline, hoặc bộ phận Partner/API):
1. Ở Phan Thiết, cụ thể là phường Phan Thiết của tỉnh Lâm Đồng mới, hiện có những dịch vụ nào (Siêu tốc, 2H, 4H, Fresh Food)? `city_id` trong API là gì?
2. Nội thành PT có nhận **hải sản đông lạnh đóng thùng xốp và đá, 1–10 kg** không? Nếu đá tan chảy nước thì ai chịu trách nhiệm?
3. Giá thực tế cho đơn 5 kg đi 5 km ở PT là bao nhiêu? Có phụ phí giờ cao điểm ở PT không?
4. Từ PT có tuyến liên tỉnh nào không, nhất là PT→HCM?
5. Ahamove có ký thoả thuận xử lý dữ liệu cá nhân (DPA) theo Luật 91/2025 với đối tác API không?

**Lalamove**:
1. API v3 có tạo được đơn **lấy hàng ở Phan Thiết/Bình Thuận** không, và dùng market/city code nào?
2. Giá xe van cho tuyến PT→TP.HCM, PT→Đà Lạt, PT→Nha Trang là bao nhiêu? Có ghép nhiều điểm giao (multi-stop) được không? Số điểm tối đa là bao nhiêu?
3. Dịch vụ "liên tỉnh xe máy" có tuyến nào xuất phát từ PT không? Cự ly tối đa và thời gian giao là bao nhiêu?
4. Danh mục hàng cấm có loại trừ hàng đông lạnh đóng thùng xốp và đá không?
5. Lalamove có DPA không?

**Viettel Post**:
1. Dịch vụ hàng đông lạnh có áp dụng cho bưu cục ở Phan Thiết không? Tuyến PT→HCM mất bao lâu?
2. Giá cho 5 kg hàng đông lạnh đi PT→HCM là bao nhiêu? Phụ phí đóng gói là bao nhiêu?
3. Có đặt mã dịch vụ đông lạnh qua API được không?

**FUTA Express**:
1. Có API cho doanh nghiệp không? Tài liệu ở đâu?
2. Có nhận thùng xốp hải sản có đá không?
3. Gửi ở PT lúc mấy giờ thì giao tận nhà ở HCM trong ngày?

**GrabExpress**:
1. Dịch vụ có hoạt động ở Phan Thiết không?
2. GrabExpress API có mở cho doanh nghiệp nhỏ ở Việt Nam không?

**J&T Express**: J&T Fresh có tuyến nào từ Phan Thiết không? Thời gian giao bao lâu? Có API không?

## Phụ lục: nguồn

Tất cả các nguồn dưới đây được truy cập ngày 2026-09-28. Tôi chỉ đọc đoạn trích qua WebSearch.

- [A1] https://ahamove.com/ahamove-chinh-thuc-co-mat-tai-tp-phan-thiet-voi-cuoc-phi-uu-dai-chi-10000d
- [A2] https://ahamove.com/dich-vu-giao-hang-thuc-pham
- [A3] https://ahamove.com/service/aha-delivery · https://ahamove.com/tinh-nang-ghep-don
- [A4] https://ahamove.com/thue-xe-tai-giao-hang-lien-tinh · https://ahamove.com/dich-vu-va-bang-gia-ahamove
- [A5] https://ahamove.com/dang-ky-biet-doi-cam-chot-don-hang-2h/ · https://ahamove.com/dich-vu-giao-hang-thuc-pham
- [A6] https://ahamove.com/chinh-sach-va-dieu-khoan-su-dung-dich-vu-giao-hang-lien-tinh · https://ahamove.com/danh-muc-hang-hoa-cam-tu-choi-van-chuyen-ung-tien
- [A7] https://ahamove.com/service/aha-delivery/price · https://ahamove.com/dich-vu-va-bang-gia-ahamove
- [A8] https://developers.ahamove.com/en/docs/introduction · https://developers.ahamove.com/en/docs/webhook · https://developers.ahamove.com/en/docs/api-reference/order-apis/estimate-order-fee · https://developers.ahamove.com/en/docs/api-reference/master-data/get-cities
- [L1] https://www.lalamove.com/vi-vn/4w/giao-lien-tinh-mien-trung
- [L2] https://www.lalamove.com/vi-vn/blog/giao-hang-lien-tinh
- [L3] https://www.lalamove.com/vi-vn/dich-vu-giao-hang-lien-tinh-xe-may
- [L4] https://www.lalamove.com/vi-vn/blog/dich-vu-giao-hang-thuc-pham-toan-quoc
- [L5] https://www.lalamove.com/vi-vn/bang-gia-giao-hang (con số lấy qua đoạn trích tổng hợp, mức tin cậy TB)
- [L6] https://www.lalamove.com/vi-vn/giao-hang-tphcm-binhphuoc
- [L7] https://developers.lalamove.com/ · https://developers.lalamove.com/files/v3_Webhook_v1.3.pdf
- [L8] https://developers.lalamove.com/ (market VN, dữ liệu từ đoạn trích, mức tin cậy TB)
- [G1] https://www.grab.com/vn/en/blog/driver/express/grabexpress-chuyenvunghoatdong/
- [G2] https://nhanh.vn/grabexpress-dich-vu-van-chuyen-hang-sieu-toc-chi-trong-4h-n113384.html
- [G3] https://www.sapo.vn/blog/grab-express-sieu-toc-thuc-pham
- [G4] https://help.grab.com/passenger/vi-vn/360000177968-Cuoc-phi-dich-vu-GrabExpress-Sieu-Toc-djuoc-tinh-nhu-the-nao
- [G5] https://help.grab.com/merchant/en-my/20000180-GrabExpress-API · https://apis.io/apis/grab/grab-express/
- [B1] https://be.com.vn/en/consumer/be-delivery/ · [B2] https://be.com.vn/tin-tuc/bedelivery-la-gi/
- [X1] https://tuoitre.vn/khoahocphothong/green-sm-bike-mo-rong-dich-vu-toi-19-tinh-thanh-tren-toan-quoc-104266758.htm
- [X2] https://dantri.com.vn/o-to-xe-may/green-sm-bike-co-mat-tai-quang-tri-an-giang-dong-thap-ca-mau-20260905123113595.htm
- [X3] https://vietnamnet.vn/xanh-sm-chinh-thuc-ra-mat-dich-vu-giao-hang-xanh-express-2222037.html
- [H1] https://ghn.vn/pages/hang-hoa-ghn-khong-nhan-van-chuyen
- [H2] https://ghn.vn/blogs/thong-tin-giao-hang/giao-hang-hoa-toc-la-gi
- [H3] https://api.ghn.vn/home/docs · https://api.ghn.vn/home/docs/detail?id=47 · https://api.ghn.vn/home/docs/detail?id=95
- [K1] https://ghtk.vn/tin-cho-nha-ban/danh-muc-hang-hoa-khong-nhan-van-chuyen/
- [K2] https://ghtk.vn/blog/giao-hang-sieu-toc/
- [K3] https://api.ghtk.vn/docs/submit-order/logistic-overview/ · https://api.ghtk.vn/docs/submit-order/webhook/
- [V1] https://viettelpost.com.vn/tin-tuc/bi-kip-trieu-don/viettel-post-co-gui-hang-dong-lanh-khong/
- [V2] https://partner2.viettelpost.vn/document
- [V3] https://nhanh.vn/viettel-post-giao-hang-trong-bao-lau-n42378.html
- [E1] https://emsvietnam.net/chuyen-phat-nhanh-hang-dong-lanh/ (không phải trang chính chủ)
- [E2] https://github.com/namph2402/shipping_integration (thông tin về webhook MyVNPost, mức tin cậy TB)
- [J1] https://jtexpress.vn/vi/fresh-service · https://vneconomy.vn/jt-fresh-van-chuyen-rieng-cho-san-pham-nong-san-va-hang-tuoi-song.htm
- [S1] https://spx.vn/downloads/templates/website/packaging_guideline_vn.pdf
- [BE1] https://nhanh.vn/best-express-don-vi-van-chuyen-an-toan-uy-tin-n71682.html
- [N1] https://dantri.com.vn/kinh-doanh/ninja-van-rut-khoi-thi-truong-giao-van-nhanh-viet-nam-20250904115129588.htm
- [F1] https://futaexpress.vn/dich-vu/chuyen-hoa-toc · https://theleader.vn/futa-express-bo-vai-nha-xe-viet-lai-luat-choi-logistics-d44866.html
- [NX1] https://limousineamazing.com/nha-xe-nam-hai-limousine/ · [NX2] https://chanhxephanthiet.com/ · [NX3] https://www.haisanphanthiett.com/hai-san-phan-thiet-giao-ve-tp-hcm-trong-ngay/
- [VX1] https://bms.vexere.com/giao-nhan-tan-noi-giai-phap-gui-hang-an-toan-va-tang-doanh-thu-trong-mua-dich-cho-nha-xe-tu-vexere/
- [LG1] https://ecotruck.vn/
- [ABA1] https://aba.com.vn/gioi-thieu-chung · https://aba.com.vn/vn/dich-vu-van-chuyen-hang-dong-lanh
