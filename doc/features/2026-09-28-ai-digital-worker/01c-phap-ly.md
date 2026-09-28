# Memo pháp lý: đề xuất "AI là digital worker" (AI tự thực thi, việc nào không làm được thì escalate)

> Soát ngày **2026-09-28** · legal-vn · Hồ sơ: `doc/features/2026-09-28-ai-digital-worker/`
> Nguồn nền đã đọc: `2026-09-27-ai-native-erp/00-adr-ai-native.md` (2.6, 2.11), `01-analysis.md` §4.3, §4.10, §7 (BR-AI-06/07/08/09), `research/03-luat-ai-va-bao-ve-du-lieu.md`, `doc/ops/go-live-phap-ly.md`, `doc/decisions.md`.
>
> **Đây là tài liệu tham khảo nội bộ, không phải tư vấn pháp lý.** Các ô ⚠ cần luật sư hoặc kế toán xác nhận.
>
> **Giới hạn kiểm chứng hôm nay:** WebFetch bị proxy chặn ở mọi trang luật (thuvienphapluat, luatvietnam, vanban.chinhphu.vn, baochinhphu, mst.gov.vn…). Vì vậy mọi kết luận dưới đây dựa trên **đoạn trích của kết quả WebSearch** từ nhiều nguồn độc lập, chưa đọc được toàn văn. Số điều nào không có trong đoạn trích được ghi **"chưa xác minh"**.

## 0. Đề xuất và cách hiểu

Duy (2026-09-28): *"Chỉ tạo bản nháp, người bấm xác nhận mới ghi. Việc tiền và chốt lô thì AI không được đụng tới → anh nghĩ là để AI tự làm cũng được, coi AI như digital worker, cái nào không làm được thì escalate tới người dùng."*

Memo hiểu rằng đề xuất này bỏ BR-AI-06 (mọi hành động Tầng 2 dừng ở bản nháp) và có thể nới BR-AI-07 (cấm AI `confirm_refund`, `confirm_payment_manual`, `close_batch`). Đây là hai quyết định nhãn **D** trong hồ sơ 27/09. Memo không lật quyết định. Mục 9 ghi đề xuất để Duy chốt.

## 1. Kết luận nhanh

1. **Cho AI tự làm không tự động đẩy hệ thống lên "rủi ro cao".** Theo luật Việt Nam, rủi ro cao là hệ thống **nằm trong Danh mục của Thủ tướng**. Danh mục đó đã ban hành theo **QĐ 33/2026/QĐ-TTg** (ký 30/6/2026, hiệu lực 15/8/2026), gồm 46 hệ thống thuộc 6 lĩnh vực. ERP của một vựa cá không thuộc lĩnh vực nào trong số đó. Mục ngân hàng nhắm tới *"AI tự động thực hiện giao dịch điện tử **trong hoạt động ngân hàng**"* và *"AI tự động quyết định cấp tín dụng"*, tức áp cho tổ chức tín dụng. ⚠ Nếu sau này AI tự gọi API ngân hàng để chuyển tiền thì phải hỏi luật sư.
2. **Phải viết lại lý do phân loại.** ADR ghi lý do xếp "trung bình" là *"chỉ đề xuất, không tự quyết"*. Đó **không phải tiêu chí pháp lý**. Tiêu chí của NĐ 142 là hệ thống không thuộc Danh mục và có khả năng gây nhầm lẫn về chủ thể AI. Khi AI tự thực thi, hồ sơ phân loại phải mô tả đúng mức tự chủ. Nếu mô tả sai thì nhà cung cấp chịu trách nhiệm về tính trung thực của kết quả phân loại.
3. **Với hệ thống không thuộc rủi ro cao, luật không bắt người duyệt từng giao dịch.** Mô hình con người giám sát (human-on-the-loop) được chấp nhận nếu còn **khả năng kiểm soát và can thiệp của con người** với mọi quyết định và hành vi của AI. Đây là nguyên tắc chung của Luật AI. Con người duyệt *trước khi quyết định có hiệu lực* chỉ là nghĩa vụ cứng với hệ thống rủi ro cao.
4. **Tuy vậy, với việc tiền và chốt lô, nên giữ người duyệt vì các luật khác, không phải vì Luật AI.** Lý do: (a) Luật Kế toán yêu cầu chứng từ thu, chi và giá vốn có chữ ký người lập và **người duyệt**, mà AI không có tư cách pháp lý; (b) Lộc chịu **trách nhiệm trực tiếp** với khách khi hoàn tiền sai hoặc ghi nhận tiền sai (Luật BVQLNTD 2023, BLDS 2015, Luật AI Điều 29); (c) quyết định tự động ảnh hưởng tới khách kéo theo nghĩa vụ **thông báo, giải thích thuật toán và cho khách lựa chọn không tham gia** (NĐ 356/2025). Nghĩa vụ này tốn kém hơn nhiều so với một cú bấm xác nhận.
5. **Kết luận:** đề xuất **nguyên dạng**, tức AI tự làm cả việc tiền và chốt lô, được đánh giá **CHƯA ĐẠT**. **Phương án 3 vùng** ở mục 7 được đánh giá **ĐẠT có điều kiện**, và cũng là phương án rẻ nhất về nghĩa vụ. Theo phương án này, AI tự làm việc đọc, nháp, cảnh báo và vận hành đảo ngược được. Việc tiền, chốt lô và quyết định bất lợi cho khách vẫn cần người duyệt từng lần.

## 2. Câu 1: AI tự thực thi có làm đổi mức rủi ro không?

