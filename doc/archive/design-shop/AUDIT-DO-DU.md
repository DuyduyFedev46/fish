# Soát độ đủ của bộ thiết kế Shop trước khi code

> `ux-designer` · 2026-10-07 · CHỈ ĐỌC (không sửa màn, không sửa tài liệu).
> Nguồn soát: `scratchpad/canvas/project/*.dc.html` + `canvas.json` (79 board), `wt-shop/doc/design/shop/` (README, UI-RULES,
> COMPONENTS, HUONG-DAN-CODE, PLAN, DOI-CHIEU-CODE), repo `/home/user/fish`: `doc/business-process-spec.md` (§13 E-01…E-17,
> BR-BH, BR-TT, BR-HT), `doc/decisions.md`, bất biến 9 (`caveve-domain`), `doc/ops/go-live-phap-ly.md`, `frontend/app/`,
> `backend/apps/common/throttling.py`.
>
> Mức độ: **Chặn code (lô N)** = fe-dev phải đoán hoặc làm sai nếu bắt đầu lô N · **Nên có** = làm được nhưng dễ lệch, nên bổ
> sung trước lô liên quan · **Để sau** = dọn dẹp, không ảnh hưởng code V1.

---

## 1. Luồng

### 1.1 Luồng chính: xem → tìm → chi tiết → giỏ → đặt → thanh toán → đơn → giao

| Bước | Màn có | Nhánh đã vẽ | Còn thiếu / lệch | Mức |
|---|---|---|---|---|
| Xem (trang chủ) | A1, DesktopHome | happy | Trạng thái tải, lỗi tải catalog, rỗng (không món nào còn hàng). Lô 1 dựng trang này | **Chặn lô 1** (nhỏ, xem đề xuất §3) |
| Tìm | A9 (gợi ý), A5 (không thấy), DesktopSearchSuggest, DesktopNotFound | happy, 0 kết quả | Gợi ý khi gõ mà không khớp món nào (dropdown hiện gì) | Nên có |
| Danh mục | A2, A0, A6, A4, DesktopCategory/Loading/Offline/Toast | đủ tải, lỗi mạng, toast | Nhóm hàng không có món (lọc `?group=` rỗng): dùng lại EmptyState `search`? ghi một dòng | Nên có |
| Chi tiết | A3, A7 (hết), A10 (combo), Desktop×3 | happy, hết hàng, combo | **Đang tải**, **mã hàng không tồn tại / đã ngưng bán** (link chia sẻ, link "Món dùng trong bài" ở Góc bếp), **lỗi mạng** | **Chặn lô 2** |
| Giỏ | B1–B4, DesktopCart (có nhánh rỗng), DesktopRemoveConfirm, DesktopCartChanged | happy, bỏ món, đổi giá/hết, rỗng | **Đang tải lại catalog để so giá** và **tải lỗi** (cho đi tiếp hay chặn?). Mâu thuẫn: B3 vẽ "Tiếp tục với 2 món còn hàng" (tự loại món hết), còn CMP-5 ghi "Nút đặt hàng bị chặn tới khi bỏ món" | **Chặn lô 2** |
| Đặt hàng | C1, C1b, C1c, C2, C3, C4, C5, Desktop×5 | happy, bản đồ, sai, hết hàng E-06, lỗi mạng, từ chối vị trí | (a) **Shop tạm chưa nhận đơn** (GL-03-AC5, code đang có `CheckoutScreen.tsx:83-97`); (b) **409 `POLICY_CHANGED`** buộc đồng ý lại (`:141-155`); (c) khối **giờ gọi xác nhận** GL-04 (`ConfirmCallNotice`); (d) **429** khi tạo đơn (`ShopOrderCreateThrottle` có sẵn); (e) vào thẳng `/shop/checkout/` khi giỏ rỗng; (f) C1 điện thoại **không có dòng "Phí giao"** (máy tính có) | **Chặn lô 3** |
| Thanh toán | D1–D6, Desktop×6 | happy, huỷ/lỗi SePay, chờ tiền, hết giờ E-01, thiếu tiền E-02, rời trang | (a) **Đang tải đơn**; (b) lỗi gọi `checkout/` (COMPONENTS ghi Banner `crit` `[copy]` nhưng không vẽ); (c) **429** `ShopCheckoutThrottle`; (d) D1 điện thoại **không có dòng "Phí giao"** | **Chặn lô 4** (a–c), Chặn lô 3 (d, chờ Q6) |
| Đơn (sau trả tiền) | E1–E4, DesktopSuccess, DesktopOrderStates | thành công, huỷ E-03/E-07, đã giao, giao lỗi E-08 | (a) **Đang tải**, **lỗi mạng**, **429** tra đơn (`ShopLookupIpThrottle/OrderThrottle`); (b) **Huỷ một phần** (E-07 "huỷ toàn/một phần", BR-HT-02): đơn còn giao một số món; (c) nhãn trạng thái ngay sau khi trả tiền (E1 vẽ "Đang chuẩn bị", CMP-5 gán "Chờ cửa hàng xác nhận" cho đúng trạng thái này, COMPONENTS lại gán `awaiting_review` cho D5) | **Chặn lô 4** (a, c), Nên có (b) |
| Tra cứu | F1, F2, DesktopLookup | happy, không thấy | Mở `/shop/orders/?code=` trên máy khác/tab mới (không có token): F1 **điền sẵn mã, chỉ hỏi SĐT** | Nên có (lô 4) |
| Giao | E3, E4 | đã giao, chưa giao được | E-08 lần 2 → E-09 hàng về kho → đơn huỷ: dùng E2 (ghi rõ trong bảng ưu tiên trạng thái) | Nên có |

### 1.2 Ngoại lệ phía khách (spec §13)

