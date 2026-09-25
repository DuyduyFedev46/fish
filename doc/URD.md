---
Tài liệu: URD (gộp BRD — yêu cầu nghiệp vụ + yêu cầu người dùng)
Dự án: Hệ thống Mua hàng – Bán hàng – Quản lý kho cho Vựa Cá (Lộc)
Ngày: 2026-09-10
Người soạn: Duy (BA/PO) — tổng hợp cùng Claude (Product Architect)
Trạng thái: Draft v4 — bổ sung Combo, Huỷ & hoàn tiền, Chi phí phụ vào giá vốn lô; chi tiết nghiệp vụ tách sang business-process-spec.md
---

# 1. Giới thiệu

## 1.1 Mục đích tài liệu
Gộp cả yêu cầu nghiệp vụ (vì sao dự án tồn tại, mục tiêu) và yêu cầu người dùng (ai làm gì trên hệ thống) trong 1 tài liệu duy nhất, làm nguồn tham chiếu để chốt phạm vi, thiết kế data model chi tiết, và làm cơ sở trao đổi giữa Duy và Lộc.

**Chi tiết vận hành** (state machine, business rules đánh số, bảng ngoại lệ, ma trận phân quyền) nằm ở `business-process-spec.md` — tài liệu này chỉ giữ mức "cái gì", không lặp lại "chạy ra sao".

## 1.2 Đối tượng đọc
Lộc (người ra yêu cầu nghiệp vụ, người dùng cuối), Duy (BA/PO kiêm người triển khai), làm input cho các phiên thiết kế kỹ thuật tiếp theo.

## 1.3 Lưu ý quan trọng: đây là dự án tương lai
Lộc **chưa vận hành thực tế** hệ thống/mô hình này — đây là dự án xây trước khi vận hành, không phải số hoá một quy trình đang chạy. Hệ quả: các yêu cầu về **mô hình kinh doanh tổng thể** (bán cho ai, hàng gì, giao thế nào) là do Lộc phát biểu ý định. Nhưng các chi tiết **hành vi vận hành cụ thể** (thao tác cân hàng có sai số không, quy trình chi tiết từng bước...) chưa có thực tế để tham chiếu — những mục này trong tài liệu được đánh dấu là **giả định thiết kế**, chọn phương án đơn giản nhất trước, và cần kiểm chứng lại khi Lộc thực sự bắt đầu vận hành.

# 2. Bối cảnh & mục tiêu nghiệp vụ

## 2.1 Bối cảnh
Lộc dự định vận hành một vựa thu mua – phân phối hải sản đông lạnh (tươi nhưng cấp đông), mua đi bán lại, mô hình bán lẻ **B2C thuần túy cho khách cá nhân** (không bán cho quán ăn/nhà hàng). Giá niêm yết theo kg, không thương lượng từng mẻ, trả thẳng có combo. Nguồn hàng mang tính thời vụ theo mùa đánh bắt. **100% đơn hàng giao tận nhà cho khách**, do nhân viên nội bộ thực hiện — không có hình thức bán tại quầy.

Quy mô: 1 điểm bán/kho duy nhất. Timeline tự đặt 6 tháng. Duy phát triển gần như một mình, có AI hỗ trợ code. **Dự án chưa có vận hành thực tế làm cơ sở đối chiếu** — xem mục 1.3.

## 2.2 Mục tiêu nghiệp vụ *(suy luận từ bối cảnh — chưa được Lộc/Duy phát biểu trực tiếp, cần xác nhận lại)*
- Số hoá & chuẩn hoá vận hành mua – bán – kho, giảm sai sót từ ghi chép/tính toán thủ công
- Có căn cứ số liệu rõ ràng theo từng lô hàng để tính đúng giá vốn và lãi/lỗ (khó làm thủ công khi giá vốn biến động theo mẻ)
- Mở kênh bán online (landing + shop) tiếp cận khách hàng cá nhân, tách biệt khỏi cách bán truyền thống tại vựa
- Kiểm soát được hao hụt hàng tồn kho đông lạnh qua kiểm kê định kỳ

*Đây là phần suy luận của Product Architect dựa trên toàn bộ yêu cầu — không phải Lộc/Duy phát biểu trực tiếp. Anh xác nhận lại hoặc sửa nếu không đúng.*

# 3. Đối tượng người dùng (Actors)

