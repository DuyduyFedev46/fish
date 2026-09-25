# Xuất kho FEFO (hết hạn trước, xuất trước) — Phân tích nghiệp vụ
> BA · 2026-09-26 · Trạng thái: **ĐÃ DUYỆT** (2026-09-26, Duy)

## 1. Yêu cầu gốc
> "có 1 thứ chúng ta làm sai, nếu làm hàng đông lạnh phải là FEFO mới đúng"

Nguồn: Duy (PO), 2026-09-26. Nhãn: **(D)**. Đây là một quyết định của Duy, không phải đề xuất cần bàn lại.

## 2. Tóm tắt
**Hệ thống** (khi Khách đặt hàng trên Shop) cần **chọn lô có hạn dùng sớm nhất để giữ chỗ và xuất trước**, thay cho việc chọn lô nhập sớm nhất, để **hàng đông lạnh ra khỏi kho trước khi hết hạn nội bộ**. Nhờ vậy giảm lỗ hàng hết hạn (BR-LO-03), và lãi lỗ theo lô phản ánh đúng việc bán hàng.

### 2.1 Vì sao FIFO sai với Cá Về
BR-BH-05 hiện ghi: *"Chọn lô theo FIFO theo ngày nhập. Lô cận hạn vẫn theo FIFO (tự nhiên ra trước)."* Câu "tự nhiên ra trước" chỉ đúng khi mọi lô của cùng một mặt hàng có **cùng số ngày hạn tính từ ngày nhập**. Hệ thống hiện có ít nhất 3 đường làm giả định đó sai:

| # | Tình huống lô nhập sau lại hết hạn trước | Nguồn hiện trạng |
|---|---|---|
| a | Lúc nhập, NV kho/Chủ **sửa hạn xuống** cho một dòng, vd hàng nhập khẩu có hạn của nhà sản xuất ngắn hơn, hoặc hàng cấp đông đã lâu trước khi về vựa | BR-MH-02; `PurchaseReceiptLine.shelf_life_days` → `purchasing/receipts/services.py::_validate_shelf_life` |
| b | Chủ **giảm hạn dùng mặc định** của mặt hàng. Lô cũ giữ hạn cũ (dài), lô mới nhận hạn mới (ngắn) | S38-AC1 (ERP console): "lô đã sinh không đổi hạn" |
| c | Dữ liệu demo đặt hạn **không phụ thuộc** ngày nhập, vd `LO-0912` nhập cách đây 3 ngày, còn 1 ngày hạn | `accounts/management/commands/seed_demo.py` (bảng `BATCHES`) |

Khi đó FIFO xuất lô dài hạn trước, còn lô ngắn hạn nằm lại, quá hạn, bị loại khỏi bán (BR-LO-02) và phải huỷ, hạch toán lỗ (BR-LO-03). FEFO xử lý đúng các trường hợp này.

**Nhận xét về quy mô tác động:** nếu mọi lô dùng hạn mặc định (ngày nhập + 90), FEFO và FIFO cho **cùng một thứ tự**. Vì vậy thay đổi này ít làm xáo trộn dữ liệu đang chạy, nhưng quan trọng khi có hạn sửa tay. Dev nên đếm trên DB thật xem hiện có bao nhiêu cặp lô cùng mặt hàng mà thứ tự FIFO khác FEFO trước khi triển khai (mục 7).

## 3. Bối cảnh trong hệ thống
- **Quy trình:** P-05 Bán hàng (chọn lô, giữ chỗ) là chính. Liên quan P-01 (combo BUNDLE), P-04 (vòng đời lô, cận hạn/quá hạn), P-06 (soạn hàng lấy đúng lô), P-07/P-08 (hoàn kho về lô gốc), P-10 (giá vốn theo lô).
- **Rule hiện có:** BR-BH-05 (đổi), BR-BH-02/06/07, BR-LO-01/02/03/06, BR-MH-02, BR-DM-06/07, BR-HV-01/04, BR-HT-05, BR-BC-02/04, BR-PQ-12 (khách không chọn lô, S1-AC6).
- **Tài liệu đang ghi FIFO:** URD §6.2 ("Xuất kho theo nguyên tắc lô nhập trước xuất trước (FIFO) khi bán"), URD §9 Thuật ngữ ("FIFO"), business-process-spec §3.1 bảng combo ("FIFO từng thành phần"), BR-BH-05, BUILD-PLAN (`allocate_fifo`: "theo FIFO ngày nhập"), doctype-mapping (Sales Invoice "theo batch, FIFO", tài liệu này đã lỗi thời).
- **Quyết định ràng buộc (decisions.md):**
  - 2026-09-09 "Hàng hoá là đông lạnh, quản lý theo lô": hạn dùng gắn theo lô, hạn nội bộ 3 tháng. Phần *Hệ quả* ghi **"Theo dõi theo ngày nhập lô là đủ."** Câu này mâu thuẫn với yêu cầu mới. BA không sửa decisions.md; Duy cần ghi một quyết định mới thay câu này (câu hỏi Q6).
  - 2026-09-10 "Combo": BUNDLE "trừ kho theo FIFO từng thành phần". Cơ chế nổ thành phần giữ nguyên, chỉ đổi thứ tự chọn lô (Q6).