| Mã | Ngoại lệ | Màn | Đánh giá |
|---|---|---|---|
| E-01 | Quá 30' không trả | D4, DesktopModalExpired | ✓ Popup khi đang ở trang. **Thiếu**: khách mở lại đơn đã tự huỷ (chưa trả tiền) vài giờ sau qua tra cứu, thấy dạng trang gì (D4 là popup đè lên D1). D4 hard-code "30 phút" trong câu (COMPONENTS cấm). Nên có |
| E-02 | Tiền về thiếu | D5, DesktopUnderpaid | ✓ (L-15: V1 gần như không xảy ra, chờ Duy giữ/bỏ) |
| E-03 | Tiền về sau khi huỷ | E2 + dòng cuối D4 "Đã chuyển khoản rồi? Liên hệ…" | ✓ Nhưng E2 chỉ vẽ lý do "Lô hàng không đạt khi soạn". Ca đặc thù E-03 là **đơn tự huỷ do hết giờ + tiền về sau**: lý do hiển thị cần nằm trong bảng nhãn công khai (L-14) |
| E-04 | Webhook trùng | — | Không lộ ra khách. Không cần màn |
| E-05 | Webhook không tới | D3 | **Thiếu**: D3 tự kiểm mỗi 5 s vô hạn. Cần ngưỡng (vd 3–5 phút) rồi chuyển sang "Cá Về sẽ kiểm tra giao dịch và gọi lại" + hotline. **Chặn lô 4** |
| E-06 | Tranh lô cuối | C3, DesktopModalSoldOut | ✓ Lệch nhỏ: điện thoại "sẽ bỏ khỏi đơn", máy tính "sẽ bỏ khỏi giỏ" |
| E-07 | Hàng hỏng khi soạn | E2 | ✓ huỷ toàn phần. **Thiếu huỷ một phần** (xem 1.1). Nên có |
| E-08 | Giao 2 lần không gặp | E4 | ✓ |
| E-13 | Thành phần combo hết | A10 banner + StockBadge `out` | ✓ |

### 1.3 Các trường hợp biên được yêu cầu

| Trường hợp | Có trong thiết kế? | Đề xuất | Mức |
|---|---|---|---|
| Mở link SePay đã hết hạn | Trang SePay nằm ngoài UI Cá Về. Khi SePay trả về `result=error/cancel` sau khi đơn đã `AUTO_CANCELLED`, D2 sẽ ghi sai "Đơn vẫn đang được giữ" nếu FE tin `result` | **Bảng ưu tiên**: trạng thái đơn thắng tham số `result`. `AUTO_CANCELLED` → D4 (dạng trang khi không phải đang xem trực tiếp) | **Chặn lô 4** |
| F5 giữa chừng | Giỏ: giữ (localStorage). Checkout: form mất (không được lưu dữ liệu cá nhân). D1: giữ được nhờ route `/shop/orders/?code=` + token sessionStorage | Ghi rõ hành vi F5 cho từng bước; cân nhắc `beforeunload` khi form checkout đã nhập | Nên có |
| Đơn đã trả mà mở lại link thanh toán | Không vẽ | `?code=X` của đơn đã PAID luôn ra E1 (không banner, không nút thanh toán). `result=cancel` đến sau webhook → vẫn E1 | **Chặn lô 4** (nằm trong bảng ưu tiên) |
| Tắt trình duyệt rồi quay lại | Không vẽ. sessionStorage mất token; khách không nhớ mã đơn thì đặt lại → **giữ chỗ gấp đôi 30'** | (a) D1/E1 thêm nút **"Sao chép mã đơn"** + câu nhắc lưu mã `[copy]`; (b) hỏi Duy cho lưu "đơn gần đây" (chỉ mã đơn + token, không dữ liệu cá nhân) ở localStorage để giỏ hiện banner "Bạn có đơn SO… đang chờ thanh toán (còn mm:ss)" | Nên có (lô 3–4) |
| Shop tạm ngưng nhận đơn (GL-03-AC5) | **Không vẽ** (L-17) | Vẽ trạng thái checkout: Banner `warn` thay form + hotline; nút "Tiếp tục" ở giỏ có báo trước. Hỏi: chỉ khi chưa có chính sách, hay Lộc bật tay được | **Chặn lô 3** |
| Trang 404 | A5/DesktopNotFound là **tìm không thấy**, không phải 404. Trang 404 chỉ có dòng trong COMPONENTS (EmptyState `page`, copy `[copy]`) | Vẽ 1 màn mỗi khổ hoặc chốt copy với `mkt-brand`. Lô 1 restyle `app/not-found.tsx` | **Chặn lô 1** (copy) |
| Lỗi máy chủ 500 | Không vẽ. Static export nên "500" = API trả 5xx, hoặc lỗi JS (cần `app/error.tsx`) | Bảng ánh xạ: mất mạng (A6) · máy chủ lỗi 5xx ("Hệ thống đang bận, thử lại sau ít phút") · 429 ("Bạn thao tác hơi nhanh, đợi … rồi thử lại") · lỗi JS (trang lỗi chung + "Tải lại trang" + hotline). Một `ErrorState` nhiều biến thể | Nên có (lô 1 dựng ErrorState) |

---

## 2. Hai khổ: ma trận điện thoại ↔ máy tính

| Màn | Điện thoại | Máy tính | Thiếu | Có cần vẽ? |
|---|---|---|---|---|
| Trang chủ | A1 `Home` | `DesktopHome` | — | |
| Danh mục | A2 `Main` | `DesktopCategory` | — | |
| Toast thêm giỏ | A4 | `DesktopToast` (+ giỏ mini) | — | |
| Tìm không thấy | A5 | `DesktopNotFound` | — | |
| Mất mạng | A6 | `DesktopOffline` | — | |
| Hết hàng | A7 | `DesktopOutOfStock` | — | |
| Đang tải | A0 (tên canvas "A8") | `DesktopLoading` | — | |
| Gợi ý tìm | A8 (canvas "A9") | `DesktopSearchSuggest` | — | |
| Chi tiết | A3 `Product` | `DesktopProduct` | — | |
| Chi tiết combo | A9 (canvas "A10") | `DesktopComboDetail` | — | |
| Giỏ | B1 `Cart` | `DesktopCart` | — | |
| Bỏ món | B2 | `DesktopRemoveConfirm` | — | |
| Giỏ thay đổi | B3 | `DesktopCartChanged` | — | |
| Giỏ trống | B4 | nhánh `isEmpty` trong `DesktopCart` | — | Không cần |
| Thông tin nhận | C1 `Checkout` | `DesktopCheckout` | — | |
| Bản đồ | C1b | `DesktopMapPicker` | — | |
| Địa chỉ tự điền | C1c | **thiếu** | máy tính | Không cần (chỉ khác nền ô + banner, suy được) |
| Nhập sai | C2 | `DesktopInvalid` | — | |
| Hết hàng lúc đặt | C3 | `DesktopModalSoldOut` | — | |
| Lỗi kết nối | C4 | `DesktopNetworkError` | — | |
| Từ chối vị trí / bản đồ lỗi | C5 | **thiếu** | máy tính | Để sau (Dialog chuẩn, suy được) |
| Thanh toán | D1 `Payment` | `DesktopPayment` | — | |
| Thanh toán chưa thành công | D2 | `DesktopPayCancelled` | — | |
| Chờ tiền | D3 | `DesktopPayPending` | — | |
| Hết giờ | D4 | `DesktopModalExpired` | — | |
| Thiếu tiền | D5 | `DesktopUnderpaid` | — | |
| Rời trang | D6 | `DesktopLeavePayment` | — | |
| Đơn sau trả tiền | E1 `Success` | `DesktopSuccess` | — | |
| Huỷ / đã giao / giao lỗi | E2, E3, E4 | `DesktopOrderStates` (gộp 3) | — | |
| Tra cứu | F1 | `DesktopLookup` vẽ ca **lỗi**; ca thường suy bằng bỏ banner | — | Không cần |
| Không thấy đơn | F2 | `DesktopLookup` | — | |
| Chính sách | P1 (canvas "F3") | `DesktopPolicy` | — | |
| Liên hệ | P2 ("F4") | `DesktopContact` | — | |
| Cách mua | P3 ("F5") là **trang riêng** | **gộp làm một khối trong `DesktopPolicy`** (`#cach-mua`) | lệch cấu trúc | **Nên có**: chốt một route (Q7). Cùng một trang Next.js không thể vừa là trang riêng vừa là khối trong trang chính sách |
| Góc bếp danh sách / bài | G1, G2 | `DesktopKitchenList`, `DesktopKitchenArticle` | — | |
| Landing `/gioi-thieu/` | **thiếu** | `Landing` (1280) | điện thoại | **Chặn lô 1** nếu lô 1 dựng landing theo thiết kế mới (Shop mobile-first). Hoặc chốt lô 1 chỉ chuyển nguyên landing cũ (đã responsive) sang `/gioi-thieu/`, restyle sau |
| Trang 404 | **thiếu** | **thiếu** | cả hai | Chặn lô 1 (copy) |
| Footer rút gọn F2 | **thiếu** (đặc tả chỉ ghi "dải pháp lý gọn") | có trong `HeaderFooter-Desktop` | điện thoại | Nên có (lô 1) |

