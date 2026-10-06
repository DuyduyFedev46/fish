# Việc cần Duy quyết — gom từ đêm 02/10/2026
> Duy dặn 02/10 00:40: "cho auto chạy qua đêm, cái gì cần anh quyết gom lại trưa mai tính sau".
> Điều phối viên không đứng chờ: lô nào gặp điểm dừng thì ghi vào đây, bỏ qua, làm lô khác.

| # | Lô | Việc cần quyết | Em đề xuất | Đang làm tạm thế nào |
|---|---|---|---|---|
| 1 | ngoài lô | ⚠️ (QA Lô 3 xác nhận lại trên BE thật: khối AI không bao giờ hiện dù bật AI, mỗi trang chi tiết có 1 lỗi 404 trong console.) **ERP gọi `GET /api/ai/status/` nhưng backend không có route** (em đã grep `config/api_urls.py`: không có; chỉ mock có). Trên backend thật request trả 404 → cổng AI coi như tắt → Trợ lý AI không bao giờ hiện trên staging/production. | Làm lô NHANH: thêm route `ai/status/` ở backend theo contract S05 (luôn 200, `ai_enabled`…), có test. | Chưa sửa (ngoài phạm vi ERP theo design). Không chặn các lô. |
| 2 | Lô 3 | Dòng thời gian đơn có sẵn (`apps/sales/orders/timeline.py`) ghép `Refund.reason` (chữ tự do) vào nhãn "Tạo phiếu hoàn … — <lý do>" → có thể lộ dữ liệu cá nhân nếu nhân viên gõ vào lý do. | Bỏ phần lý do khỏi nhãn timeline (lý do vẫn xem ở trang phiếu hoàn). | Em giao Lô 3 sửa luôn vì cùng thư mục `sales/orders` và là bất biến 9 (Critical) — anh lật được. |
| 3 | Lô 3 | Còn 4 chỗ dòng thời gian ghép **chữ tự do** do nhân viên gõ: `orders/timeline.py` (huỷ đơn đã trả tiền: "<nhãn> — <ghi chú>"; báo chuyển hoàn thất bại: ghi chú), `refunds/timeline.py:32` (lý do hoàn), `:64` (lý do thất bại). Timeline đơn xem được bởi cả NV kho. Sửa = đổi hành vi đã nghiệm thu S14/S16 (2 test cũ). | Nhãn theo mã lý do (`reason_code`) thay chữ tự do; chữ tự do chỉ xem ở trang phiếu hoàn/đơn cho Chủ/Quản lý. | Giữ nguyên chờ anh quyết. Riêng lý do phiếu hoàn trong timeline **đơn** đã bỏ (mục 2). |
| 4 | Lô 4 | Bộ chặn dữ liệu cá nhân trong ghi chú giao thất bại dùng luật "từ 9 chữ số liền": **chặn nhầm** "Khách hẹn lại 10/10/2026 9h", "Thu 1.250.000.000 đ"; **bỏ sót** "Gọi 0912,345,678". Ghi chú không đi vào nhật ký/AI/log nên bỏ sót không rò ra ngoài. | Giữ luật hiện tại đợt này; làm lô riêng nhận diện SĐT VN chuẩn hơn nếu anh muốn. | Giữ nguyên. |
| 5 | Lô 6 | Sửa **SĐT khách** trên trang Khách hàng: 02b (Tech Lead) khoá SĐT; story ED-13 AC5/AC6 cho đổi SĐT + báo trùng. | Giữ khoá đợt này (SĐT là khoá nhận diện khách khi đặt đơn guest; đổi dễ gộp/nhầm khách). Muốn đổi thì làm lô riêng. | Code theo 02b: PATCH chỉ `name`, `default_address`, `note`; FE không có ô sửa SĐT. |
| 6 | Lô 8 | Luật mới **BR-KK-08**: người đã nhập/sửa số đếm của phiếu kiểm kê **không được tự duyệt** phiếu đó (mở rộng BR-KK-02 "người tạo không tự duyệt"). Mặc định 🟡 T8 trong 02b. Hệ quả: vựa ít người thì cần người thứ hai duyệt. | Giữ (chống tự khai khống kho). Anh đồng ý thì PO ghi chính thức vào `business-process-spec.md`. | Đã code theo T8; phiếu bị chặn hiện lý do ngắn ở nút Duyệt. |
| 7 | Lô 8 | ⚠️ **Tồn kho — cần anh chốt trước khi commit Lô 8.** Duyệt phiếu kiểm kê đang **tính lại** chênh lệch = số đếm − tồn *lúc duyệt*. Nếu giữa lúc đếm và lúc duyệt có bán hàng thì sổ sai. Ví dụ: tồn 50, đếm 48 (hụt 2), bán 5, duyệt → tồn sổ thành 48 (thật còn 43), sổ ghi "thừa +3". Lỗi có sẵn nhưng trước giờ API chưa gửi được số đếm nên chưa ai gặp. | **Phương án B (em + Tech Lead đề xuất, mã BR-KK-09):** lúc duyệt áp đúng chênh lệch đã chụp lúc nhập số (hụt 2 → trừ 2 → còn 43). Phương án A: tồn đổi thì trả lỗi bắt nhập lại (an toàn hơn nhưng Shop bán liên tục thì khó duyệt). | Em cho dev **làm sẵn phương án B kèm test nhưng chưa commit** Lô 8; anh gật là commit ngay, chọn A thì em đổi. |
| 8 | Lô 9 | Phiếu **hàng hoàn** đang "Chờ duyệt" mà nhập sai số kg thì **không sửa, không huỷ được**, và số sai vẫn chiếm hạn mức "đã giao" → lối ra duy nhất là duyệt với số sai. | Thêm thao tác "Từ chối / huỷ phiếu hoàn" (Chủ/Quản lý, khi còn Chờ duyệt) — story mới, đề xuất BR-HV-05. | Chưa làm (ngoài phạm vi R9). |
| 9 | Lô 10 | Spec ghi **NV kho chỉ xem phiếu nhập "của mình, trong ngày"** (Tầng 3), nhưng code hiện cho ai có quyền xem phiếu nhập thấy **mọi** phiếu (lỗi có sẵn). Giá mua vẫn ẩn với NV kho nên không rò giá vốn. | Làm lô NHANH: thêm phạm vi dòng phiếu nhập cho NV kho đúng spec (kèm test) — hoặc anh bỏ dòng đó khỏi spec nếu muốn NV kho xem hết. | Giữ hành vi hiện tại. |
| 10 | Lô 13 | **Đặt giá lùi ngày**: hiện Chủ đặt được giá mới có "từ ngày" trong quá khứ → lịch sử giá trên ERP bị viết lại (đơn cũ không đổi tiền vì giá đã chốt vào đơn). | Chặn "từ ngày" trước hôm nay (giờ VN); muốn sửa giá quá khứ thì không cho. | Đang cho phép (giữ hành vi cũ). |
| 11 | Lô 6 | Tìm khách theo SĐT gửi số trong **URL** (`?q=0900…`) → số nằm trong log máy chủ/proxy (QA L6-N2). | Đổi tìm khách sang POST (như màn Gọi xác nhận đang làm) — đổi API, cần lô nhỏ. | Giữ GET như thiết kế. |
| 12 | Lô 12 | **NV kho có xem Hoá đơn bán không?** Story ED-33-AC4: NV kho thấy "Không có quyền". 02b + quyền hiện có: NV kho **xem được** danh sách (không có cột Giá vốn/Lãi gộp, tên khách theo phạm vi). | Theo 02b (NV kho xem, không giá vốn) — kho cần đối chiếu hàng đã xuất theo hoá đơn. Muốn khoá thì đổi quyền nhóm (migration nhỏ). | Code theo 02b: NV kho xem danh sách nhưng **tên khách để trống** (chỉ ai có quyền "Xem khách hàng" mới thấy tên) — chọn hướng an toàn dữ liệu cá nhân trong lúc chờ anh. |
| 13 | Lô 14 | Màn Phân quyền cho Chủ **bật "Xem khách hàng" cho bất kỳ nhóm nào**, kể cả NV giao/CSKH. Bật xong, nhóm đó xem được **toàn bộ** tên, SĐT, địa chỉ khách (danh bạ khách không giới hạn theo phiếu). | Chặn hẳn bật "Xem khách hàng" cho NV giao và CSKH (giống việc "Chỉ Chủ"), vì họ đã có phạm vi riêng theo phiếu/cuộc gọi. | Đang cho phép như 02b; màn hiện đúng "Tất cả khách" khi bật. |
| 14 | ngoài lô | (Lỗi có sẵn, QA tìm thấy) Chủ **sửa số tiền chi phí phụ** (`PATCH /api/purchasing/costs/{id}/`) thì hệ thống **không phân bổ lại** vào giá vốn lô và **không ghi nhật ký** → giá vốn lô lệch với chi phí thật. | Chặn sửa tiền chi phí phụ sau khi đã phân bổ (sai thì huỷ + nhập lại), hoặc làm lô sửa có phân bổ lại + nhật ký. Đụng giá vốn → cần anh chọn. | Giữ nguyên (ngoài phạm vi). |
| 15 | Lô 3 | Đơn **đã tự huỷ vì hết giờ giữ chỗ** vẫn có nút "Xác nhận đã nhận tiền" và BE vẫn nhận (trường hợp khách chuyển khoản trễ). Có phải chủ ý không? Nếu xác nhận thì hàng đã nhả về kho có được giữ lại cho đơn không? | Giữ được thì giữ (tiền đã vào), nhưng phải kiểm còn hàng; hết hàng thì chỉ cho Lập phiếu hoàn. Cần anh xác nhận nghiệp vụ. | FE hiện nút theo BE (`available_actions`). |
| 16 | Lô 3 | Sau "Xác nhận đã nhận tiền", đơn chuyển thẳng sang **Đang xử lý** (BE), trong khi story ED-10-AC1 viết "Đã thanh toán". | Giữ theo code (code thắng về trạng thái); sửa chữ AC. | Chip "Đang xử lý", toast "Đã nhận tiền". |
| 17 | Lô 4 | (Báo trước, dữ liệu cá nhân) **R4b**: danh sách "Việc giao của tôi" trả sẵn SĐT khách cho chính người giao (chỉ phiếu của họ, chỉ khi Đang giao/Giao thất bại, cùng cửa sổ thời gian như trang chi tiết). Hiện mỗi thẻ phải gọi API chi tiết riêng để lấy số cho nút Gọi khách. Không mở rộng ai được xem gì. | Làm (Tech Lead đã duyệt contract). | Chưa làm — chờ anh gật vì đụng dữ liệu khách. |
| 18 | Lô 4 | Phiếu giao **không lưu mốc "Bắt đầu giao"** (và "Lúc báo thất bại"). Story ED-19-AC2/AC3/AC5 yêu cầu hiện các mốc này. | BE thêm 2 trường thời điểm (migration nhỏ, chỉ thêm) — giúp đo thời gian giao. Hoặc bỏ khỏi AC (xem ở dòng thời gian). | Chưa làm; thời điểm xem được ở dòng thời gian của phiếu. |
| 19 | Lô 3, 7 | Nút **"Nhờ" (chuyển việc cho người khác xử lý, DW-23)** nằm trong bảng hướng dẫn cũ (GuidancePanel) — trang chi tiết mới thay bằng khối Trợ lý AI nên **nút Nhờ mất** ở trang đơn và trang lô (AC7 cũ: "AI tắt thì Nhờ vẫn chạy"). Thiết kế mới không vẽ nút này. | (a) Thêm mục "Nhờ người xử lý" vào menu "…" của trang chi tiết (làm chung ở Lô 17). (b) Bỏ hẳn, ghi vào decisions. | Đang thiếu; em đề xuất (a). |
| 20 | Lô 8 | Phiếu kiểm kê **không có bước "Gửi duyệt" riêng**: BE chỉ có Nháp → Đã duyệt, nên phiếu "Lưu nháp" đếm dở vẫn duyệt được ngay. Màn hiện chặn Gửi duyệt khi còn lô chưa đếm, nhưng người duyệt vẫn duyệt được bản nháp. | Thêm trạng thái "Chờ duyệt" (BE migration nhỏ): chỉ duyệt phiếu đã gửi. Hoặc giữ, dựa vào người duyệt đọc kỹ. | Giữ như BE hiện tại. |
| 21 | Lô 9 | **Quản lý có được tự nhập hàng hoàn về kho không?** Hiện nhóm Quản lý chỉ có quyền **duyệt** hàng hoàn, không có quyền **tạo** (`add_returntostock`) → không có nút "Nhập hàng hoàn". NV kho và NV giao (phiếu của mình) tạo được. | Cho Quản lý tạo (data migration nhỏ cấp quyền) — Quản lý thường nhận hàng thay khi kho vắng. Lưu ý: người tạo vẫn duyệt được phiếu của chính mình (chưa có luật tách như kiểm kê). | Giữ như quyền hiện tại. |
| 22 | Lô 10 | **Nhập lô tại cảng khi chưa biết giá mua**: để trống ô Giá mua thì hệ thống gửi giá 0 đ và **ghi nhận lô ngay** (BE cho giá ≥ 0) → giá vốn lô = 0 cho tới khi có hoá đơn/chi phí. Có phải chủ ý (nhập trước, giá sau) không? | Bắt buộc giá mua > 0 khi nhập lô; nếu thật sự chưa biết giá thì cần luồng "chờ giá" riêng (lô không mở bán khi giá vốn = 0). | Giữ hành vi cũ (cho phép trống = 0 đ). |