| Nội dung | Kết quả kiểm chứng (2026-09-28) |
|---|---|
| Căn cứ phân loại | Luật AI 134/2025/QH15 **Điều 9** chia 3 mức: cao, trung bình, thấp. Luật hiệu lực 01/3/2026. NĐ 142/2026/NĐ-CP ban hành 30/4/2026, hiệu lực 01/5/2026. **Điều 8** của nghị định quy định tiêu chí rủi ro cao, **khoản 2 Điều 8** quy định các trường hợp loại trừ (nội dung khoản 2 **chưa xác minh**). Nhà cung cấp **tự phân loại** trước khi đưa vào sử dụng và **chịu trách nhiệm trước pháp luật về tính chính xác, trung thực** của kết quả. |
| Rủi ro cao | Hệ thống nằm trong **Danh mục theo QĐ 33/2026/QĐ-TTg** (ký 30/6/2026, **hiệu lực 15/8/2026**), gồm 46 hệ thống trong 6 lĩnh vực: giáo dục, dân tộc và tôn giáo, y tế, **ngân hàng** (2 hệ thống), tố tụng, giao thông vận tải. Hai hệ thống ngân hàng là *"AI tự động thực hiện giao dịch điện tử trong hoạt động ngân hàng"* và *"AI tự động quyết định cấp tín dụng"*. Với các hệ thống này, quyết định AI đề xuất phải được cấp có thẩm quyền phê duyệt, không được tự động hoá hoàn toàn, trừ nghiệp vụ chống gian lận và rửa tiền. **Research 27/09 ghi "danh mục chưa công bố" nay đã lỗi thời.** |
| Rủi ro trung bình | NĐ 142: hệ thống (i) **không thuộc Danh mục rủi ro cao** và (ii) **có khả năng gây nhầm lẫn, tác động hoặc thao túng người dùng** vì họ không nhận biết mình đang tương tác với AI hoặc nội dung do AI tạo. Nguồn luật sư cho biết có ngoại lệ với hệ thống **không tương tác và không cung cấp nội dung trực tiếp cho công chúng**. ⚠ Nghĩa là ERP chỉ dùng nội bộ còn có thể lập luận là rủi ro **thấp**. |
| Cá Về khi AI tự thực thi | **Vẫn không thuộc Danh mục**, nên **không lên mức cao**. Giao dịch của Cá Về là bán hàng, không phải "hoạt động ngân hàng", vì vựa không nhận tiền gửi, không cấp tín dụng và không cung ứng dịch vụ thanh toán. Tiền vào tài khoản của Lộc qua SePay. Hiện AI **không thể** tự chuyển tiền đi, vì SePay không có API hoàn tiền (decisions 2026-09-10). ⚠ Lúc nào nối API ngân hàng cho AI tự chuyển tiền thì phải để luật sư đối chiếu lại mục ngân hàng của QĐ 33. |
| Nghĩa vụ **tăng thêm** nếu AI tự làm (vẫn ở mức trung bình) | (1) **Viết lại hồ sơ phân loại** (NĐ 142 Đ.12) để mô tả đúng việc AI tự thực thi, danh sách lệnh tự động, ngưỡng và kill switch. Bỏ câu "chỉ đề xuất, không tự quyết". (2) Nếu đã thông báo Bộ KH&CN mà sau đó đổi sang tự thực thi, đây là thay đổi làm tăng rủi ro, nên phải **phân loại lại và thông báo trong 15 ngày làm việc** (theo research 27/09, chưa kiểm lại hôm nay). (3) Khả năng xảy ra **sự cố nghiêm trọng** tăng lên. NĐ 142 định nghĩa sự cố nghiêm trọng gồm cả *"thiệt hại đáng kể về tài sản hoặc ảnh hưởng nghiêm trọng đến hoạt động của tổ chức"* và *"xâm phạm nghiêm trọng quyền, lợi ích hợp pháp"*. Hạn báo cáo sơ bộ là **5 ngày làm việc**, báo cáo chính thức trong **15 ngày** kể từ báo cáo sơ bộ, và 72 giờ với trường hợp khẩn cấp theo research 27/09. Nếu AI hoàn tiền hoặc ghi nhận tiền sai hàng loạt thì có thể phải báo cáo. (4) Nếu AI tự gửi thông báo cho **khách**, hệ thống bắt đầu tương tác với công chúng. Khi đó chắc chắn thuộc mức trung bình và **mất miễn gắn nhãn nội bộ** (NĐ 142 Đ.18 khoản 4). |
| Nghĩa vụ **không phát sinh** | **Đánh giá sự phù hợp** (Luật AI Đ.14, Đ.18), hệ thống quản lý rủi ro bắt buộc và cơ chế người duyệt trước khi quyết định có hiệu lực chỉ áp cho **rủi ro cao**, nên Cá Về không phải làm. Không có thủ tục đăng ký hay xin phép riêng. |
| Mức phạt | Theo nhiều báo, tối đa **2 tỷ đồng với tổ chức** và **1 tỷ đồng với cá nhân**. Một số vi phạm nặng bị phạt tới **2% doanh thu năm trước tại Việt Nam**, tái phạm tới 2% doanh thu toàn cầu. Có nguồn nêu vi phạm **lần đầu** về thông báo phân loại hoặc gắn nhãn có thể chỉ bị **cảnh cáo**. ⚠ **Chưa xác minh trên văn bản gốc.** Các con số này xuất phát từ bản trình Quốc hội 21/11/2025, và chưa tìm thấy nghị định xử phạt riêng cho lĩnh vực AI. |