- **Hiện trạng code (đã đọc):**
  - `inventory/batches/services.py::sellable_batches` lọc lô `SELLING/NEAR_EXPIRY` và `expiry_date >= hôm nay` (BR-LO-02), sắp theo `received_date, id`. Đây là **nguồn duy nhất** cho thứ tự chọn lô.
  - `allocate_fifo` duyệt `sellable_batches` theo thứ tự trên và lấy dần tồn khả dụng (`qty_available − qty_reserved`).
  - `sales/orders/services.py::create_order` gọi `allocate_fifo` cho từng dòng/thành phần combo, rồi `reserve` và ghi `SalesOrderLineBatch` (kèm ảnh chụp `unit_cost`).
  - `sales/payments/services.py::issue_invoice` **không phân bổ lại**. Hàm này trừ kho đúng các lô đã giữ trong `SalesOrderLineBatch` và ghi `SalesInvoiceLineBatch` với `landed_unit_cost` hiện hành.
  - `Batch.expiry_date` **bắt buộc** (không null). `create_batch` luôn tính hạn = ngày nhập + (hạn sửa tay, hoặc hạn mặc định của mặt hàng, hoặc `BATCH_DEFAULT_SHELF_LIFE_DAYS`). Cờ `Item.has_expiry_date` có trong model nhưng không có logic nào dùng. Hiện **không có lô nào không có hạn**.
  - `Batch.Meta.ordering = ["received_date", "id"]`, chú thích "FIFO theo ngày nhập (BR-BH-05)".
  - `catalog/items/services.py::sellable_qty` (số tồn trên Shop) chỉ **cộng tổng** các lô bán được, không phụ thuộc thứ tự, nên **không đổi**.
  - `reports/dashboard_api.py`: bảng "Tồn theo lô" lấy ≤20 lô, sắp theo `received_date, id`. Cảnh báo cận hạn đã sắp theo `expiry_date`.
  - ERP console đang ghi chữ "FIFO theo ngày nhập" ở `features/overview/components/OverviewScreen.tsx`, `features/inventory/components/InventoryScreen.tsx`, `shared/lib/nav.ts` ("Tồn theo lô, xuất FIFO…"), `shared/lib/dashboardSummary.ts`, `features/overview/README.md`. Mock `features/orders/mock.ts` cũng nhắc FIFO.
  - Hàng hoàn (`inventory/returns/services.py::apply_return`) và huỷ đơn đã thanh toán (`cancel_paid_order`) cộng lại **đúng lô gốc**, không chọn lô, nên không bị thứ tự ảnh hưởng.
  - Job `update_batch_statuses` chỉ đổi trạng thái theo hạn/tồn và không nhả giữ chỗ, nên không bị thứ tự ảnh hưởng.

## 4. Tác nhân & quyền
| Tác nhân | Group | Làm được gì trong phạm vi này | Quyền Tầng 2 cần |
|---|---|---|---|
| Khách | (không phải User) | Đặt hàng. **Không chọn lô**: hệ thống tự phân bổ (BR-PQ-12, S1-AC6 giữ nguyên) | — |
| Hệ thống | `actor=None` | Chọn lô theo FEFO khi tạo đơn, giữ chỗ, trừ kho đúng lô đã giữ khi thanh toán | — |
| NV kho | `nv_kho` | Soạn hàng: lấy **đúng lô** hệ thống đã phân bổ (xem mã lô và hạn trên đơn). Xem Kho & lô theo thứ tự xuất | — (không thấy giá vốn) |
| Quản lý | `quan_ly` | Như NV kho, cộng thêm duyệt hàng hoàn về lô gốc (không đổi) | `approve_returntostock` (không đổi) |
| Chủ | `chu` | Xem thứ tự xuất, giá vốn theo lô, lãi lỗ | `view_costprice`, `view_profitreport` (không đổi) |

