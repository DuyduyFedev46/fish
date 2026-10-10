# Review P1–P7: CMS, khung go-live, chất lượng FE và đối chiếu QA
> **ĐÃ ĐÓNG — lịch sử (rà 11/10).** Lỗi đã sửa ở P8 (`2026-09-30-sua-loi-review`, XONG). Không dời thư mục vì test trong code còn trỏ tới.
> Tech Lead (Claude) · 2026-09-30 · `main` @ `75e5dd3` · chỉ đọc code, không sửa code sản phẩm, không commit.
> Phạm vi gồm hồ sơ `2026-09-28-cms-viet-bai`, `2026-09-28-khung-go-live`, phần FE của `2026-09-28-cskh-xac-nhan-in-tem` và phần FE của `2026-09-28-ai-digital-worker`.

## Kết luận: REVIEW FAIL (sửa có điều kiện)

Không có lỗi Critical. Không thấy rò giá vốn hay PII của khách qua API công khai.

Còn **3 lỗi Medium** phải sửa trước khi đưa CMS và go-live lên production:
- F1: IDOR ảnh khi tạo bài.
- F3: link bằng chứng đồng ý mở sai phiên bản.
- F4: vi phạm BR-AI-17 về bundle.

QA báo APPROVED cho mọi lô, nhưng phần lớn AC phía FE chỉ có bằng chứng là "đọc code". Playwright mà 02c bắt buộc thì chưa chạy lần nào. Chi tiết ở bảng "AC thiếu bằng chứng".

Lệnh đã chạy trong lượt review:
- `manage.py test apps.content apps.sales.orders.tests.test_privacy_consent apps.sales.orders.tests.test_privacy_consent_view`: 110 test, OK.
- Script tạm (DB test tự tạo rồi huỷ) để tái hiện F1.
- `node` chạy `safeHref.ts` của web với các payload để tái hiện F2.
- Đo gzip các chunk trong `erp-console/.next` (bản build lúc 05:27 ngày 30/09) để tái hiện F4.

## Bảng phát hiện