**Kết luận câu 1:** mức rủi ro giữ ở **trung bình** (hoặc thấp nếu luật sư đồng ý). Không phát sinh đánh giá sự phù hợp. Chi phí tăng thêm nằm ở hồ sơ, rủi ro sự cố và **trách nhiệm dân sự** (mục 4), không nằm ở thủ tục cấp phép.

## 3. Câu 2: phải duyệt từng giao dịch hay chỉ cần giám sát?

- **Hệ thống không thuộc rủi ro cao:** luật **không** bắt duyệt từng giao dịch. Nguyên tắc chung của Luật AI 134/2025 là *"duy trì khả năng kiểm soát và can thiệp của con người đối với mọi quyết định và hành vi của hệ thống AI"*. Số điều cụ thể **chưa xác minh**; các nguồn mô tả đây là nguyên tắc cơ bản. Như vậy mô hình giám sát (human-on-the-loop) **hợp pháp** nếu chứng minh được con người **kiểm soát và can thiệp được**. Tối thiểu cần:
  1. **Kill switch** tắt ngay chế độ tự thực thi. Có thể mở rộng `AI_ENABLED` (BR-AI-10), tách thêm công tắc riêng cho tự thực thi.
  2. **Danh sách trắng lệnh được tự thực thi**, mặc định là cấm. Mọi lệnh khác phải escalate.
  3. **Ngưỡng** về số tiền, số kg, độ lệch giá và số lệnh mỗi giờ. Vượt ngưỡng thì escalate.
  4. **Hoàn tác được**, bằng cách huỷ qua trạng thái hoặc chứng từ đảo (không xoá, theo bất biến 3).
  5. **Nhật ký đầy đủ** (BR-AI-08) ghi actor, lệnh, tham số, trạng thái trước và sau, lý do. Kèm **người chịu trách nhiệm** được gán cho tác vụ tự động (xem mục 4).
  6. **Người rà soát định kỳ**, ví dụ Chủ đọc báo cáo "AI đã làm gì hôm nay", và **quy trình sự cố** 5 ngày làm việc hoặc 72 giờ.
- **Hệ thống rủi ro cao** (không áp cho Cá Về): theo nguồn luật sư, NĐ 142 buộc có *"giám sát có ý nghĩa, người được uỷ quyền có thể độc lập xem xét, can thiệp, từ chối hoặc sửa quyết định **trước khi quyết định có hiệu lực**"*. Đây mới là mô hình duyệt từng lần bắt buộc.
- **Lưu ý:** ngoài Luật AI, việc duyệt từng lần vẫn *bắt buộc trên thực tế* với chứng từ cần **người duyệt** theo Luật Kế toán (mục 5), và *nên có* với quyết định bất lợi cho khách (mục 6).

## 4. Câu 3: AI làm sai thì ai chịu?

| Chủ thể | Trách nhiệm | Căn cứ |
|---|---|---|
| **AI** | **Không có tư cách pháp lý.** AI không phải "người lao động" hay "người lập chứng từ" và không chịu trách nhiệm. "Digital worker" chỉ là cách nói trong thiết kế. Về pháp lý, mọi hành vi của AI được quy về chủ thể đã thiết lập hoặc vận hành nó. | Luật GDĐT 2023 (20/2023/QH15): thông điệp dữ liệu được gửi bởi **hệ thống thông tin tự động do người khởi tạo thiết lập** thì được coi là của người khởi tạo. Số điều **chưa xác minh**. |
| **Lộc** (bên triển khai, người bán) | **Chịu trước tiên với khách.** Nếu AI ghi nhận "đã trả" sai (tiền của đơn A gắn vào đơn B) hoặc đánh dấu "đã hoàn" khi tiền chưa rời tài khoản, Lộc vẫn phải thực hiện đúng nghĩa vụ với khách, gồm giao đúng hàng và hoàn đủ, đúng hạn. Khi khách đơn phương chấm dứt hợp đồng từ xa theo luật, **hạn hoàn tiền là 30 ngày**. Với hệ thống không rủi ro cao, trách nhiệm dân sự theo pháp luật dân sự, có xét lỗi. Với hệ thống rủi ro cao, bên triển khai **bồi thường kể cả khi vận hành đúng quy định**, rồi yêu cầu nhà cung cấp hoàn trả nếu có thoả thuận. | Luật AI **Điều 29** (khoản 1: xử phạt, bồi thường theo pháp luật dân sự; khoản 2: rủi ro cao). Luật BVQLNTD 19/2023/QH15 (hiệu lực 01/7/2024), Chương III, giao dịch từ xa Đ.37–38. Mức phạt: NĐ 98/2020 được sửa bởi **NĐ 24/2025/NĐ-CP** (hiệu lực 21/02/2025). |
| **Nhân viên hoặc người được gán tác vụ** | Nếu lệnh chạy "thay cho user" (BR-AI-04), hành vi được quy cho user đó trong quan hệ nội bộ. Với khách, Lộc vẫn chịu, sau đó có quyền yêu cầu người có lỗi hoàn trả. | BLDS 2015 **Đ.597** (pháp nhân) và **Đ.600** (người làm công), áp khi Lộc có tư cách tương ứng. |
| **Duy** (nhà phát triển, nhà cung cấp hệ thống) | Chịu với **Lộc** theo **hợp đồng** giữa hai người, **hiện chưa có** (Q3 còn mở trong ADR). Chịu với cơ quan nhà nước về **tính trung thực của hồ sơ phân loại** và nghĩa vụ thông báo. Nếu không có hợp đồng giới hạn trách nhiệm, Lộc có thể đòi Duy bồi hoàn theo pháp luật dân sự khi lỗi do phần mềm. ⚠ | Luật AI Đ.29 khoản 2 (quyền yêu cầu hoàn trả dựa trên thoả thuận); NĐ 142 (trách nhiệm phân loại). |
| **Xiaomi** (MiMo) và nhà cung cấp model on-device | Chỉ chịu tới đâu **điều khoản dịch vụ** cho phép, thường được miễn trừ tối đa. Thực tế gần như không đòi được. | Điều khoản MiMo Open Platform (research 27/09). |