Tính năng này **không mở thao tác mới** cho vai nào, trừ khi Duy chọn cho phép chọn tay lô ở Q2. Khi đó phải thêm một quyền Tầng 2, và theo ranh giới BR-PQ quyền này thuộc Chủ vì nó đổi con số lời lỗ theo lô.

## 5. Use case

### UC-1 Khách đặt mặt hàng thường: hệ thống phân bổ lô theo FEFO
- **Tiền điều kiện:** mặt hàng có ít nhất một lô *bán được*: trạng thái Đang bán/Cận hạn **và** hạn dùng ≥ hôm nay (giờ VN) (BR-LO-02, S1). Lô Nháp, Quá hạn, Đã huỷ, Đã chốt không tham gia.
- **Luồng chính:**
  1. Khách đặt X kg mặt hàng M.
  2. Hệ thống xếp các lô bán được của M theo **hạn dùng tăng dần**. Hai lô cùng hạn thì lô **nhập sớm hơn** đứng trước. Nếu vẫn trùng thì lô **tạo trước** đứng trước (BR-BH-05 sửa).
  3. Hệ thống lấy dần tồn khả dụng (tồn sổ − đang giữ chỗ) của từng lô theo thứ tự trên cho tới khi đủ X kg. Một dòng được phép ăn nhiều lô (BR-BH-06).
  4. Hệ thống giữ chỗ trên từng lô và ghi bảng phân bổ dòng ↔ lô ↔ kg ↔ giá vốn ảnh chụp (BR-BH-02/06).
  5. Đơn ở trạng thái Giữ chỗ, TTL 30 phút (BR-BH-03).
- **Luồng thay thế:**
  - 2a. Lô cận hạn (hạn ≤ hôm nay + `BATCH_NEAR_EXPIRY_DAYS`) đứng đầu vì hạn sớm nhất. Chỉ **thứ tự** đẩy lô này ra trước, **giá không đổi** (BR-LO-01). Muốn xả giá thì Chủ tạo Item Price mới.
  - 2b. Lô có hạn = **hôm nay** vẫn bán được (C1: `expiry_date` là ngày cuối còn bán) và FEFO chọn nó **đầu tiên**. Xem rủi ro R-3 và Q3.
  - 3a. Lô đứng đầu còn ít hơn X kg: lấy hết lô đó rồi lấy tiếp lô sau. Đơn có nhiều dòng phân bổ.
- **Ngoại lệ:**
  - E1. Tổng tồn khả dụng < X kg: không tạo đơn, báo thiếu (BR-BH-02). Không đổi so với hiện tại.
  - E2. Hai khách cùng tranh lô hạn sớm nhất: người tạo đơn trước thắng. Với người sau, hệ thống tính phân bổ lại trên tồn còn lại, hoặc báo hết hàng nếu không đủ (BR-BH-02, E-06). Với FEFO mọi đơn đều nhắm cùng một lô hạn sớm nhất, tương tự FIFO nhắm lô cũ nhất, nên mức tranh chấp không tăng.
  - E3. Khách cố gửi mã lô trong yêu cầu đặt hàng: bỏ qua, vẫn phân bổ FEFO (S1-AC6, BR-PQ-12).
- **Hậu điều kiện:** bảng phân bổ lô của đơn phản ánh thứ tự FEFO **tại thời điểm tạo đơn**. Tồn khả dụng trên Shop giảm đúng X kg (con số không phụ thuộc thứ tự).

### UC-2 Khách đặt combo BUNDLE: FEFO từng thành phần
- **Tiền điều kiện:** BUNDLE có công thức (BundleLine). Mọi thành phần có đủ tồn khả dụng (BR-DM-06).
- **Luồng chính:**
  1. Hệ thống nổ combo thành thành phần theo công thức đóng băng lúc đặt (BR-DM-07, BR-BH-08).
  2. Với **mỗi thành phần**, hệ thống chạy UC-1 bước 2–4 (FEFO trong phạm vi lô của thành phần đó).
  3. Giữ chỗ đồng thời mọi thành phần (BR-BH-07).
- **Luồng thay thế:** 2a. Hai thành phần có lô hạn khác nhau: mỗi thành phần tự chọn lô hạn sớm nhất của mình, không có ràng buộc "cùng hạn" giữa các thành phần.
- **Ngoại lệ:** E1. Thiếu một thành phần thì huỷ cả đơn, không giữ chỗ phần nào (BR-BH-07).
- **Hậu điều kiện:** giá vốn combo = tổng giá vốn các lô thành phần thực xuất (decisions 2026-09-10). Các lô này giờ được chọn theo FEFO.

