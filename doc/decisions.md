# Nhật ký quyết định kiến trúc — Cảng cá Lộc

Format: bối cảnh – lựa chọn – lý do – hệ quả (5 dòng/quyết định).

**Lưu ý xuyên suốt**: Dự án này là dự án tương lai — Lộc chưa vận hành thực tế. Những gì không phải Lộc phát biểu trực tiếp về mô hình kinh doanh (B2C, đông lạnh, giao hàng...) mà liên quan đến **hành vi vận hành cụ thể** (thao tác cân hàng, sai số, quy trình chi tiết) đều là **giả định thiết kế**, cần đánh dấu rõ và kiểm chứng lại khi Lộc bắt đầu vận hành thật — không hỏi Lộc như hỏi về "hiện tại đang làm sao" vì chưa có "hiện tại" nào cả.

## 2026-09-09 — Scope B2C thuần túy — [ĐÃ CHỐT: chỉ khách cá nhân]

- **Bối cảnh**: Dự án ban đầu kế thừa tinh thần "vựa thu mua – phân phối" (có thể phục vụ cả khách lẻ lẫn khách sỉ như quán ăn, nhà hàng).
- **Lựa chọn**: B2C thuần túy. **Đã chốt cuối**: Lộc là bên mua đi bán lại, chỉ bán cho khách cá nhân — KHÔNG có quán ăn/nhà hàng.
- **Lý do**: Lộc phát biểu trực tiếp bản chất mô hình kinh doanh (dự định).
- **Hệ quả**: Customer entity giữ đơn giản (cá nhân, có địa chỉ giao hàng) — không cần field phân loại khách hàng doanh nghiệp/mã số thuế/hạn mức tín dụng. Không có công nợ.

## 2026-09-09 — Hàng hoá là đông lạnh, quản lý theo lô (batch)

- **Bối cảnh**: Từ chat thực tế với Lộc — hàng "tươi nhưng cấp đông", không phải tươi sống bán trong ngày. Nguồn hàng theo mùa đánh bắt (thời vụ, không đều).
- **Lựa chọn**: Quản lý tồn kho theo lô nhập (batch/lot), mỗi lô đơn vị kg, hạn dùng gắn theo lô — hạn dùng nội bộ 3 tháng/lô (dù kỹ thuật cấp đông có thể để 6 tháng–1 năm).
- **Lý do**: Giá vốn và hạn dùng biến động theo từng lần nhập; 3 tháng là ngưỡng bảo thủ để đảm bảo chất lượng dù hạn kỹ thuật dài hơn.
- **Hệ quả**: Theo dõi theo ngày nhập lô là đủ. Quy trình: gom hàng theo lô → publish bán → hết lô đánh dấu hết hàng.
- **Gap đã giải quyết bằng doctype**: Stock Reconciliation (kiểm kê định kỳ) đo hao hụt.

## 2026-09-09 — Level 2: mapping doctype ERPNext, đơn giản hoá tối đa

- **Lựa chọn**: Giữ Item/Item Group/UOM/Batch/Warehouse/Price List/Item Price/Stock Entry/Stock Reconciliation (Kho); Supplier/Purchase Receipt/Purchase Invoice (Mua hàng, bỏ Purchase Order); Customer/Sales Order/Sales Invoice/Delivery Note (Bán hàng, bỏ Quotation).
- **Lý do**: ERPNext có sẵn toggle cho use case nhỏ gọn — `Supplier.allow_purchase_invoice_creation_without_purchase_order`, `Item.shelf_life_in_days/has_batch_no/has_expiry_date`.
- Sơ đồ chi tiết: `doctype-mapping.md` và artifact "Doctype Cảng Cá Lộc".
- **⚠ Cảnh báo tính nhất quán (phát hiện 2026-09-10)**: `doctype-mapping.md` được viết TRƯỚC quyết định "100% giao tận nhà" và "Sales Order booked TTL 30'", nên trong đó còn ghi "Delivery Note: Bỏ" và "Sales Order: Bỏ" — **đã lỗi thời, decisions.md và URD.md mới là bản đúng**. Cần viết lại `doctype-mapping.md` trước khi dịch sang Django models.

## 2026-09-09 — Sales Order booked (TTL 30'), Purchase Invoice tách riêng, Item Price lưu lịch sử

- **Purchase Invoice**: TÁCH riêng khỏi Purchase Receipt — hai việc khác nhau (kiểm đếm vật lý vs ghi chi phí).
- **Sales Order**: GIỮ, trạng thái "Đang giữ chỗ" (booked) — giữ Batch tạm, chưa trừ kho thật. **TTL 30 phút**, quá hạn tự huỷ nhả lô.
- **Item Price**: CÓ lưu lịch sử giá theo mùa (valid_from/valid_upto).