Tổng: 38 màn điện thoại, 31 màn máy tính, 3 bảng đặc tả. Cặp **thật sự cần bổ sung**: Landing điện thoại, 404 (cả hai), Cách mua (lệch cấu trúc), F2 điện thoại.

---

## 3. Trạng thái (UI-RULES §7)

✓ có màn · ~ có đặc tả chữ trong COMPONENTS nhưng không vẽ · ✗ thiếu · — không áp dụng.

| Màn | Đang tải | Rỗng | Lỗi mạng | Lỗi máy chủ / 429 | Lỗi nghiệp vụ | Đang gửi | Thành công |
|---|---|---|---|---|---|---|---|
| Trang chủ | ✗ | ✗ (không món còn hàng) | ✗ | ✗ | — | — | ✓ |
| Danh mục | ✓ A0 | ✓ A5 · ~ nhóm rỗng | ✓ A6 | ✗ | hết hàng xếp cuối ✓ | — | ✓ A4 |
| Gợi ý tìm | — | ✗ (gõ không khớp) | — | — | — | — | ✓ |
| Chi tiết | ✗ | ✗ mã không tồn tại/ngưng bán | ✗ | ✗ | ✓ A7, A10 | — | ✓ toast |
| Giỏ | ~ `CartLineSkeleton` | ✓ B4 | ✗ (tải giá lỗi) | ✗ | ✓ B3 | — | — |
| Đặt hàng | — | ✗ (vào thẳng khi giỏ rỗng) | ✓ C4 | ✗ 429 | ✓ C2, C3 · ✗ GL-03-AC5, ✗ 409 POLICY_CHANGED | ✓ (nút "Đang đặt…") | → D1 ✓ |
| Bản đồ | ~ Skeleton + Spinner | — | ✓ C5 | — | — | — | ✓ C1c |
| Thanh toán | ✗ | — | ✗ (gọi `checkout/` lỗi, chỉ `[copy]`) | ✗ 429 | ✓ D2, D4, D5 | ~ (nút loading) | → SePay |
| Trang đơn / tra cứu | ✗ (`OrderSkeleton` chỉ có tên) | — | ✗ | ✗ 429 | ✓ F2, E2, E4 · ✗ D3 quá lâu · ✗ huỷ một phần | ✓ D3 | ✓ E1, E3 |
| Chính sách | ✗ | ✗ slug không có | ✗ | — | — | — | ✓ (nội dung chờ legal) |
| Góc bếp | ✗ | ✗ chuyên mục rỗng | ✗ | — | ✗ bài đã gỡ (code có câu "Bài này không còn trên web") | — | ✓ |
| Liên hệ | ~ ẩn dòng thiếu | — | — | — | — | — | ✓ |
| 404 | — | ✗ | — | — | — | — | — |

**Đề xuất gọn (để không phải vẽ thêm nhiều):** ghi một bảng "trạng thái dùng chung" vào UI-RULES §7:
- *Tải*: mọi trang có dữ liệu dùng Skeleton đúng hình (trang chủ: hàng chip + 2 hàng thẻ; chi tiết: ảnh + 3 vạch + thanh mua xương; trang đơn: `OrderSkeleton`).
- *Lỗi tải*: ErrorState (A6) giữ header/footer; trang chủ lỗi thì **chỉ khối sản phẩm** thành ErrorState, banner/lưới nhóm/Góc bếp vẫn hiện.
- *Không tồn tại*: EmptyState `page` có nút về danh mục (chi tiết món, chính sách, bài viết).
- *429*: Banner `crit` cạnh nút vừa bấm, không popup.
- *5xx*: như lỗi mạng nhưng câu khác.

---

## 4. Pháp lý và dữ liệu cá nhân

### 4.1 Footer (đối chiếu `go-live-phap-ly.md` mục 1, 2, 3, 9)

| Yêu cầu | Thiết kế | Đánh giá | Mức |
|---|---|---|---|
| Tên, địa chỉ, MST/GCN ĐKDN, SĐT, email chủ website (mục 2) | F1 cả hai khổ: tên DN, MST, địa chỉ, GCN ĐKKD, email, hotline, Zalo | ✓ | |
| Chính sách bảo mật, quyền và nghĩa vụ, **cơ chế khiếu nại** (mục 2) và kênh tiếp nhận khiếu nại công khai (mục 9) | 5 link: đổi trả, giao hàng, thanh toán, quyền riêng tư, điều khoản (có mục "Giải quyết tranh chấp") | **Thiếu link/trang "Giải quyết khiếu nại"** | Nên có (go-live) |
| Chính sách giá, thanh toán, giao hàng, **đổi trả và hoàn tiền** (mục 3) | Khung "Chính sách đổi trả" không có mục hoàn tiền; UI-RULES §2.6 cấm chữ "hoàn tiền" trên **toàn Shop** | **Mâu thuẫn luật nội bộ với luật nhà nước.** Thu hẹp §2.6: chỉ áp cho trang đơn/thanh toán; trang chính sách phải nêu cách xử lý tiền khi huỷ | **Chặn lô 5 / go-live** |
| Thông báo website (mục 1): **UBND tỉnh (Sở Công Thương) xác nhận**, không còn Bộ Công Thương; cổng nộp ⚠ | Ô "Logo Đã thông báo Bộ Công Thương" + link `online.gov.vn` | Nhãn và link có thể đã cũ theo NĐ 248. `legal-vn` xác nhận nhãn/logo. Prop `bctVerifyUrl` nên đổi thành tên chung (`ecommerceNoticeUrl`) | Nên có (không chặn lô 1 vì ô chỉ hiện khi có link) |
| Footer ở bước đặt hàng (F2) | Máy tính có; điện thoại chưa vẽ | xem §2 | Nên có |
| F2 chỉ 3 link (đổi trả, quyền riêng tư, thanh toán) | Thiếu "Chính sách giao hàng" ngay ở bước khách cần biết phí giao | Nên có |