**Hệ quả:** càng để AI tự làm, rủi ro càng dồn về **Lộc** với khách và về **Duy** với Lộc. Muốn chuyển sang mô hình digital worker thì **phải ký thoả thuận Duy–Lộc** trước, gồm phạm vi tự động, giới hạn trách nhiệm và việc Lộc chấp nhận quy chế uỷ quyền cho AI.

## 5. Câu 4: kế toán, thuế và chứng từ do AI lập hoặc xác nhận

- **Luật Kế toán 88/2015/QH13, Đ.16** (sửa bởi Luật 56/2024/QH15, hiệu lực 01/01/2025; nội dung sửa **chưa xác minh chi tiết**): chứng từ phải có *"chữ ký, họ và tên của **người lập, người duyệt** và những người có liên quan"*. **Đ.18:** chứng từ chỉ được lập một lần, không tẩy xoá. **Đ.17:** chứng từ điện tử.
  - Chứng từ **do hệ thống tự sinh** là hợp lệ khi hệ thống thuộc đơn vị kế toán và có người chịu trách nhiệm. Đây là trường hợp `SalesInvoice` do Hệ thống tạo khi IPN SePay báo `ORDER_PAID`, là quy tắc cố định chứ không phải AI.
  - **"Người duyệt" không thể là AI.** Các chứng từ có bước duyệt như **phiếu thu tay** (`confirm_payment_manual`), **phiếu chi hoàn tiền** (`confirm_refund`), **chốt giá vốn lô** (`close_batch`) và **duyệt kiểm kê/hao hụt** mà để AI tự xác nhận thì **thiếu yếu tố người duyệt**. Khi thanh tra, chứng từ có thể bị coi là không hợp lệ, nên chi phí và giá vốn liên quan có nguy cơ bị loại.
- **Ghi nhận doanh thu:** căn cứ là **sự kiện thanh toán có bằng chứng**, gồm IPN, sao kê và hoá đơn, chứ không căn cứ vào việc AI đã "xác nhận". Nếu AI ghép sai giao dịch ngân hàng với đơn, doanh thu và công nợ sẽ lệch. Trường hợp `confirm_payment_manual` là khi IPN không khớp và phải đọc **sao kê có tên người chuyển**. Sao kê là dữ liệu cá nhân (bất biến 9), nên đưa lên model cloud là vi phạm BR-AI-09 và thành chuyển dữ liệu xuyên biên giới.
- **Hộ kinh doanh từ 01/01/2026:** bỏ thuế khoán, chuyển sang kê khai. Ghi sổ theo **TT 152/2025/TT-BTC** (hiệu lực 01/01/2026). Tài liệu kế toán **lưu tối thiểu 5 năm**, hoá đơn lưu theo luật thuế. Sổ do ERP sinh ra là căn cứ đối chiếu với số thuế. Nếu AI ghi sai thì số kê khai sai theo. ⚠ Hình thức pháp lý của Lộc vẫn chưa rõ (go-live mục 7). Giá vốn ảnh hưởng thuế tới đâu tuỳ phương pháp tính thuế của Lộc, **cần kế toán xác nhận**.
- **Kết luận câu 4:** AI được **lập nháp** chứng từ (vai người lập hỗ trợ, người ra lệnh đứng tên). **Không** để AI là người duyệt chứng từ thu, chi, hoàn tiền, chốt giá vốn hay hao hụt.

## 6. Câu 5: dữ liệu cá nhân và quyết định tự động ảnh hưởng tới khách

- **Đính chính căn cứ:** **NĐ 356/2025/NĐ-CP** (ban hành 31/12/2025, hiệu lực 01/01/2026) hướng dẫn Luật BVDLCN 91/2025/QH15 và **thay thế NĐ 13/2023**. Research 27/09 và `go-live-phap-ly.md` còn ghi "NĐ 13 phần còn phù hợp, nghị định mới chưa ban hành". Chỗ này đã **lỗi thời** và cần sửa ở lượt khác.
- **Luật BVDLCN Đ.30:** xử lý dữ liệu cá nhân bằng AI phải **phân loại theo mức độ rủi ro**, đúng mục đích và trong phạm vi cần thiết.
- **NĐ 356/2025** (số điều **chưa xác minh**): bên kiểm soát dữ liệu phải **thông báo cho chủ thể về việc xử lý dữ liệu cá nhân tự động**, **giải thích nguyên tắc hoạt động của thuật toán** và ảnh hưởng tới quyền lợi, đồng thời **đưa ra lựa chọn để chủ thể không tham gia**. Chủ thể có **quyền phản đối** và hạn chế xử lý (Luật BVDLCN, điều về quyền của chủ thể).
- **Áp vào Cá Về:**
  - AI **tự huỷ hoặc tự hoàn đơn** của khách là quyết định tự động trên dữ liệu gắn với một người xác định được (mã đơn gắn SĐT và địa chỉ), dù prompt không chứa dữ liệu cá nhân nhờ BR-AI-09. Việc này **kích hoạt nghĩa vụ trên**: ghi vào chính sách quyền riêng tư, giải thích quy tắc, và cho khách **đường không tham gia**, tức có người xử lý thay. ⚠ Cần luật sư xác nhận đơn gắn mã có bị coi là xử lý dữ liệu cá nhân tự động hay không.
  - Chi phí rẻ nhất là **không để AI tự ra quyết định bất lợi cho khách**. AI chỉ đề xuất, người duyệt. Khi đó nghĩa vụ chọn không tham gia gần như không phát sinh, vì đã có người quyết định.
  - Job `cancel_expired_orders` là **quy tắc cố định** (TTL), không phải AI, nhưng vẫn là xử lý tự động. Cần nêu quy tắc hết hạn giữ chỗ trong **điều kiện giao dịch chung** và **chính sách quyền riêng tư**. Việc này đã nằm trong go-live mục 3 và 6, chỉ cần bổ sung một câu.