## 2026-09-09 — Mô hình vận hành: 100% giao hàng tận nhà — [ĐÃ CHỐT: nhân viên nội bộ giao]

- **Bối cảnh**: Quyết định đầu dự án "không làm giao hàng" bị hiểu nhầm — Lộc làm rõ: không hề có quầy, 100% đơn giao tận nhà. Ý gốc chỉ là không quản lý chi phí xe cộ/điều phối phức tạp (bài học từ vụ app shipper trước).
- **Lựa chọn**: Khôi phục Delivery Note dạng đơn giản (chờ lấy → đang giao → hoàn tất). **Đã chốt cuối**: người giao hàng là **nhân viên nội bộ** (không thuê ngoài/Grab/Ahamove).
- **Hệ quả**: Field "người giao" trên Delivery Note tham chiếu thẳng Django User (staff account đã có sẵn cho đăng nhập nội bộ). ⚠ **Câu "không cần entity Driver/Employee riêng" đã bị lật một phần ngày 10/09** — vẫn giữ FK trỏ `User`, nhưng thêm `StaffProfile` mỏng vì `User` không có số điện thoại. Xem quyết định 10/09 về phân quyền.
- Luồng đầy đủ: Customer (địa chỉ giao hàng) → Sales Order (booked, TTL 30') → xác nhận qua webhook thanh toán → Sales Invoice (trừ kho + thu tiền) → Delivery Note (soạn hàng → chờ lấy → đang giao → hoàn tất, gán nhân viên nội bộ).

## 2026-09-09 — Phí giao hàng: OUTSCOPE hoàn toàn, Lộc tự quản lý (sửa lại so với quyết định gốc)

- **Bối cảnh**: Quyết định gốc đầu dự án: "phí ship nội tỉnh set sau — nhưng chừa sẵn dòng phí ship trong cấu trúc đơn." Lộc làm rõ lại: mức phí này **outscope hoàn toàn**, tự quản lý ngoài hệ thống.
- **Lựa chọn**: KHÔNG chừa field/dòng phí ship trong Sales Order/Sales Invoice cho giai đoạn này — khác với giả định ban đầu là "chừa chỗ sẵn".
- **Lý do**: Lộc tự thoả thuận phí giao với khách ngoài hệ thống.
- **Hệ quả**: Đơn giản hoá thêm Sales Order/Invoice — không cần trường phí vận chuyển. Nếu sau này Lộc muốn đưa phí ship vào hệ thống, đây là điểm cần quay lại sửa (thêm field + logic tính).

## 2026-09-09 — Thanh toán: VietQR qua SePay (chọn tạm làm đại diện)

- **Lựa chọn**: SePay — chọn tạm để đi tiếp, không chặn thiết kế. Có thể đổi sang PayOS sau vì không ảnh hưởng schema.
- **Lưu ý còn treo**: cần Duy tự xác nhận điều kiện/phí hiện tại trực tiếp với SePay trước khi ký.

## 2026-09-09 — Backend: Django làm 100% lõi; FastAPI CHỈ là adapter cho bên thứ 3 — ĐÃ CHỐT

- **Bối cảnh**: Sau khi thảo luận phương án "dùng chung ORM", Duy chốt rõ hơn: Django làm hết phần lõi, FastAPI chỉ dùng khi tích hợp bên thứ 3 (T3) gọi vào — không có bên nào khác nối thẳng vào Django.
- **Lựa chọn (kiến trúc cuối)**:
  - **Django**: 100% lõi — ORM, migration, Admin panel (back-office cho Lộc/nhân viên), API (DRF) phục vụ Next.js (Shop/Landing gọi thẳng Django).
  - **FastAPI**: lớp adapter MỎNG, chỉ nhận call từ bên thứ 3 (hiện tại: webhook SePay) → validate/transform payload → gọi vào API nội bộ của Django (KHÔNG đụng DB/ORM trực tiếp).
  - Không bên thứ 3 nào được nối thẳng vào Django — luôn phải qua FastAPI trước.
- **Lý do**: Mẫu kiến trúc "anti-corruption layer" — cô lập lõi (Django) khỏi format/quirk riêng của từng bên thứ 3 (SePay, và các bên khác nếu có sau này). Tránh hoàn toàn rủi ro lệch schema so với phương án "dùng chung ORM" đã bàn trước đó.
- **Hệ quả**: Thêm 1 lượt gọi mạng (bên thứ 3 → FastAPI → Django) so với để webhook nằm thẳng trong Django, nhưng đổi lại cô lập rủi ro dữ liệu từ bên ngoài khỏi lõi. Cần cơ chế xác thực nội bộ giữa FastAPI và Django (service token riêng, không dùng chung auth với Next.js) — chi tiết để lại lúc build, không chặn thiết kế data model.
- **Cái đắt nếu sửa sau**: nếu để bên thứ 3 nối thẳng Django ngay từ đầu (bỏ qua FastAPI), sau này khó tách ra an toàn. Giữ nguyên tắc "FastAPI luôn là cửa vào duy nhất cho bên ngoài" ngay từ đầu để không phải sửa lớn khi có thêm bên thứ 3 mới.

## 2026-09-10 — Build mới bằng Django, KHÔNG fork/clone Frappe-ERPNext — ĐÃ CHỐT

- **Bối cảnh**: Duy hỏi trực tiếp nên clone ERPNext về chỉnh hay build mới, sau khi đã tham khảo sâu doctype ERPNext ở Level 2.
- **Lựa chọn**: Build mới hoàn toàn bằng Django models, chỉ dùng ERPNext làm tài liệu tham chiếu shape dữ liệu (đã trích xuất trong `doctype-mapping.md`) — không cài/fork Frappe framework.
- **Lý do**: Frappe là framework đóng khung chặt (ORM riêng, frontend Desk/Vue riêng, job queue riêng qua Redis+RQ, hàng trăm doctype không dùng tới như Kế toán sổ cái kép/HR/Manufacturing/Assets/Projects/CRM) — muốn lấy vài doctype vẫn phải gánh cả hệ thống. Ngoài ra Frappe xung đột trực tiếp 2 quyết định đã chốt: frontend Desk (Vue) thay vì Next.js, và ưu tiên MariaDB thay vì Postgres.
- **Hệ quả**: Toàn quyền kiểm soát schema, không có module thừa cần dọn, khớp 100% với stack đã chốt (Django + Next.js + Postgres). Việc dịch từ doctype-mapping.md sang Django models cần làm thủ công (không có tool auto-convert), nhưng khối lượng nhỏ vì đã đơn giản hoá tối đa ở Level 2.
- **Cái đắt nếu sửa sau**: nếu lỡ fork Frappe rồi sau muốn thoát sang Django/Next.js riêng — gần như viết lại từ đầu vì schema/ORM/auth/admin đều khoá vào runtime Frappe, tốn hơn build mới ngay từ đầu. Ngược lại, build Django trước mà thiếu tính năng ERPNext có sẵn (kế toán sổ cái kép, đa tiền tệ...) thì bổ sung dần rẻ hơn nhiều vì không bị ràng buộc kiến trúc người khác.

## 2026-09-10 — Social: không tích hợp API, đăng tay + báo cáo số liệu qua UTM nếu cần — [ĐỀ XUẤT DUY, ĐÃ CHỐT]

- **Bối cảnh**: Yêu cầu gốc "Social chỉ đăng bài, dẫn link vào Shop, không bán trên social" chưa nói rõ đăng bằng cách nào — tự động qua API hay thủ công.
- **Lựa chọn**: Đăng bài thủ công trực tiếp trên từng nền tảng (Facebook/Zalo/TikTok...) bằng công cụ có sẵn của nền tảng đó — không tích hợp API đăng bài, không OAuth, không scheduler riêng. Social không phải là 1 app/module trong hệ thống.
- **Lý do**: Duy đề xuất — khối lượng đăng bài của 1 vựa cá không đủ lớn để cần tự động hoá; social API (Meta/TikTok/Zalo) đòi hỏi review app, OAuth, quota — chi phí kỹ thuật không tương xứng lợi ích ở quy mô này.
- **Hệ quả**: Loại hoàn toàn nhu cầu tích hợp social platform ra khỏi backend. Nếu cần đo hiệu quả sau này, dùng UTM param trên link Shop + analytics phía Shop *(đề xuất của Product Architect, chưa phải yêu cầu)* thay vì kéo số liệu từ social API — rẻ và không đụng core.
- **Cái đắt nếu sửa sau**: Không có — Social là leaf node, không module lõi nào phụ thuộc vào nó. Tự động hoá đăng bài/kéo báo cáo sau này là việc thêm thuần tuý.

## 2026-09-10 — Soạn hàng: thêm bước trong Delivery Note; số kg đặt = số kg tính tiền = số kg trừ kho — [GIẢ ĐỊNH THIẾT KẾ, dự án chưa vận hành thực tế]

- **Bối cảnh**: Duy đặt câu hỏi hàng đông lạnh cần bước soạn hàng (cân/đóng gói) trước khi giao. Khi đào sâu, phát sinh câu hỏi số kg cân thực tế lúc soạn có luôn khớp số khách đặt online không. Duy làm rõ: **Lộc chưa vận hành thực tế, đây là dự án tương lai** — nên câu hỏi này không thể hỏi "hiện Lộc làm sao", mà là một quyết định thiết kế cần đặt ra trước.
- **Lựa chọn**:
  1. Thêm trạng thái "Soạn hàng" vào Delivery Note: **Soạn hàng → Chờ lấy → Đang giao → Hoàn tất** (trước đây chỉ có 3 trạng thái, thiếu bước chuẩn bị vật lý).
  2. V1: KHÔNG tách riêng "số kg thực cân" — số kg khách đặt trên Shop là số duy nhất dùng để tính tiền (VietQR) và trừ kho. Cân đúng số đặt là ràng buộc thao tác (vận hành), không phải thứ hệ thống theo dõi/đối soát.
- **Lý do**: (1) là bổ sung rẻ, không tranh cãi. (2) là **đề xuất của Product Architect**, chọn vì: thanh toán VietQR bắt buộc chốt số tiền *trước* khi soạn hàng (không thể đợi cân xong mới thu tiền); và chưa có dữ liệu vận hành thật nào để biện minh cho việc xây cơ chế đối soát chênh lệch cân nặng ngay từ V1.
- **Hệ quả**: Sales Invoice/kho đơn giản, không có logic điều chỉnh sau cân. Rủi ro: nếu thực tế sai số cân đáng kể và không được xử lý vận hành tốt, sổ cái giá vốn theo lô sẽ trôi dần theo thời gian — cần theo dõi qua Stock Reconciliation định kỳ như một tín hiệu cảnh báo sớm.
- **Cái đắt nếu sửa sau**: Thấp — nếu vận hành thật cho thấy cần tách bạch, chỉ cần thêm field "số kg thực xuất" ở Delivery Note/Sales Invoice line, không phải đổi kiến trúc. **Cần kiểm chứng lại giả định này ngay khi Lộc bắt đầu vận hành thật** (không phải trước đó, vì chưa có cách nào biết được).

## 2026-09-10 — Combo: 3 dạng, cấu hình trong Admin — KHÔNG xây rule engine tổng quát — [DUY CHỌN "FLEX", PA GIỚI HẠN PHẠM VI]

- **Bối cảnh**: "Trả thẳng có combo" nằm trong brief gốc của Lộc từ đầu nhưng **vắng mặt hoàn toàn** ở cả 4 tài liệu (URD, doctype-mapping, ecosystem-l1, decisions) cho tới 10/09. Duy chốt hướng: "làm flex có thể setup được thay vì fix cứng scheme".
- **Lựa chọn**: Hỗ trợ 3 dạng combo bằng **2 cơ chế**, cả hai cấu hình được trong Django Admin, không cần sửa code khi thêm combo mới:
  1. **Combo dạng gói (BUNDLE)** — `Item.item_type = BUNDLE` + bảng `BundleLine` (mặt hàng thành phần, định mức kg). Bán như 1 SKU với giá niêm yết riêng; khi chốt đơn thì nổ ra thành phần và trừ kho theo FIFO từng thành phần. Giá vốn combo = tổng giá vốn thành phần thực xuất.
  2. **Combo đóng gói sẵn** — không cần cơ chế mới: đó chỉ là `Item` thường (`item_type = SIMPLE`) có lô riêng, cân đóng sẵn lúc nhập.
  3. **Combo dạng ưu đãi (`PricingRule`)** — điều kiện 1 tầng (mua ≥ N kg mặt hàng X, hoặc đơn ≥ M đồng) → giảm số tiền hoặc %. Kho vẫn trừ từng mặt hàng riêng.
- **Lý do**: "Flex" được diễn giải là *cấu hình được trong Admin*, KHÔNG phải *rule engine tổng quát*. Ranh giới cố ý: PricingRule chỉ 1 tầng điều kiện, **không lồng nhau, không cộng dồn nhiều ưu đãi** (chọn rule có lợi nhất cho khách), không ngân sách khuyến mãi, không mã giảm giá. Rule engine tổng quát (DSL điều kiện, thứ tự ưu tiên, stacking) là thứ giết dự án do 1 người maintain — chi phí test tổ hợp tăng theo cấp số nhân.
- **Hệ quả**: Tồn khả dụng của BUNDLE là giá trị **tính ra**, không lưu: `min(floor(tồn khả dụng thành phần i / định mức i))`. Giữ chỗ 1 combo = giữ chỗ đồng thời tất cả thành phần; thiếu 1 thành phần thì không bán được combo. Báo cáo lãi lỗ theo lô vẫn đúng vì trừ kho ở mức thành phần.
- **Cái đắt nếu sửa sau**: Thấp nếu cần luật phức tạp hơn — thêm field vào PricingRule, hoặc thay riêng module ưu đãi (leaf node, không ai phụ thuộc). CAO nếu bây giờ xây DSL rồi bỏ. Cũng cao nếu chọn "combo = SKU độc lập" duy nhất rồi sau muốn tách thành phần — mất toàn bộ lịch sử giá vốn thành phần, không dựng lại được.

## 2026-09-10 — Huỷ đơn & hoàn tiền: có trong hệ thống, thực thi hoàn tiền là thủ công — [DUY CHỌN "1+3", PA SỬA LẠI VÌ RÀNG BUỘC NHÀ CUNG CẤP]

- **Bối cảnh**: Luồng bán hàng cho tới 10/09 chỉ có happy path — không có nhánh nào cho huỷ sau khi đã thu tiền, giao thất bại, khách từ chối nhận, hay soạn hàng phát hiện hàng hỏng. Duy chọn "1+3": vừa huỷ/hoàn kho trong hệ thống, vừa refund tự động qua cổng.
- **Lựa chọn**: Lấy (1), **loại (3) khỏi V1 vì không khả thi với nhà cung cấp đã chọn**. Thay vào đó dựng entity `Refund` (Phiếu hoàn tiền) là công dân hạng nhất, có field `method` = `MANUAL_TRANSFER` (V1) | `GATEWAY` (chỗ chừa sẵn, chưa hiện thực). Trạng thái: Chờ hoàn → Đã hoàn / Thất bại. Hỗ trợ hoàn **một phần**.
- **Lý do**: Kiểm chứng trực tiếp trang SePay và tài liệu developer — mô hình VietQR của SePay là *tiền vào thẳng tài khoản ngân hàng của người bán, không qua ví trung gian*, và SePay tự mô tả là nền tảng **giám sát/thông báo biến động số dư**. Tài liệu API của họ chỉ có webhook, tra cứu giao dịch, virtual account, IPN — **không có API hoàn tiền hay chuyển tiền đi**. Không giữ tiền thì không hoàn hộ được: hoàn tiền là một lệnh chuyển khoản từ chính tài khoản của Lộc.
- **Hệ quả**: Hệ thống chịu trách nhiệm *sổ sách* của việc hoàn (trạng thái đơn, hoàn kho, ghi nhận số tiền + mã giao dịch chuyển khoản nhập tay), còn *thao tác chuyển tiền* Lộc làm trên app ngân hàng. Sổ kho và sổ lãi lỗ vẫn đúng và truy được nguyên nhân. **Bổ sung 10/09**: quyền tách đôi — `create_refund` mở cho Quản lý, `confirm_refund` chỉ Chủ.
- **Cái đắt nếu sửa sau**: Thấp — vì `Refund` đã là entity riêng có `method`, sau này đổi sang cổng có API hoàn tiền chỉ là thêm một cách thực thi, không đụng schema đơn hàng/kho. Sẽ RẤT đắt nếu V1 không có `Refund` mà sửa kho bằng kiểm kê tay: mất dấu vết nguyên nhân, giá vốn theo lô trôi không giải thích được.

## 2026-09-10 — Chi phí phụ mua hàng gom vào giá vốn lô (landed cost) — [DUY CHỐT: CÓ]

- **Bối cảnh**: Trọng tâm dự án là "chi phí hàng hoá — giá vốn/lãi lỗ", nhưng cho tới 10/09 giá vốn chỉ gồm giá mua thuần; đá, xe từ cảng về, bốc vác không được tính vào đâu cả.
- **Lựa chọn**: Thêm chứng từ `PurchaseCost` (Chi phí mua hàng) gắn với một hoặc nhiều Purchase Receipt, có loại chi phí (đá / vận chuyển / bốc vác / khác) và phương pháp phân bổ (**theo kg** hoặc **theo giá trị**). Khi ghi nhận → cập nhật `Batch.landed_unit_cost`.
- **Lý do**: Duy chốt trực tiếp. Không gom thì lãi gộp theo lô luôn cao hơn thực tế và **không biết lệch bao nhiêu** — làm hỏng đúng thứ dự án sinh ra để đo.
- **Hệ quả**: Chi phí thường về SAU khi lô đã bán được vài kg → chấp nhận **giá vốn hồi tố**: giá vốn ghi trên đơn là ảnh chụp tại thời điểm bán, còn **báo cáo lãi lỗ theo LÔ tính lại từ `Batch.landed_unit_cost` hiện hành và là nguồn sự thật**; báo cáo theo đơn chỉ là chỉ báo. Kèm thao tác **chốt lô**. Quyền `add_purchasecost` và `close_batch` chỉ Chủ.
- **Cái đắt nếu sửa sau**: Trung bình-cao nếu bỏ qua bây giờ — thêm sau phải dựng chứng từ phân bổ *và* tính lại toàn bộ lô lịch sử (mà chứng từ chi phí cũ có thể không còn). Ngược lại nếu sau này thấy chi phí phụ không đáng kể, chỉ cần ngừng nhập `PurchaseCost`.

## 2026-09-10 — Phân quyền 3 tầng, thêm vai trò Quản lý, thêm StaffProfile — [DUY YÊU CẦU "CRUD + PROFILE + LEADER", PA NHẬN CẢ BA VỚI ĐIỀU KIỆN]

- **Bối cảnh**: Bản Level 3 v1 mô tả quyền bằng **động từ nghiệp vụ** ("được soạn hàng", "được duyệt kiểm kê") với 3 vai trò, và quyết định 09/09 đã chốt "không cần entity Driver/Employee riêng". Duy chất vấn: phải là CRUD, phải có profile, phải có leader.
- **Lựa chọn**:
  1. **Ba tầng quyền**, không phải một: (T1) CRUD theo model qua `auth.Permission` + `Group`; (T2) custom permission trong `Meta.permissions` cho các chuyển trạng thái (duyệt/chốt/huỷ/xác nhận); (T3) phạm vi dòng (`get_queryset`) và phạm vi cột (serializer/Admin tách theo Group).
  2. **Bốn Group cộng dồn** (`chu`, `quan_ly`, `nv_kho`, `nv_giao`) — không xếp bậc thang; người kiêm nhiệm gán nhiều Group.
  3. **`StaffProfile`** OneToOne với `User`: SĐT (bắt buộc), ngày vào làm, trạng thái, ghi chú. **Lật một phần quyết định 09/09.**
  4. **`AuditLog`** riêng cho mọi hành động T2.
- **Lý do**: CRUD là xương sống và Django cho sẵn — nhưng CRUD **không diễn đạt được** ba thứ: chuyển trạng thái ("nhập số kiểm kê nhưng chỉ Chủ duyệt"), phạm vi dòng ("chỉ đơn được gán cho mình"), phạm vi cột ("không thấy giá vốn"). Profile cần vì `User` **không có số điện thoại**, mà khách và Lộc phải gọi được người đang cầm hàng đi giao. Leader cần **không phải vì sơ đồ tổ chức mà vì Lộc đi cảng lúc rạng sáng** — bản v1 bắt "chỉ Chủ duyệt" cho kiểm kê/hàng hoàn/huỷ đơn, tức là hàng nằm chờ tới khi Lộc rảnh. Đó là nút cổ chai thật.
- **Hệ quả**: Đường ranh Chủ ↔ Quản lý: Quản lý được uỷ **mọi thứ làm khách phải chờ** (duyệt kiểm kê, duyệt hàng hoàn, huỷ đơn, tạo phiếu hoàn); Chủ giữ **mọi thứ làm tiền rời túi hoặc đổi con số lời lỗ** (`close_batch`, `add_purchasecost`, `confirm_refund`, `confirm_payment_manual`, `view_costprice`, `view_profitreport`, `manage_staff`). `confirm_payment_manual` không uỷ được vì phải đối chiếu sao kê — chỉ Lộc truy cập được. Cột `delete` gần như trống toàn bộ: chứng từ không xoá, chỉ huỷ bằng trạng thái. SalesOrder/SalesInvoice **không ai có quyền tạo tay** — chỉ Hệ thống tạo, chống ghi doanh thu khống. Mặc định Quản lý **không** xem giá vốn/lãi lỗ *(PA — rẻ để lật, chỉ là gán thêm permission vào Group)*.
- **Cái đắt nếu sửa sau**: Chỉ có **một** điểm thật sự đắt trong cả mục này — **chiều của FK**. Mọi FK nghiệp vụ (người giao, người nhập lô, người duyệt) phải trỏ `User`, `StaffProfile` chỉ là OneToOne mở rộng. Nếu trỏ FK vào `StaffProfile` thì ai chưa có hồ sơ là không làm được việc và migrate về sau rất phiền. Mọi thứ còn lại (thêm Group, đổi permission, thêm field profile) đều rẻ. Rủi ro triển khai lớn nhất không nằm ở thiết kế mà ở **field-level leak**: Django Admin ẩn cột thì dễ, nhưng DRF dùng chung serializer `fields='__all__'` sẽ trả đủ giá vốn cho bất kỳ ai gọi được endpoint — phải tách serializer theo Group và test bằng token nhân viên thật.

## 2026-09-10 — Các mặc định do PA chốt để không treo tiếp (Duy có quyền lật)

Những điểm dưới đây chưa từng được Lộc hoặc Duy phát biểu; PA chốt một mặc định để tài liệu đóng kín, chi tiết đầy đủ ở `business-process-spec.md`:

- **Danh tính khách**: guest checkout, `Customer` gộp theo số điện thoại (khoá tự nhiên). Khách **không phải `User`**, không nằm trong ma trận Group. Thêm đăng nhập OTP sau không đổi schema.
- **1 dòng đơn ăn nhiều lô**: BẮT BUỘC có bảng phân bổ lô con trên dòng hoá đơn (dòng ↔ lô ↔ số kg ↔ đơn giá vốn). Không có nó thì không tồn tại báo cáo giá vốn theo lô.
- **Tồn hiển thị trên Shop**: tồn khả dụng = tồn sổ − đang giữ chỗ. Không cho bán vượt.
- **Mua tại cảng**: trả tiền ngay, không gối đầu, không công nợ nhà cung cấp. *Câu hỏi mở #2 của `doctype-mapping.md` treo từ 09/09; nếu Lộc thực tế gối đầu thì phải mở lại.*
- **Ghi nhận doanh thu**: tại thời điểm xác nhận thanh toán, không phải lúc giao xong.
- **Hàng giao thất bại quay về**: nhập lại đúng lô gốc nhưng gắn cờ hàng hoàn, phải qua `approve_returntostock`; quá ngưỡng thời gian ngoài chuỗi lạnh thì mặc định huỷ bỏ và hạch toán lỗ vào lô.
- **Kiểm kê**: người nhập số và người duyệt phải là hai người khác nhau.

## Bối cảnh dự án (tham chiếu nhanh)

- Hệ thống mua hàng – bán hàng – quản lý kho cho vựa cảng cá của Lộc (bạn của Duy). **Đây là dự án tương lai — Lộc chưa vận hành thực tế**, nên mọi chi tiết hành vi vận hành cụ thể đều là giả định thiết kế, cần kiểm chứng khi vận hành thật. Timeline tự đặt 6 tháng, Duy làm gần một mình + AI hỗ trợ.
- Trọng tâm: mua hàng, bán hàng, chi phí hàng hoá (giá vốn/lãi lỗ). Bán theo kg, niêm yết giá, trả thẳng có combo.
- Hàng hoá: đông lạnh, nguồn theo mùa, hạn dùng nội bộ 3 tháng/lô, quản lý kho theo lô.
- **Combo: 3 dạng (gói có công thức / đóng gói sẵn / ưu đãi 1 tầng), cấu hình trong Admin, không có rule engine tổng quát.**
- **Giá vốn lô = giá mua + chi phí phụ phân bổ (landed cost). Báo cáo lãi lỗ theo lô là nguồn sự thật.**
- **Phân quyền: 3 tầng (CRUD model / custom action perm / phạm vi dòng-cột), 4 Group cộng dồn (`chu`, `quan_ly`, `nv_kho`, `nv_giao`), `StaffProfile` OneToOne với `User`, `AuditLog` cho mọi hành động duyệt-chốt-huỷ-xác nhận.**
- Landing (SEO) và Shop (giỏ hàng + thanh toán) tách nhau. **Social chỉ đăng tay, không tích hợp API** — chỉ dẫn link vào Shop.
- **Khách hàng: chỉ cá nhân, B2C thuần** (đã chốt cuối). Guest checkout, gộp theo SĐT, không có tài khoản hệ thống.
- **100% đơn giao tận nhà, nhân viên nội bộ giao** (đã chốt cuối). Không quản lý chi phí xe cộ/điều phối phức tạp.
- **Phí giao hàng: outscope hoàn toàn**, Lộc tự quản lý ngoài hệ thống.
- Thanh toán: VietQR qua SePay (chọn tạm), webhook tự xác nhận qua FastAPI adapter, khớp TTL giữ chỗ 30 phút. **Hoàn tiền: SePay không có API hoàn tiền — hệ thống ghi sổ, Lộc chuyển khoản tay.**
- Luồng bán hàng: Customer (địa chỉ giao hàng) → Sales Order (booked, TTL 30') → xác nhận qua webhook (SePay → FastAPI → Django) → Sales Invoice (trừ kho thật + thu tiền) → Delivery Note (soạn hàng → chờ lấy → đang giao → hoàn tất). Nhánh ngoại lệ: huỷ / hoàn tiền / hàng hoàn về kho — xem `business-process-spec.md`.
- Luồng mua hàng: Supplier → Purchase Receipt (trực tiếp tại cảng, không qua PO, sinh Batch) → Purchase Invoice (tách riêng) → Purchase Cost (chi phí phụ, phân bổ vào giá vốn lô) → Chốt lô.
- **Hướng kiến trúc (đã chốt)**: học mô hình doctype ERPNext làm tài liệu tham chiếu, build mới hoàn toàn bằng Django. Quy mô 1 điểm bán duy nhất.
- **Backend stack (ĐÃ CHỐT)**: Django 100% lõi; FastAPI CHỈ adapter mỏng cho bên thứ 3. Frontend Next.js. DB PostgreSQL.
- Nguyên tắc thiết kế xuyên suốt: hạn chế tối đa nhập liệu thủ công; ưu tiên đơn giản/dễ 1 mình maintain; ưu tiên công cụ có sẵn (Django Admin/auth) hơn tự build; bên thứ 3 luôn qua adapter; **chưa có dữ liệu vận hành thật → ưu tiên giả định đơn giản nhất, dễ mở rộng sau**.
- **Level 2 (doctype)**: `doctype-mapping.md` — ⚠ ĐÃ LỖI THỜI, cần viết lại. **URD v4**: `URD.md`. **Level 3 (nghiệp vụ chi tiết) v2: `business-process-spec.md`.**
- **Câu hỏi mở còn lại**: (1) mục tiêu nghiệp vụ suy luận ở URD 2.2, (2) service token FastAPI ↔ Django, (3) điều kiện/phí SePay, (4) giả định "số kg đặt = số kg thực giao", (5) combo thực tế bán dạng nào, (6) mua tại cảng có gối đầu không, (7) ngưỡng thời gian ngoài chuỗi lạnh, (8) **vựa có bao nhiêu người và có ai để Lộc uỷ quyền duyệt khi vắng mặt không**.

## 2026-09-26 — Xuất kho FEFO (hết hạn trước xuất trước) thay FIFO — [DUY CHỐT]
Hàng đông lạnh phải xuất lô **hạn dùng sớm nhất** trước. Chọn lô như sau:
- Chỉ xét các lô còn bán được (BR-LO-02 lọc trước).
- Sắp theo `expiry_date` tăng dần. Cùng hạn thì lô nhập sớm hơn ra trước, còn trùng nữa thì lô tạo trước.
- Áp dụng cho **toàn bộ mặt hàng**, gồm cả từng thành phần của combo.
- Lô được chốt **một lần lúc tạo đơn**, khi thanh toán không chọn lại (BR-BH-11).
- Hàng hoàn và huỷ đơn trả về lô gốc.
- V1 không cho chọn tay lô.

Quyết định này **thay thế** hai ghi chú trước:
- "theo dõi theo ngày nhập lô là đủ" (2026-09-09);
- "FIFO từng thành phần" (combo, 2026-09-10).

Hồ sơ: `doc/features/2026-09-26-fefo/`.

## 2026-09-26 — Hạn dùng mặc định hàng đông lạnh 12 tháng; giữ FEFO — [DUY CHỐT]
Hàng đông lạnh có hạn theo niên hạn, nên hạn dùng mặc định là **365 ngày** kể từ ngày nhập (trước đây là 90 ngày). Mức này áp cho tham số `BATCH_DEFAULT_SHELF_LIFE_DAYS` và cho giá trị mặc định `Item.shelf_life_in_days` của mặt hàng **tạo mới**. Mặt hàng và lô đã có thì giữ nguyên hạn.

**Giữ FEFO.** Khi mọi lô tính hạn theo cùng một công thức thì FEFO chọn lô giống hệt FIFO. FEFO chỉ khác khi có lô bị sửa hạn cho ngắn hơn; lúc đó FEFO giúp tránh phải huỷ hàng.

## 2026-09-26 — Thanh toán qua Cổng thanh toán SePay, chỉ VietQR — [DUY CHỐT]
- Cổng thanh toán SePay thay mã VietQR giả. **V1 chỉ có VietQR**: không thẻ, không NAPAS khác, không cọc, thanh toán 100%.
- Chỉ IPN `ORDER_PAID` gửi về adapter `/ipn/sepay` mới xác nhận được thanh toán. Khách quay lại `success_url` không có nghĩa là đã trả tiền.
- **Webhook ngân hàng SePay (`/webhook/sepay`) tắt ở V1.** Code vẫn giữ. Nếu bật lại thì phải chống ghi trùng với IPN.
- Giai đoạn sandbox dùng luôn production, dữ liệu hiện có coi là dữ liệu thử. **Shop chưa mở công khai** cho tới khi có khoá production. Trước khi mở phải dọn DB.
- Tổng đơn làm tròn về nguyên đồng.

Hồ sơ: `doc/features/2026-09-26-sepay-cong-thanh-toan/`.