### 4.2 Chỗ đồng ý chính sách

- ✓ C1/DesktopCheckout có ô "Tôi đồng ý để Cá Về dùng họ tên, số điện thoại và địa chỉ này để giao đơn hàng, theo chính sách quyền riêng tư", có link.
- Lệch nhỏ: prototype `Checkout.dc.html` khởi tạo `consent: true` (tick sẵn), COMPONENTS cấm tick sẵn. Dev theo COMPONENTS. Để sau.
- Câu đồng ý không nhắc việc gửi địa chỉ cho Google khi dùng bản đồ. Chốt 7 yêu cầu chính sách quyền riêng tư nêu việc này. Đề xuất thêm **một dòng tại chỗ** trong MapPicker: "Bản đồ do Google cung cấp; địa chỉ bạn tìm sẽ được gửi tới Google." `[copy]` + `legal-vn`. Nên có (lô 3).
- Q-UX-4 (nút "Đặt hàng" luôn bấm được) vẫn mở.

### 4.3 Cookie / consent

- Shop không có analytics, pixel, chat (UI-RULES §3.4). Lưu trên trình duyệt: giỏ (mã + số lượng), "tìm gần đây", token tra đơn (sessionStorage), cờ đóng banner. Không lưu dữ liệu cá nhân.
- Google Maps chỉ nạp khi khách bấm "Bản đồ" (đúng). Luật BVDLCN 2025 không có điều khoản riêng kiểu "cookie banner" như ePrivacy, nhưng chính sách phải nêu.
- **Đề xuất:** V1 **không cần banner cookie**. Bù lại: (1) chính sách quyền riêng tư có mục "Lưu trên trình duyệt" và "Bên thứ ba (Google Maps, SePay)"; (2) dòng thông báo tại chỗ khi mở bản đồ. Nhờ `legal-vn` xác nhận. Nên có.

### 4.4 Khung trang chính sách quyền riêng tư

`DesktopPolicy` dựng 4 mục: Dữ liệu thu thập · Mục đích · Thời gian lưu · Quyền của bạn. **Thiếu mục**: Bên thứ ba nhận dữ liệu (Google Maps, SePay, ngân hàng); **Lưu trữ ở nước ngoài** (Cloud Run/Supabase ở Singapore, checklist 6b); Lưu trên trình duyệt; Cách yêu cầu xem/sửa/xoá (kênh liên hệ, thời hạn trả lời). Nội dung do `legal-vn`, nhưng khung mục nên có sẵn. Nên có (lô 5).

### 4.5 Dữ liệu cá nhân trên màn

| Kiểm | Kết quả |
|---|---|
| Khối "Giao tới [tên · SĐT · địa chỉ]" (L-01 cũ) | ✓ Đã bỏ khỏi E1, E3, E4, DesktopSuccess, DesktopOrderStates. Chỉ còn nhãn ghim "Giao tới đây" trên bản đồ (không phải dữ liệu khách) |
| F2 không chỉ ô sai | ✓ "Không tìm thấy đơn khớp mã và số điện thoại." |
| Dữ liệu mẫu | ✓ Toàn bộ là `[…]`, "Nguyễn Văn A", "09xx xxx xxx" |
| SĐT trên URL | Form "Tra đơn khác" ở E1/DesktopSuccess là `<form>` không `method` (mặc định GET). Code **phải** gửi bằng JS/POST, không submit GET. Thêm ca test QA | Nên có (ca test) |
| Tên field | `DesktopSuccess.dc.html:190` dùng `name="sdt"` (tiếng Việt, trái luật đặt tên). Code dùng `phone` | Để sau |
| `noindex` trang đơn | Chưa đặc tả. `/shop/orders/` hiện món + số tiền của đơn theo mã: nên `noindex` (xem §7) | Nên có |

---

## 5. Component

COMPONENTS.md phủ 47 component, có bảng "Ánh xạ màn → component". Phần tử **xuất hiện trên màn nhưng chưa có đặc tả riêng**:

| Phần tử | Màn | Đề xuất | Mức / lô |
|---|---|---|---|
| Banner quảng bá trang chủ (hero: chữ, CTA `on-brand`, nền `brand-deep`) | A1, DesktopHome | Tách khỏi Banner/Alert (Banner/Alert là thông báo trạng thái). Thêm `HeroBanner` | **Chặn lô 1** (nhỏ: thêm mục) |
| Khối cam kết 3 ý (icon + tiêu đề + 1 câu) | DesktopHome, Landing | `ValueProps` | Nên có (lô 1) |
| Đầu mục có "Xem tất cả" | A1, DesktopHome, G1 | `SectionHeader` | Nên có (lô 1) |
| Bảng thông tin sản phẩm (Danh mục, Quy cách, Bảo quản, Nguồn hàng, Đơn vị bán, Mô tả, Đổi trả, Giao hàng) | A3, A7, DesktopProduct | `ProductInfo` (`<dl>`), ẩn dòng khi field trống | **Chặn lô 2** (đi cùng BE-2) |
| Bảng thành phần combo | A10, DesktopComboDetail | `ComboComponents` | **Chặn lô 2** |
| Thẻ bài viết, nội dung bài CMS (prose: h2, list, ảnh, ghi chú) | G1, G2, Desktop×2, A1 | `ArticleCard`, `Prose` | Nên có (lô 5) |
| Bảng đối chiếu tiền (cần / đã nhận / còn thiếu) | D5, DesktopUnderpaid | `PaymentReconciliation` | Nên có (lô 4, nếu giữ D5) |
| Danh sách bước "Cách mua" | P3, DesktopPolicy, Landing | `StepList` | Nên có (lô 5) |
| FAQ thu gọn | P3 | `Disclosure` (`<details>` gốc) | Nên có (lô 5) |
| Danh sách liên hệ (gọi, Zalo, email, địa chỉ, giờ) | P2, DesktopContact | `ContactList` | Nên có (lô 5) |
| Link "Bỏ qua tới nội dung chính" | mọi trang | `SkipLink` (đã nhắc ở ShopHeader, chưa có mục) | Nên có (lô 1) |
| Khối "Tra đơn khác" | E1, DesktopSuccess | ghép TextField + Button, ghi rõ submit không GET | Nên có (lô 4) |
| Các khối Landing (hero lớn 60px, ảnh, quy trình 3 bước, bảng giá mẫu) | Landing | đặc tả section Landing | Chặn lô 1 nếu dựng landing mới |
| Trang lỗi chung / error boundary | (chưa có màn) | `ErrorState` thêm biến thể `server`, `rate-limit`, `crash` | Nên có (lô 1) |
| Banner "đơn đang chờ thanh toán" ở giỏ | (chưa có màn) | nếu Duy chọn N-03 | Nên có (lô 3–4) |

