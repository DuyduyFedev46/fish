# Luật AI & bảo vệ dữ liệu khi tích hợp AI vào Cá Về
> Research · 2026-09-27 · Kiểm chứng ADR mục 2.11, 4 (`00-adr-ai-native.md`) và `01-analysis.md` (BR-AI-03/05/09/14)

> **Lưu ý:** tài liệu tham khảo nội bộ, **không phải tư vấn pháp lý**. Các ô **⚠️** cần luật sư hoặc cơ quan nhà nước xác nhận trước khi triển khai thật. Mọi nguồn đều là văn bản chính thức hoặc báo/tổng hợp uy tín, kèm URL và ngày truy cập 2026-09-27.

**Tóm tắt 1 dòng:** ADR phân loại "rủi ro trung bình" là **đúng và có nghĩa vụ thật** (tự phân loại + thông báo Bộ KH&CN trước khi đưa vào sử dụng, qua cổng một cửa AI); "không dữ liệu cá nhân vào prompt" (BR-AI-09) là **chốt chặn pháp lý** giúp kênh AI không phát sinh thêm hồ sơ chuyển dữ liệu xuyên biên giới; còn giá vốn được bảo vệ bằng chế độ **bí mật kinh doanh** — gửi lên cloud mà không có ràng buộc hợp đồng vừa rò rỉ vừa **làm mất tư cách bảo hộ**.

---

## 1. Luật Trí tuệ nhân tạo 134/2025/QH15 — ✅ có hiệu lực

| Câu hỏi | Kết quả kiểm chứng |
| :--- | :--- |
| Hiệu lực | ✅ **Có hiệu lực từ 01/3/2026** (thông qua 10/12/2025, Kỳ họp thứ 10 QH khóa XV; 8 chương, 35 điều). Không phải 1/1/2026. Hướng dẫn đầu tiên: **NĐ 142/2026/NĐ-CP** ban hành 30/4/2026, hiệu lực 01/5/2026. |
| "Rủi ro trung bình" là gì | ✅ Định nghĩa theo luật: hệ thống AI **có khả năng gây nhầm lẫn, tác động hoặc thao túng người sử dụng khi người dùng không nhận biết được chủ thể tương tác là AI hoặc không nhận biết nội dung do AI tạo ra**. "Rủi ro cao" = thuộc **Danh mục do Thủ tướng ban hành** (thiệt hại đáng kể đến tính mạng, sức khỏe, quyền lợi, lợi ích quốc gia/công cộng/an ninh). "Thấp" = còn lại. ⚠️ Lưu ý: tiêu chí pháp lý của "trung bình" là **khả năng gây nhầm lẫn về chủ thể AI**, không phải "có con người phê duyệt" như cách ADR diễn đạt. Với chatbot/auto-fill/gợi ý trong ERP, phân loại **trung bình là an toàn và đúng tinh thần ADR** (có thể tranh luận "thấp" vì người dùng là nhân viên nội bộ — ⚠️ nhờ luật sư chốt). |
| Nghĩa vụ của mức trung bình | ✅ (a) **Tự phân loại trước khi đưa vào sử dụng** + lập **hồ sơ phân loại rủi ro** (NĐ 142 Điều 12); (b) **thông báo kết quả phân loại cho Bộ KH&CN** qua **Cổng thông tin điện tử một cửa về trí tuệ nhân tạo trước khi đưa vào sử dụng** (NĐ 142 Điều 14 — nhà cung cấp hệ thống rủi ro trung bình và cao); (c) **minh bạch**: người dùng nhận biết đang tương tác AI, nội dung do AI tạo phải gắn nhãn/đánh dấu (trừ ngoại lệ nội bộ — xem dưới); (d) giải trình khi cơ quan quản lý yêu cầu; (e) **báo cáo sự cố**: 72 giờ (khẩn cấp/không kiểm soát được), 5 ngày làm việc (sự cố nghiêm trọng khác) — NĐ 142; (f) phân loại lại khi thay đổi làm tăng rủi ro, thông báo trong **15 ngày làm việc**. |
| Ngoại lệ gắn nhãn | ✅ **NĐ 142/2026 Điều 18(4): nội dung chỉ sử dụng nội bộ trong cơ quan/tổ chức/doanh nghiệp và không cung cấp cho công chúng được miễn gắn nhãn.** Cá Về giai đoạn 1 AI chỉ trong ERP nội bộ → có căn cứ miễn; nhưng nghĩa vụ phân loại + thông báo vẫn áp. Nếu AI ra Shop (khách hàng) → **bắt buộc** gắn nhãn + minh bạch. |
| Chuyển tiếp | ✅ Điều 35: hệ thống AI đưa vào hoạt động **trước 1/3/2026** có 12 tháng (đến ~1/3/2027) để hoàn thành nghĩa vụ; lĩnh vực y tế/giáo dục/tài chính 18 tháng. **Hệ thống AI của Cá Về là mới (chưa xây) → không hưởng chuyển tiếp, phải tuân thủ ngay khi đưa vào sử dụng.** |
| Ai quản lý | ✅ **Bộ Khoa học và Công nghệ** — vận hành Cổng thông tin điện tử một cửa về AI + Cơ sở dữ liệu quốc gia về hệ thống AI. Bộ Công an (A05) quản lý dữ liệu cá nhân; Bộ Công Thương/Sở Công Thương quản lý TMĐT. |
| Vai trò pháp lý | ✅ NĐ 142 phân 4 vai: nhà phát triển, nhà cung cấp, **bên triển khai** (đưa AI vào quy trình kinh doanh/dịch vụ), người sử dụng. Một tổ chức có thể đóng nhiều vai. Cá Về: **Duy/nhóm phát triển = nhà phát triển + nhà cung cấp hệ thống; vựa của Lộc = bên triển khai; nhân viên = người sử dụng.** Nghĩa vụ phân loại + thông báo đè lên nhà cung cấp; bên triển khai phải giám sát, bảo đảm con người kiểm soát và báo cáo sự cố. Dùng AI **nội bộ không được miễn** phân loại. |