| Actor | Mô tả |
|---|---|
| Khách hàng | Cá nhân đặt hàng qua Shop online, **không có tài khoản** — nhận diện bằng số điện thoại, tra đơn bằng mã đơn + 4 số cuối SĐT. Thanh toán trước qua VietQR, nhận hàng giao tận nhà bởi nhân viên nội bộ |
| Chủ vựa (Lộc) | Toàn quyền: danh mục, giá, combo, chi phí mua hàng, chốt lô, huỷ đơn, hoàn tiền, duyệt kiểm kê, duyệt hàng hoàn, xem báo cáo lãi lỗ |
| Nhân viên vận hành | Nhập lô, soạn hàng, giao hàng, nhập số kiểm kê. **Không** đụng tới giá, chi phí, hoàn tiền, báo cáo. Đăng nhập qua tài khoản nội bộ (Django User) |
| Hệ thống thanh toán (bên ngoài) | SePay (chọn tạm làm đại diện VietQR aggregator) — xác nhận thanh toán qua webhook, đi qua lớp adapter (FastAPI), không nối thẳng vào lõi hệ thống |

*Ma trận phân quyền đầy đủ: `business-process-spec.md` mục 1.*

# 4. Phạm vi

## 4.1 Trong phạm vi
- Quản lý danh mục mặt hàng, nhóm hàng, giá niêm yết (có lưu lịch sử giá theo mùa)
- **Combo — 3 dạng**: gói có công thức thành phần, hàng đóng gói sẵn, ưu đãi giảm giá 1 tầng. Cấu hình được trong Admin, không cần sửa code khi thêm combo mới
- Mua hàng: ghi nhận nhập kho theo lô, ghi nhận chi phí mua hàng (tách riêng khỏi bước nhập kho)
- **Chi phí phụ mua hàng (đá, vận chuyển, bốc vác) phân bổ vào giá vốn lô** (landed cost)
- Kho: quản lý tồn theo lô (số lượng kg, hạn dùng mặc định 90 ngày), vòng đời lô có bước **chốt lô**, kiểm kê định kỳ để đo hao hụt
- Bán hàng: giỏ hàng, đặt hàng, giữ chỗ tạm thời (TTL 30 phút), xác nhận thanh toán tự động qua webhook VietQR
- **Huỷ đơn & hoàn tiền**: hệ thống ghi sổ (trạng thái đơn, hoàn kho, phiếu hoàn tiền toàn phần/một phần); thao tác chuyển tiền do Lộc làm tay trên app ngân hàng
- **Hàng giao thất bại quay về kho**: ghi nhận, Chủ duyệt tái nhập hoặc huỷ bỏ
- Giao hàng: theo dõi trạng thái vận hành từ soạn hàng đến hoàn tất, gán nhân viên phụ trách
- Landing (giới thiệu, SEO) và Shop (bảng giá, giỏ hàng, thanh toán) — 2 mặt tiền tách biệt
- Social: đăng bài thủ công ngoài hệ thống, chỉ dẫn link thẳng vào Shop — không phải 1 module của hệ thống
- Báo cáo giá vốn/lãi lỗ **theo lô** (nguồn sự thật) và **theo kỳ** (điều hành)

## 4.2 Ngoài phạm vi (giai đoạn này)
- Bán sỉ/B2B, khách hàng doanh nghiệp, công nợ khách, đàm phán giá theo khách
- **Công nợ nhà cung cấp** — mua tại cảng trả tiền ngay, không gối đầu *(mặc định PA, cần Lộc xác nhận)*
- **Tài khoản đăng nhập cho khách** — V1 dùng guest checkout, gộp khách theo số điện thoại
- **Hoàn tiền tự động qua cổng thanh toán** — SePay không có API hoàn tiền/chuyển tiền đi (đã kiểm chứng); hoàn tiền là chuyển khoản tay, hệ thống chỉ ghi sổ
- **Rule engine khuyến mãi tổng quát** — không điều kiện lồng nhau, không cộng dồn ưu đãi, không mã giảm giá, không ngân sách khuyến mãi
- Điều phối/tối ưu tuyến giao hàng, quản lý chi phí xe cộ, app shipper phức tạp
- **Phí giao hàng**: hoàn toàn ngoài phạm vi hệ thống — Lộc tự thoả thuận và quản lý với khách
- Giao hàng qua đối tác thứ 3 (Grab/Ahamove) — chỉ dùng nhân viên nội bộ
- Đa kho, đa điểm bán/chuỗi cửa hàng
- Bán hàng trực tiếp trên mạng xã hội (social chỉ dẫn link, đăng tay, không tích hợp API)
- Đối soát/tách bạch số kg cân thực tế khác số kg đặt — xem giả định ở mục 6.4
- Đa ngôn ngữ