- **Miễn trừ cho hộ kinh doanh và doanh nghiệp siêu nhỏ** (Luật BVDLCN **Đ.38**): **không phải thực hiện Đ.21** (đánh giá tác động xử lý), **Đ.22** (cập nhật hồ sơ đánh giá tác động, gồm hồ sơ chuyển xuyên biên giới) và **Đ.33 khoản 2** (nhân sự bảo vệ dữ liệu). Miễn trừ **không áp** khi trực tiếp xử lý **dữ liệu nhạy cảm** hoặc **số lượng lớn chủ thể**. Doanh nghiệp nhỏ và khởi nghiệp được tự chọn trong 5 năm. ⚠ Phát hiện này có thể giảm nghĩa vụ ở go-live mục 6b, cần luật sư xác nhận phạm vi. Nghĩa vụ thông báo xử lý tự động và quyền của khách **không** thuộc miễn trừ.

## 7. Câu 6: phương án hợp pháp và rẻ nhất (3 vùng)

Nguyên tắc: AI được **tự làm** khi hành động **nội bộ**, **không đụng tiền**, **không đổi con số lãi lỗ đã chốt**, **không bất lợi cho khách** và **đảo ngược được**. Những việc còn lại cần người duyệt.

| Vùng | Gồm | Điều kiện kèm theo |
|---|---|---|
| **XANH: AI tự làm, chỉ ghi nhật ký** | Tra cứu; tóm tắt; cảnh báo lô cận hạn, đơn chờ, phiếu hoàn chờ; gợi ý FEFO; soạn **bản nháp** mọi lệnh; điền form; phân loại hoặc gắn nhãn nội bộ; nhắc việc; **escalate** | Lọc context theo quyền (BR-AI-05); **không** đưa dữ liệu cá nhân vào prompt (BR-AI-09); gắn nhãn AI (BR-AI-14); AuditLog `ai:<user>` |
| **VÀNG: AI tự thực thi, người giám sát sau** | Thao tác vận hành đảo ngược được, không đụng tiền và giá vốn đã chốt. Ví dụ: chuyển trạng thái soạn hàng theo sự kiện, tạo phiếu nhập kho **khi người ra lệnh bằng giọng có mặt**, nhập số kiểm kê ở vai *người nhập* (vai *người duyệt* vẫn là người khác) | Danh sách trắng; ngưỡng; kill switch; hoàn tác bằng trạng thái; báo cáo "AI đã làm gì" hằng ngày cho Chủ; mọi sai sót phải sửa xong **trước khi chốt lô**. Có **người chịu trách nhiệm** cho từng tác vụ, ví dụ tài khoản dịch vụ `ai-worker` do Lộc sở hữu, quyền hẹp, kèm quy chế uỷ quyền nội bộ. Với phiếu nhập, **khuyến nghị giữ một lần xác nhận** vì người ra lệnh đang ở đó, chi phí gần bằng 0, và phiếu mang giá mua là chứng từ gốc của giá vốn. |
| **ĐỎ: người duyệt từng lần (giữ BR-AI-07 và mở rộng)** | `confirm_payment_manual`; `confirm_refund`; `create_refund` và `cancel_paid_order` cho đơn đã thanh toán; `close_batch`; thêm hoặc sửa chi phí mua và giá vốn; **duyệt** kiểm kê và hao hụt; đổi **giá bán niêm yết**; xuất hoặc huỷ hoá đơn điện tử; mọi thông báo hay quyết định **bất lợi cho khách**; gửi dữ liệu ra bên ngoài; quản trị quyền và nhân sự | AI chỉ soạn nháp kèm lý do. Người có quyền duyệt; khung xác nhận buộc tương tác thật (BR-AI-14). Căn cứ: Luật Kế toán Đ.16 (người duyệt); Luật BVQLNTD; NĐ 356 (quyết định tự động); Luật AI Đ.29 (trách nhiệm); ranh giới BR-PQ "việc làm tiền rời túi hoặc đổi con số lời lỗ do Chủ giữ". |

Nếu chọn phương án này, **nghĩa vụ tăng thêm so với hiện trạng 27/09 là nhỏ**:
- Hồ sơ phân loại mô tả thêm vùng VÀNG.
- Làm kill switch, ngưỡng và báo cáo hằng ngày. Đây là việc kỹ thuật.
- Viết quy chế uỷ quyền nội bộ một trang.
- Không phát sinh nghĩa vụ cho khách chọn không tham gia, không cần đánh giá sự phù hợp, không phải đăng ký thêm.

## 8. Bảng hành động → mức rủi ro → nghĩa vụ → khuyến nghị