**Bảng hình CMP lệch COMPONENTS.md** (dev hoặc QA so ảnh có thể chép nhầm):
- `CMP-7-Overlay-Feedback.dc.html:451` toast **"Tôm sú chỉ còn 2 kg, đã đặt tối đa"** và `:558` **"Chỉ còn 2 kg trong lô này"**: trái chốt 3 (không hiện số kg), lộ khái niệm "lô". COMPONENTS ghi "+ không có trần".
- `CMP-4-Product.dc.html:491` "thẻ → thùng rác, **bấm bỏ ngay (có toast Hoàn tác)**"; `CMP-5-Cart-Order.dc.html:151` "toast 'Đã bỏ … · Hoàn tác'": trái UI-RULES §1.2 và COMPONENTS (luôn qua Dialog B2).
- `CMP-4-Product.dc.html:530` "Lạc quan · **gọi API sau**": giỏ ở client, không có API thêm giỏ.
- `CMP-5-Cart-Order.dc.html:149` "Nút đặt hàng bị chặn tới khi bỏ món" ↔ B3 "Tiếp tục với 2 món còn hàng".
- `CMP-5-Cart-Order.dc.html:626` tổng 17/20 ↔ COMPONENTS 24/600.

→ Sửa 3 bảng CMP, hoặc đóng dấu đầu mỗi bảng: "Khi khác COMPONENTS.md, theo COMPONENTS.md". **Chặn lô 1** với CMP-7 (lô 1 dựng Toast/Banner).

**Tệp viện dẫn bị thiếu:** COMPONENTS.md lấy số từ `SO-CHUAN.md`, nhưng file này chỉ nằm ở `scratchpad/shop-handoff/`, **không có trong `doc/design/shop/`**. Chép vào trước khi giao. **Chặn lô 1** (nhỏ).

---

## 6. Câu chữ

| Chốt / luật | Chỗ trái hoặc lệch | Sửa | Mức |
|---|---|---|---|
| Không hiện số kg tồn | CMP-7 :451, :558 (xem §5). File cũ `Card-states.dc.html:71` "Chỉ còn 2 kg" | Sửa CMP-7; xoá file cũ khỏi thư mục canvas | Chặn lô 1 (CMP-7) |
| Tối thiểu 1 kg | `Landing.dc.html:133` "Bạn chọn **0,5 kg** hay 2 kg" | "Bạn chọn 1 kg hay 2 kg" | **Chặn lô 1** nếu dựng landing mới |
| Không ngày nhập lô / không "lô mới về" (Q8) | `Home.dc.html:68`, `DesktopHome.dc.html:110` "Lô mới vừa nhập kho"; `DesktopHome :308` ô "Lô mới về (4)"; `Landing :186` "Bảng hàng cập nhật mỗi khi có lô mới về" | Mặc định theo L-24: bỏ ô, banner chữ tĩnh | Chặn lô 1 (chờ Q8, có mặc định) |
| Không hứa "về cảng mỗi ngày" | `Landing :185` "**Hôm nay** cảng có gì?" (gợi ý hàng về mỗi ngày); file cũ `Desktop.dc.html:26` "Hải sản về cảng mỗi ngày" | Đổi tiêu đề `[copy]` | Nên có |
| Không hứa điều hệ thống chưa làm | `Landing :174` nút **"Kiểm tra khu vực giao"**: không có chức năng | Bỏ nút hoặc thành link trang Chính sách giao hàng | Nên có |
| Đổi trả chờ pháp lý | `Landing :177` **"Không ưng thì đổi"** (rộng hơn câu dưới "hàng có vấn đề"; dễ bị coi là hứa) | `[copy]` + `legal-vn` | Nên có |
| Miễn phí giao | Chỉ còn ở file cũ `Desktop.dc.html:204` | Xoá file cũ | Để sau |
| Hoàn tiền | Màn đơn sạch. Xem §4.1 về trang chính sách | — | — |
| Hoá đơn điện tử | Không còn trên màn | ✓ | — |
| Hứa báo khi có hàng | A7 dùng câu đã chốt Q-UX-7 | ✓ | — |
| Mã đơn `SO…` | ✓ mọi màn đơn. Nhưng **mã hàng** mẫu `CV-MUC-01`, `CV-CA-06` (`Product :49`, `DesktopProduct :134`, `A7 :43`, `DesktopOutOfStock :132`) dễ bị hiểu là tiền tố "CV-" đã bỏ | Đổi mẫu thành `[mã hàng]`; code hiện `item_code` thật | Để sau |
| Phí giao: một cách viết | 4 biến thể: "Báo khi xác nhận đơn" · "Cá Về báo khi gọi xác nhận" · "phí giao Cá Về báo khi xác nhận đơn" · "báo phí giao trước khi giao" | Chốt một câu sau Q6 + `legal-vn` | Chặn lô 3 (gắn Q6) |
| SuccessBanner hai khổ cùng một câu | Điện thoại "Cá Về sẽ gọi xác nhận trước khi giao." · máy tính "…và báo phí giao trước khi giao" | COMPONENTS đã ghi `[copy]` | Chặn lô 4 (gắn Q6) |
| Không hard-code 30 phút | `D4 :69` "đã tự huỷ sau **30 phút**"; `P3 :62, :85` | Lấy từ field BE (`hold_minutes`) | Nên có |
| Nhãn trạng thái | E2 "Đơn đã huỷ" ↔ chuẩn "Đã huỷ"; D5 màu hổ phách ↔ chuẩn `neutral` (đã ghi COMPONENTS) | theo COMPONENTS | — |
| Nhất quán | C3 "sẽ bỏ khỏi **đơn**" ↔ máy tính "khỏi **giỏ**"; footer điện thoại "Về Cá Về" ↔ máy tính "Về chúng tôi" | thống nhất "khỏi giỏ", "Về Cá Về" | Để sau |
| Dư chú thích | `Landing :179` "Câu chữ chính sách chờ duyệt pháp lý."; `Product :98` "[chính sách đổi trả, chờ duyệt pháp lý]"; `DesktopPolicy :131` "[Nội dung chờ legal-vn duyệt]" | Ghi chú thiết kế, không lên production (COMPONENTS đã cấm cho PolicyNav; nhắc cho Landing và Product) | Nên có |
| Claim cần Lộc xác nhận | "Mua theo lô, biết rõ nguồn", "cấp đông **ngay tại cảng**", "Xem tận mắt từng mẻ khi tàu cập bến, chỉ lấy lô đạt", "rõ nguồn từng lô" (phụ thuộc field `origin` BE-2 có được nhập) | `mkt-brand` + Lộc xác nhận đúng sự thật (Luật BVQLNTD về thông tin sai lệch) | Nên có |
| "Lô gần hạn được xuất trước" (Landing :133) | Nói về FEFO, đúng nghiệp vụ nhưng chữ "gần hạn" dễ gây lo | `[copy]` | Để sau |
| Thanh toán trên chính điện thoại | D1 "**Quét mã** bằng app ngân hàng bất kỳ": khách xem QR trên chính điện thoại thì không quét được | Kiểm SePay có nút mở app ngân hàng/lưu ảnh QR; câu cho điện thoại `[copy]` | Nên có |