### UC-3 Thanh toán: trừ kho đúng lô đã giữ
- **Tiền điều kiện:** đơn Giữ chỗ, đã có bảng phân bổ lô.
- **Luồng chính:**
  1. Tiền về đủ (webhook hoặc Chủ xác nhận tay).
  2. Hệ thống trừ kho **đúng các lô đã giữ chỗ** và ghi bảng phân bổ lô trên hoá đơn với giá vốn hiện hành (BR-BH-06, BR-BC-02).
  3. **Không** chạy lại FEFO lúc thanh toán (BR-BH-11 mới, hệ thống đang làm vậy).
- **Luồng thay thế:** 1a. Giữa lúc đặt và lúc thanh toán có lô mới nhập với hạn sớm hơn: vẫn trừ lô đã giữ. Khách đã giữ đúng lô đó.
- **Ngoại lệ:**
  - E1. Đơn giữ chỗ trước nửa đêm trên lô hết hạn hôm đó, tiền về sau nửa đêm: vẫn xác nhận được, không nhả giữ chỗ (C1, `update_batch_statuses`). Không đổi so với hiện tại, nhưng FEFO làm tình huống này **xảy ra thường hơn** (R-3).
  - E2. Tiền về sau khi đơn đã tự huỷ: vào hàng chờ Chủ (BR-TT-05). Không đổi.
- **Hậu điều kiện:** sổ kho (StockLedgerEntry SALE) và bảng phân bổ trên hoá đơn khớp các lô đã giữ.

### UC-4 Chuyển đổi: đơn đang giữ chỗ lúc triển khai FEFO
- **Tiền điều kiện:** đang có đơn Giữ chỗ được phân bổ theo FIFO.
- **Luồng chính (mặc định PA, Q4):**
  1. Triển khai FEFO. Không đụng vào đơn đang giữ chỗ.
  2. Các đơn này đi tiếp như UC-3 trên lô đã giữ, hoặc tự huỷ khi hết TTL 30 phút.
  3. Mọi đơn tạo **sau** thời điểm triển khai dùng FEFO.
- **Ngoại lệ:** E1. Đơn đã thanh toán/đang giao/hoàn tất **không bao giờ** được phân bổ lại. Bảng phân bổ lô là append-only và là nguồn giá vốn.
- **Hậu điều kiện:** sau tối đa 30 phút kể từ khi triển khai, mọi giữ chỗ còn lại đều theo FEFO. Dữ liệu lịch sử giữ nguyên.

### UC-5 Hàng quay về kho (huỷ đơn đã thanh toán / giao thất bại tái nhập)
- **Tiền điều kiện:** đơn đã trừ kho theo bảng phân bổ lô.
- **Luồng chính:**
  1. Huỷ đơn đã thanh toán: hoàn kho về **đúng lô gốc** theo bảng phân bổ trên hoá đơn (BR-HT-05). Hoặc hàng giao thất bại được Quản lý/Chủ duyệt tái nhập về **đúng lô gốc** (BR-HV-01/02).
  2. Số kg hoàn lại vào lô gốc trở thành tồn khả dụng **với hạn của lô gốc**. Đơn sau sẽ gặp lô này theo vị trí hạn của nó trong FEFO.
- **Luồng thay thế:** 2a. Lô gốc đang Hết hàng và còn hạn: job trả lô về Đang bán/Cận hạn (S2-AC4). Lô trở lại hàng đợi FEFO theo hạn.
- **Ngoại lệ:**
  - E1. Lô gốc đã quá hạn: hàng về nhưng không bán được (BR-LO-02). Chủ huỷ và hạch toán lỗ (BR-LO-03/07).
  - E2. Lô gốc đã chốt: không nhận hàng hoàn, phải hạch toán lỗ (BR-HV-04, BR-LO-05).
- **Hậu điều kiện:** không tạo lô mới, không đổi hạn của lô gốc. Hạn dùng là thuộc tính của lô, hàng hoàn không "làm mới" hạn.

### UC-6 Nhân viên xem thứ tự xuất và soạn đúng lô
- **Tiền điều kiện:** người dùng nội bộ có quyền xem Kho & lô / Tổng quan / Đơn.
- **Luồng chính:**
  1. Màn Kho & lô và bảng "Tồn theo lô" ở Tổng quan hiển thị lô **theo thứ tự xuất FEFO**, nhãn "FEFO · hạn sớm nhất trước" thay cho "FIFO theo ngày nhập".
  2. Khi soạn hàng, NV kho thấy **mã lô và hạn dùng** của từng phần phân bổ trên đơn để lấy đúng thùng/khay vật lý.