# 5. Yêu cầu người dùng theo vai trò

## 5.1 Khách hàng
- Xem danh mục mặt hàng, combo và giá niêm yết theo kg trên Shop
- Thấy đúng tình trạng còn/hết hàng (tồn khả dụng đã trừ phần khách khác đang giữ chỗ)
- Thêm mặt hàng/combo vào giỏ, đặt hàng (khởi tạo đơn ở trạng thái giữ chỗ)
- Nhập địa chỉ giao hàng và số điện thoại khi đặt (bắt buộc)
- Thanh toán qua quét mã VietQR; hệ thống tự động xác nhận khi nhận được tiền
- Nếu không thanh toán trong 30 phút, đơn tự huỷ và phải đặt lại
- Tra cứu trạng thái đơn bằng mã đơn + 4 số cuối SĐT: đã xác nhận / soạn hàng / chờ lấy hàng / đang giao / đã giao / đã huỷ

## 5.2 Chủ vựa (Lộc)
- Quản lý danh mục mặt hàng, nhóm hàng, bảng giá niêm yết, **cấu hình combo và ưu đãi**
- Ghi nhận lô hàng nhập và **chi phí phụ mua hàng**, xem giá vốn lô sau phân bổ
- **Chốt lô** khi lô bán hết — khoá số lãi/lỗ của lô
- Xem danh sách đơn cần xử lý, gán nhân viên phụ trách
- **Huỷ đơn đã thanh toán, tạo phiếu hoàn tiền (toàn phần/một phần), xác nhận đã chuyển khoản hoàn**
- **Duyệt hàng giao thất bại quay về**: tái nhập lô gốc hoặc huỷ bỏ hạch toán lỗ
- **Duyệt kiểm kê**, chốt chênh lệch hao hụt vào lô
- Xem báo cáo giá vốn/lãi lỗ theo lô và theo kỳ

## 5.3 Nhân viên vận hành
- Đăng nhập hệ thống bằng tài khoản nội bộ
- Ghi nhận lô hàng nhập: số lượng (kg), hạn dùng, nhà cung cấp, ngày nhập — thực hiện ngay tại cảng khi mua, không qua bước đặt hàng trước
- Xem danh sách đơn hàng đã xác nhận thanh toán, cần soạn/giao
- Soạn hàng (cân/đóng gói đúng số kg đã đặt) và tự cập nhật trạng thái giao đơn phụ trách
- Ghi nhận hàng giao thất bại mang về kho (chờ Chủ duyệt)
- Nhập số kiểm kê định kỳ (chờ Chủ duyệt)

# 6. Yêu cầu chức năng theo module

## 6.1 Mua hàng
- Ghi nhận nhập kho trực tiếp theo lô (không qua bước đặt hàng/PO với nhà cung cấp)
- Mỗi lô: gắn nhà cung cấp, số lượng kg, ngày nhập, hạn dùng (mặc định 90 ngày)
- Ghi nhận chi phí mua hàng như một bước tách biệt, gắn với lô đã nhập
- **Chứng từ chi phí phụ**: loại chi phí, số tiền, phương pháp phân bổ (theo kg hoặc theo giá trị), danh sách lô nhận phân bổ → cập nhật giá vốn lô

## 6.2 Kho
- Tồn kho quản lý theo lô, không gộp theo mặt hàng
- Xuất kho theo nguyên tắc **hết hạn trước xuất trước (FEFO)** khi bán: lô có hạn dùng sớm nhất xuất trước; cùng hạn thì lô nhập trước xuất trước. Áp dụng cho mọi mặt hàng, kể cả từng thành phần combo *(sửa 2026-09-26, xem decisions.md)*
- **Vòng đời lô**: Nháp → Đang bán → Cận hạn (cảnh báo, không tự giảm giá) → Hết hàng/Quá hạn → Đã chốt
- Kiểm kê định kỳ: đối chiếu tồn sổ sách với tồn thực tế, ghi nhận chênh lệch (hao hụt) — cũng là tín hiệu cảnh báo sớm nếu giả định ở mục 6.4 sai lệch trong thực tế
- Chỉ 1 kho duy nhất