## Duy trả lời (02/10/2026, chiều)
| # | Duy chốt | Việc phải làm |
|---|---|---|
| 1 | Làm BE `/api/ai/status/` cho hoàn chỉnh (FE cần biết khi nào AI bật/tắt). | BE route + test; FE giữ nguyên contract S05. |
| 2 | OK bỏ lý do khỏi dòng thời gian đơn, **nhưng phải có link xem chi tiết**. | Dòng "Tạo phiếu hoàn" trên timeline đơn link sang phiếu hoàn. |
| 3 | Chưa hiểu — em giải thích lại (chờ Duy chốt). | — |
| 4 | OK giữ luật chặn 9 chữ số. | Không làm gì. |
| 5 | Cho sửa SĐT khách; trùng thì báo trùng. | BE PATCH nhận `phone` (400 khi trùng, ghi AuditLog không giá trị) + FE ô sửa SĐT. |
| 6 | Theo phân quyền: ai có quyền nhập và quyền duyệt thì tự duyệt được, chỉ cần ghi sự kiện ("cứ event là được"). | Bỏ chặn cứng BR-KK-08 (và BR-KK-02 — em hiểu cùng ý); giữ AuditLog ai nhập/ai duyệt. |
| 7 | OK phương án B (BR-KK-09). | Đã code; PO ghi BR-KK-09 vào spec. |
| 8 | Cho **huỷ** phiếu hoàn rồi tạo phiếu mới; **xoá** chỉ Chủ/admin. | Thao tác huỷ phiếu hoàn (Chờ duyệt) + quyền xoá chỉ Chủ — xem lưu ý về luật "không xoá chứng từ". |
| 9 | Phạm vi dòng ("chỉ xem của mình") phải là **cấu hình phân quyền**, không viết cứng. | Thiết kế: ma trận phân quyền (Lô 14) có thêm phạm vi theo nhóm × đối tượng (Tất cả / Của mình). Cần BA + Tech Lead. |
| 10 | Cho sửa giá; giá đã chốt vào đơn không đổi; giá áp theo thời gian hiệu lực; **sửa giá đã dính đơn thì báo không sửa được**. | BE: cho phép đặt giá lùi ngày/sửa giá khi chưa có đơn nào dùng trong khoảng đó; có đơn → 400 kèm lý do. |
| 11 | OK tìm khách bằng POST. | BE + FE đổi tìm khách sang POST body. |
| 12 | Xem hoá đơn bán (và tên khách) theo **phân quyền cấu hình**, không viết cứng. | Gộp với #9: quyền xem hoá đơn bán / tên khách bật tắt được trong ma trận. |
| 13 | Không chặn cứng: bật "Xem khách hàng" cho nhóm nào là do admin quyết. | Giữ như hiện tại (màn hiện "Tất cả khách" khi bật). |
| 14 | Chọn cách an toàn: **chặn sửa tiền chi phí phụ sau khi đã phân bổ** — sai thì huỷ + nhập lại (em chọn theo câu Duy dán; Duy muốn "sửa có phân bổ lại" thì báo). | BE PATCH `amount`/phân bổ của chi phí đã phân bổ → 400; hướng dẫn huỷ + nhập lại. |
| 15 | Đơn đã tự huỷ (hết giờ giữ chỗ) là huỷ hẳn: **không còn thao tác** trên FE (xác nhận tiền sẽ sai). | BE bỏ `confirm_payment` khỏi `available_actions` và chặn API với đơn AUTO_CANCELLED; tiền về muộn xử lý ở Hàng chờ thanh toán → hoàn. |
| 16 | Giữ "Đang xử lý" như hiện tại. | Không làm gì. |
| 17 | Làm R4b (SĐT sẵn trong "Việc giao của tôi"). | BE + FE. |
| 18 | BE thêm 2 trường thời điểm "Bắt đầu giao", "Lúc báo thất bại" (migration chỉ thêm). | BE + FE hiện. |
| 19 | (a) Thêm "Nhờ người xử lý" vào menu "…" trang chi tiết. | FE (dùng API chuyển việc sẵn có). |
| 20 | Thêm trạng thái "Chờ duyệt" cho phiếu kiểm kê (gửi duyệt rồi mới duyệt). | BE migration + FE nút Gửi duyệt. |
| 21 | Cho Quản lý quyền tạo hàng hoàn (phân quyền, cấp thêm). | Data migration cấp `add_returntostock` cho nhóm Quản lý. |
| 22 | Giá mua bắt buộc > 0. | BE + FE. |