**Nguồn:**
- [Luật 134/2025/QH15 — Cơ sở dữ liệu văn bản Chính phủ (vanban.chinhphu.vn)](https://vanban.chinhphu.vn/?docid=216334&orggroupid=1&pageid=27160)
- [Những nội dung đáng chú ý của Luật Trí tuệ nhân tạo (xaydungchinhsach.chinhphu.vn)](https://xaydungchinhsach.chinhphu.vn/nhung-noi-dung-dang-chu-y-cua-luat-tri-tue-nhan-tao-119260212091614393.htm)
- [Nguyên tắc phân loại và đánh giá sự phù hợp hệ thống AI — NĐ 142/2026 (baochinhphu.vn, 05/2026)](https://baochinhphu.vn/print/nguyen-tac-phan-loai-va-danh-gia-su-phu-hop-he-thong-tri-tue-nhan-tao-102260507163337677.htm)
- [Những điểm mới đáng chú ý của Nghị định 142 (thanhtra.com.vn)](https://thanhtra.com.vn/chuyen-doi-so-DFC98D38D/nhung-diem-moi-dang-chu-y-cua-nghi-dinh-142-huong-dan-thi-hanh-luat-tri-tue-nhan-tao-5c80c26df.html)
- [Sử dụng AI trong doanh nghiệp: chuẩn bị gì để tuân thủ NĐ 142? (BLawyers VN, 21/7/2026)](https://www.blawyersvn.com/vi/su-dung-ai-trong-doanh-nghiep-can-chuan-bi-gi-de-tuan-thu-nghi-dinh-142-2026-nd-cp/)
- [Legal Update: Vietnam's New AI Compliance Regime (GVW)](https://www.gvw.com/en/news/blog/detail/legal-update-from-innovation-to-regulation-vietnams-new-ai-compliance-regime)
- [Vietnam's AI Law No. 134/2025/QH15 Takes Effect March 2026 (Licentium)](https://www.licentium.io/post/vietnam-ai-law-134-2025-qh15-march-2026)

---

## 2. NĐ 248/2026 (TMĐT) — ✅ có hiệu lực, không có nghĩa vụ "khai báo chatbot" riêng

| Câu hỏi | Kết quả kiểm chứng |
| :--- | :--- |
| Văn bản | ✅ **NĐ 248/2026/NĐ-CP ban hành 30/6/2026, hiệu lực 01/7/2026** (9 chương, 52 điều), hướng dẫn **Luật TMĐT 122/2025/QH15** (10/12/2025, hiệu lực 01/7/2026); thay thế NĐ 52/2013 và NĐ 85/2021. |
| Thông báo website | ✅ **Thông báo trước khi hoạt động với UBND cấp tỉnh (Sở Công Thương)** qua Hệ thống quản lý hoạt động TMĐT (NĐ 248 Điều 24, Phụ lục I) — đã nằm trong checklist go-live (mục 1). Không phải "đăng ký Bộ Công Thương" — việc đăng ký với BCT chỉ áp cho sàn trung gian/mạng xã hội TMĐT/nền tảng tích hợp, Cá Về là **nền tảng kinh doanh trực tiếp** nên không thuộc diện đó. |
| Định danh người bán | ✅ Là nghĩa vụ của **sàn trung gian** (xác thực danh tính người bán trên sàn, áp từ 01/01/2027) — **không áp** cho Cá Về (Lộc tự bán trên website của mình). |
| Lưu trữ | ✅ Lưu dữ liệu hợp đồng (đơn hàng) **tối thiểu 3 năm** (hộ KD/doanh nghiệp siêu nhỏ: 1 năm). Hệ quả: AI không được xóa/chỉnh chứng từ — đã có bất biến dự án, không xung đột. |
| Chatbot phải khai báo là AI? | ❌ **Không tìm thấy** quy định riêng về AI/chatbot trong Luật TMĐT 2025 hay NĐ 248. Nghĩa vụ "minh bạch khi tương tác AI" đến từ **Luật AI 134/2025** (mục 1), không phải từ TMĐT. |
| Thuật toán hiển thị | ✅ Điều 11 NĐ 248: nền tảng dùng **thuật toán ưu tiên/hạn chế hiển thị hàng hóa** phải **công khai tiêu chí chính**. Cá Về giai đoạn 1: AI không xếp hạng hiển thị sản phẩm ở Shop (Shop không có AI) → **chưa kích hoạt**. ⚠️ Nếu sau này dùng AI gợi ý/tìm kiếm ngữ nghĩa cho khách trên Shop → phải công khai tiêu chí. |

**Nguồn:**
- [NĐ 248/2026/NĐ-CP — LuatVietnam](https://luatvietnam.vn/thuong-mai/nghi-dinh-248-2026-nd-cp-quy-dinh-chi-tiet-luat-thuong-mai-dien-tu-2026-439480-d1.html) · [Thư viện pháp luật](https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-248-2026-ND-CP-huong-dan-Luat-Thuong-mai-dien-tu-713280.aspx) · [Bộ Công Thương phổ biến](https://moit.gov.vn/tin-tuc/bo-cong-thuong-pho-bien-luat-thuong-mai-dien-tu-va-nghi-dinh-so-248-2026-nd-cp.html)
- [NĐ 248 có hiệu lực từ 01/7/2026 (Sở Công Thương Ninh Bình)](https://congthuong.ninhbinh.gov.vn/nghi-dinh-so-2482026nd-cp-quy-dinh-chi-tiet-mot-so-dieu-cua-luat-thuong-mai-dien-tu-co-hieu-luc-thi-hanh-ke-tu-ngay-01-thang-7-nam-2026.html)
- [Bước chuyển trong quản lý TMĐT — NĐ 248 (Cục QLTT Hà Tĩnh)](https://hatinh.dms.gov.vn/tin-chi-tiet/-/chi-tiet/nghi-dinh-so-2482026nd-cp-buoc-chuyen-quan-trong-trong-quan-ly-thuong-mai-dien-tu-17905-2007.html)
- [Luật TMĐT 122/2025/QH15 (vanban.chinhphu.vn)](https://vanban.chinhphu.vn/?pageid=27160&docid=216503&classid=1&orggroupid=1)

---

## 3. Chuyển dữ liệu cá nhân xuyên biên giới — ✅ căn cứ đã đổi: Luật BVDLCN 2025 (Điều 20), NĐ 13/2023 chỉ còn phần phù hợp

| Câu hỏi | Kết quả kiểm chứng |
| :--- | :--- |
| Căn cứ hiện hành | ✅ Từ **01/01/2026**, **Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15** (thông qua 26/6/2025) là căn cứ chính; **NĐ 13/2023/NĐ-CP chỉ còn áp dụng phần phù hợp**, đang chờ nghị định mới thay thế (⚠️ chưa ban hành tại thời điểm nghiên cứu — theo dõi tiếp). Hồ sơ đã nộp theo NĐ 13 vẫn có giá trị; hồ sơ cập nhật sau 01/01/2026 phải theo Luật 2025. |
| Khi nào là "chuyển xuyên biên giới" | ✅ **Luật 2025 Điều 20 khoản 1 — 3 trường hợp:** (1) chuyển dữ liệu đang lưu tại VN đến hệ thống lưu trữ ở nước ngoài; (2) tổ chức/cá nhân tại VN chuyển dữ liệu cá nhân cho tổ chức/cá nhân ở nước ngoài; (3) tổ chức/cá nhân tại VN hoặc nước ngoài **sử dụng nền tảng ở ngoài lãnh thổ VN để xử lý dữ liệu cá nhân thu thập tại VN**. → **Gửi prompt chứa dữ liệu cá nhân sang model cloud ở nước ngoài = chuyển xuyên biên giới (trường hợp 2/3), kể cả không lưu trữ.** |
| Nghĩa vụ | ✅ Lập **Hồ sơ đánh giá tác động chuyển dữ liệu xuyên biên giới (DTIA)** và gửi cơ quan chuyên trách (Cục A05, Bộ Công an) **trong 60 ngày kể từ lần chuyển đầu tiên**; đánh giá **một lần cho toàn bộ thời gian hoạt động**, cập nhật khi có thay đổi (định kỳ 6 tháng nếu thay đổi); chịu kiểm tra định kỳ/đột xuất; có thể bị **yêu cầu dừng chuyển**. Nội dung hồ sơ theo mẫu NĐ 13 (vẫn tham chiếu được): mô tả loại dữ liệu, mục đích xử lý, bên chuyển/bên nhận, biện pháp bảo vệ, đánh giá thiệt hại, **sự đồng ý của chủ thể dữ liệu**, văn bản ràng buộc trách nhiệm giữa các bên. |
| Chế tài | ✅ Phạt đến **5% doanh thu năm trước liền kề** (hoặc 3 tỷ đồng, lấy mức cao hơn) cho vi phạm chuyển xuyên biên giới. |
| Miễn trừ | ✅ Không phải làm DTIA khi: chuyển theo yêu cầu cơ quan nhà nước; tổ chức **lưu dữ liệu của người lao động của mình** trên dịch vụ điện toán đám mây; **chủ thể tự chuyển dữ liệu của mình**. → Dữ liệu **khách hàng** (tên/SĐT/địa chỉ) **không được miễn**. |
| Dữ liệu kinh doanh (giá vốn) | ✅ **Không thuộc phạm vi BVDLCN/NĐ 13** (không phải dữ liệu cá nhân). Nhưng được bảo vệ bằng chế độ **bí mật kinh doanh** theo **Luật SHTT**: khoản 23 Điều 4 + **Điều 84** — bảo hộ khi (1) không phải hiểu biết thông thường, (2) tạo lợi thế kinh doanh, (3) **chủ sở hữu đã dùng biện pháp bảo mật cần thiết**. Hệ quả quan trọng: **gửi giá vốn cho bên thứ ba không có ràng buộc bảo mật (NDA/DPA) vừa là rò rỉ, vừa có thể làm mất luôn tư cách bảo hộ bí mật kinh doanh** vì điều kiện (3) không còn được thỏa mãn. Điều 127 liệt kê hành vi xâm phạm (tiếp cận trái phép, bộc lộ, vi phạm hợp đồng bảo mật…). |

**Nguồn:**
- [Chuyển dữ liệu cá nhân xuyên biên giới: khung pháp lý mới (biznext.vn)](https://biznext.vn/chuyen-du-lieu-ca-nhan-xuyen-bien-gioi-khung-phap-ly/)
- [Thủ tục thông báo gửi hồ sơ DTIA xuyên biên giới (luatvietnam.vn)](https://luatvietnam.vn/hanh-chinh/thu-tuc-thong-bao-gui-ho-so-danh-gia-tac-dong-chuyen-du-lieu-ca-nhan-xuyen-bien-gioi-570-107387-article.html)
- [Có được chuyển dữ liệu cá nhân ra nước ngoài không (CAND)](https://cand.vn/co-duoc-chuyen-du-lieu-ca-nhan-ra-nuoc-ngoai-hay-khong-post693508.html) · [Quy định đánh giá tác động xử lý dữ liệu cá nhân (Sở Tư pháp Huế)](https://stp.hue.gov.vn/giai-dap-phap-luat/quy-dinh-viec-danh-gia-tac-dong-xu-ly-du-lieu-ca-nhan.html)
- [04 lưu ý lập hồ sơ đánh giá tác động theo NĐ 13/2023 (BLawyers)](https://www.blawyersvn.com/vi/04-luu-y-cho-viec-lap-ho-so-danh-gia-tac-dong-xu-ly-du-lieu-ca-nhan-va-ho-so-danh-gia-tac-dong-chuyen-du-lieu-ra-nuoc-ngoai-theo-nghi-dinh-so-13-2023-nd-cp-cua-viet-nam/)
- [Vietnam's new PDP Law (LNT & Partners)](https://www.lntpartners.com/legal-briefing/vietnams-new-personal-data-protection-law-imposes-administrative-fines-up-to-5-of-annual-revenue-for-non-compliance) · [Frasers Legal Update PDP Law 7/2025 (PDF)](https://www.frasersvn.com/api/uploads/Legal_Update_VN_New_Law_on_Personal_Data_Protection_July_2025_ff4b8bcc4a.pdf)
- [Bí mật kinh doanh — điều kiện bảo hộ Điều 84 (ĐBND)](https://daibieunhandan.vn/print/10339614.html) · [Xâm phạm bí mật kinh doanh bị xử lý thế nào (SBLAW)](https://vi.sblaw.vn/xam-pham-bi-mat-kinh-doanh-bi-xu-ly-nhu-the-nao/)

---

## 4. Best practice chống rò rỉ qua prompt model cloud — ✅ có khung chuẩn quốc tế + công cụ cụ thể

### 4.1 Khung tham chiếu

- **OWASP Top 10 for LLM Applications**: rủi ro **"Sensitive Information Disclosure" (LLM06 trong bản v1.1; LLM02 trong bản 2026)** mô tả đúng hai rủi ro của Cá Về: rò PII và rò dữ liệu/bí mật riêng qua prompt, output hoặc do model ghi nhớ (memorization). Khuyến nghị cốt lõi: **làm sạch dữ liệu trước khi vào prompt, kiểm soát output, không tin "nhắc nhở trong system prompt"** (dễ bị prompt injection vượt qua). Nguồn: [OWASP GenAI (genai.owasp.org, bản v1.1 chính thức)](https://genai.owasp.org/wp-content/uploads/2024/05/OWASP-Top-10-for-LLM-Applications-v1_1_Chinese.pdf) · [F5 — hướng dẫn LLM06](https://my.f5.com/manage/MyF5_KnowledgeArticlePDF?article=K000149817) · [Forcepoint — OWASP LLM Top 10 2026](https://www.forcepoint.com/ko/blog/insights/owasp-llm-top-10).
- **NIST AI RMF Generative AI Profile (NIST AI 600-1, 26/7/2024)**: nhóm rủi ro "data privacy" + hành động quản trị gồm **input filtering và output redaction ở thời điểm suy luận (inference-time privacy controls)**, data minimization, kiểm tra memorization, quản trị dữ liệu huấn luyện. Nguồn: [NIST AI 600-1 (DOI)](https://doi.org/10.6028/NIST.AI.600-1) · [Tóm tắt 12 nhóm rủi ro (Modulos)](https://docs.modulos.ai/frameworks/nist-ai-rmf/generative-ai-profile).

### 4.2 Kỹ thuật từng loại (kèm nguồn)

| Kỹ thuật | Chống rò gì | Mô tả + nguồn | Áp cho Cá Về |
| :--- | :--- | :--- | :--- |
| **Allowlist context (default-deny)** | Cả hai | Chỉ đưa vào prompt đúng trường được khai báo (mã đơn, trạng thái, số liệu gộp); mạnh hơn denylist vì không phụ thuộc nhận diện mẫu. Chính là tinh thần BR-AI-05/09. Nguồn: [grc_library ai-security.md](https://github.com/jposluns/grc_library/blob/main/guardrails/ai/ai-security.md) (OWASP LLM06: "never include PII in prompts") | **Đã có trong thiết kế — giữ làm bất biến** |
| **PII redaction trước khi gửi** | PII khách | **Microsoft Presidio** (open source, Apache-2.0): phát hiện + thay/mã hóa PII (tên, SĐT, địa chỉ, thẻ…) bằng NER + regex, chạy như sidecar/microservice ngay trước khi dữ liệu rời hệ thống; có thể chạy "reversible" (khôi phục sau khi model trả lời). Lưu ý: cần huấn luyện recognizer tiếng Việt (SĐT VN, tên VN) — không có sẵn hoàn hảo; coi là **tầng lưới thứ 2**, không thay allowlist. Nguồn: [github.com/microsoft/presidio](https://github.com/microsoft/presidio) (qua [deps.dev](https://deps.dev/project/github/microsoft%2Fpresidio)) · [hướng dẫn chạy production (hoop.dev)](https://hoop.dev/blog/running-microsoft-presidio-in-production) | Adapter `/ai/*` — **nên có** |
| **DLP gateway / classifier cho prompt + output** | Cả hai | Cổng DLP phân loại prompt đi và câu trả lời về: chặn/mask PII, secret, và pattern giá vốn; ghi log metadata không ghi nội dung. Nguồn: [Forcepoint](https://www.forcepoint.com/ko/blog/insights/owasp-llm-top-10) · [F5 Data Guard](https://my.f5.com/manage/MyF5_KnowledgeArticlePDF?article=K000149817) · [NeuralTrust DLP docs](https://docs.neuraltrust.ai/platform/compliance/owasp-llm-top-10) | Adapter (proxy duy nhất) |
| **Output filter + redaction** | Cả hai | Quét câu trả lời trước khi về người dùng: chặn PII người khác, chặn giá vốn với user thiếu quyền (dù model "lỡ" trả). Nguồn: OWASP/F5/Forcepoint như trên; demo mã nguồn mở [rag-pii-guardrails](https://github.com/Ihsan-Aziz-CISSP/rag-pii-guardrails) | BE Django — **bắt buộc** |
| **On-device filtering / local-first** | Cả hai | Dữ liệu nhạy cảm xử lý tại chỗ, chỉ gửi đi phần đã lọc/gộp — đúng kiến trúc hybrid của ADR (lệnh `cao` ở local, ASR on-device BR-AI-15). Nguồn: NIST AI 600-1 inference-time controls; chính ADR 2.3/2.4 | **Đã có — giữ** |
| **Synthetic data / dữ liệu gộp** | Cả hai | Test, spike và đo hiệu năng dùng dữ liệu giả định (ADR 2.12 đã yêu cầu LLMock); không dùng dữ liệu vận hành thật (cũng là ràng buộc Q3 — chưa có thoả thuận với Lộc thì không dùng). Nguồn: NIST AI 600-1 (data minimization, training-data provenance) | Spike/training |
| **Zero data retention / không huấn luyện trên dữ liệu khách** | Cả hai | Cam kết của nhà cung cấp: **OpenAI** mặc định giữ API log 30 ngày, ZDR theo thoả thuận doanh nghiệp; **Anthropic** giữ 7 ngày (từ 9/2025), ZDR theo hợp đồng doanh nghiệp (có ngoại lệ lưu khi bị gắn cờ an toàn). **Xiaomi MiMo API** (công bố chính thức): Xiaomi là **bên xử lý**, khách là bên kiểm soát; **không dùng nội dung bạn cung cấp để huấn luyện nếu chưa được đồng ý**; xóa khi hết mục đích/yêu cầu; nền tảng toàn cầu lưu dữ liệu ở **EU/Singapore**. ⚠️ Cần xác nhận lại trong hợp đồng cụ thể khi mua API (chính sách nền tảng ≠ app tiêu dùng MiMo Desktop — app Desktop có dùng dữ liệu cho tối ưu model nếu bật "体验优化计划"). Nguồn: [MiMo Open Platform User Agreement (mimo.mi.com)](https://mimo.mi.com/docs/quick-start/terms/user-agreement) · [MiMo 开放平台隐私政策 (termshub.cn lưu trữ)](https://termshub.cn/public/archive/6637) · [Zero Data Retention: What Every AI Provider Actually Promises (securityboulevard.com, 9/2026)](https://securityboulevard.com/2026/09/zero-data-retention-what-every-ai-provider-actually-promises-you/) · [LLM API retention cross-provider (TheRouter.ai)](https://therouter.ai/blog/llm-api-privacy-data-retention-cross-provider-reference/) | Hợp đồng + hồ sơ |
| **Đánh giá bên thứ ba (security review)** | Cả hai | Rà soát chứng nhận (SOC 2/ISO 27001), chính sách dữ liệu, sub-processor, nơi lưu dữ liệu của nhà cung cấp API trước khi ký; kèm NDA/DPA. Nguồn: [AI vendors tighten data rules (4sysops)](https://4sysops.com/archives/ai-vendors-tighten-data-rules-as-enterprises-fear-intellectual-property-leakage/) · BLawyers checklist mục 3 | Trước khi bật cloud (Q1) |

---

## 5. Tiền lệ/khuyến cáo tại VN 2026 — doanh nghiệp dùng AI nội bộ (không bán sản phẩm AI)

| Câu hỏi | Kết quả kiểm chứng |
| :--- | :--- |
| Có phải đăng ký/giấy phép riêng không? | ✅ **Không có chế độ đăng ký hay thẩm định riêng** cho việc dùng AI trong vận hành nội bộ. Nghĩa vụ duy nhất mang tính "khai báo" là **tự phân loại rủi ro + thông báo Bộ KH&CN** nếu hệ thống ở mức **trung bình hoặc cao** (NĐ 142 Điều 14), làm trước khi đưa vào sử dụng, qua cổng một cửa AI (thủ tục điện tử, hệ thống tự cấp mã định danh). **Đánh giá sự phù hợp (conformity assessment) chỉ bắt buộc với rủi ro cao** — danh mục rủi ro cao do Thủ tướng ban hành **chưa được công bố** tại thời điểm nghiên cứu (dự kiến Q3/2026, ⚠️ theo dõi). |
| Dùng nội bộ có được miễn không? | ✅ Có hai miễn giảm đáng kể: (1) **miễn gắn nhãn nội dung AI dùng nội bộ, không công khai** (NĐ 142 Điều 18(4)); (2) miễn DTIA cho dữ liệu **người lao động** lưu trên cloud (Luật BVDLCN 2025 Điều 20). Nhưng **không có miễn trừ nào cho việc phân loại rủi ro + thông báo** — BLawyers (21/7/2026) nhấn mạnh không mặc định "chỉ là người sử dụng AI" để né nghĩa vụ. |
| Khuyến cáo thực hành phổ biến 2026 | ✅ Lập **AI inventory** (mỗi hệ thống: vai trò, mục đích, dữ liệu vào/ra, mức rủi ro); ban hành **chính sách AI nội bộ** (dữ liệu được phép, human review, đầu mối leo thang); quy trình **ứng phó sự cố AI** (72h/5 ngày làm việc); rà soát hợp đồng vendor; hạn chế nhập dữ liệu cá nhân/bí mật vào công cụ AI. Nguồn: [BLawyers 21/7/2026](https://www.blawyersvn.com/vi/su-dung-ai-trong-doanh-nghiep-can-chuan-bi-gi-de-tuan-thu-nghi-dinh-142-2026-nd-cp/) · [Lexology — Nghĩa vụ pháp lý quan trọng theo Luật AI mới](https://www.lexology.com/library/document.ashx?g=9fad9867-d01b-4cc3-80a4-a4af628af991) · [Licentium](https://www.licentium.io/post/vietnam-ai-law-134-2025-qh15-march-2026) |

---

## 6. Hệ quả cho thiết kế Cá Về

1. **Phân loại + thông báo là việc thật, trước khi bật production.** Hệ thống AI của Cá Về là **mới** → không hưởng chuyển tiếp Điều 35 (12 tháng). Trước khi `AI_ENABLED=true` ở production: (a) chốt phân loại **trung bình** (khớp ADR 2.11 — lưu lý do: có chatbot/gợi ý/auto-fill, nội dung AI tạo sinh; nếu chỉ nội bộ có thể tranh luận thấp, ⚠️ luật sư chốt); (b) lập **hồ sơ phân loại rủi ro** (NĐ 142 Điều 12); (c) **thông báo Bộ KH&CN qua cổng một cửa AI** (Điều 14). Vai trò: Duy/nhóm = nhà phát triển + nhà cung cấp; Lộc = bên triển khai (giám sát + báo cáo sự cố 72h/5 ngày).
2. **BR-AI-09 ("không PII vào prompt") không chỉ là bất biến dự án mà là chốt chặn pháp lý.** Giữ tuyệt đối → kênh AI không chuyển dữ liệu cá nhân xuyên biên giới → **không phát sinh DTIA riêng cho AI**. Một lần PII lọt vào prompt sang Xiaomi = chuyển xuyên biên giới chưa có hồ sơ (phạt tới 5% doanh thu). Vì vậy cần **chặn kỹ thuật ở adapter** (allowlist + redaction + hard-block), không chỉ dựa vào quy ước code. Lưu ý riêng: DTIA cho hạ tầng Supabase/Cloud Run ở Singapore (go-live mục 6b) là **việc độc lập** với AI, vẫn còn nợ.
3. **Giá vốn = bí mật kinh doanh, gửi cloud không có ràng buộc hợp đồng làm mất tư cách bảo hộ (Luật SHTT Điều 84).** Đây là lý do pháp lý củng cố Q5: **lệnh `cao` không lên cloud** ở MVP; nếu sau này Duy bật lệnh cloud+cao thì phải có **DPA/NDA + cam kết không huấn luyện** với nhà cung cấp API và ghi rõ trong hồ sơ phân loại. MiMo API công bố "không huấn luyện nếu chưa đồng ý, xóa khi hết mục đích, lưu ở EU/Singapore (nền tảng toàn cầu)" — ⚠️ xác nhận trong hợp đồng cụ thể.
4. **Minh bạch:** BR-AI-14 (giao diện nhận diện được AI) giữ nguyên — vừa là nghĩa vụ mức trung bình vừa là cơ sở phân loại. Gắn nhãn nội dung có thể miễn khi chỉ dùng nội bộ (NĐ 142 Điều 18(4)), nhưng **giữ nhãn AI trên mọi màn** — rẻ, an toàn, và bắt buộc nếu AI mở ra Shop.
5. **TMĐT:** thông báo website Sở Công Thương + lưu đơn tối thiểu 3 năm đã nằm trong go-live, AI không đổi gì. **Không có nghĩa vụ "khai báo chatbot" riêng trong NĐ 248.** Nếu sau này AI gợi ý/xếp hạng hiển thị hàng hóa cho khách ở Shop → công khai tiêu chí thuật toán (Điều 11 NĐ 248) + gắn nhãn AI (Luật AI).
6. **Log:** không log prompt chứa PII (BR-AI-09 — khớp OWASP khuyến nghị "log metadata, không log nội dung"); AuditLog `ai:<user>` chính là bằng chứng phục vụ **nghĩa vụ giải trình** của mức trung bình.

---

## 7. Checklist kỹ thuật chống rò rỉ (trước khi bật cloud — gắn với Q1/Q5)

| # | Hạng mục | Căn cứ | BR tương ứng | Trạng thái |
|---|---|---|---|---|
| 1 | **Allowlist context default-deny**: context builder chỉ đưa vào prompt đúng trường khai báo cho từng lệnh; mọi field khác bị loại kể cả model hỏi | OWASP LLM06; NIST AI 600-1 input filtering | BR-AI-05 | ☐ Giai đoạn 0 |
| 2 | **Cấm tuyệt đối PII khách trong prompt** (tên/SĐT/địa chỉ); context chỉ dùng mã đơn/mã khách/trạng thái | Luật BVDLCN 2025 Đ.20 (chuyển xuyên biên giới); bất biến 9 | BR-AI-09 | ☐ Giai đoạn 0 |
| 3 | **Redaction layer tại adapter** `/ai/*`: nhận diện + thay PII (Presidio tự build recognizer tiếng Việt: SĐT 10 số, pattern tên/địa chỉ) **và hard-block** nếu prompt/context có field nhạy cảm `cao` của lệnh cloud | OWASP LLM06; F5/Forcepoint DLP | BR-AI-03 | ☐ Giai đoạn 2 (khi mở cloud) |
| 4 | **Output filter**: quét câu trả lời trước khi về UI — chặn/mask PII và giá vốn đối với user thiếu `view_costprice` (model "lỡ" trả lời) | OWASP output redaction | BR-AI-05 | ☐ Giai đoạn 2 |
| 5 | **Không log prompt**; log chỉ metadata (mã lệnh, user, token, kênh) | OWASP logging hygiene; bất biến 9 | BR-AI-09 | ☐ Giai đoạn 0 |
| 6 | **Lệnh `cao` chỉ on-device** (giá vốn, lãi lỗ, giá mua); ASR/OCR on-device cho nội dung nhạy cảm | NIST AI 600-1; ADR 2.3; Luật SHTT Đ.84 | BR-AI-03/15 | ☐ Chờ Duy chốt Q5 |
| 7 | **Cam kết không huấn luyện + retention** trong hợp đồng API với nhà cung cấp cloud; kiểm tra nơi lưu dữ liệu (MiMo toàn cầu: EU/Singapore); ghi vào hồ sơ phân loại | MiMo terms; securityboulevard ZDR | Q1 | ☐ Trước khi ký/bật |
| 8 | **Đánh giá bên thứ ba**: SOC 2/ISO 27001, sub-processor, chính sách xử lý dữ liệu của nhà cung cấp API; NDA/DPA nếu có dữ liệu nhạy cảm | 4sysops; BLawyers checklist | Q1 | ☐ Trước khi ký/bật |
| 9 | **Dữ liệu giả (synthetic/mock)** cho spike, test, đo hiệu năng — không dùng dữ liệu vận hành thật khi chưa có thoả thuận với Lộc | ADR 2.12; NIST AI 600-1 data minimization; Q3 | — | ☐ Từ đầu |
| 10 | **Test chống prompt injection + test không-PII** cho kênh AI từng Group (tinh thần BR-PQ-13); pentest OWASP LLM01 | OWASP Top 10 for LLM | BR-PQ-13 | ☐ QA |
| 11 | **Hồ sơ phân loại rủi ro + thông báo Bộ KH&CN** qua cổng một cửa AI trước khi đưa vào sử dụng; quy trình báo cáo sự cố 72h/5 ngày làm việc | Luật AI 134; NĐ 142 Đ.12/14 | ADR 2.11 | ☐ Trước production |
| 12 | **Chính sách quyền riêng tư** nêu việc dùng AI + nhà cung cấp; đồng ý xử lý dữ liệu cá nhân ở checkout (việc go-live mục 6, AI không tạo thêm nghĩa vụ nếu giữ BR-AI-09) | Luật BVDLCN 2025 | go-live mục 6 | ☐ Go-live |

---

## 8. Đánh giá mức tin cậy

| Mục | Trạng thái | Ghi chú |
| :--- | :--- | :--- |
| Luật AI 134/2025 + NĐ 142/2026 | ✅ **Xác minh đầy đủ** | Văn bản chính thức + nhiều nguồn thứ cấp thống nhất; ⚠️ còn 2 điểm chờ: danh mục rủi ro cao của Thủ tướng (chưa công bố), diễn giải "trung bình vs thấp" cho AI nội bộ |
| NĐ 248/2026 TMĐT | ✅ **Xác minh đầy đủ** | Không có quy định AI/chatbot riêng — đã tìm 2 lượt, kết luận "không tìm thấy" là có cơ sở |
| Chuyển dữ liệu xuyên biên giới | ✅ **Xác minh đầy đủ** (⚠️ 1 điểm) | Căn cứ đã chuyển sang Luật BVDLCN 2025 Đ.20; NĐ 13/2023 phần còn phù hợp; ⚠️ nghị định hướng dẫn BVDLCN mới chưa ban hành |
| Best practice chống rò rỉ | ✅ **Xác minh đầy đủ** | OWASP, NIST, Presidio, chính sách ZDR của các hãng, chính sách chính thức của MiMo API |
| Tiền lệ VN 2026 (AI nội bộ) | ✅ **Xác minh** | Không có đăng ký riêng; nguồn luật sư VN cập nhật 7/2026 |

**Việc tiếp theo gợi ý:** chốt Q5 (lệnh `cao` không lên cloud) → ghi quyết định vào `decisions.md`; thêm 2 dòng vào hồ sơ feature: "trước production phải làm hồ sơ phân loại + thông báo Bộ KH&CN" và "trước khi bật cloud phải có cam kết không huấn luyện của nhà cung cấp API".