---

## 7. SEO và chia sẻ

**Không có đặc tả nào** trong 6 tài liệu thiết kế (grep `SEO|favicon|og:|manifest|robots|sitemap` = 0). Hiện trạng code: `app/layout.tsx` có title mẫu `%s | Cá Về` + description; `app/page.tsx` (landing) có `openGraph`; `bai-viet`, `trang` đặt `document.title` phía client; `frontend/public/` trống (không favicon).

Lưu ý quyết định: `decisions.md:150` "**Landing (SEO) và Shop tách nhau**". Thiết kế đưa Shop lên `/` và landing sang `/gioi-thieu/`, tức đổi trang SEO chính. Chốt này **chưa có trong 9 chốt của README** → cần ghi decisions ở lô 0.

| Hạng mục | Đề xuất | Mức |
|---|---|---|
| Title + description từng route | `/` "Cá Về — Hải sản cấp đông theo lô, giao tận nhà" (chuyển metadata landing cũ về đây) · `/gioi-thieu/` "Về Cá Về" · `/shop/` "Hàng đang có" (+ tên nhóm khi lọc) · chi tiết: tên món (client) · giỏ/đặt/thanh toán/đơn: tiêu đề bước · chính sách, bài: `seo_title` CMS. Mẫu `%s · Cá Về` | **Chặn lô 1** (cho `/` và `/gioi-thieu/`) |
| Ảnh OG 1200×630 + `og:locale vi_VN` | Một ảnh chung từ logo/ảnh hàng; bài viết dùng ảnh bìa CMS | Nên có (chờ logo) |
| Favicon, `apple-touch-icon` 180, `manifest` (name "Cá Về", `theme_color` = `accent`) | Từ file logo Duy upload; tạm thời favicon chữ "CV" trên nền `accent` | Nên có (chờ logo) |
| `noindex` | `/shop/cart/`, `/shop/checkout/`, `/shop/orders/` (trang đơn có món + số tiền theo mã) | Nên có (lô 2–4) |
| `robots.txt`, `sitemap.xml` tĩnh | Liệt kê `/`, `/shop/`, `/gioi-thieu/`, trang chính sách, bài viết (sinh lúc build hoặc tay) | Để sau (lô 7) |
| Trang sản phẩm qua `?code=` | Static export + query string: máy tìm kiếm chỉ thấy một URL `/shop/item/`, title đặt phía client. SEO từng món yếu. Chấp nhận ở V1 hay cần trang tĩnh sinh lúc build | Hỏi Duy (Để sau) |
| Structured data `Product`, `Organization` | — | Để sau |

---

## 8. Câu hỏi mở (một danh sách, đã bỏ trùng)

Đã chốt, **không hỏi lại**: Q1 (bỏ khối "Giao tới"), Q3 (popup không nêu số kg), Q5 (giữ mã `SO…`), Q-UX-7 (câu A7).