## 6.3 Bán hàng
- Giá bán lấy từ bảng giá niêm yết hiện hành theo mặt hàng, không nhập tay từng đơn
- **Combo**: bán như 1 mặt hàng có giá niêm yết riêng; combo dạng gói khi chốt đơn thì nổ ra thành phần và trừ kho theo từng lô thành phần; tồn khả dụng combo tính từ thành phần khan hiếm nhất
- Đặt hàng qua giỏ hàng tạo đơn ở trạng thái "giữ chỗ" — giữ tạm số lượng trong lô tương ứng, chưa trừ tồn kho chính thức
- Trạng thái "giữ chỗ" tự động huỷ sau 30 phút nếu không được xác nhận thanh toán, nhả lại số lượng đã giữ
- Tồn hiển thị trên Shop = tồn sổ − đang giữ chỗ; không cho bán vượt
- Khi thanh toán được xác nhận (qua webhook), đơn chuyển sang trạng thái chính thức, trừ tồn kho thật và ghi nhận doanh thu — dùng **số kg khách đặt** (xem giả định mục 6.4)
- **Một dòng đơn có thể lấy hàng từ nhiều lô** — hệ thống lưu bảng phân bổ dòng ↔ lô ↔ kg ↔ đơn giá vốn, làm nền cho toàn bộ báo cáo giá vốn
- **Không có trường/logic phí giao hàng trong đơn** (đã chốt outscope)

## 6.4 Giao hàng
- Sau khi đơn được xác nhận thanh toán, tạo phiếu giao hàng theo dõi vận hành
- Trạng thái phiếu giao hàng: **soạn hàng → chờ lấy hàng → đang giao → hoàn tất**, có nhánh **giao thất bại** (đếm số lần thử, hẹn giao lại hoặc mang về kho)
- "Soạn hàng": nhân viên cân/đóng gói cách nhiệt đúng số kg đã đặt cho từng mặt hàng trong đơn
- Gán nhân viên nội bộ phụ trách giao đơn (tham chiếu tài khoản nhân viên có sẵn trong hệ thống)
- Không có chức năng định tuyến, tối ưu lộ trình, hay theo dõi chi phí vận chuyển
- **Giả định thiết kế (chưa kiểm chứng, dự án chưa vận hành thực tế)**: số kg cân thực tế lúc soạn hàng luôn khớp số kg khách đặt online — hệ thống KHÔNG ghi nhận/đối soát số kg thực xuất riêng biệt trong V1. Đây là lựa chọn đơn giản hoá có chủ đích (Product Architect đề xuất), vì thanh toán VietQR bắt buộc chốt tiền trước khi soạn hàng. Cần kiểm chứng lại khi Lộc bắt đầu vận hành thật; nếu sai số đáng kể, bổ sung field "số kg thực xuất" sau — không phải sửa kiến trúc.

## 6.5 Thanh toán
- Thanh toán qua mã VietQR động, tạo riêng cho từng đơn
- Nhà cung cấp: **SePay** (chọn tạm làm đại diện — có thể đổi sau, không ảnh hưởng schema)
- Xác nhận thanh toán tự động qua webhook, đi qua lớp adapter riêng — không nối thẳng vào lõi hệ thống
- Chống trùng webhook bằng mã giao dịch ngân hàng
- **Cần màn hình xác nhận thanh toán thủ công** cho trường hợp webhook không tới — nếu không có, webhook lỗi làm đơn treo vĩnh viễn
- Tiền về thiếu, hoặc tiền về sau khi đơn đã tự huỷ → không tự xử lý, đẩy vào hàng chờ Chủ quyết

## 6.6 Huỷ đơn & hoàn tiền
- Bốn tình huống huỷ: quá TTL chưa trả tiền (tự động) / khách đổi ý sau khi trả tiền / soạn hàng phát hiện hàng hỏng / giao thất bại thôi không giao
- Huỷ sau khi đã thu tiền → hoàn kho về đúng lô gốc + tạo **phiếu hoàn tiền**
- Phiếu hoàn tiền hỗ trợ **toàn phần và một phần**, bắt buộc nhập mã giao dịch chuyển khoản khi xác nhận đã hoàn
- Thao tác chuyển tiền do Lộc làm trên app ngân hàng — hệ thống chịu trách nhiệm sổ sách, không tự động chuyển tiền
- Chỉ Chủ được huỷ đơn đã thu tiền và xác nhận hoàn tiền