## Đã tự chốt theo nguyên tắc (Duy xem lại nếu muốn lật)
- 02b viết trước đợt đổi tên P8b Lô 4–5 → dùng tên mới trong code (bảng ở `03-dev-notes.md`).
- Tên e2e 02b đặt `ed_lo<N>_…` bị `scripts/check_naming.py` chặn (viết tắt tiếng Việt) → dùng `ed_lot<N>_…`.
- Lệnh grep màu cứng 02b §5.0 ghi "phải rỗng" nhưng gốc đã có 553 dòng → áp "không tăng tổng + file lô đụng phải sạch".

## Nợ chuyển lô sau (điều phối ghi, không cần Duy quyết)
- Lô 6: test timeline `customer` với quyền mới `sales.view_customer_list` (provider tự chuyển khi quyền tồn tại).
- Lô 9: siết phạm vi dòng hàng hoàn cho `delivery_staff` ở API **và** provider timeline `return` (dùng chung hàm), test 404 NV giao khác (review Lô 2 L1).
- Lô 6: gom hàm quyền "Xem khách hàng" trùng nhau ở `apps/sales/orders/scope.py` và `apps/sales/customers/next_steps.py` về một chỗ, chuyển sang `has_perm("sales.view_customer_list")` (review Lô 3 L3).
- Lô sau được sửa test `apps/sales`: bỏ mặc định `mark_failed(reason=None)` để không còn đường bỏ qua lý do bắt buộc (review Lô 4 L4).
- FE Lô 4: form "Giao cho người giao" xử lý **409** `STALE_STATE` (02b ghi 400; BE trả 409 — techlead chấp nhận).
- **Không deploy giữa chừng:** sau Lô 1, khung mới bỏ cột phải nên nút "Tóm tắt" AI (DW-16) tạm mất cho tới khi Lô 2 FE gắn khối Trợ lý AI vào trang. Đằng nào cũng chỉ deploy khi anh bảo — nhưng đừng deploy bản có Lô 1 mà chưa có Lô 2.
- Font icon ERP (`erp-console/public/fonts/ms/*.woff2`, 93 KB, Apache-2.0) trước bị `.gitignore` chặn → clone sạch build ra icon vỡ. Em bỏ chặn và commit font cùng Lô 1.
- Ký hiệu tiền: ERP thống nhất **"đ"** theo thiết kế. FE tự định dạng từ số (`format.vnd`), không hiển thị chuỗi `vnd_display` "₫" của BE; BE và Shop giữ nguyên (không đổi API).
- Lô sau (có migration `inventory`): index sổ nhập xuất `(batch, created_at, id)`, `(-created_at, -id)`, lọc ngày theo khoảng giờ VN thay `__date`; PATCH đổi tên kho ghi AuditLog + chặn trùng hoa thường; gom hàm đọc tham số lọc về `apps/common/params.py` (review Lô 7 L1–L4).
- Trước deploy Lô 8: đếm (chỉ đọc) dòng kiểm kê thuộc phiếu DRAFT cũ trên staging/production — số "tồn sổ" của phiếu tạo qua Django Admin do người gõ tay, BR-KK-09 sẽ áp đúng số đó (review Lô 8 L5).
- Lô 15: `/ai/policy/` thiếu ViewGuard (lỗi có sẵn, QA Lô 1 P1) — mọi vai vào được màn (BE vẫn chặn API).
- Staging Postgres: thử 2 POST hàng hoàn 6 kg cùng lúc vào phiếu 10 kg → phải ra một 201 + một 400 `RETURN_QTY_EXCEEDS` (review Lô 9 L3; SQLite không thử được khoá đồng thời).
- Quy ước FE: mỗi trang chỉ một `useTabParam` (ghi tham số `tab`); trang cần 2 thanh tab thì thêm tham số `param` (review Lô 1 L7).
- Lô 11: "Tổng tiền mua" của nhà cung cấp chỉ **Chủ** thấy (02b B3; khác tiền hoá đơn mua D-3 — vì tổng = kg × giá mua, chia ra được giá vốn). Số phiếu / lần nhập gần nhất / tổng tiền chỉ tính phiếu **đã ghi nhận** (không tính Nháp) theo mặc định Q4 trong 02-stories.
- Lô 11: nhà cung cấp **không xoá** được qua API (DELETE → 405), ngừng hợp tác = tắt "Đang hợp tác".
- Lô sau được sửa `apps/sales`: tạo đơn dùng chung hàm chọn giá `current_item_price` của catalog (review Lô 13 L4).
- QA BE Low gom (lô dọn dẹp): khoảng trắng trong tham số lọc được chấp nhận; chữ số Ả Rập ở chi tiết khách; `reference` tự do cũ ở sổ kho echo nguyên; `reference_link` kiểm kê không tồn tại không null; tên kho dạng NFD không coi là trùng; giờ trả lẫn `+07:00` và `Z`.
- Tech Lead xem (QA Lô 8 N8-2, có sẵn): chặn H6 trong `apps/ai/actions/services.py` khoá **mọi** lệnh AI kiểm kê khi người xác nhận là chủ AI (kể cả `create`, `replace_lines`) → chủ AI không bao giờ xác nhận được đề xuất kiểm kê. Đề xuất chỉ chặn `approve`.
- QA Low Lô 8/9/10 (lô dọn dẹp): duyệt kiểm kê lần 2 trả mã chung `BUSINESS_ERROR` thay `RECON_NOT_DRAFT`; NV giao PATCH/duyệt hàng hoàn người khác ra 403 (dev-notes ghi 404, không rò); số kg trong lỗi vượt kg không chuẩn 3 chữ số; `status=DRAFT,,` được chấp nhận; id chữ số Ả Rập không ra 404.
- Lô 12 FE: màn Hoá đơn bán ghi chú tổng tiền gồm cả hoá đơn của đơn đã huỷ (chứng từ đảo), doanh thu thật xem ở Báo cáo lãi lỗ.
- Lô 12 FE: ghi tiêu chí "lô phát sinh trong tháng" dưới bộ lọc tháng của Báo cáo lãi lỗ theo lô (lô cũ chỉ có hao hụt/hàng hoàn trong tháng không hiện). Nợ: bản `batch_pnl` hàng loạt nếu staging đo trang > 1 s.
- Luật code (review Lô 14 L4): action nào kiểm thêm quyền của **việc khác** (kể cả `has_perm` trong thân hàm) thì phải khai `requires` ở `apps/accounts/capabilities/registry.py`; nợ: mở rộng test quét sang AST. Staging: thử timeline nhóm quyền (lọc JSON `icontains`) trên Postgres.
- Lô 15: dòng "đề xuất AI chờ duyệt" ở Tổng quan phải gồm cả việc AI đã **chuyển nhóm (ESCALATED)**, vì khi AI tắt khối Trợ lý AI trong trang bị ẩn (T10). Lô 3+: màn chi tiết gắn `DetailPage` + `AiDocBlockGate`; màn danh sách đăng ký nguồn mất mạng (`usePagedList`/`ListPage`).
- Lô 3: thêm route chi tiết vào `TARGETS` của `erp-console/scripts/check-ai-chunks.mjs` (review Lô 2 FE L3); InfoField sửa tại chỗ gặp 409 phải báo (L5); cờ AI bật không "dính" theo trang đã ghé (L2).
- QA BE Low gom thêm: id chữ số Ả Rập trả 200 ở chi tiết nhà cung cấp (`lookup_value_regex=[0-9]+`); `reports/batches` ~34 truy vấn/trang; ưu đãi giảm 100% cho đơn 0 đồng; `rate="1e3"` được hiểu là 1000.
- Staging Postgres (⏸ QA): tranh chấp tên nhà cung cấp nhiều tiến trình; hai người đặt giá cùng lúc; hai PUT ma trận quyền song song; timeline nhóm quyền; thời gian phản hồi `reports/batches`.
- Khối Trợ lý AI (ED-04-AC8): chip câu hỏi nhanh + ô chat hiện **sẵn** dạng khung tĩnh; mô hình AI chỉ nạp khi người dùng bấm vào — giữ đúng thiết kế mà không làm chậm trang (BR-AI-17, "hiệu năng không đánh đổi"). Khối AI không hiện ghi chú chữ tự do (chống lộ dữ liệu khách).
- Lô 3: chip "chứng từ này" của khối AI phải gửi kèm ngữ cảnh chứng từ (loại + mã, không dữ liệu khách) để trợ lý trả lời đúng chứng từ (review Lô 2 L8); người chưa đồng ý AI focus ô hỏi thì focus không rơi về body (L9).
- Lô 3+: khung hỏi nhanh AI giữ ô tĩnh tới khi panel nạp xong để không mất ký tự gõ sớm (QA Lô 2 B6); panel AI cũ còn chữ "đang chờ chốt ở S17" và dòng "RAM…WebGPU…Mạng" dính nhau (có sẵn) → Lô 15.
- Lô ngang (gộp Lô 17): `AiBarGate` dùng chung cho mọi `ListPage` (thanh "AI · Có n đề xuất…", AI tắt → 0 request `/api/ai/*`) — hiện chưa danh sách nào có thanh AI (review Lô 4 FE nợ 4).
- Sau khi có Lô 3 + Lô 4: menu "…" chi tiết phiếu giao thêm mục khoá "Huỷ đơn", "Huỷ xác nhận đơn" kèm lý do + link sang trang đơn (ED-17-AC3).
- Backlog BE: tham số tìm `q` cho danh sách phiếu giao (hiện FE chỉ lọc trên các trang đã tải, có câu báo).
- Lô 9 FE: nút "Mang hàng về kho" trên thẻ phiếu giao thất bại (Việc giao của tôi) mở F2m điền sẵn phiếu giao (QA Lô 4 B5 — hoãn từ Lô 4).
- BE nhỏ: chi tiết đơn trả `customer.id` (để link "Mở trang khách" khi có quyền) và pk lô trong phân bổ (để link sang lô) — làm cùng FE Lô 6/Lô 7.
- BE nhỏ cho Lô 4: dòng phân bổ phiếu giao trả `warehouse_name`; phiếu giao lưu mốc "Bắt đầu giao" và "Lúc báo thất bại" (ED-19-AC3/AC5 hiện thiếu, thời điểm vẫn xem ở dòng thời gian).
- Backlog BE: `state=ALL` cho hàng chờ gọi xác nhận (FE đang gộp 4 lần gọi); tham số `q` cho hàng chờ. PO xác nhận nghĩa cột "Hạn gọi" (suy từ `callback_at` / `decide_deadline` / `window_ends_at`).
- Lô 5: cách viết cờ mock trong `features/confirmation/api.ts` từng làm mock lọt vào bản build thật khi sửa màn; đã viết lại, `check-no-mock` XANH. (Số gốc trên `main` trước đợt này `check-no-mock` cũng XANH → production không bị.)
- Nợ chung: tiền trong nhãn dòng thời gian / "Đã làm" do BE dựng chuỗi ghi "₫" (`common/formatting.vnd_display`) — lệch quy ước ERP "đ"; sửa ở BE khi dọn (ảnh hưởng chuỗi Shop → cần kiểm). BE trả `refundable_amount` để FE không tự tính.
- Lô 17 / lô AiBar chung: `AiDocBlockGate` nhận prop `chips`, bỏ bản chép `ConfirmationAiBlock` (review Lô 5 L3); `features/purchasing/api.ts` đổi cờ mock sang cách viết `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? … : undefined` (L4, làm ở Lô 10 FE); sau merge Lô 3+5: link huỷ đơn từ Gọi xác nhận trỏ thẳng `/orders/detail/?id=&open=refund` (L5).
- Người thuộc cả CSKH lẫn NV giao chỉ thấy dòng thời gian phiếu gán cho mình (thiếu quyền, không rò) — chưa có tài khoản nào hai vai (QA5-B2 Low).
- BE nhỏ (Lô 5): chi tiết hàng chờ gọi xác nhận trả `note_code` (mã phiếu giao) — FE đang hiện "—" trên BE thật. Lô 4: `ReprintLabelModal`, `AssignCourierModal` còn dòng gợi ý xám (UI-RULES §6.2) → Lô 17.
- Lô 17 dọn: nút `aria-disabled` không đổi nền khi rê/nhấn (`globals.css` thêm `:not([aria-disabled="true"])`); `SkeletonBody` của DataTable ẩn cột như bảng thật ở 360px; PO: cột "Lý do" của hàng chờ gọi xác nhận bị ẩn trên điện thoại (xem ở chi tiết) — giữ hay hiện (review Lô 5 R1–R3). TL5-BE1 đã sửa (6f1a235).
- Đã tự chốt (Lô 5): màn < 1024px (tablet) bảng hàng chờ gọi xác nhận ẩn cột "Hàng" (xem ở chi tiết) theo T4 — ERP chỉ thiết kế cho máy tính. Mock giao hàng còn mã `DH-` → đổi sang `SO…` ở Lô 17.
- BE nhỏ: nhãn dòng thời gian lô (`backend/apps/inventory/batches/timeline.py` `kg_str`) ra "Nhập kho 18.000 kg" — đọc nhầm thành mười tám nghìn; đổi sang "18 kg" / "18,5 kg". Màn ERP chưa có thao tác ghi lô trên BE thật (seed không có lô Quá hạn còn tồn) → viết lại `p8_lo5_qa_real_backend.py` (Lô 7 nợ).
- PO (Lô 3 QA N2/N3): ô tiền gõ tay dấu thập phân không bị bắt ("150.000,50" → 15.000.050; "150k" → 150) — nút gửi luôn hiện số đang hiểu, hoàn bị chặn bởi "Còn hoàn được", BE kiểm lại. Đề xuất Lô 17: báo lỗi khi gõ "," + 1–2 chữ số cuối và khi có chữ (k, tr).
- Staging (chỉ đọc): kiểm nhóm owner có đủ quyền các model sinh sau migration `accounts/0002` (`itemimage`, `salescreditnote`, `batchsupplierreturn`, `demorecord`) — review Lô 7.
- Đã tự chốt (Lô 8 F3): sau 409, nút "Tải lại" nạp **bản mới của người kia** (bỏ bản đang gõ), đúng board W6f "Tải lại để xem bản mới" — tránh ghi đè mà người dùng không biết.
- BE Low: chuỗi lỗi "Chỉ publish được lô…" còn chữ tiếng Anh (Lô 7 QA). Nhật ký hoạt động: các dòng huỷ/trả NCC/chốt lô có số tiền suy ra giá vốn — Quản lý xem dòng nhưng khoá tiền đã che; kho/giao/CSKH 403 (QA Lô 7 xác nhận không rò).
- Lô 17 hồi quy: `qa_ed_batch1_shell` 3 ca cũ cần cập nhật theo màn mới (⌘K khớp mục menu "Khách hàng" khi gõ tên khách là khớp nhãn menu, không phải tìm khách; tab `/orders/` đổi bố cục ở Lô 3; console.error của React prod).
- BE nhỏ: `ReturnToStockSerializer` trả `order: {id, code}` để FE bỏ hook `useReturnOrderId` (đang đọc thêm phiếu giao để lấy id đơn) — Lô 9 nợ. Sau Lô 7 vào main: "Lô" ở chi tiết hàng hoàn thành liên kết.
- PO biết (Lô 10): ô "Giá mua" nhập lô chỉ nhận đồng nguyên (form cũ nhận số lẻ). Quản lý nhập được giá mua lúc nhập lô (hành vi cũ) nhưng không xem lại được — muốn cấm Quản lý nhập giá là đổi quy tắc. Nợ Lô 12: ô chọn phiếu ở form hoá đơn/chi phí chỉ tải 20 phiếu; gợi ý tiền hoá đơn làm tròn phần lẻ .50.
- Lô 17 dùng chung: `.lt-link` trong DataTable phủ cả ô (display:block + min-height 44px) để bàn phím/nhấn giữ/mở tab mới có vùng bấm đủ; bỏ loại trừ `.lt-link` trong e2e vùng bấm (review Lô 11). Mock nhà cung cấp còn `NCC-${id}`.
- BE nhỏ (Lô 8): PATCH phiếu kiểm kê (ngày/ghi chú) kiểm `expected_updated_at` để đóng khe "ghi chú ai lưu sau thắng"; FE cảnh báo rời trang khi chưa lưu (Lô 17).
- BE nợ (Lô 10 N3): `POST /api/purchasing/costs/` trả 500 khi chi phí chia vào một lô làm giá vốn/kg vượt 10 chữ số phần nguyên (cùng gốc cột `landed_unit_cost`) → bắt lỗi trả 400 theo `allocations`. Rủi ro vận hành thấp. PO: số kg gõ "1.000" được hiểu là 1 kg (có thể nhầm thành một nghìn).