| # | Câu hỏi | Nguồn | Người trả lời | Chặn |
|---|---|---|---|---|
| 1 | Ghi thêm chốt: `/` thành trang chủ Shop, Landing sang `/gioi-thieu/` (đổi "Landing (SEO) tách Shop", decisions:150)? | mới | Duy | **lô 0 → 1** |
| 2 | Lô 1 dựng Landing theo thiết kế mới (cần vẽ bản điện thoại, sửa copy) hay chỉ chuyển landing cũ sang `/gioi-thieu/`? | mới | Duy | **lô 1** |
| 3 | "Lô mới về" / "Lô mới vừa nhập kho": bỏ hay định nghĩa N ngày? (mặc định: bỏ ô, chữ tĩnh) | Q8, L-24 | Duy | lô 1 |
| 4 | Nguồn chip "Tìm nhiều": model ERP, biến cấu hình, hay 4 nhóm đầu? (mặc định 4 nhóm đầu) | L-25, BE-7 | Duy + techlead | lô 1 |
| 5 | Dark mode V1? (mặc định chỉ light) | Q-UX-1 | Duy | lô 1 |
| 6 | Icon SVG nét hay Material Symbols? (mặc định SVG) | Q-UX-2 | Duy | lô 1 |
| 7 | BottomNav có hiện ở trang tra cứu đơn? (mặc định có) | Q-UX-5 | Duy | lô 1, 4 |
| 8 | Menu nhóm hai cấp trên máy tính (cần `parent_slug`)? (mặc định không mũi tên) | L-20 | Duy + techlead | lô 1 |
| 9 | Liên hệ / Cách mua: trang tĩnh hay CMS; giữ `/trang/?slug=`; "Cách mua" là trang riêng (như điện thoại) hay khối trong trang chính sách (như máy tính)? | Q7, L-13, mới | Duy | lô 1 (href footer), **lô 5** |
| 10 | Copy trang 404 | mới | `mkt-brand` | **lô 1** |
| 11 | Bước tăng sau 1 kg đúng là 0,5 kg? | PLAN | Duy | **lô 2** |
| 12 | Đuôi lô dưới 1 kg / số lẻ: cho mua "phần còn lại", bán ngoài, hay chấp nhận tồn chết? | Q4, L-05 | Duy | **lô 2** |
| 13 | Field thông tin sản phẩm (BE-2: quy cách, bảo quản, nguồn hàng, mô tả, ghi chú ngắn) làm ở lô nào? PLAN chưa xếp BE-2 vào lô nào, trong khi A3 hiện các field này | L-23, mới | Duy + điều phối | **lô 2** |
| 14 | Nhiều ảnh mỗi món? (mặc định 1 ảnh, ẩn thumb) | L-22 | Duy | lô 2 |
| 15 | Có hiện ưu đãi PricingRule ở giỏ/đặt hàng (cần BE-9)? | L-26 | Duy | lô 2–3 |
| 16 | CartBar nằm trên BottomNav khi có món? (mặc định có) | Q-UX-6 | Duy | lô 2 |
| 17 | Giỏ đang tải lỗi (không so được giá): cho đi tiếp hay chặn? Món hết trong giỏ: tự loại (B3) hay chặn tới khi bỏ (CMP-5)? | mới | ux + Duy | **lô 2** |
| 18 | `lines[].stock_level: 'out' \| 'short'` trong lỗi hết hàng (BE-3) | COMPONENTS, L-03 | techlead | lô 2–3 |
| 19 | Khách trả phí giao bằng cách nào; câu công bố trước khi đặt (dòng "Phí giao" ở C1, D1 điện thoại) | Q6, L-09 | Duy + `legal-vn` | **lô 3** |
| 20 | Tra đơn bằng SĐT đầy đủ + `lookup_token` thay 4 số cuối? | Q2, L-02 | Duy | **lô 3** (BE-4/5), lô 4 |
| 21 | Giữ nút "Huỷ đơn" ở D2 (cần BE-6 + BR-BH-19) hay bỏ? | Q9, L-07 | Duy | **lô 3**, 4 |
| 22 | Nút "Đặt hàng" luôn bấm được, báo lỗi ở ô đồng ý? | Q-UX-4 | Duy | lô 3 |
| 23 | Một luật SĐT chung FE = BE (10 số bắt đầu 0? nhận `+84`?) | L-19 | Duy + techlead | lô 3 |
| 24 | API key Google Maps: ai tạo, bật billing, giới hạn referrer; tên biến (COMPONENTS ghi "hai tên" nhưng thực ra trùng `NEXT_PUBLIC_GOOGLE_MAPS_KEY`) | L-10, PLAN điểm dừng | Duy + techlead | **lô 3** |
| 25 | "Shop tạm ngưng nhận đơn": chỉ khi chưa có chính sách (GL-03-AC5) hay Lộc bật tay được; hiện ở giỏ, đặt hàng hay toàn trang? | L-17, mới | Duy | **lô 3** |
| 26 | Giỏ được xoá lúc nào: khi tạo đơn hay khi trả tiền xong? "Đặt lại / Mua lại" khi giỏ đang có món: gộp hay thay? | mới | Duy + techlead | **lô 3–4** |
| 27 | Cho lưu "đơn gần đây" (chỉ mã đơn + token, không dữ liệu cá nhân) ở localStorage để khách đóng trình duyệt quay lại được, tránh giữ chỗ gấp đôi? | mới | Duy + techlead | lô 3–4 |
| 28 | Cần banner cookie không? Thêm dòng thông báo Google khi mở bản đồ? | mới, chốt 7 | `legal-vn` | lô 3 |
| 29 | `hold_minutes` (hoặc `booked_at`) + `server_now` cho đồng hồ | COMPONENTS | techlead | lô 3–4 |
| 30 | Bảng enum BE → nhãn hiển thị, gồm trạng thái **"đã trả tiền, chờ gọi xác nhận"** (E1 vẽ "Đang chuẩn bị", CMP-5 ghi "Chờ cửa hàng xác nhận") | COMPONENTS, mới | techlead + Duy | **lô 4** |
| 31 | Bảng ưu tiên: (trạng thái đơn × tiền × giao × `result`) → màn nào (D2/D3/D4/E1/E2…) | mới | techlead + ux | **lô 4** |
| 32 | D3 chờ ngân hàng bao lâu thì chuyển sang "Cá Về sẽ kiểm tra và gọi lại" (E-05)? | mới | Duy | **lô 4** |
| 33 | Câu báo đơn huỷ sau khi đã trả tiền ("Cá Về sẽ gọi để xử lý số tiền…") thay chi tiết hoàn tiền (lật nội dung CS-10) | L-08 | Duy + `legal-vn` | lô 4 |
| 34 | Bảng nhãn lý do huỷ công khai cố định (gồm "hết giờ giữ hàng, tiền về sau") | L-14 | techlead + Duy | lô 4 |
| 35 | Huỷ một phần (E-07, BR-HT-02): trang đơn hiện thế nào; lookup có trả dòng bị huỷ? | mới | techlead + Duy | lô 4 |
| 36 | Giữ màn D5 thiếu tiền ở V1 (gần như không xảy ra)? | L-15 | Duy | lô 4 |
| 37 | Cỡ số đồng hồ 40/600 vào số chuẩn? (mặc định 40) | Q-UX-3 | Duy | lô 4 |
| 38 | Luật "không hiện chữ hoàn tiền" chỉ áp cho trang đơn/thanh toán, trang chính sách được nêu cách xử lý tiền? | mới, go-live mục 3 | Duy + `legal-vn` | **lô 5**, go-live |
| 39 | Thêm trang/link "Giải quyết khiếu nại"; nhãn + link thông báo website theo NĐ 248 (Sở Công Thương, cổng mới) | mới, go-live mục 1, 2, 9 | `legal-vn` | lô 5, go-live |
| 40 | `site-info`: `seller.zalo`, `search_chips`, `policies.return_report_hours` | BE-7 | techlead | lô 1 (ẩn Zalo nếu thiếu), lô 5 |
| 41 | Ghi quyết định bỏ hoá đơn điện tử là "Shop không hiển thị/không xuất", `legal-vn` xác nhận nghĩa vụ HĐĐT | L-29 | Duy + `legal-vn` | lô 0 |
| 42 | SEO trang sản phẩm qua `?code=` (title phía client): chấp nhận yếu ở V1? | mới | Duy | lô 2 / 7 |

---

## Kết luận

### Bảng "Còn thiếu" xếp theo mức độ