- **Luồng thay thế:** 1a. Lô Nháp vẫn hiện trong danh sách hoạt động nhưng không nằm trong hàng đợi xuất, vì chưa bán được (BR-MH-05).
- **Ngoại lệ:** E1. NV kho lấy nhầm lô vật lý (khác lô hệ thống phân bổ): sổ theo lô lệch với thực tế. Kiểm kê theo lô sẽ phát hiện (BR-KK-01/03, BR-KK-06). Hệ thống không kiểm soát được thao tác này (R-4).
- **Hậu điều kiện:** không lộ giá vốn cho người thiếu `view_costprice`. Thứ tự hiển thị không kéo theo thêm cột nhạy cảm nào.

## 6. Business rule
| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| **BR-BH-05** | Chọn lô theo **FEFO**: trong các lô *bán được* (BR-LO-02), lô có **hạn dùng sớm nhất** xuất trước. Cùng hạn thì lô **nhập sớm hơn** trước. Vẫn trùng thì lô **tạo trước** trước, để thứ tự luôn cố định. Bỏ câu "Lô cận hạn vẫn theo FIFO (tự nhiên ra trước)". | FEFO: **(D)** Duy 2026-09-26 · khoá phụ: **(PA)** | **Sửa** |
| **BR-BH-11** | Phân bổ lô được **xác định một lần lúc tạo đơn**. Thanh toán trừ kho đúng lô đã giữ, không chạy lại FEFO. Đơn đã phân bổ không bị phân bổ lại khi có lô mới hay khi đổi quy tắc chọn lô. | (PA), khớp hiện trạng `issue_invoice` | **Mới** (ghi thành luật cho hành vi đang có) |
| BR-BH-06 | Một dòng ăn nhiều lô, bắt buộc có bảng phân bổ dòng ↔ lô ↔ kg ↔ giá vốn | (PA) | Giữ |
| BR-BH-02 | Giữ chỗ mức lô, người tạo đơn trước thắng | (PA) | Giữ |
| BR-BH-07 | Combo giữ chỗ đồng thời mọi thành phần. Mỗi thành phần chọn lô theo BR-BH-05 (FEFO) | (D)/(PA) | Giữ (chỉ đổi câu "FIFO từng thành phần" ở spec §3.1 thành "FEFO từng thành phần") |
| BR-PQ-12 / S1-AC6 | Khách không chọn được lô | (PA) | Giữ |
| BR-LO-01 | Lô cận hạn chỉ cảnh báo, không tự giảm giá. FEFO bảo đảm lô này được chọn trước, không cần "tự nhiên" | (PA) | Giữ |
| BR-LO-02 | Lô quá hạn loại khỏi bán ngay. FEFO chỉ xếp **trong** tập lô còn bán được | (PA) | Giữ, vẫn là cổng lọc trước FEFO |
| BR-LO-03 | Lỗ hàng hết hạn hạch toán vào lô. FEFO nhằm giảm con số này | (PA) | Giữ |
| BR-MH-02 | Hạn lô = ngày nhập + hạn mặt hàng, chỉ sửa xuống. Đây là **nguồn** của khoá sắp xếp FEFO | (PA) | Giữ (xem Q5) |
| BR-HV-01 / BR-HT-05 | Hàng về đúng lô gốc, giữ hạn lô gốc | (PA) | Giữ |
| BR-BC-02 / BR-BC-04 | Giá vốn lấy từ bảng phân bổ lô, báo cáo lô tính lại từ `landed_unit_cost` hiện hành | (PA) | Giữ. Cách tính không đổi, chỉ đổi **lô nào** bị trừ |
| **BR-LO-08** *(chỉ tạo nếu Duy chọn có ở Q3)* | Hạn còn lại tối thiểu khi bán trên Shop: lô còn < N ngày hạn không được phân bổ cho đơn mới (N là tham số cấu hình, giống BR-LO-06) | (PA) | Mới, **có điều kiện** |

## 7. Tác động dữ liệu & tích hợp
Chỉ mô tả *cái gì*, không thiết kế cách làm.