| Hành động nếu AI tự làm | Mức rủi ro (Luật AI) và pháp lý | Nghĩa vụ phát sinh | Khuyến nghị |
|---|---|---|---|
| Tra cứu, tóm tắt, cảnh báo, nháp | Trung bình (hoặc thấp). Rủi ro pháp lý thấp. | Hồ sơ phân loại, thông báo Bộ KH&CN, minh bạch, BR-AI-09 | **XANH**, tự làm |
| Gợi ý FEFO, điền form | Như trên | Như trên | **XANH** |
| Chuyển trạng thái vận hành (soạn/giao) | Trung bình. Rủi ro dân sự thấp, đảo ngược được. | Kill switch, nhật ký, người chịu trách nhiệm | **VÀNG** |
| Nhập lô bằng giọng (ghi phiếu nhập kèm giá mua) | Trung bình. Là chứng từ gốc của giá vốn, bí mật kinh doanh (Luật SHTT Đ.84). | Luật Kế toán Đ.16 (người lập = người ra lệnh); sửa được trước chốt lô | **VÀNG**, khuyến nghị giữ một lần xác nhận |
| Nhập số kiểm kê | Trung bình | Người nhập ≠ người duyệt (decisions) | **VÀNG** cho vai nhập; **ĐỎ** cho vai duyệt |
| Xác nhận đã nhận tiền (tay, ghép sao kê) | Không phải rủi ro cao (không phải hoạt động ngân hàng ⚠). Rủi ro dân sự và kế toán **cao**; sao kê chứa dữ liệu cá nhân. | Luật Kế toán (người duyệt phiếu thu); BR-AI-09; nếu lên cloud: Luật BVDLCN Đ.20 (phạt tới 5% doanh thu) | **ĐỎ**. AI chỉ đề xuất cặp ghép, chạy **on-device**. IPN tự động hiện tại giữ nguyên vì không phải AI. |
| Hoàn tiền (tạo hoặc xác nhận) | Như trên. Tác động trực tiếp tới khách. | Luật BVQLNTD (hoàn đúng, đủ, hạn 30 ngày khi khách đơn phương chấm dứt hợp lệ); NĐ 356 (quyết định tự động); Luật AI Đ.29; Luật Kế toán (phiếu chi) | **ĐỎ**. AI không thể tự chuyển tiền (SePay không có API), nên để AI xác nhận chỉ gây rủi ro sổ sách lệch thực tế. |
| Huỷ hoặc hoàn đơn đã thanh toán | Tác động bất lợi cho khách | NĐ 356: thông báo, giải thích thuật toán, cho khách không tham gia; quyền phản đối | **ĐỎ** |
| Chốt lô, sửa giá vốn, duyệt hao hụt | Không phải rủi ro cao. Chốt con số lãi lỗ và sổ kế toán. | Luật Kế toán Đ.16/18; TT 152/2025 (hộ KD, lưu 5 năm); bí mật kinh doanh | **ĐỎ**, chỉ Chủ duyệt |
| Đổi giá bán niêm yết | Thông tin bắt buộc chính xác với khách | Luật BVQLNTD (thông tin giá, giao dịch từ xa); NĐ 24/2025 (phạt) | **ĐỎ** |
| AI tự nhắn khách | Mất miễn gắn nhãn nội bộ; chắc chắn mức trung bình | NĐ 142 Đ.18 (gắn nhãn); minh bạch | **Ngoài phạm vi**, cần hồ sơ riêng |
| AI gọi API ngân hàng để chuyển tiền (tương lai) | ⚠ Vùng xám với QĐ 33, mục ngân hàng | Có thể phải đánh giá sự phù hợp nếu bị coi là rủi ro cao | **Không làm** khi luật sư chưa xác nhận |

## 9. Đề xuất để Duy chốt (không sửa `decisions.md`)

1. **Giữ BR-AI-07 và mở rộng** thành danh sách ĐỎ ở mục 7. Mã đề xuất: **BR-AI-18** "Danh sách lệnh bắt buộc người duyệt từng lần".
2. **Nới BR-AI-06:** thay "mọi hành động Tầng 2 dừng ở bản nháp" bằng "Tầng 2 dừng ở bản nháp, **trừ** lệnh trong danh sách trắng VÀNG". Mã đề xuất: **BR-AI-19** "Tự thực thi có giám sát", gồm kill switch, ngưỡng, hoàn tác, báo cáo hằng ngày và người chịu trách nhiệm.
3. **BR-AI-20** (đề xuất): mọi tác vụ AI tự thực thi phải gắn một người chịu trách nhiệm (tài khoản dịch vụ do Lộc sở hữu). AuditLog ghi rõ `ai:<service>` kèm người chịu trách nhiệm.
4. **Sửa lý do phân loại** trong ADR 2.11 và `01-analysis.md` §4.10: bỏ "chỉ đề xuất, không tự quyết" và dùng đúng tiêu chí của NĐ 142.
5. **Ký thoả thuận Duy–Lộc (Q3)** trước khi bật vùng VÀNG ở production.

## 10. Checklist

**Chặn bật chế độ tự thực thi ở production:**
- [ ] Duy chốt 3 vùng và các mã BR-AI-18/19/20 vào `decisions.md`.
- [ ] Hồ sơ phân loại (NĐ 142 Đ.12) mô tả đúng mức tự chủ, danh sách trắng, ngưỡng và kill switch. Thông báo Bộ KH&CN qua cổng một cửa AI. Nếu đã thông báo bản cũ thì phân loại lại và thông báo trong 15 ngày làm việc.
- [ ] Kill switch cho tự thực thi, tách khỏi `AI_ENABLED`. Ngưỡng. Hoàn tác bằng trạng thái. Báo cáo hằng ngày cho Chủ.
- [ ] Quy trình sự cố AI: 5 ngày làm việc (sơ bộ), 15 ngày (chính thức), 72 giờ (khẩn cấp). Đầu mối là Lộc, dự phòng là Duy.
- [ ] Quy chế uỷ quyền nội bộ một trang (Lộc ký) và thoả thuận Duy–Lộc về trách nhiệm.
- [ ] Test: lệnh ĐỎ **không bao giờ** chạy tự động, kể cả khi user có quyền (mở rộng test BR-AI-07). Test: sao kê và dữ liệu cá nhân không vào prompt.