| # | Việc | Mức | Lô | Ai làm |
|---|---|---|---|---|
| 1 | Lô 0 chưa chạy: chưa có `doc/features/2026-10-06-shop-giao-dien-moi/` (01, 02-stories, 02b), 9 chốt + chốt "/ thay landing" chưa vào `decisions.md` | Chặn code | 1 trở đi | điều phối, BA, PO, techlead |
| 2 | SEO/metadata `/` và `/gioi-thieu/` (title, description, OG) | Chặn code | 1 | ux (đề xuất ở §7) + Duy |
| 3 | Trạng thái trang chủ (tải, lỗi, rỗng) + copy trang 404 | Chặn code | 1 | ux (bảng §3) + `mkt-brand` |
| 4 | Landing: bản điện thoại hoặc chốt "chỉ chuyển landing cũ"; sửa "0,5 kg" | Chặn code | 1 | Duy chọn; ux vẽ nếu dựng mới |
| 5 | Sửa CMP-7 (toast "chỉ còn 2 kg"), CMP-4, CMP-5 lệch COMPONENTS; chép `SO-CHUAN.md` vào `doc/design/shop/`; thêm mục `HeroBanner` | Chặn code | 1 | ux |
| 6 | BE-2 chưa xếp lô; `ProductInfo`, `ComboComponents` chưa đặc tả | Chặn code | 2 | điều phối + ux |
| 7 | Chi tiết sản phẩm: tải, không tồn tại/ngưng bán, lỗi mạng | Chặn code | 2 | ux |
| 8 | Giỏ: tải lại giá, lỗi tải; mâu thuẫn B3 ↔ CMP-5 về món hết | Chặn code | 2 | ux + Duy |
| 9 | Checkout: Shop tạm ngưng (GL-03-AC5), 409 POLICY_CHANGED, khối giờ gọi xác nhận, 429, giỏ rỗng | Chặn code | 3 | ux |
| 10 | Dòng "Phí giao" ở C1/D1 điện thoại + câu chốt (Q6, `legal-vn`) | Chặn code | 3 | Duy + `legal-vn` + ux |
| 11 | Thời điểm xoá giỏ; "Đặt lại" gộp hay thay | Chặn code | 3–4 | Duy + techlead |
| 12 | Bảng ưu tiên trạng thái trang đơn (link hết hạn, mở lại link đã trả, `result` sai, máy khác không token) | Chặn code | 4 | techlead + ux |
| 13 | D3 chờ quá lâu (E-05); nhãn "đã trả, chờ gọi xác nhận"; tải/lỗi/429 trang đơn | Chặn code | 4 | ux + techlead |
| 14 | Luật "không chữ hoàn tiền" ↔ nghĩa vụ công khai chính sách hoàn tiền | Chặn code | 5 / go-live | Duy + `legal-vn` |
| 15 | Trang/link "Giải quyết khiếu nại"; nhãn thông báo website theo NĐ 248; khung chính sách quyền riêng tư thêm mục bên thứ ba, nước ngoài, trình duyệt | Nên có | 5 / go-live | `legal-vn` + ux |
| 16 | Bảng lỗi chung (mất mạng / 5xx / 429 / crash) + `app/error.tsx` | Nên có | 1 | ux |
| 17 | Footer F2 bản điện thoại; F2 thêm link Chính sách giao hàng | Nên có | 1 | ux |
| 18 | `SkipLink`, `SectionHeader`, `ValueProps` | Nên có | 1 | ux |
| 19 | "Sao chép mã đơn" ở D1/E1; "đơn gần đây" (Q27) | Nên có | 3–4 | ux + Duy |
| 20 | Huỷ một phần trên trang đơn | Nên có | 4 | techlead + ux |
| 21 | F1 điền sẵn mã khi mở `?code=` không token | Nên có | 4 | ux |
| 22 | Thông báo Google tại MapPicker; quyết định banner cookie | Nên có | 3 | `legal-vn` + `mkt-brand` |
| 23 | Chính sách, Góc bếp: tải, không tồn tại, bài đã gỡ, lỗi | Nên có | 5 | ux |
| 24 | `ArticleCard`, `Prose`, `StepList`, `Disclosure`, `ContactList`, `PaymentReconciliation` | Nên có | 4–5 | ux |
| 25 | Copy: phí giao một câu, claim nguồn hàng, "Hôm nay cảng có gì", "Không ưng thì đổi", nút "Kiểm tra khu vực giao", "Quét mã" trên điện thoại, hard-code 30 phút, ghi chú "chờ pháp lý" | Nên có | 1–5 | `mkt-brand` + Lộc |
| 26 | `noindex` giỏ/đặt/đơn; OG ảnh; favicon/manifest (chờ logo) | Nên có | 1–4 | ux + Duy (logo) |
| 27 | Cách mua: trang riêng (điện thoại) ↔ khối trong Chính sách (máy tính) | Nên có | 5 | Duy (câu 9) |
| 28 | Xoá `Desktop.dc.html`, `Card-states.dc.html` khỏi thư mục canvas (có "miễn phí giao", "chỉ còn 2 kg", "về cảng mỗi ngày") | Để sau | — | ux |
| 29 | Mã canvas lệch tên file (A0="A8", A8="A9", A9="A10", P1–P3="F3–F5", G1–G2="F6–F7") | Để sau | — | ux |
| 30 | Desktop C1c, C5 | Để sau | 3 | — |
| 31 | Mã hàng mẫu `CV-…`; `name="sdt"`; C3/C4 nền còn form nhiều ô địa chỉ; "khỏi đơn"/"khỏi giỏ"; "Về chúng tôi" | Để sau | — | ux |
| 32 | robots.txt, sitemap, structured data; SEO trang sản phẩm | Để sau | 7 | techlead |

### Đủ để bắt đầu lô 1 chưa?

**Chưa, nhưng chỉ còn giấy tờ, không cần vẽ lại màn lớn.** Phần lô 1 cần (token, header H1–H4, footer F1/F2, BottomNav,
Dialog/Sheet/Toast/EmptyState/ErrorState/Skeleton) đã được đặc tả kỹ trong COMPONENTS.md và HeaderFooter-*. Trước khi giao `fe-dev`
cần xong 5 việc:

1. **Lô 0:** ghi 9 chốt và chốt thứ 10 ("/" thành trang chủ Shop, landing sang `/gioi-thieu/`) vào `decisions.md`, tạo hồ sơ tính năng
   có `02-stories.md` đã duyệt. CLAUDE.md và PLAN đều đặt lô 0 trước lô 1.
2. **Duy gật các mặc định** của câu 3, 4, 5, 6, 7, 8, 9 (href footer), và chọn phương án Landing (câu 2).
3. **Bổ sung đặc tả nhỏ:** metadata `/` và `/gioi-thieu/`, trạng thái tải/lỗi/rỗng của trang chủ, copy trang 404 (`mkt-brand`), mục `HeroBanner`.
4. **Dọn nguồn:** sửa CMP-7/CMP-4/CMP-5 cho khớp COMPONENTS.md (nhất là toast "chỉ còn 2 kg"), chép `SO-CHUAN.md` vào `doc/design/shop/`.
5. Nếu dựng Landing mới: vẽ bản điện thoại và sửa câu "0,5 kg".

Lô 2 trở đi còn cần trả lời các câu chặn 11–13, 17 (lô 2), 19–26 (lô 3), 30–32 (lô 4), 38 (lô 5).