| Mã | Mức | File:dòng | Mô tả | Tái hiện | Đề xuất |
|---|---|---|---|---|---|
| F1 | **Medium** (R5 của 02b CMS) | `backend/apps/content/entries/services.py:157`; `backend/apps/content/body/sanitize.py:170`; `backend/apps/content/public/serializers.py:43` | IDOR ảnh khi **tạo** bài. Lúc `POST /api/content/entries/` thì `entry=None`, nên cả hai chỗ kiểm "ảnh cùng bài" đều bị bỏ qua. Kết quả là `cover_image` và khối `image` trỏ được tới `ContentImage` của bài khác, kể cả bài nháp chưa đăng. Lớp 1b `public_body` tra ảnh theo `pk__in` mà không lọc `entry_id`, nên khi đăng bài thì ảnh của bài nháp khác bị lộ công khai và giới hạn 20/100 ảnh mỗi bài cũng bị lách. QA ghi "IDOR đã chặn (payload 14)", nhưng payload 14 chỉ thử nhánh bài đã tồn tại. Test "PATCH `cover_image` ảnh bài khác → 400" mà R5 bắt buộc thì không có. | Tạo bài A có ảnh id=1, rồi `POST /api/content/entries/ {"title":"x","cover_image":1,"body":{"type":"doc","blocks":[{"type":"image","image_id":1}]}}` bằng token `quan_ly`. Kết quả **201**, `cover_image_id=1` thuộc bài A. | Khi tạo (`entry is None`), từ chối mọi `cover_image` và mọi khối `image` với 400 `BR-ND-07`, vì ảnh chỉ tải lên được cho bài đã có. `public_body` và ảnh bìa công khai lọc thêm `entry_id=version.entry_id`. Thêm test cho nhánh tạo và nhánh PATCH. |
| F2 | Low | `frontend/features/content/safeHref.ts:14`, `ArticleBody.tsx:40` | Lớp 2 lệch §6.2. `isSafeHref` nhận mọi chuỗi bắt đầu bằng `/`, gồm `//evil.example/phish` và `/\evil.example`. Link đó được dựng bằng `<Link>` cùng tab, không có `rel`. Lớp 1 và 1b ở server vẫn chặn nên hiện chưa khai thác được, nhưng lớp phòng thủ thứ hai bị hở. Bản ERP (`erp-console/features/content/editor/convert.ts:7`) thì làm đúng, tức là cùng một hàm đang có hai bản khác nhau. | `node` chạy `isSafeHref("//evil.example/phish")` và `isSafeHref("/\\evil.example")` đều trả `true`. | Chép đúng luật của `convert.ts::safeHref` (chặn `//`, `/\`, khoảng trắng và ký tự điều khiển, độ dài tối đa 2000). Thêm unit test 15 payload cho web. |
| F3 | **Medium** | `erp-console/features/orders/components/OrderDetailView.tsx:266`; `erp-console/app/(console)/content/edit/page.tsx:73-74` | GL-05-AC1 chưa đạt. Link "xem đúng phiên bản" trỏ tới `/content/edit/?id=…&version=N`, nhưng màn edit chỉ đọc `id` và `new`, bỏ qua `version`. Chủ bấm vào thì thấy **bản đang soạn hiện tại**, không phải phiên bản khách đã đồng ý. Đây là bằng chứng pháp lý nên sai là nghiêm trọng. QA chấm PASS chỉ dựa vào code backend. | Mở chi tiết đơn có consent v1 sau khi chính sách đã lên v2, rồi bấm link. Màn hình mở bản nháp hoặc v2. | Màn edit đọc `version` và mở thẳng panel lịch sử ở phiên bản đó (`GET …/versions/<n>/`, CMS-11). Hoặc làm màn xem phiên bản chỉ đọc. Thêm test FE. |
| F4 | **Medium** (BR-AI-17, DW-09-AC8) | `erp-console/features/guidance/components/GuidancePanel.tsx:14-18,69` | `GuidancePanel` được gắn ở `/orders`, `/orders/payments`, `/orders/refunds` và `/inventory`. Nó **import tĩnh** `features/ai/runtime/engine` (kéo theo `worker-manager` và `new Worker`), cùng `ai/commands/call`, `ai/actions/api` và `ai/api`, trong đó có `mock.ts`. Vì vậy code AI nằm trong chunk của màn nghiệp vụ với **mọi người dùng**, kể cả người không bật AI. Ngoài ra mỗi lần mở màn đều gọi `GET /api/ai/status/`, trái nguyên tắc "AI không bật thì 0 request" mà `AiAssistantGate` đang giữ. Dev notes ghi "/orders giữ nguyên 128 kB", nhưng mốc gốc là 127 kB và không có số đo sau Lô 3a trở đi. | Chunk `static/chunks/6877-*.js` (2,15 kB gzip, chứa `new Worker`, `/call/` và `wllama`) có trong manifest của `/orders` và `/inventory`. Chunk `9907-*.js` (7,8 kB gzip) chứa `AI_MSG`. | Tách phần "Để AI làm/Nhờ" thành component nạp bằng `next/dynamic`, chỉ render khi `ai_enabled` và người dùng đã đồng ý. `GuidancePanel` chỉ giữ phần tất định. Chỉ gọi `ai/status` khi cần. Ghi bảng First Load JS trước/sau vào `03-dev-notes.md`. |
| F5 | Low | `backend/apps/sales/orders/tests/test_privacy_consent.py:285`, `:277-283`, `:257` | Có 3 test rỗng hoặc yếu mà QA vẫn tính là bằng chứng. (a) Test cờ `PRIVACY_CONSENT_REQUIRED` gọi `_bool(..., "1")` với hằng số, nên luôn đúng và không kiểm biểu thức ở `settings.py:329`. (b) Phần "Admin POST không đổi 2 field" của GL-03-AC10 so giá trị với chính nó và không gọi Admin. (c) GL-03-AC9 chỉ `assertNotIn` 3 khoá, trong khi 02c yêu cầu so **đúng tập khoá** của response tra đơn. | Đọc test. | (a) Tách hàm đọc cờ nhận `testing` và `debug` rồi test hàm đó. (b) Dùng `Client.force_login(superuser)` để POST lên admin change form. (c) So `set(resp.json())` với tập khoá hằng. |
| F6 | Low | `frontend/lib/api.ts:39` | `apiFetch` của Shop đã đổi hành vi 404: thêm 410 và lấy `detail` từ server. 02c CMS ghi đây là **điểm dừng** ("apiFetch Shop cần đổi hành vi 404 → Lệch thiết kế"). `03-dev-notes.md` của CMS ghi "Lệch thiết kế: *(Không có)*" ở cả 7 lô. | `git show 9c03606 -- frontend/lib/api.ts` | Ghi bổ sung "Lệch thiết kế" và kiểm lại các chỗ Shop đang so chuỗi "Không tìm thấy". |
| F7 | Low | `frontend/features/content/components/ItemCard.tsx:25` | Lệch §13 mà không ghi lại. Thiết kế yêu cầu gọi `getCatalog()` **một lần** cho cả bài, còn code gọi `getCatalogItem` một lần **cho mỗi thẻ**, nên N thẻ thành N request và dễ chạm throttle Shop. | Đọc code. | Nạp catalog một lần ở `ArticleBody` rồi truyền map xuống, hoặc ghi "Lệch thiết kế". |
| F8 | Low | `frontend/features/content/components/ArticleBody.tsx:96-104` | Ảnh thân bài dùng bản `lg` (1600 px), không có `srcSet`/`sizes` như §6.2. Điện thoại vì vậy tải ảnh lớn gấp khoảng 3 lần cần thiết. | Đọc code. | Thêm `srcSet` 480w/960w/1600w và `sizes`. |
| F9 | Low | `frontend/features/content/mock.ts` | Không có mock `xss-mau` và không có Playwright XSS, dù 02b §6.3/§8.7 và 02c Lô 3 bắt buộc. Lớp 2 chưa bao giờ được chạy thật với payload. | `grep -i xss frontend/features/content/mock.ts` không ra kết quả. | Thêm mock và spec Playwright như 02c. |
| F10 | Low | `frontend/features/checkout/components/CheckoutScreen.tsx:287-310` và `PaymentPanel.tsx:76-100`; `frontend/lib/api.ts:121` và `frontend/features/site/api.ts:5`; `backend/config/settings.py:288,333` | Code lặp. Khối câu CSKH được chép nguyên ở hai file. Có hai hàm `getSiteInfo` với hai kiểu dữ liệu khác nhau. Màn thanh toán gọi `site-info` 3 lần (`PaymentPanel` + `ConfirmCallNotice`, cộng thêm lần ở Checkout). Hai giờ gọi mặc định mâu thuẫn nhau: `SHOP_CONFIRM_CALL_HOURS=7:00–20:00` và `CSKH_WORKING_HOURS=07:00-21:00`. Nếu bật `SHOP_CONFIRM_CALL_NOTICE`, khách thấy 2 câu với 2 khung giờ khác nhau. | Đọc code. | Tách component `CskhNotice` dùng chung, giữ một `getSiteInfo`, và dùng một nguồn giờ gọi. |
| F11 | Low | `erp-console/app/(console)/content/edit/page.tsx` (1556 dòng); `erp-console/features/guidance/index.ts` | File route quá dài, trái quy ước "app/ chỉ route, mỏng". Màn soạn nên nằm ở `features/content/components/`. Ngoài ra có barrel `index.ts` mà skill cấm. | `wc -l` | Chuyển màn soạn sang `features/content`. Bỏ barrel. |
| F12 | Low | `erp-console/app/ai-spike/page.tsx`, `erp-console/spikes/dw02/` | 02c AI Lô 2 yêu cầu xoá hai thư mục này, nhưng chúng vẫn được git theo dõi và vẫn build ra `out/ai-spike`. Dev notes chỉ ghi đã xoá `backend/spikes/dw01/`. | `git ls-files erp-console/app/ai-spike erp-console/spikes` | Xoá, hoặc ghi "Lệch thiết kế". |
| F13 | Info | `erp-console/features/ai/messages.ts` (có trong chunk `layout`) | Chunk layout chứa chuỗi `wllamaMissing`, trái chú thích C.4 #3 "chunk ban đầu không có chuỗi wllama". Đây chỉ là chuỗi thông báo, không phải code runtime. | Tìm chuỗi `wllama` trong `layout-*.js`. | Tách `AI_MSG` phần runtime ra khỏi file mà gate import. |
| F14 | Info | `erp-console/app/print/label/page.tsx:262` | `dangerouslySetInnerHTML` được dùng cho SVG QR do thư viện `qrcode` sinh từ `barcode_value` của server. Hiện an toàn vì thư viện chỉ xuất path, nhưng chỗ này nằm ngoài lệnh grep của 02c. Lúc chưa đăng nhập, trang chuyển về `?next=/print/label/` và mất `note`. | Đọc code. | Có thể render `<img src="data:image/svg+xml,…">`. Giữ nguyên query khi chuyển về trang đăng nhập. |

## AC thiếu bằng chứng (QA chấm PASS nhưng không có test tự động hoặc Playwright như 02c yêu cầu)

| Hồ sơ | AC | Bằng chứng QA đưa ra | Thiếu gì |
|---|---|---|---|
| CMS | CMS-13-AC1 | Một câu mô tả "đã sửa endpoint" | Không có test FE hay E2E nào |
| CMS | CMS-13-AC2 (lớp 2), AC6, AC7, AC8, AC10 | Đọc `ArticleBody.tsx` và `page.tsx` | Playwright `xss-mau` (không `dialog`/`script`/`javascript:`), kiểm `rel`, kiểm chỉ gọi API + bucket. Mock `xss-mau` cũng không tồn tại (F9) |
| CMS | CMS-03-AC13, CMS-05-AC6, AC8 | File CSS, `ImageUploader.tsx` | 375×667 không cuộn ngang và nút ≥ 44 px; mất mạng khi tải ảnh; test FE dán HTML |
| CMS | CMS-05-AC5 | Trích `storage.py` | Không có test "gỡ ảnh khỏi bài thì URL cũ vẫn còn" |
| CMS | R5 (02b §14): PATCH/POST `cover_image` bằng ảnh bài khác | Payload 14 (chỉ kiểm body, chỉ bài đã có) | Test nhánh bìa và nhánh tạo. Nhánh tạo đang lỗi (F1) |
| CMS | CMS-06-AC3, AC4, AC5, AC7 (phần FE) | Đọc `ItemCard.tsx` | Playwright: giá mới, URL UTM đúng, "Tạm hết hàng", không request tới API ERP |
| CMS | CMS-14-AC3, AC4 | Đọc `LatestPosts.tsx` | Test FE khi API tắt thì ẩn khối và Landing vẫn đủ |
| CMS | CMS-04-AC1…AC5, CMS-11-AC3 | Trích số dòng trong `edit/page.tsx` | Playwright offline/online và 409 mà 02c Lô 7 bắt buộc. Chỉ AC6 có một phần unit test |
| Go-live | GL-01-AC2, AC5, AC6 (FE); GL-02-AC1…AC5 (FE) | Đọc `SiteLegalFooter.tsx` và CSS | Playwright footer trên 7 route, trường hợp API lỗi, 375×667 |
| Go-live | GL-03-AC2, AC4 (FE), AC5 (FE), AC8 (storage/URL) | Đọc `CheckoutScreen.tsx` | Test FE mock 409/404 và kiểm `localStorage`/`sessionStorage` |
| Go-live | GL-03-AC9, GL-03-AC10 (Admin), cờ `PRIVACY_CONSENT_REQUIRED` | Có test nhưng rỗng hoặc yếu (F5) | So đúng tập khoá, POST Admin thật, test biểu thức settings |
| Go-live | GL-04-AC1…AC5 | Đọc `ConfirmCallNotice.tsx` và `PaymentPanel.tsx` | Test FE mock bật/tắt cờ và quét DOM/URL không có SĐT đầy đủ |
| Go-live | GL-05-AC1 (FE link đúng phiên bản) | Chỉ test BE | Không có test FE, và thực tế đang sai (F3) |
| CSKH | CS-11-AC6 (PDF 1 trang 100×150 ±1 mm, giải mã QR) | Trích CSS `@page` | Playwright `page.pdf` mà 02c Lô 2 bắt buộc |
| CSKH | X-AC4 (storage/URL/console) | Lệnh `grep` | Playwright mà 02c Lô 2 bắt buộc. Grep sạch là điều kiện cần, chưa đủ |
| CSKH | CS-02-AC6, CS-05-AC8 (mobile 360×640) | Trích CSS | Chưa kiểm giao diện thật |
| AI | DW-09-AC8 / BR-AI-17 ("chunk AI không tải khi AI tắt", First Load JS tăng không quá 1 KB) | Unit test `index` trả 410 | Chưa từng kiểm chunk. Thực tế đang vi phạm (F4) |

## Đã kiểm, ổn

- **XSS lớp 1 (server):** `normalize_body` dùng danh sách trắng khối, mark và khoá, và idempotent. `href` bị chặn khi có khoảng trắng hoặc ký tự điều khiển (gồm `java\tscript:`), khi scheme nằm ngoài {http, https, mailto, tel}, và khi là `//` hoặc `/\`. Chữ `<img …>` được giữ nguyên. 15 payload §6.3 có test (`body/tests/test_sanitize.py`).
- **XSS lớp 1b:** `public_body` chạy lại `normalize_body(strict=False)` và bỏ `image_id`. Serializer công khai dựng dict tường minh, `author` là hằng "Cá Về", không có `published_by_name`.
- **XSS lớp 2:** `ArticleBody` dùng `switch` theo danh sách trắng, `default: null`, chữ luôn là React children. Grep `dangerouslySetInnerHTML` trong `frontend/features/content`, `app/bai-viet`, `app/trang` và `erp-console/features/content` cho kết quả rỗng. ERP Tiptap: `Link.configure({ validate: safeHref })`, và `safeHref` bản ERP đúng luật §6.1.
- **API công khai CMS:** chỉ cho GET/HEAD/OPTIONS, `AllowAny`, có throttle `public_content` và `Cache-Control: public, max-age=60`. Bài nháp, bài chờ duyệt và slug không tồn tại trả cùng một body 404. Bài đã gỡ trả 410. Page vượt quá thì trả 404, không phải 500.
- **Consent server-side:** `resolve_privacy_consent` chạy trong `create_order` **trước** `transaction.atomic`, trước giữ chỗ và trước FEFO. `accepted` phải đúng là `True`, còn `policy_version_id` phải là `int` và bằng phiên bản hiện hành, nếu không thì trả 409 `POLICY_CHANGED` kèm `current`. Không có chính sách mà cờ đang bật thì trả 503. Thiếu hoặc sai payload thì trả 400 `BR-BH-17`. Test GL-03-AC3 kiểm cả việc không giữ chỗ.
- **Thu tối thiểu:** `SalesOrder` chỉ thêm `privacy_consent_at` và `privacy_policy_version` (FK `PROTECT`, `editable=False`). Không lưu IP hay UA, và không có code đọc `REMOTE_ADDR` hay `HTTP_USER_AGENT`.
- **Cờ `PRIVACY_CONSENT_REQUIRED`:** mặc định bật khi không ở chế độ `TESTING` hay `DEBUG` (`settings.py:329`). Biểu thức đúng, chỉ có test là rỗng (F5).
- **Footer người bán:** `site_info()` đọc `settings.SELLER_*` ở mỗi request và dựng dict tường minh, nên không lộ secret. System check `content.W001` chỉ in tên biến. Repo không có giá trị người bán thật. `tel:` và `mailto:` có làm sạch.
- **GL-05 phân quyền:** `privacy_consent` chỉ có khi user có `sales.view_privacy_consent` (chỉ `chu` và `quan_ly`). `nv_kho`/`nv_giao` bị bỏ khoá này, có test quét đệ quy. Group `cskh` không có quyền `content` nào.
- **Checkout FE:** ô đồng ý mặc định chưa tick, nút bị khoá tới khi tick, link mở tab mới. Khi nhận 409 thì bỏ tick, cập nhật link và giữ form. Khi nhận 503 thì hiện "Shop tạm chưa nhận đơn". `sessionStorage` chỉ lưu `order_code` và 4 số cuối. Giỏ hàng chỉ lưu mã và số lượng. Không có `console.*` trong `frontend/`.
- **Trang in tem:** URL chỉ có `note` và `print_no`. Tem hiện `recipient_phone_masked`. Không có `localStorage`, `sessionStorage` hay `console` trong `features/cskh`, `features/deliveries` và `app/print`.
- **Gate trợ lý AI** (`AiAssistantGate`): panel nặng nạp qua `next/dynamic`, chỉ khi `ai_enabled` và đã đồng ý. `ai/status` chỉ được gọi khi mở tab. Vấn đề còn lại nằm ở đường khác (F4).
- **Thư viện thêm:** ERP chỉ thêm `@tiptap/*` 2.x (nằm trong danh sách 02c CMS Lô 2) và `vitest` (TL-7). `frontend/` không thêm thư viện nào.
- **Tiếng Việt:** thông điệp lỗi, trạng thái tải, lỗi kèm "Thử lại" và rỗng ("Chưa có bài") có đủ ở `/bai-viet`, `/trang` và checkout.