## 6.7 Hàng giao thất bại quay về kho
- Ghi nhận hàng mang về (lô gốc, số kg, giờ rời kho, giờ về kho)
- Chủ duyệt: **tái nhập** (cộng lại đúng lô gốc, gắn cờ hàng hoàn) hoặc **huỷ bỏ** (hạch toán lỗ hàng hỏng vào lô gốc)
- Vượt ngưỡng thời gian ngoài chuỗi lạnh → hệ thống mặc định đề xuất huỷ bỏ; ngưỡng cấu hình được, **cần Lộc cho con số thực tế**
- Nhân viên không được tự nhập lại kho

## 6.8 Landing & Shop
- Landing: trang giới thiệu, tối ưu SEO, không có giao dịch
- Shop: hiển thị bảng giá, giỏ hàng, thanh toán — tách biệt hoàn toàn khỏi Landing
- Link từ mạng xã hội trỏ thẳng vào Shop, không qua trang trung gian; social tự đăng bài thủ công, không có tích hợp/API nào giữa hệ thống và các nền tảng social

## 6.9 Báo cáo
- **Lãi lỗ theo lô** (nguồn sự thật): doanh thu bán từ lô − (giá mua + chi phí phân bổ + hao hụt + hàng hỏng). Chốt lô là chốt số
- **Lãi lỗ theo kỳ** (điều hành, theo tháng): doanh thu ghi nhận − giá vốn ghi nhận − hoàn tiền trong kỳ
- Doanh thu ghi nhận tại thời điểm **xác nhận thanh toán**, không phải lúc giao xong
- Lô chưa chốt hiển thị nhãn "tạm tính"

# 7. Yêu cầu phi chức năng

- **Đơn giản vận hành**: ưu tiên dễ vận hành/bảo trì bởi 1 người hơn tối ưu hiệu năng/độ chính xác tuyệt đối
- **Hạn chế nhập liệu thủ công**: giá, chi phí combo, giá trị tính toán được nên tự động hoá tối đa
- **Độ tin cậy của cơ chế giữ chỗ**: job tự huỷ đơn quá hạn (30 phút) phải chạy ổn định, **giám sát được và có cảnh báo khi chết** — job này hỏng thì hàng bị khoá vô hình, không ai biết cho tới khi Shop báo hết hàng oan
- **Cô lập bên ngoài khỏi lõi**: mọi tích hợp bên thứ 3 phải đi qua lớp adapter riêng, không nối thẳng vào hệ thống lõi
- **Truy vết số nhạy cảm**: mọi thay đổi giá vốn lô và mọi phiếu hoàn tiền phải ghi log (ai, khi nào, chứng từ nào)
- **Phân quyền theo bản chất việc**: nhân viên làm việc phát sinh từ thao tác vật lý; việc đụng tới tiền và giá vốn chỉ Chủ làm
- **Khả năng mở rộng có kiểm soát**: kiến trúc không cố tình chặn mở rộng sau này (thêm kho, thêm điểm bán, thêm bên thứ 3, tài khoản khách, tách bạch số kg thực giao) nhưng không xây dựng trước cho nhu cầu chưa xác nhận bằng thực tế vận hành

# 8. Giả định & ràng buộc kỹ thuật

- **Backend (đã chốt)**: Python — **Django làm 100% lõi** (ORM, migration, Admin panel quản lý master data, API phục vụ Next.js). **FastAPI chỉ là lớp adapter mỏng cho bên thứ 3** (nhận webhook SePay, gọi vào API nội bộ Django, không đụng DB trực tiếp) — không bên ngoài nào nối thẳng vào Django.
- **Frontend**: Next.js
- **Cơ sở dữ liệu**: PostgreSQL
- Kiến trúc tham khảo doctype ERPNext làm tài liệu, **build mới hoàn toàn bằng Django — không cài/fork Frappe framework**
- Cơ chế tự huỷ đơn quá hạn: recurring job định kỳ trong hệ sinh thái Python (Celery Beat, cụ thể chọn khi build)
- Cần cơ chế xác thực nội bộ (service token) giữa FastAPI và Django — chi tiết để lúc build
- **Ràng buộc từ nhà cung cấp thanh toán (đã kiểm chứng)**: SePay theo mô hình tiền vào thẳng tài khoản ngân hàng người bán, không qua ví trung gian; tài liệu API chỉ có webhook/tra cứu/virtual account/IPN, **không có API hoàn tiền hay chuyển tiền đi** → hoàn tiền tự động không khả thi ở V1
- **Giả định vận hành chưa kiểm chứng**: số kg khách đặt = số kg thực cân khi soạn hàng = số kg trừ kho (xem mục 6.4)
- **Giá vốn hồi tố**: chi phí phụ có thể về sau khi lô đã bán một phần → giá vốn ghi trên đơn là ảnh chụp, báo cáo theo lô tính lại từ giá vốn hiện hành. Hai con số có thể lệch trong lúc lô còn mở