**Có thể làm sau:**
- [ ] Chính sách quyền riêng tư và điều kiện giao dịch chung nêu quy tắc tự động (TTL huỷ đơn, AI nội bộ). Việc này thuộc go-live mục 3 và 6.
- [ ] Hỏi luật sư về các điểm ⚠ ở mục 11.
- [ ] Cập nhật research 27/09 và `go-live-phap-ly.md`: QĐ 33/2026 đã ban hành; NĐ 356/2025 thay NĐ 13/2023; miễn trừ Đ.38 cho hộ kinh doanh.

## 11. Điểm chưa rõ, cần luật sư hoặc kế toán xác nhận

1. Nội dung **khoản 2 Điều 8 NĐ 142** (loại trừ khỏi rủi ro cao) và ngoại lệ mức trung bình cho hệ thống **không tương tác với công chúng**: ERP nội bộ có được xếp **thấp** không? Nếu được thì bỏ được thủ tục thông báo Bộ KH&CN.
2. Phạm vi "**giao dịch điện tử trong hoạt động ngân hàng**" (QĐ 33) có bao giờ chạm tới người bán tự ghép sao kê hoặc tự chuyển tiền qua API ngân hàng không.
3. **Mức phạt** Luật AI (2 tỷ, 2% doanh thu, cảnh cáo lần đầu) trên văn bản đã thông qua, và nghị định xử phạt lĩnh vực AI đã có chưa.
4. **NĐ 356/2025**: số điều và phạm vi của nghĩa vụ "thông báo xử lý tự động, cho chủ thể không tham gia". Đơn gắn mã có bị tính là xử lý dữ liệu cá nhân tự động không.
5. **Luật BVDLCN Đ.38**: miễn trừ cho hộ kinh doanh có loại bỏ nghĩa vụ **lập** hồ sơ chuyển dữ liệu xuyên biên giới (go-live mục 6b) hay chỉ miễn **cập nhật**. Thế nào là "số lượng lớn chủ thể".
6. **Kế toán**: chứng từ do hệ thống hoặc AI lập mà người ra lệnh đứng tên có đủ điều kiện "người lập" không. Hình thức pháp lý và phương pháp tính thuế của Lộc, để biết giá vốn ảnh hưởng thuế tới đâu.
7. Số điều Luật GDĐT 2023 về hệ thống thông tin tự động, và số điều nguyên tắc "kiểm soát, can thiệp của con người" trong Luật AI.

## 12. Kết luận

- **Đề xuất nguyên dạng** (AI tự làm cả việc tiền và chốt lô): **CHƯA ĐẠT**. Lý do không phải hệ thống thành rủi ro cao. Lý do là (a) chứng từ thu, chi, hoàn tiền và giá vốn thiếu **người duyệt** (Luật Kế toán Đ.16); (b) Lộc chịu trách nhiệm trực tiếp với khách khi AI sai (Luật BVQLNTD, Luật AI Đ.29, BLDS); (c) quyết định tự động bất lợi cho khách kéo theo nghĩa vụ thông báo và cho chọn không tham gia (NĐ 356/2025); (d) hồ sơ phân loại hiện tại mô tả sai mức tự chủ.
- **Phương án 3 vùng** (mục 7): **ĐẠT có điều kiện**. Điều kiện là hoàn thành checklist chặn ở mục 10. Đây là phương án rẻ nhất: giữ mức trung bình (hoặc thấp), không phải đánh giá sự phù hợp, không phát sinh nghĩa vụ cho khách chọn không tham gia, và chi phí người duyệt chỉ rơi vào khoảng mười loại lệnh ĐỎ.

## Nguồn (truy cập 2026-09-28, qua WebSearch; WebFetch bị chặn)