- **Schema:** mặc định **không cần** thêm model/field. `Batch.expiry_date` đã có và bắt buộc. Chỉ cần thêm field nếu (a) Q1 chọn "FEFO chỉ cho một số mặt hàng", hoặc (b) Q2 chọn cho phép chọn tay lô (cần lưu lý do/người chọn).
- **Thứ tự lô mặc định của model:** `Batch.Meta.ordering` và chú thích đang ghi FIFO. Việc có đổi thứ tự mặc định của model hay không (ảnh hưởng Admin, API danh sách lô) do BE quyết. Yêu cầu nghiệp vụ chỉ là: **mọi chỗ chọn lô để bán dùng FEFO**, và mọi chỗ hiển thị "thứ tự xuất" khớp với cách chọn đó.
- **Nguồn chung "lô bán được":** giữ một nguồn duy nhất, đang là `sellable_batches`. Thứ tự FEFO phải nằm ở nguồn này để phân bổ, dashboard và mọi nơi khác không lệch nhau (bài học S1).
- **Tên gọi trong code/tài liệu kỹ thuật:** `allocate_fifo`, docstring, README các app `inventory`/`sales`, `PRODUCT.md`, `README.md` gốc đều ghi FIFO. Đổi tên hay chỉ sửa mô tả là việc của BE. BA chỉ yêu cầu không còn mô tả nào nói "FIFO theo ngày nhập" là luật chọn lô.
- **API/màn hình:**
  - Shop: không đổi. Số tồn không phụ thuộc thứ tự, Shop không hiện lô.
  - ERP Tổng quan: bảng "Tồn theo lô" (≤20 lô, đang sắp theo ngày nhập) nên sắp theo thứ tự xuất FEFO. Lưu ý: đổi thứ tự sắp làm **đổi tập 20 lô hiển thị** khi có hơn 20 lô. Cảnh báo cận hạn đã sắp theo hạn, không đổi.
  - ERP Kho & lô: đổi nhãn/thứ tự như trên. `nav.ts` mô tả menu "xuất FIFO" đổi thành "xuất FEFO".
  - ERP Đơn / soạn hàng: phần phân bổ lô trên đơn (`OrderDetailView`) cần hiện **hạn dùng** bên cạnh mã lô (PA, UC-6) để NV kho lấy đúng hàng.
  - Mock ERP (`features/orders/mock.ts`, `shared/lib/dashboardSummary.mock.ts`) phải tính giống BE mới.
- **Dữ liệu demo (`seed_demo`):** đã có lô hạn không tỉ lệ với ngày nhập nên sẽ thấy FEFO khác FIFO ngay. Cần thêm ít nhất một ca **cùng mặt hàng, lô nhập sau nhưng hạn sớm hơn** để QA kiểm được. Lưu ý QA-report 2026-09-24 (Kịch bản B): đơn thật đã bị phân bổ vào lô demo. FEFO có thể làm việc này **thường hơn** nếu lô demo được đặt hạn ngắn (R-5).
- **Kiểm tra trước khi triển khai (việc cho Dev/QA):** đếm trên DB thật số cặp lô cùng mặt hàng, cùng đang bán, có thứ tự FIFO khác FEFO, để Duy biết ngay sau khi bật thì bao nhiêu đơn sẽ đổi lô.
- **Test hiện có sẽ đổi kỳ vọng:** `inventory/batches/tests/test_services.py::test_allocate_fifo_orders_by_received_date`. Test S1 (`test_s1_expiry`) giữ nguyên ý (lô quá hạn không được chọn).
- **Bên thứ 3:** không ảnh hưởng (SePay/adapter không biết lô).
- **Job:** `cancel_expired_orders`, `update_batch_status` không đổi.