# 9. Thuật ngữ

| Thuật ngữ | Giải thích |
|---|---|
| Lô (Batch) | Đơn vị hàng nhập theo từng lần mua tại cảng, tính bằng kg, có hạn dùng và nhà cung cấp riêng |
| Giữ chỗ (Booked) | Trạng thái đơn hàng đã tạo, đã giữ tạm số lượng trong lô, nhưng chưa xác nhận thanh toán |
| TTL | Thời gian tối đa một đơn được giữ ở trạng thái "giữ chỗ" trước khi tự huỷ (30 phút) |
| FEFO | First Expired, First Out: lô hết hạn trước thì xuất trước. Đây là nguyên tắc chọn lô khi bán *(sửa 2026-09-26, xem decisions.md)* |
| FIFO | First In, First Out: lô nhập trước xuất trước. Chỉ dùng làm **tiêu chí phụ** khi hai lô cùng hạn dùng, không còn là nguyên tắc chọn lô chính *(sửa 2026-09-26, xem decisions.md)* |
| Kiểm kê | Đối chiếu định kỳ giữa tồn kho ghi trên hệ thống và tồn thực tế đếm được |
| Soạn hàng | Bước nhân viên cân/đóng gói hàng đúng số kg đã đặt, trước khi bàn giao cho người giao hàng |
| Combo dạng gói | Mặt hàng bán có công thức thành phần; khi bán thì nổ ra và trừ kho từng thành phần |
| Giá vốn lô (landed cost) | Giá mua lô cộng chi phí phụ được phân bổ, chia cho số kg nhập ban đầu |
| Chốt lô | Thao tác khoá lô sau khi bán hết — không cho thêm chi phí, không nhận hàng hoàn, lãi/lỗ đông cứng |
| Phiếu hoàn tiền | Chứng từ ghi nhận việc hoàn tiền cho khách; thực thi bằng chuyển khoản tay ở V1 |
| Aggregator (thanh toán) | Bên trung gian kết nối tài khoản ngân hàng, tự động báo hệ thống khi nhận được tiền qua VietQR (SePay) |
| Adapter | Lớp trung gian (FastAPI) cô lập lõi hệ thống (Django) khỏi format/quirk của bên thứ 3 |

# 10. Câu hỏi mở / rủi ro còn treo

**Cần Lộc trả lời:**
1. Combo thực tế sẽ bán ở dạng nào trong 3 dạng (gói có công thức / đóng gói sẵn / ưu đãi)? Có thể nhiều dạng cùng lúc.
2. Mua tại cảng có gối đầu với đầu mối quen không, hay trả ngay 100%? *(Gối đầu ⇒ phải mở lại công nợ nhà cung cấp, hiện đang outscope.)*
3. Hàng ra khỏi chuỗi lạnh bao lâu thì không bán lại được? Con số này quyết định ngưỡng duyệt hàng hoàn.
4. Xác nhận lại mục tiêu nghiệp vụ ở mục 2.2 — phần Product Architect suy luận, chưa được phát biểu trực tiếp.

**Duy tự xử lý:**
5. Xác nhận chính thức với SePay về điều kiện/phí hiện tại trước khi ký; hỏi luôn khả năng hoàn tiền qua đường thẻ quốc tế nếu sau này cần.
6. Cơ chế xác thực nội bộ giữa FastAPI và Django (service token) — chi tiết kỹ thuật, không chặn thiết kế data model.

**Chỉ kiểm chứng được khi vận hành thật:**
7. Giả định "số kg khách đặt = số kg thực giao" (mục 6.4) — theo dõi qua hao hụt kiểm kê.

**Nợ tài liệu:**
8. `doctype-mapping.md` đã lỗi thời (còn ghi "bỏ Sales Order", "bỏ Delivery Note") và chưa có 6 thực thể mới phát sinh từ `business-process-spec.md`. Phải viết lại trước khi dịch sang Django models.

---
*Tài liệu tham chiếu liên quan trong project: `business-process-spec.md` (Level 3 — nghiệp vụ chi tiết, state machine, business rules), `decisions.md` (nhật ký quyết định kiến trúc), `doctype-mapping.md` (Level 2 — ⚠ lỗi thời), `ecosystem-l1.md` (sơ đồ tổng thể), artifact "Doctype Cảng Cá Lộc" (sơ đồ Level 2).*