- QĐ 33/2026/QĐ-TTg, Danh mục AI rủi ro cao: [vanban.chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=218658&classid=1&typegroupid=5) · [thuvienphapluat](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Quyet-dinh-33-2026-QD-TTg-Danh-muc-he-thong-tri-tue-nhan-tao-co-rui-ro-cao-712969.aspx) · [luatvietnam, hiệu lực 15/8/2026](https://luatvietnam.vn/tin-van-ban-moi/danh-muc-he-thong-tri-tue-nhan-tao-co-rui-ro-cao-tu-15-8-2026-186-110045-article.html) · [VnExpress, 46 hệ thống, 2 hệ thống ngân hàng](https://vnexpress.net/cong-bo-danh-muc-46-he-thong-ai-rui-ro-cao-5092772.html) · [Bộ KH&CN](https://mst.gov.vn/46-he-thong-ai-duoc-xep-vao-nhom-rui-ro-cao-phai-quan-ly-nghiem-ngat-197260703152945179.htm)
- Luật AI 134/2025/QH15: [vanban.chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=216334&classid=1&typegroupid=3) · [Luật Việt An](https://luatvietan.vn/luat-tri-tue-nhan-tao.html) · [thuvienphapluat, bồi thường Đ.29](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/101752/boi-thuong-thiet-hai-khi-vi-pham-ve-tri-tue-nhan-tao-moi-nhat) · [lsvn, trách nhiệm bồi thường](https://lsvn.vn/quy-dinh-ve-trach-nhiem-boi-thuong-khi-tri-tue-nhan-tao-gay-thiet-hai-a167983.html) · [VTC News, mức phạt](https://vtcnews.vn/vi-pham-hanh-chinh-trong-linh-vuc-tri-tue-nhan-tao-co-the-bi-phat-den-2-ty-dong-ar988249.html) · [Tuổi Trẻ, bản trình 21/11/2025](https://tuoitre.vn/lan-dau-trinh-quoc-hoi-luat-ve-tri-tue-nhan-tao-phat-toi-da-2-ti-dong-hanh-vi-vi-pham-ve-ai-20251121085727822.htm)
- NĐ 142/2026/NĐ-CP: [vanban.chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=218029) · [thuvienphapluat, phân loại](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/111767/phan-loai-he-thong-tri-tue-nhan-tao-tu-1-5-2026-nghi-dinh-142-2026) · [Frasers](https://www.frasersvn.com/legal-updates-and-publications/Vietnams-AI-Law-Takes-Shape:-Key-Insights-from-Decree-142) · [Tilleke & Gibbins](https://www.tilleke.com/insights/vietnam-takes-major-step-in-ai-governance-with-new-guiding-decree/) · [Lexology](https://www.lexology.com/library/detail.aspx?g=65081162-5c28-47cf-8e8d-189dc50a1a3a) · [luatvietnam, mẫu báo cáo sự cố nghiêm trọng](https://luatvietnam.vn/bieu-mau/mau-bao-cao-su-co-nghiem-trong-cua-he-thong-tri-tue-nhan-tao-moi-nhat-571-108879-article.html)
- Luật BVDLCN 91/2025 và NĐ 356/2025: [chinhphu.vn](https://chinhphu.vn/?pageid=27160&docid=214590&classid=1&typegroupid=3) · [thuvienphapluat, NĐ 356](https://thuvienphapluat.vn/van-ban/Quyen-dan-su/Nghi-dinh-356-2025-ND-CP-huong-dan-Luat-Bao-ve-du-lieu-ca-nhan-687428.aspx) · [luatvietnam, điểm mới NĐ 356](https://luatvietnam.vn/dan-su/diem-moi-cua-nghi-dinh-356-2025-so-voi-nghi-dinh-13-2023-ve-bao-ve-du-lieu-ca-nhan-568-106269-article.html) · [thuvienphapluat, AI phân loại rủi ro Đ.30](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/93089/tu-01-01-2026-xu-ly-du-lieu-ca-nhan-bang-tri-tue-nhan-tao-phai-phan-loai-theo-muc-do-rui-ro) · [thuvienphapluat, hộ KD và DN siêu nhỏ Đ.38](https://thuvienphapluat.vn/phap-luat/mot-so-luu-y-khi-luat-bao-ve-du-lieu-ca-nhan-2025-co-hieu-luc-danh-cho-ho-kinh-doanh-doanh-nghiep-s-924781-244918.html)
- Luật BVQLNTD 19/2023/QH15: [vanban.chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=208363) · [Wikisource, Chương III](https://vi.wikisource.org/wiki/Lu%E1%BA%ADt_B%E1%BA%A3o_v%E1%BB%87_quy%E1%BB%81n_l%E1%BB%A3i_ng%C6%B0%E1%BB%9Di_ti%C3%AAu_d%C3%B9ng_n%C6%B0%E1%BB%9Bc_C%E1%BB%99ng_h%C3%B2a_x%C3%A3_h%E1%BB%99i_ch%E1%BB%A7_ngh%C4%A9a_Vi%E1%BB%87t_Nam_2023/Ch%C6%B0%C6%A1ng_III) · [NĐ 24/2025, xaydungchinhsach](https://xaydungchinhsach.chinhphu.vn/nghi-dinh-24-2025-nd-cp-sua-doi-bo-sung-quy-dinh-xu-phat-vi-pham-hanh-chinh-bao-ve-quyen-loi-nguoi-tieu-dung-119250225072906906.htm)
- Luật Kế toán 88/2015 Đ.16–18: [accgroup Đ.16](https://accgroup.vn/dieu-16-luat-ke-toan) · [thuvienphapluat, nội dung chứng từ từ 01/01/2025](https://thuvienphapluat.vn/phap-luat-doanh-nghiep/bai-viet/quy-dinh-moi-ve-noi-dung-chung-tu-ke-toan-tu-ngay-01-01-2025-10140.html) · TT 152/2025/TT-BTC: [luatvietnam](https://luatvietnam.vn/ke-toan/thong-tu-152-2025-tt-btc-huong-dan-ke-toan-cho-ho-kinh-doanh-ca-nhan-kinh-doanh-423164-d1.html) · [Thuế cơ sở 14 TP.HCM](https://www.binhthanhtax.gov.vn/?p=2391)
- Luật GDĐT 20/2023/QH15: [mst.gov.vn](https://mst.gov.vn/van-ban-phap-luat/24987.htm) · [thuvienphapluat, gửi và nhận thông điệp dữ liệu](https://thuvienphapluat.vn/phap-luat-doanh-nghiep/bai-viet/quy-dinh-ve-gui-nhan-thong-diep-du-lieu-theo-luat-giao-dich-dien-tu-2023-6098.html)
- BLDS 2015 Đ.597/600: [accgroup](https://accgroup.vn/dieu-597-cua-bo-luat-dan-su-2015) · [Kiểm sát Online](https://kiemsat.vn/trach-nhiem-boi-thuong-cua-nguoi-su-dung-lao-dong-voi-thiet-hai-ngoai-hop-dong-do-nguoi-lao-dong-gay-ra-65507.html)