## 8. Rủi ro Cá Về
| # | Nhóm | Rủi ro | Mức | Ghi chú / giảm thiểu |
|---|---|---|---|---|
| R-1 | Giá vốn / lãi lỗ | FEFO đổi **lô nào** bị trừ, nên đổi `unit_cost` trên bảng phân bổ, **đổi giá vốn hàng bán theo kỳ** và phân bổ lãi giữa các lô. Tổng giá vốn cả đời của một lô không đổi, nhưng lãi lỗ theo kỳ quanh ngày triển khai sẽ khác nếu tính giả định theo FIFO. Không được tính lại lịch sử: bảng phân bổ là append-only | Trung bình | Ghi ngày bật FEFO vào AuditLog/nhật ký triển khai để Chủ đối chiếu báo cáo kỳ. Không phân bổ lại đơn cũ (BR-BH-11) |
| R-2 | Rò giá vốn | Thêm cột hạn dùng / đổi thứ tự trên màn Kho & lô, Đơn **không** được kéo theo `landed_unit_cost`/`unit_cost` cho người thiếu `view_costprice` | Thấp | Test rò giá vốn hiện có phải chạy lại cho mọi màn bị sửa |
| R-3 | Hàng / chất lượng | FEFO **chủ động** đẩy lô sát hạn cho khách, kể cả lô hết hạn **hôm nay** (C1). Đơn đặt hôm nay có thể giao ngày mai, tức là khách nhận hàng **đã qua hạn nội bộ**. FIFO cũng có ca này nhưng hiếm hơn | Trung bình | Hạn nội bộ 90 ngày ngắn hơn nhiều so với hạn kỹ thuật cấp đông 6–12 tháng (decisions 09-09) nên chưa nguy hiểm về an toàn thực phẩm, nhưng là vấn đề uy tín. Xem Q3 (hạn còn lại tối thiểu) |
| R-4 | FIFO/tồn (vật lý) | Hệ thống chọn lô A nhưng NV kho lấy thùng lô B: sổ theo lô sai, lãi lỗ theo lô sai, và phải tới kiểm kê mới lộ | Trung bình | Hiện mã lô và hạn khi soạn hàng (UC-6). Kiểm kê theo lô hằng tuần (BR-KK-05) |
| R-5 | Dữ liệu demo | Lô demo hạn ngắn sẽ được FEFO ưu tiên, **hút đơn thật** vào lô demo mạnh hơn trước | Trung bình (chỉ khi demo còn trên prod) | Gỡ demo khỏi prod hoặc đặt demo hạn dài / mặt hàng riêng. Đưa vào kế hoạch QA |
| R-6 | Chứng từ / AuditLog | Không phát sinh chứng từ hay chuyển trạng thái mới, trừ khi Q2 = có chọn tay. Khi đó mỗi lần chọn tay phải có AuditLog (BR-PQ-04/05) và là quyền của Chủ | Thấp / Cao nếu Q2 = có | — |
| R-7 | Tài liệu lệch | Nhiều nơi (URD, spec, decisions, BUILD-PLAN, skill `caveve-domain` bất biến #6, UI) còn chữ FIFO. Người/agent sau đọc sẽ làm ngược lại | Trung bình | Danh sách sửa ở mục 9.1 |

## 9. Ngoài phạm vi
- Đổi cách **tính** hạn dùng (theo ngày đánh bắt/cấp đông/hạn nhà sản xuất thay cho ngày nhập + 90). FEFO dùng hạn hiện có của lô, xem Q5.
- Tự động giảm giá lô cận hạn (BR-LO-01 giữ nguyên: chỉ Chủ tạo giá mới).
- Cho khách chọn lô / xem hạn từng lô trên Shop.
- Phân bổ lại các đơn đã thanh toán hoặc đơn lịch sử.
- Quy tắc riêng cho hàng hoàn (vd ưu tiên xuất hàng hoàn trước): hàng hoàn đi theo hạn lô gốc.
- Chọn tay lô khi soạn hàng, **trừ khi** Duy chọn có ở Q2.

### 9.1 Tài liệu cần sửa sau khi Duy duyệt
| Tài liệu | Chỗ | Sửa thành |
|---|---|---|
| `doc/URD.md` §6.2 | "Xuất kho theo nguyên tắc lô nhập trước xuất trước (FIFO) khi bán" | "Xuất kho theo nguyên tắc **hết hạn trước xuất trước (FEFO)** khi bán: lô hạn dùng sớm nhất xuất trước; cùng hạn thì lô nhập trước" |
| `doc/URD.md` §9 Thuật ngữ | dòng "FIFO" | Thêm dòng "FEFO: First Expired, First Out, lô hết hạn trước xuất trước". Giữ FIFO chỉ như **tiêu chí phụ** khi cùng hạn, hoặc bỏ |
| `doc/business-process-spec.md` §3.1 | "Nổ ra thành phần, FIFO từng thành phần" | "…, FEFO từng thành phần" |
| `doc/business-process-spec.md` §7.3 | BR-BH-05 | Theo mục 6. Thêm BR-BH-11 |
| `doc/decisions.md` 2026-09-09 và 2026-09-10 | "Theo dõi theo ngày nhập lô là đủ", "trừ kho theo FIFO từng thành phần" | **Duy tự ghi** một mục quyết định mới 2026-09-26 "Xuất kho FEFO". BA không sửa file này |
| `doc/BUILD-PLAN.md` | contract `allocate_fifo`: "theo FIFO ngày nhập" | Mô tả theo FEFO (tên hàm do BE quyết) |
| `doc/doctype-mapping.md` | Sales Invoice "theo batch, FIFO" | Tài liệu đã lỗi thời. Sửa chữ khi viết lại |
| Ngoài `doc/` (điều phối viên chuyển tiếp) | `.claude/skills/caveve-domain/SKILL.md` bất biến #6 "Xuất kho theo FIFO lô"; `PRODUCT.md`; `README.md` gốc; README các app | "FEFO lô" |

## 10. Câu hỏi mở
| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q1 | 🔴 | Anh nói "**nếu** làm hàng đông lạnh". Vậy FEFO áp dụng cho **toàn bộ mặt hàng** hay chỉ nhóm đông lạnh? Cá Về có định bán hàng không đông lạnh (tươi sống, khô…) theo luật khác không? | Áp dụng **toàn bộ**, vì decisions 2026-09-09 ghi mọi hàng là đông lạnh. Không thêm cấu hình theo mặt hàng. Với hàng cùng hạn mặc định thì FEFO cho kết quả giống FIFO, nên áp toàn bộ không có hại |
| Q2 | 🔴 | Có cho phép **chọn tay một lô khác FEFO** không (vd Chủ muốn xả lô hạn dài có vấn đề chất lượng, hoặc NV kho lấy nhầm thùng rồi muốn sửa cho khớp)? Nếu có: ai được làm (chỉ Chủ?), ở bước nào (trước thanh toán hay lúc soạn hàng), có bắt ghi lý do không? | **Không** ở V1. FEFO bắt buộc, không ai sửa tay, vì sửa tay đổi con số lời lỗ theo lô (thuộc Chủ) và cần AuditLog. Nếu thật cần thì làm tính năng riêng, quyền Tầng 2 chỉ Chủ, bắt ghi lý do |
| Q3 | 🟡 | Có cần **hạn còn lại tối thiểu** khi bán không (vd lô còn < 2 ngày hạn thì không bán qua Shop nữa, để tránh khách nhận hàng qua hạn nội bộ, R-3)? | **Không** thêm ở tính năng này. Giữ C1 (bán tới hết ngày hạn), vì hạn nội bộ 90 ngày đã bảo thủ so với hạn kỹ thuật. Mở lại khi Lộc vận hành thật. Nếu có thì dùng tham số cấu hình (BR-LO-08) |
| Q4 | 🟡 | Đơn **đang giữ chỗ** lúc triển khai (phân bổ theo FIFO): giữ nguyên hay phân bổ lại theo FEFO? | **Giữ nguyên** (UC-4). TTL 30 phút tự dọn. Phân bổ lại đơn đang giữ có rủi ro tranh lô, không đáng làm. Đơn đã thanh toán tuyệt đối không động (BR-BH-11) |
| Q5 | 🟡 | Hạn dùng của lô có cần phản ánh **hạn thật của hàng** (ngày đánh bắt/cấp đông, hạn nhà sản xuất cho hàng nhập khẩu) thay vì luôn là ngày nhập + 90 không? FEFO chỉ có giá trị khi hạn lô khác nhau | **Ngoài phạm vi**. Giữ BR-MH-02 (sửa tay xuống khi hàng có hạn thật ngắn hơn). Đây là cách hiện có để ghi "hạn thật", và FEFO sẽ tôn trọng nó |
| Q6 | 🟡 | Anh xác nhận sẽ tự ghi quyết định mới vào `decisions.md` (thay câu "Theo dõi theo ngày nhập lô là đủ" ở mục 09-09 và "FIFO từng thành phần" ở mục combo 09-10)? | Có. Mục mới "2026-09-26: Xuất kho FEFO, [DUY CHỐT]". BA đề xuất nội dung theo mục 6 |
| Q7 | 🟡 | Khi hai lô **cùng hạn**, lô nhập trước ra trước (FIFO làm tiêu chí phụ). Anh đồng ý? | Đồng ý: cùng hạn thì ngày nhập sớm hơn trước, rồi lô tạo trước. Thứ tự luôn cố định, dễ kiểm thử |
| Q8 | 🟢 | Bảng "Tồn theo lô" (≤20 lô) ở Tổng quan chuyển sang sắp theo thứ tự xuất FEFO, nên tập 20 lô hiển thị có thể khác trước. Chấp nhận? | Chấp nhận. Hiển thị đúng thứ tự xuất quan trọng hơn giống bản cũ (tiền lệ L-12) |
| Q9 | 🟢 | Hiện mã lô **và hạn dùng** trên màn soạn hàng/chi tiết đơn cho NV kho (UC-6)? | Có. Chỉ thêm hạn, không thêm cột giá vốn |

---
## Quyết định của Duy (2026-09-26)
- **Q1:** FEFO áp dụng cho **toàn bộ mặt hàng**, không có cấu hình riêng theo mặt hàng.
- **Q2:** V1 **chưa cho chọn tay lô** khác FEFO. Nếu sau này cần thì làm tính năng riêng: chỉ Chủ được dùng, bắt ghi lý do, có AuditLog.
- **Q3–Q9:** áp dụng mặc định 🟡/🟢 như mục câu hỏi mở.
- **Q6:** điều phối viên đã ghi quyết định vào `doc/decisions.md`.