- Duy dặn 02/10 chiều: làm các quyết định trên **ở máy này luôn**. Còn chờ: #3 (giải thích lại), #8 (xoá thật hay ẩn), #9/#12 (thiết kế phạm vi cấu hình — BA + Tech Lead).

### Duy quyết 03/10/2026
- **SĐT khách trên ERP: hiện đủ** (không che "…0412" như board). Áp cho danh sách/chi tiết khách, Gọi xác nhận, Nhân sự, phiếu giao. Nhóm F trong `04b-ra-soat-giao-dien.md` đóng — không phải lệch. Phạm vi ai được xem vẫn theo phân quyền (bất biến 9 + ma trận Lô 14).
- **#3 (chốt):** dòng thời gian **không** chép ghi chú tự do — chỉ nhãn chuẩn (mã lý do → nhãn, mã chứng từ, kg, tiền, người làm). Tiền trên timeline ghi "đ".
- **#8 (chốt):** xoá phiếu hàng hoàn **ở màn chi tiết**, chỉ Chủ/admin. Làm **xoá mềm** (ẩn khỏi mọi danh sách/báo cáo, giữ bản ghi + nhật ký) vì luật "không xoá chứng từ"; chỉ xoá được phiếu Nháp/Đã huỷ — phiếu đã cộng tồn phải huỷ trước.
