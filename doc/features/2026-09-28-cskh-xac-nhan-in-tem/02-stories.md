# CSKH gọi xác nhận đơn → in tem → kho soạn hàng — User stories
> PO · 2026-09-28 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT, mục "Câu trả lời của Duy") · Tiền đề: S17, S19 của
> `2026-09-24-erp-console-noi-that/02-stories.md` · Trạng thái: **ĐÃ DUYỆT (Duy 28/09 — chốt scope qua câu hỏi)**

---

## Mục tiêu & thước đo

**Vì sao làm.** Hiện đơn vừa trả tiền là **ngay lập tức** vào danh sách soạn (signal tạo phiếu giao PREPARING). Kho có thể
soạn đơn sai địa chỉ, khách vắng nhà hoặc đổi ý. Hàng đông lạnh giao hỏng thì thành lỗ (BR-HV-03) cộng một lần hoàn tay
(P-07). Duy chốt: mọi đơn đã trả tiền phải được **người** (CSKH) gọi xác nhận trước, rồi kho mới soạn và in tem.

**Đo thành công bằng:**
1. **100%** phiếu giao tạo sau ngày deploy đi qua "Chờ xác nhận". Truy vấn: 0 phiếu có `created_at` ≥ ngày deploy ở
   Soạn hàng trở đi mà không có `confirmed_at` hoặc quyết định Quản lý (CS-04, CS-06, CS-07).
2. **0 đơn** "Cần quyết định" quá hạn Quản lý + 10 phút mà vẫn chưa huỷ, chưa được xử lý (CS-08, kiểm bằng truy vấn
   hằng tuần).
3. **100%** đơn tự huỷ có phiếu hoàn và nhắc việc gọi khách, và khách tra đơn thấy lý do + cách nhận hoàn (CS-08…CS-10).
4. **0** endpoint, tem, log hay AuditLog của hồ sơ này chứa dữ liệu cá nhân ngoài phạm vi, hoặc key giá vốn (bộ test X-AC).
5. Theo dõi (chưa đặt ngưỡng vì chưa vận hành thật): tỉ lệ phiếu FAILED với lý do `WRONG_ADDRESS`/`CUSTOMER_ABSENT`,
   thời gian từ thanh toán tới xác nhận. Báo cáo CSKH là Q-C18 (để sau).

## Phạm vi

**Trong:** Group `cskh` và phạm vi PII; bản tối thiểu của S17, S19 (tiền đề); trạng thái "Chờ xác nhận"; hàng chờ gọi,
ghi kết quả gọi, khoá mềm; không liên lạc được (3 lần/30') → Quản lý quyết định → tự huỷ sau 30'; phiếu hoàn + nhắc
việc gọi khách; thông báo khách trên Shop; tem 100×150 in tay từ trình duyệt; đổi địa chỉ/người nhận; in lại, huỷ tem;
khối "Cần chú ý" cho các việc mới; (Could) phiếu soạn in, quét tem, kịch bản gọi.

**Ngoài (Won't đợt này):** in tự động, trạm in kiosk, thiết bị kho lấy lệnh (đoạn C6, Q-C4). Vai trò tự định nghĩa.
AI gợi ý khi gọi và khối Tiếp theo/Đã làm (đoạn C9). Ghi âm, tổng đài ảo, SMS, Zalo ZNS. Hoàn kho một phần theo dòng.
CSKH tạo đơn thay khách. Bên vận chuyển ngoài. S18 (gán NV giao), S20–S24 của backlog cũ (vẫn nằm ở hồ sơ
`2026-09-24-erp-console-noi-that`, trừ phần tối thiểu của S24 trong CS-15).

---

## Quy ước chung (BE/FE/QA đọc một lần)

**Definition of Done:** test BE xanh (`manage.py test`), `erp-console` và `frontend` build tĩnh sạch, QA report
APPROVED, bộ X-AC dưới đây xanh, không rò giá vốn, không rò PII, doc cập nhật (BR mới vào `business-process-spec.md`;
Duy ghi `decisions.md`).

**Contract API:** giữ đúng quy ước của `2026-09-24-erp-console-noi-that/02-stories.md` (gốc `/api/`, token, lỗi 400
`{"detail","code"}`, 403 thiếu quyền, 404 ngoài phạm vi dòng, 409 `STALE_STATE`/`CLAIMED` khi xung đột, phân trang 20,
tiền/kg dạng chuỗi, `available_actions`). **Tên endpoint, field và trạng thái trong file này là dự kiến.** Tech Lead chốt
ở `02b-tech-design.md`. Nếu Tech Lead đổi tên thì cập nhật contract ở đây trước khi FE dựng mock.

**Dữ liệu mẫu trong contract là giả** (`Khách Thử A`, `0900000123`, `Số 1 Đường Thử`). Không dùng dữ liệu thật ở
test, ảnh QA hay commit (bất biến 9).

**Tên trạng thái dự kiến:** phiếu giao thêm `CONFIRMING` ("Chờ xác nhận", vừa `max_length=12` hiện có). Tình trạng
gọi `confirm_state` ∈ `PENDING` (chờ gọi) · `CALLBACK` (hẹn gọi lại) · `ESCALATED` ("Cần quyết định") ·
`REFUND_CALL` (đơn đã tự huỷ, cần gọi báo hoàn).

**Tham số mới (settings/env, bất biến 7):**

| Tên dự kiến | Mặc định | Nguồn |
|---|---|---|
| `CSKH_MAX_UNREACHABLE_ATTEMPTS` | 3 | Duy Q-C2 |
| `CSKH_UNREACHABLE_WINDOW_MINUTES` | 30 (tính từ lần "không liên lạc được" đầu tiên) | Duy Q-C2 |
| `CSKH_MIN_RETRY_MINUTES` | 10 (khoảng cách tối thiểu giữa hai lần gọi không được) | PO, để 3 lần nằm vừa 30' |
| `CSKH_MANAGER_DECISION_MINUTES` | 30 | Duy Q-C2 |
| `CSKH_PII_RECENT_DAYS` | 7 | Duy Q-C5 |
| `CSKH_CLAIM_MINUTES` | 5 (khoá mềm) | BA UC-CS-2 |
| `CSKH_EXTEND_MAX_HOURS` | 24 (Quản lý gia hạn tối đa) | BA UC-CS-5 (b) |
| `CSKH_WORKING_HOURS` | `"07:00-21:00"` (chỉ để hiển thị cho khách) | BA Q-C9 |
| `CSKH_QUEUE_ALERT_MINUTES` | 60 (đơn chờ chưa ai gọi) | PO |
| `LABEL_UNPRINTED_ALERT_MINUTES` | 15 | BA UC-CS-3 E4 |
| `REFUND_DEADLINE_DAYS` | 30 | `2026-09-28-ai-digital-worker/01c-phap-ly.md` |
| `SHOP_HOTLINE` | (chuỗi, Chủ đặt) | PO, để khách liên hệ khi đơn bị huỷ |

**Business rule áp dụng:** BR-GH-09 (sửa), BR-GH-10…BR-GH-12, BR-GH-14…BR-GH-20 như `01-analysis.md` §6.
**BR-GH-13 viết lại theo Duy** (thay bản BA):

> **BR-GH-13 (sửa 28/09).** CSKH gọi tối đa **N lần** (3) trong **W phút** (30) tính từ lần "không liên lạc được" đầu
> tiên, mỗi lần cách nhau ≥ **M phút** (10). Hết N lần, hết W phút, hoặc "sai số" → đơn sang **Cần quyết định** cho
> Quản lý/Chủ. Quản lý không quyết trong **D phút** (30) → **Hệ thống tự huỷ** đơn (hoàn kho về lô gốc, AuditLog actor
> = Hệ thống, lập phiếu hoàn toàn phần, tạo nhắc việc gọi khách). **Không** tự huỷ khi phiếu đã sang Soạn hàng trở đi,
> đơn đã huỷ, hoặc Quản lý đã quyết. N, W, M, D là tham số.

**Mã BR mới PO đề xuất:**

| Mã | Nội dung |
|---|---|
| **BR-HT-10** | Đơn bị **Hệ thống** tự huỷ theo BR-GH-13 thì Hệ thống lập **một** phiếu hoàn toàn phần `PENDING` ngay lúc huỷ (`created_by` = Hệ thống). Tiền chỉ rời túi khi **Chủ** `confirm_refund` (BR-HT-03). Hạn hoàn cho khách là `REFUND_DEADLINE_DAYS` kể từ lúc huỷ |
| **BR-GH-21** | Quyết định tự động bất lợi cho khách (tự huỷ) phải được **báo cho khách**: lý do, số tiền hoàn, trạng thái hoàn, hạn hoàn, cách liên hệ để phản hồi. Kênh V1: trang tra đơn trên Shop + cuộc gọi của nhân viên (không SMS/Zalo). Câu chữ do `legal-vn` duyệt (NĐ 356/2025). Shop phải báo **trước** luật gọi xác nhận/tự huỷ ở lúc đặt hàng |

---

## AC chung áp cho mọi story (QA chạy một lần cho cả hồ sơ, mã X-AC)

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| X-AC1 (PII log) | Dữ liệu giả có tên `Khách Thử PII`, SĐT `0900000999`, địa chỉ `Số 1 Đường Kiểm Thử`, ghi chú gọi có chữ `ghichu-bimat` | Chạy toàn bộ luồng CS-04…CS-14 (API + job) với `assertLogs` bắt **mọi** logger mức DEBUG | Không bản ghi log nào chứa 4 chuỗi trên. Log chỉ có mã đơn, mã phiếu, mã kết quả, SĐT đã che | Bất biến 9, BR-GH-19 |
| X-AC2 (AuditLog) | Như X-AC1 | Đọc mọi `AuditLog` sinh ra | `detail`/`changes`/`note` không chứa 4 chuỗi trên. Có đủ: ai (hoặc Hệ thống), hành động, đối tượng | BR-PQ-04, BR-GH-19 |
| X-AC3 (giá vốn) | Token **mọi Group** (kể cả `chu`) | Gọi mọi endpoint mới/sửa của hồ sơ (`/api/cskh/*`, `/label*`, chi tiết/danh sách phiếu giao, tra đơn Shop) | Không có key `unit_cost`, `purchase_rate`, `landed_unit_cost`, `rate`, `cost`, `profit`, `margin` ở bất kỳ độ sâu nào | Bất biến 1, BR-GH-10 |
| X-AC4 (FE lưu trữ) | Playwright chạy luồng CSKH, in tem, tra đơn Shop với dữ liệu X-AC1 | Sau luồng, đọc `localStorage`, `sessionStorage`, IndexedDB, danh sách URL request và console | Không nơi nào chứa tên, SĐT (đủ 10 số) hay địa chỉ. URL chỉ chứa id/mã phiếu/mã đơn | Bất biến 9 |
| X-AC5 (AI tắt) | `AI_ENABLED=false` | Chạy toàn bộ AC của CS-01…CS-18 | Tất cả đạt như khi bật. FE không gửi request nào tới `/api/ai/`. Khi `AI_ENABLED=true`, client AI (mock) được gọi **0 lần** trong mọi luồng của hồ sơ này | Bất biến 9, UC-CS-7 |
| X-AC6 (chứng từ) | Bản ghi cuộc gọi, lượt in tem, phiếu giao | `PATCH`/`PUT`/`DELETE` trực tiếp | 405, không đổi dữ liệu. Chỉ đổi qua action | BR-PQ-10, BR-GH-12 |
| X-AC7 (ma trận quyền) | Mỗi người thuộc đúng **một** Group, cộng một người không Group | Gọi từng endpoint ở bảng dưới | Đúng mã trả về từng ô. Người kiêm `nv_kho`+`cskh` được hợp hai cột | BR-PQ-09, BR-PQ-12 |

**Ma trận quyền (X-AC7).** ✓ = 2xx trong phạm vi · 403 · 404 = ngoài phạm vi dòng.

| Endpoint | `chu` | `quan_ly` | `nv_kho` | `nv_giao` | `cskh` | không Group |
|---|---|---|---|---|---|---|
| `GET /api/cskh/queue/`, chi tiết, `claim`, `POST /api/cskh/search` | ✓ | ✓ | 403 | 403 | ✓ (phạm vi BR-GH-18) | 403 |
| `POST /api/cskh/queue/{id}/calls` | ✓ | ✓ | 403 | 403 | ✓ / 404 ngoài phạm vi | 403 |
| `POST /api/cskh/queue/{id}/recipient` | ✓ | ✓ | 403 | 403 | ✓ / 404 | 403 |
| `POST /api/cskh/queue/{id}/decide` | ✓ | ✓ | 403 | 403 | 403 | 403 |
| `GET /api/delivery/notes/` (bảng điều phối) | ✓ | ✓ | ✓ | ✓ chỉ phiếu của mình | 403 | 403 |
| `POST /api/delivery/notes/{id}/status` → READY | ✓ | ✓ | ✓ | 403 | 403 | 403 |
| `GET …/label`, `POST …/label/print`, `POST …/label/void` | ✓ | ✓ | ✓ | 403 | 403 | 403 |
| `GET /api/sales/orders/` | ✓ | ✓ | ✓ | chỉ đơn của mình (S5) | chỉ phạm vi BR-GH-18 | 403 |
| `POST /api/sales/orders/{id}/cancel`, `POST /api/sales/refunds/create` | ✓ | ✓ | 403 | 403 | 403 | 403 |
| `POST /api/sales/refunds/{id}/confirm` | ✓ | 403 | 403 | 403 | 403 | 403 |
| `GET /api/inventory/batches/`, `/api/reports/*` | như hiện nay | như hiện nay | như hiện nay | như hiện nay | 403 | 403 |

---

# LÔ 1 — Nền: Group CSKH + tiền đề màn Giao hàng

## CS-01 — Group `cskh` và phạm vi xem dữ liệu khách · Must · BE
**Là** Chủ vựa, **tôi muốn** có nhóm "CSKH" chỉ thấy tên, SĐT, địa chỉ của những đơn đang cần gọi và đơn chính họ vừa
gọi, **để** nhân viên gọi điện làm được việc mà không xem được toàn bộ khách của vựa.
Bối cảnh: Q-C5 (Duy chọn Group thứ năm, cộng dồn), BR-GH-18, bất biến 9. Đổi quyết định 10/09 "bốn Group" → Duy ghi
`decisions.md`. Chủ gán Group qua màn Nhân sự đã có (`manage_staff`).
Why Must: không có vai này thì phải cho người gọi điện Group `quan_ly` (thấy mọi khách, huỷ được đơn).

**Contract**
```
Data migration: Group "cskh" + quyền dự kiến
  sales.view_salesorder (T1, lọc T3), delivery.confirm_with_customer (T2 mới: ghi kết quả gọi),
  delivery.change_recipient (T2 mới: đổi thông tin nhận)
  Gán thêm 2 quyền T2 mới cho quan_ly, chu. Quyền T2 mới delivery.decide_unconfirmed chỉ cho quan_ly, chu.
GET /api/auth/me/   (người chỉ thuộc cskh)
200 {"groups": ["cskh"], "group_labels": [{"code": "cskh", "label": "CSKH"}], "home": "cskh-queue",
     "can_view_cost": false, "can_view_profit": false, ...}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-01-AC1 | DB chưa có Group `cskh` | Chạy migrate, rồi chạy lại lần 2 | Có đúng 1 Group `cskh` với đúng danh sách quyền ở contract. Lần 2 không đổi gì | BR-PQ-01 |
| CS-01-AC2 | `cs1` chỉ thuộc `cskh` | `GET /api/auth/me/` | `home = "cskh-queue"`, `can_view_cost = false`, nhãn "CSKH" | BR-PQ-09 |
| CS-01-AC3 | Đơn D1 phiếu `CONFIRMING`/`PENDING`; D2 phiếu `CONFIRMING`/`ESCALATED`; D3 phiếu READY chưa ai gọi; D4 phiếu PREPARING, `cs1` đã gọi 2 ngày trước | `cs1` gọi `GET /api/sales/orders/` | Có D1, D2, D4, **không** có D3 | BR-GH-18 |
| CS-01-AC4 (quyền) | Như AC3 | `cs1` gọi `GET /api/sales/orders/{D3}/` hoặc `GET /api/sales/customers/{khách D3}/` | 404 | BR-GH-18, BR-PQ-12 |
| CS-01-AC5 | `cs1` gọi D5 cách đây 8 ngày, D5 đã PREPARING | `cs1` xem chi tiết D5; rồi đặt `CSKH_PII_RECENT_DAYS=10` và xem lại | Lần 1: 404. Lần 2: 200 | BR-GH-18, bất biến 7 |
| CS-01-AC6 (quyền) | `cs2` gọi D6 hôm qua, D6 nay PREPARING, `cs1` chưa từng gọi D6 | `cs1` xem D6 | 404 (phạm vi "mình đã gọi" tính theo người) | BR-GH-18 |
| CS-01-AC7 (quyền) | `cs1` | Gọi các endpoint hàng 5, 6, 7, 9, 10, 11 của ma trận X-AC7 | Đúng như ma trận (403) | BR-PQ-12 |
| CS-01-AC8 (quyền) | Quản lý | Gán Group `cskh` cho nhân viên qua màn Nhân sự | 403 (chỉ Chủ có `manage_staff`). Chủ gán được, có AuditLog | BR-PQ-02 |

## CS-02 — [Tiền đề S17, thu gọn] Bảng phiếu giao theo trạng thái · Must · BE+FE · cả hai thiết bị
**Là** NV kho / Quản lý / Chủ vựa, **tôi muốn** thấy mọi phiếu giao theo nhóm trạng thái, kèm dòng hàng tóm tắt và
tình trạng tem, **để** biết phiếu nào cần soạn, phiếu nào còn chờ gọi.
Bối cảnh: **Nguồn S17** (`2026-09-24-erp-console-noi-that`), chỉ lấy S17-AC1, AC5 và thêm nhóm "Chờ xác nhận", cột tem.
Bỏ lọc `assigned_to` và `needs_decision` của giao thất bại (thuộc S18/S21, vẫn ở backlog cũ). Màn
`erp-console/app/(console)/deliveries/page.tsx` đang là Placeholder (đã kiểm 28/09).

**Contract**
```
GET /api/delivery/notes/?status=CONFIRMING,PREPARING,READY,DELIVERING,FAILED&page=1
200 {"count": 3, "results": [
  {"id": 31, "code": "GH-HD-0001-AB12C", "status": "PREPARING", "status_label": "Soạn hàng",
   "order": {"id": 101, "code": "DH-260928-0001"}, "paid_at": "2026-09-28T08:05:00+07:00",
   "confirmed_at": "2026-09-28T08:20:00+07:00", "lines_summary": "Tôm sú L1 2,000 kg · Mực lá 1,000 kg",
   "total_kg": "3.000", "label": {"printed": false, "valid_print_no": null, "needs_void": 0},
   "customer_name": "Khách Thử A", "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng",
   "available_actions": ["set_status:READY", "print_label"]}]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-02-AC1 | Có phiếu ở đủ 7 trạng thái (kể cả CONFIRMING, CANCELLED) | NV kho mở Giao hàng | Nhóm theo thứ tự Chờ xác nhận → Soạn hàng → Chờ lấy → Đang giao → Thất bại → Hoàn tất (hôm nay). Không có CANCELLED | UC-08, BR-GH-11 |
| CS-02-AC2 | Phiếu PREPARING chưa in tem | Mở bảng | Dòng có nhãn "Chưa in tem"; nhóm Soạn hàng xếp `confirmed_at` cũ nhất lên đầu | BR-GH-09 (sửa) |
| CS-02-AC3 | Phiếu CONFIRMING | NV kho xem dòng | `available_actions` rỗng, không có nút soạn/in | BR-GH-11 |
| CS-02-AC4 (quyền) | `giao1` chỉ thuộc `nv_giao` | `GET /api/delivery/notes/` | Chỉ phiếu gán `giao1`; menu "Giao hàng (điều phối)" không hiện | BR-GH-06 |
| CS-02-AC5 (quyền) | `cs1` chỉ thuộc `cskh` | `GET /api/delivery/notes/` | 403; menu không hiện | BR-GH-18 |
| CS-02-AC6 (mobile) | 360×640 | Mở bảng | Không cuộn ngang; mỗi nhóm là danh sách thẻ; vùng bấm ≥ 44 px | Quy ước mobile |
| CS-02-AC7 (giá vốn) | NV kho | Gọi danh sách | Không có key giá vốn (X-AC3); không có giá bán từng dòng | BR-PQ-15 |

## CS-03 — [Tiền đề S19, thu gọn] Chi tiết phiếu soạn và "Đã đóng gói" · Must · BE+FE · ưu tiên điện thoại
**Là** NV kho, **tôi muốn** mở phiếu thấy dòng hàng, số kg, lô cần lấy và hạn dùng, rồi bấm "Đã đóng gói", **để** lấy
đúng lô FEFO đã chốt và báo hàng sẵn sàng.
Bối cảnh: **Nguồn S19** (`2026-09-24-erp-console-noi-that`), giữ S19-AC1…AC6, thêm hạn dùng lô (UC-CS-8 bước 2). Service
`advance_status` hiện **chưa** nhận `from_status` và chưa trả `already` (đã kiểm 28/09), và chưa chặn `nv_giao` soạn.

**Contract** (như S19, thêm `expiry_date`)
```
GET /api/delivery/notes/31/
200 {"id": 31, "code": "GH-HD-0001-AB12C", "status": "PREPARING", ...,
  "lines": [{"item_name": "Tôm sú loại 1", "qty_kg": "2.000", "batch_id": "TOM-SU-1-260920-AB12C", "expiry_date": "2027-09-20"}],
  "available_actions": ["set_status:READY", "print_label"]}
POST /api/delivery/notes/31/status   {"to_status": "READY", "from_status": "PREPARING"}
200 {"status": "READY", "already": false}  |  200 {"status": "READY", "already": true}
400 {"code": "STALE_STATE", "detail": "Phiếu đang ở Đang giao, tải lại để xem.", "current_status": "DELIVERING"}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ, không soạn."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-03-AC1 | Phiếu PREPARING, đơn 2 kg từ lô L (hạn 20/09/2027) | NV kho mở chi tiết | Thấy dòng "Tôm sú loại 1 · 2,000 kg · lô L · HSD 20/09/2027", đúng bảng phân bổ đã chốt lúc đặt | BR-BH-06, BR-BH-11 |
| CS-03-AC2 | Phiếu PREPARING | Bấm "Đã đóng gói" | READY, 1 AuditLog | BR-GH-03 |
| CS-03-AC3 (lỗi mạng) | Lần 1 đã ghi, FE không nhận phản hồi | Gửi lại cùng `from_status=PREPARING` | `already: true`, vẫn READY, **không** có AuditLog thứ hai | UC-09 E2 |
| CS-03-AC4 (lỗi) | Phiếu PREPARING | `to_status=COMPLETED` | 400 `BR-GH-05` | BR-GH-05 |
| CS-03-AC5 (lỗi) | Phiếu CANCELLED | Bất kỳ `to_status` | 400 `BR-GH-07`; FE hiện "Đơn đã huỷ, không soạn" | BR-GH-07 |
| CS-03-AC6 (quyền) | `giao1` được gán phiếu PREPARING | PREPARING → READY | 403 | UC-09 |
| CS-03-AC7 (quyền) | `cs1` | `GET /api/delivery/notes/31/` | 403 | BR-GH-18 |
| CS-03-AC8 (giá vốn) | NV kho | Chi tiết phiếu | Không key giá vốn/đơn giá mua | BR-PQ-15 |

---

# LÔ 2 — Luồng xác nhận chạy được sớm nhất (bước gọi + tem in tay)

## CS-04 — Đơn đã trả tiền vào "Chờ xác nhận", kho chưa soạn được · Must · BE
**Là** Chủ vựa, **tôi muốn** mọi đơn vừa trả đủ tiền dừng ở "Chờ xác nhận" thay vì vào thẳng danh sách soạn, **để** kho
chỉ soạn đơn đã gọi khách xác nhận.
Bối cảnh: Q-C1 (a), BR-GH-11, UC-CS-1. `issue_invoice` giữ nguyên (trừ kho, ghi doanh thu, đơn PROCESSING). Chỉ đổi trạng
thái đầu của phiếu giao tạo trong signal. Sửa chuỗi trạng thái của quyết định 10/09 → Duy ghi `decisions.md`.
**Schema:** thêm `CONFIRMING` vào `DeliveryNote.Status` + các field tình trạng gọi (Tech Lead chọn chỗ đặt) + migration.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-04-AC1 | Đơn BOOKED 2 kg lô L | IPN `ORDER_PAID` đủ tiền | Đơn PROCESSING, hoá đơn ISSUED, tồn L −2 kg, doanh thu ghi như cũ; phiếu giao `CONFIRMING`, `confirm_state=PENDING` | BR-GH-11, BR-TT-06 |
| CS-04-AC2 | Đơn BOOKED | Chủ xác nhận tay (S11), và riêng một đơn qua hàng chờ lệch (S12) | Cả hai phiếu đều `CONFIRMING` | UC-CS-1 |
| CS-04-AC3 (trùng) | Đơn đã PROCESSING | IPN gửi lại lần 2 | Vẫn đúng 1 phiếu giao, 1 mục chờ | BR-TT-03 |
| CS-04-AC4 (lỗi) | Phiếu `CONFIRMING` | `POST …/status` với `to_status` = PREPARING hoặc READY | 400 `BR-GH-11` "Chưa xác nhận với khách". Phiếu không đổi | BR-GH-11 |
| CS-04-AC5 | Phiếu `CONFIRMING` | Quản lý huỷ đơn (S14) | Đơn CANCELLED, kho cộng lại đúng lô gốc (ledger `CANCEL_RESTORE`), phiếu CANCELLED | BR-HT-05, BR-GH-07 |
| CS-04-AC6 | Phiếu `CONFIRMING` 3 ngày | So bảng phân bổ lô trước/sau | Không đổi (không chọn lại lô) | BR-BH-11 |
| CS-04-AC7 (migration) | DB có phiếu PREPARING/READY tạo trước deploy | Chạy migrate | Không phiếu cũ nào bị chuyển sang `CONFIRMING` | Bất biến 8 |
| CS-04-AC8 (quyền) | `giao1` | `GET /api/delivery/notes/` khi có phiếu CONFIRMING chưa gán | Không thấy | BR-GH-06 |

## CS-05 — Hàng chờ gọi của CSKH · Must · BE+FE · ưu tiên điện thoại
**Là** NV CSKH, **tôi muốn** mở điện thoại là thấy danh sách đơn cần gọi, cũ nhất lên đầu, bấm một chạm để gọi, và
biết đơn nào người khác đang gọi, **để** không bỏ sót đơn và không gọi trùng khách.
Bối cảnh: UC-CS-2 bước 1–2, khoá mềm, tìm đơn khi khách gọi ngược (3a). Tìm theo SĐT gửi trong **body** (không để SĐT
lên URL, bất biến 9).

**Contract**
```
GET /api/cskh/queue/?state=PENDING|CALLBACK|ESCALATED|REFUND_CALL&page=1     (mặc định: PENDING + CALLBACK đã tới giờ)
200 {"count": 2, "results": [
  {"note_id": 31, "order_code": "DH-260928-0001", "paid_at": "2026-09-28T08:05:00+07:00",
   "confirm_state": "PENDING", "attempts": 1, "next_call_after": "2026-09-28T09:10:00+07:00",
   "window_ends_at": "2026-09-28T09:30:00+07:00", "callback_at": null, "decide_deadline": null,
   "customer_name": "Khách Thử A", "phone": "0900000123", "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng",
   "lines_summary": "Tôm sú L1 2,000 kg", "total_amount": "540000",
   "claimed_by": null, "claimed_until": null}]}
GET /api/cskh/queue/31/
200 {... như trên, "recipient_name": null, "recipient_phone": null,
     "calls": [{"at": "...", "by": "cs1", "result": "UNREACHABLE", "result_label": "Không nghe máy", "note": ""}],
     "available_actions": ["claim", "call:CONFIRMED", "call:UNREACHABLE", "call:WRONG_NUMBER", "call:CALLBACK",
                           "call:WANT_CHANGE", "call:WANT_CANCEL", "change_recipient"]}
POST /api/cskh/queue/31/claim  {}  → 200 {"claimed_by": "cs1", "claimed_until": "..."}
409 {"code": "CLAIMED", "detail": "Đơn đang được cs2 xử lý tới 09:14.", "claimed_until": "..."}
POST /api/cskh/search  {"q": "0900000123"}      // hoặc mã đơn; KHÔNG có GET ?q=
200 {"results": [{"note_id": 31, "order_code": "DH-…", "in_scope": true, "phone": "0900000123", "customer_name": "Khách Thử A", "status_label": "Chờ xác nhận"},
                 {"note_id": 12, "order_code": "DH-…", "in_scope": false, "phone_masked": "09xx xxx 123", "status_label": "Đang giao"}]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-05-AC1 | 3 phiếu PENDING trả tiền lúc 08:00, 08:10, 08:05 | `cs1` mở hàng chờ | Thứ tự 08:00 → 08:05 → 08:10; mỗi dòng có mã đơn, giờ trả, dòng hàng, số lần đã gọi, tên, SĐT | UC-CS-1 bước 3 |
| CS-05-AC2 | Phiếu `CALLBACK` hẹn 10:00 | Mở mặc định lúc 09:50 / lúc 10:00 | 09:50: không có. 10:00: có, gắn "Hẹn gọi lại 10:00". Lọc `state=CALLBACK` lúc 09:50 thì thấy | UC-CS-2 bước 4 |
| CS-05-AC3 (khoá mềm) | `cs1` vừa `claim` phiếu 31 | `cs2` mở chi tiết rồi gửi `claim` hoặc `calls` | Chi tiết hiện "Đang được cs1 xử lý tới hh:mm", nút kết quả tắt; API 409 `CLAIMED` | UC-CS-2 bước 1 |
| CS-05-AC4 | Như AC3, đã qua `CSKH_CLAIM_MINUTES` | `cs2` `claim` | 200, `claimed_by = cs2` | Bất biến 7 |
| CS-05-AC5 (tìm) | Phiếu 31 trong phạm vi `cs1`, phiếu 12 (READY, `cs1` chưa gọi) cùng SĐT | `POST /api/cskh/search` với SĐT | 31 đủ thông tin; 12 chỉ có mã đơn, trạng thái, `phone_masked`, **không** có tên và địa chỉ | BR-GH-18, bất biến 9 |
| CS-05-AC6 (lỗi) | — | `GET /api/cskh/search?q=0900000123` | 405. FE không bao giờ đặt SĐT/tên vào URL | Bất biến 9 |
| CS-05-AC7 (lỗi) | `cs1` đang mở chi tiết phiếu 31 | Quản lý huỷ đơn (S14) rồi `cs1` tải lại | Chi tiết hiện "Đơn đã huỷ", không còn nút kết quả; phiếu rời hàng chờ | BR-GH-07 |
| CS-05-AC8 (mobile) | 360×640 | Mở hàng chờ và chi tiết | SĐT là link `tel:`; không cuộn ngang; nút kết quả cao ≥ 44 px, nằm trong 1/2 dưới màn hình | Quy ước mobile |
| CS-05-AC9 (quyền) | `kho1` chỉ `nv_kho`; `giao1` chỉ `nv_giao` | Gọi `GET /api/cskh/queue/` | 403; menu "Gọi xác nhận" không hiện | BR-GH-18 |

## CS-06 — Ghi kết quả cuộc gọi; "Đã xác nhận" chuyển sang Soạn hàng · Must · BE+FE
**Là** NV CSKH, **tôi muốn** chọn kết quả cuộc gọi từ danh sách cố định, kèm ghi chú ngắn, **để** đơn đã xác nhận vào
ngay danh sách soạn của kho và mọi lần gọi đều có dấu vết.
Bối cảnh: UC-CS-2 bước 4–5, 4a, E1–E3; BR-GH-12, BR-GH-19. Bản ghi cuộc gọi append-only. Kết quả `CONFIRMED_CHANGED`
mở ở CS-12; `WANT_CHANGE`/`WANT_CANCEL` xử lý tiếp ở CS-13; `UNREACHABLE`/`WRONG_NUMBER` ở CS-07. Story này ghi được
**mọi** mã (bản ghi + trạng thái tối thiểu), riêng hệ quả chuyển trạng thái của `CONFIRMED` và `CALLBACK` nằm ở đây.

**Contract**
```
POST /api/cskh/queue/31/calls
{"result": "CONFIRMED", "note": "Giao sau 17h", "callback_at": null, "request_id": "0b6e…uuid"}
   // result ∈ CONFIRMED | CONFIRMED_CHANGED | UNREACHABLE | WRONG_NUMBER | CALLBACK | WANT_CHANGE | WANT_CANCEL
201 {"call_id": 77, "note_status": "PREPARING", "confirm_state": null, "duplicate": false}
200 {"call_id": 77, ..., "duplicate": true}                          // cùng request_id
409 {"code": "STALE_STATE", "detail": "Đơn vừa được xác nhận bởi người khác.", "current_status": "PREPARING"}
400 {"code": "BR-GH-19", "detail": "Không ghi SĐT hay số tài khoản vào ghi chú."}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ."}
POST /api/cskh/queue/31/unconfirm  {"reason": "Bấm nhầm đơn"}   → 200 {"note_status": "CONFIRMING"}
400 {"code": "BR-GH-16", "detail": "Tem đã in — nhờ Quản lý xử lý."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-06-AC1 | Phiếu 31 `CONFIRMING`, `cs1` đã claim | Ghi `CONFIRMED` | 1 bản ghi gọi (ai, lúc, kết quả, ghi chú); phiếu → PREPARING, lưu `confirmed_at/by`; 1 AuditLog `delivery_confirmed` actor `cs1`; phiếu hiện ở CS-02 nhóm Soạn hàng với "Chưa in tem" | BR-GH-11, BR-GH-12, BR-GH-09 (sửa) |
| CS-06-AC2 (trùng) | AC1 đã ghi, FE không nhận phản hồi | Gửi lại cùng `request_id` | 200 `duplicate: true`; vẫn 1 bản ghi, 1 AuditLog | UC-CS-2 E3 |
| CS-06-AC3 (xung đột) | `cs2` đã xác nhận phiếu 31 (khoá đã hết) | `cs1` gửi `CONFIRMED` với `request_id` khác | 409 `STALE_STATE`, không thêm bản ghi | UC-CS-2 E1 |
| CS-06-AC4 | Phiếu `PENDING` | Ghi `CALLBACK` với `callback_at` = +2 giờ | `confirm_state=CALLBACK`, `attempts` **không** tăng; rời hàng chờ mặc định tới giờ hẹn | UC-CS-2 bước 4 |
| CS-06-AC5 (lỗi) | — | `CALLBACK` với `callback_at` ở quá khứ hoặc thiếu | 400 | |
| CS-06-AC6 (lỗi PII) | — | `note` có chuỗi ≥ 9 chữ số liên tiếp (bỏ qua khoảng trắng, dấu chấm, gạch), hoặc dài > 200 ký tự | 400 `BR-GH-19`; không ghi | BR-GH-19, bất biến 9 |
| CS-06-AC7 (lỗi) | Đơn đã CANCELLED | Ghi bất kỳ kết quả | 400 `BR-GH-07` | BR-GH-07 |
| CS-06-AC8 (huỷ xác nhận) | Phiếu PREPARING do `cs1` xác nhận, chưa in tem | `cs1` gọi `unconfirm` có lý do | Phiếu → `CONFIRMING`/`PENDING`; AuditLog. Nếu tem đã in: 400 `BR-GH-16` | UC-CS-2 4a |
| CS-06-AC9 (lịch sử) | Phiếu có 3 lần gọi | Mở chi tiết | Hiện 3 dòng mới nhất trước: giờ, nhãn kết quả, người gọi, ghi chú | BR-GH-12 |
| CS-06-AC10 (quyền) | `kho1`; `cs1` với phiếu ngoài phạm vi (READY, chưa từng gọi) | Ghi kết quả | `kho1`: 403. `cs1`: 404 | BR-GH-18 |

## CS-11 — Tem giao khổ 100×150 in tay từ trình duyệt, chỉ sau khi xác nhận · Must · BE+FE
*(Mã CS-11 giữ theo nhóm tem; làm trong Lô 2 vì kho cần tem ngay khi có bước xác nhận.)*
**Là** NV kho, **tôi muốn** bấm "In tem" trên phiếu đã xác nhận để ra tem 100×150 dán thùng, **để** thùng hàng có đủ
thông tin giao mà không lộ giá hay SĐT đầy đủ.
Bối cảnh: Q-C4 (chưa có máy in, V1 in tay), Q-C6 (nội dung tem theo BA, **chờ `legal-vn`** về ghi nhãn hàng hoá),
BR-GH-09 (sửa), BR-GH-10, BR-GH-16. FE gọi `print` (ghi lượt in) rồi mở trang in `/deliveries/31/label` và gọi
`window.print()`. Trang in có `@page { size: 100mm 150mm }`.

**Contract**
```
GET /api/delivery/notes/31/label
200 {"note_code": "GH-HD-0001-AB12C", "order_code": "DH-260928-0001", "next_print_no": 1,
     "barcode_value": "GH-HD-0001-AB12C.1",
     "recipient_name": "Khách Thử A", "recipient_phone_masked": "09xx xxx 123",
     "address": "Số 1 Đường Thử, P. Thử, Lâm Đồng", "packages": "1/1", "total_kg": "3.000",
     "earliest_expiry": "2027-09-20", "paid_text": "ĐÃ THANH TOÁN – không thu thêm"}
POST /api/delivery/notes/31/label/print  {"request_id": "…uuid"}
201 {"print_no": 1, "printed_at": "...", "is_reprint": false, "duplicate": false}
400 {"code": "BR-GH-09", "detail": "Chưa xác nhận với khách, chưa in tem."}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ, không in tem."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-11-AC1 | Phiếu PREPARING đã xác nhận | NV kho bấm "In tem" | `print_no=1`; 1 AuditLog `label_printed` (chỉ mã phiếu + số lần in); nhãn "Chưa in tem" ở CS-02 biến mất; hộp thoại in của trình duyệt mở | BR-GH-09 (sửa) |
| CS-11-AC2 (lỗi) | Phiếu `CONFIRMING` | `GET label` hoặc `POST print` | 400 `BR-GH-09`; FE không hiện nút In | BR-GH-09 (sửa), BR-GH-11 |
| CS-11-AC3 (lỗi) | Phiếu CANCELLED | `POST print` | 400 `BR-GH-07` | BR-GH-07 |
| CS-11-AC4 (không tiền) | Đơn tổng 540.000đ | Đọc JSON `label` và text DOM trang in | Không có key `total_amount`, `price`, `amount`; text trang in không chứa "540.000" hay "540000"; có dòng "ĐÃ THANH TOÁN – không thu thêm" | BR-GH-10, X-AC3 |
| CS-11-AC5 (PII) | SĐT nhận `0900000123` | Đọc JSON và DOM trang in | Chỉ có `09xx xxx 123`; chuỗi `0900000123` không xuất hiện | BR-GH-18, bất biến 9 |
| CS-11-AC6 (khổ in) | Địa chỉ dài 250 ký tự, 5 dòng hàng | Playwright `page.pdf({preferCSSPageSize: true})` trang in | PDF đúng **1 trang**, kích thước 100×150 mm (±1 mm) | Q-C4 |
| CS-11-AC7 (mã vạch) | Như AC1 | Giải mã mã vạch/QR trên trang in | Ra đúng `GH-HD-0001-AB12C.1`, không chứa SĐT, tên hay URL | BR-GH-16, §7.3 ý 3 |
| CS-11-AC8 (trùng) | Đã in với `request_id=R` | Gửi lại `R` | 200 `duplicate: true`, vẫn `print_no=1` | UC-CS-3 E1 |
| CS-11-AC9 (quyền) | `cs1`; `giao1` | `GET label` / `POST print` | 403 | BR-GH-10 |

---

# LÔ 3 — Không liên lạc được, tự huỷ, báo khách (lên production cùng nhau)

> **Ràng buộc phát hành:** CS-07, CS-08, CS-09, CS-10 lên **production cùng một lần**. Không bật job tự huỷ (CS-08)
> khi Shop chưa báo trước luật gọi/tự huỷ và chưa hiện lý do huỷ cho khách (CS-10, BR-GH-21), và khi nội dung chưa
> qua `legal-vn`.

## CS-07 — Không liên lạc được: 3 lần trong 30 phút rồi chuyển Quản lý quyết định · Must · BE+FE
**Là** Quản lý, **tôi muốn** đơn gọi 3 lần trong 30 phút không được sẽ tự chuyển sang "Cần quyết định" cho tôi, với ba
lựa chọn giao luôn / gia hạn / huỷ, **để** không đơn đã trả tiền nào nằm chờ mà không ai biết.
Bối cảnh: Q-C2 (Duy), BR-GH-13 (sửa), UC-CS-5. Chuyển "Cần quyết định" do lúc ghi lần gọi thứ N **hoặc** do job định kỳ
(Cloud Scheduler, cùng cơ chế `cancel_expired_orders`, chạy mỗi 5 phút) khi hết cửa sổ W phút.

**Contract**
```
POST /api/cskh/queue/31/decide
{"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "Khách quen, địa chỉ đã giao 2 lần"}
{"decision": "EXTEND", "until": "2026-09-28T17:00:00+07:00", "reason": "Khách nhắn đang họp"}
{"decision": "CANCEL", "reason_code": "UNREACHABLE", "note": ""}
200 {"note_status": "PREPARING"|"CONFIRMING"|"CANCELLED", "confirm_state": null|"CALLBACK", "suggest_refund_amount": "540000"}
400 {"code": "BR-GH-13", "detail": "Chưa đủ 10 phút kể từ lần gọi trước."}              // từ POST calls
409 {"code": "STALE_STATE", "detail": "Đơn đã được xử lý.", "current_status": "CANCELLED"}
403 thiếu delivery.decide_unconfirmed
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-07-AC1 | Phiếu `PENDING`, `attempts=0` | 09:00 `cs1` ghi `UNREACHABLE` | `attempts=1`, `next_call_after=09:10`, `window_ends_at=09:30`, vẫn `PENDING` | BR-GH-13 |
| CS-07-AC2 (lỗi) | Như AC1 | 09:05 ghi `UNREACHABLE` | 400 `BR-GH-13`, `attempts` giữ 1 | BR-GH-13 |
| CS-07-AC3 | `attempts=2` (09:00, 09:12) | 09:25 ghi `UNREACHABLE` | `attempts=3`, `confirm_state=ESCALATED`, `escalated_at=09:25`, `decide_deadline=09:55`; hiện trong lọc "Cần quyết định" của Quản lý | BR-GH-13 |
| CS-07-AC4 | `attempts=1` lúc 09:00, không gọi thêm | Job chạy 09:31 | `ESCALATED`, `escalated_at=09:31`, `decide_deadline=10:01`. Job chạy lại lần 2: không đổi, không thêm AuditLog | BR-GH-13, bất biến 6 (idempotent) |
| CS-07-AC5 | Phiếu `PENDING` | Ghi `WRONG_NUMBER` | `ESCALATED` ngay | UC-CS-5 E1 |
| CS-07-AC6 | `CSKH_MAX_UNREACHABLE_ATTEMPTS=2` | Ghi `UNREACHABLE` lần 2 (đủ khoảng cách) | `ESCALATED` | Bất biến 7 |
| CS-07-AC7 | Phiếu `CALLBACK` (khách đã nghe máy, hẹn lại) | Qua 30 phút, job chạy | Không đổi. `CALLBACK` không tính là lần không liên lạc được | BR-GH-13 |
| CS-07-AC8 | Phiếu `ESCALATED` | Quản lý chọn `DELIVER_WITHOUT_CONFIRM` có lý do | Phiếu → PREPARING, `decide_deadline` xoá, AuditLog `delivery_confirm_skipped` actor Quản lý | UC-CS-5 (a) |
| CS-07-AC9 | Phiếu `ESCALATED` | Quản lý chọn `EXTEND` tới +3 giờ | `confirm_state=CALLBACK`, `callback_at=until`, `attempts=0`, `decide_deadline` xoá; AuditLog | UC-CS-5 (b) |
| CS-07-AC10 (lỗi) | — | `EXTEND` vượt `CSKH_EXTEND_MAX_HOURS`, hoặc thiếu `reason` ở `DELIVER_WITHOUT_CONFIRM` | 400 | Bất biến 7 |
| CS-07-AC11 | Phiếu `ESCALATED` | Quản lý chọn `CANCEL` | Như S14: đơn CANCELLED, hoàn kho đúng lô gốc, phiếu CANCELLED; FE mở ngay form phiếu hoàn (S15) điền sẵn toàn phần | BR-HT-05, UC-CS-5 (c) |
| CS-07-AC12 (quyền) | `cs1`; `kho1` | `POST decide` | 403 | BR-PQ, ranh giới Quản lý |

## CS-08 — Hệ thống tự huỷ khi Quản lý không xử lý trong 30 phút · Must · BE
**Là** Chủ vựa, **tôi muốn** đơn đã chuyển Quản lý mà 30 phút không ai quyết thì hệ thống tự huỷ, trả hàng về kho và
ghi nợ hoàn cho khách, **để** hàng không bị giữ vô thời hạn và khách được hoàn tiền mà không ai phải nhớ.
Bối cảnh: Q-C2 nguyên văn "ko giải quyết trong 30' sẽ tự hủy". BR-GH-13 (sửa), BR-HT-10 (mới). Job
`cancel_unresolved_unconfirmed` chạy cùng job ở CS-07-AC4, gọi đúng service huỷ của S14 với `actor=None`,
`reason_code=UNREACHABLE_AUTO`. Đây là **quyết định tự động bất lợi cho khách** → CS-09, CS-10 bắt buộc đi cùng.
**Schema:** thêm `UNREACHABLE_AUTO` vào lý do huỷ; `Refund.created_by` cho phép Hệ thống (nếu hiện đang bắt buộc) +
migration.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-08-AC1 | Phiếu `ESCALATED` lúc 09:25 (lý do không liên lạc được), đơn 540.000đ, 2 kg lô L | Job chạy 09:56 | Đơn CANCELLED `UNREACHABLE_AUTO`; phiếu CANCELLED; tồn L +2 kg (ledger `CANCEL_RESTORE` đúng lô gốc); 1 phiếu hoàn PENDING 540.000đ `created_by` = Hệ thống; `confirm_state=REFUND_CALL`; AuditLog `order_auto_cancelled` **actor = None**, `detail` chỉ có mã đơn + mã lý do | BR-GH-13, BR-HT-05, BR-HT-10, BR-PQ-04 |
| CS-08-AC2 | Như AC1 | Job chạy 09:54 | Không đổi gì | BR-GH-13 |
| CS-08-AC3 (idempotent) | AC1 đã chạy | Job chạy thêm 2 lần | Vẫn 1 lần huỷ, 1 phiếu hoàn, 1 bút toán kho mỗi lô, 1 AuditLog | Bất biến 6 |
| CS-08-AC4 | Quản lý đã chọn `DELIVER_WITHOUT_CONFIRM` lúc 09:50 (phiếu PREPARING) | Job chạy 09:56 | Không huỷ | BR-GH-13 |
| CS-08-AC5 | Đơn đã bị Quản lý huỷ tay lúc 09:40 | Job chạy | Không đổi, không tạo phiếu hoàn thứ hai | BR-HT-04 |
| CS-08-AC6 (tranh chấp) | Quản lý bấm quyết định đúng lúc job đang chạy trên cùng phiếu | Hai giao dịch đồng thời | Đúng **một** bên thắng (khoá dòng). Job thua thì bỏ qua; API thua thì 409 `STALE_STATE` | BR-GH-13 |
| CS-08-AC7 (lỗi) | Lô L đã CLOSED | Job tới hạn huỷ | **Không** huỷ; phiếu gắn cờ `auto_cancel_blocked` (mã `BR-LO-05`), hiện ở "Cần chú ý" của Chủ (CS-15). Log chỉ có mã đơn | BR-LO-05 |
| CS-08-AC8 | `CSKH_MANAGER_DECISION_MINUTES=60` | Job chạy 09:56 | Không huỷ; 10:26 thì huỷ | Bất biến 7 |
| CS-08-AC9 (lãi lỗ) | AC1 xong, Chủ chưa xác nhận hoàn | Báo cáo kỳ | Doanh thu kỳ chưa giảm; giảm khi Chủ `confirm_refund` | BR-BC-03, BR-HT-03 |
| CS-08-AC10 | Phiếu `ESCALATED` vì **khách muốn huỷ/đổi** (CS-13) | Quá hạn | **Không** tự huỷ (chỉ áp cho không liên lạc được, xem câu hỏi D3) | BR-GH-13 |
| CS-08-AC11 (quyền) | Mọi token người dùng | Gọi endpoint kích job | 403. Chỉ service token của Cloud Scheduler gọi được | BR-PQ-11 |

## CS-09 — Nhắc việc gọi khách báo huỷ và hoàn tiền · Must · BE+FE
**Là** NV CSKH, **tôi muốn** thấy danh sách đơn vừa bị tự huỷ cần gọi báo khách, kèm số tiền và hạn hoàn, **để** khách
biết lý do và cách nhận lại tiền.
Bối cảnh: Q-C2 "nhắc nhỏ cho nhân viên gọi hoàn tiền", BR-GH-21. Nhắc việc là mục `confirm_state=REFUND_CALL` trong
hàng chờ. Phạm vi PII giữ đúng Q-C5: người đã gọi đơn (trong 7 ngày) thấy đủ; CSKH khác thấy SĐT che; Quản lý/Chủ thấy
đủ (xem câu hỏi D4). Số tài khoản của khách **không** lưu trong hệ thống.

**Contract**
```
GET /api/cskh/queue/?state=REFUND_CALL
200 {"results": [{"note_id": 31, "order_code": "DH-…", "cancelled_at": "2026-09-28T09:56:00+07:00",
  "refund": {"id": 5, "amount": "540000", "status": "PENDING", "deadline": "2026-10-28"},
  "in_scope": true, "customer_name": "Khách Thử A", "phone": "0900000123", "attempts": 0}]}
POST /api/cskh/queue/31/calls  {"result": "NOTIFIED" | "UNREACHABLE", "note": "", "request_id": "…"}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-09-AC1 | CS-08-AC1 vừa chạy, `cs1` là người gọi đơn này | `cs1` mở lọc "Báo huỷ & hoàn" | Có đơn, kèm số tiền 540.000đ, trạng thái hoàn "Chờ Chủ chuyển", hạn `cancelled_at + 30 ngày`; SĐT là link `tel:` | BR-GH-21, BR-HT-10 |
| CS-09-AC2 | Như AC1 | `cs1` ghi `NOTIFIED` | Nhắc việc đóng (`confirm_state` rỗng), bản ghi gọi + AuditLog | BR-GH-12 |
| CS-09-AC3 | Như AC1 | Ghi `UNREACHABLE` 3 lần | Nhắc việc vẫn mở, **không** có hành động tự động nào thêm; hiện ở "Cần chú ý" của Quản lý là "chưa báo được khách" | BR-GH-21 |
| CS-09-AC4 (PII) | `cs2` chưa từng gọi đơn này | Mở lọc "Báo huỷ & hoàn" | Dòng có mã đơn, số tiền, `phone_masked`, `in_scope=false`, **không** có tên và địa chỉ | BR-GH-18 |
| CS-09-AC5 | Chủ xác nhận phiếu hoàn (S16) | `cs1` xem lại | Trạng thái hoàn "Đã hoàn dd/mm" | BR-HT-03 |
| CS-09-AC6 (quyền) | `cs1` | `POST /api/sales/refunds/5/confirm` hoặc `POST /api/sales/refunds/create` | 403 | BR-HT-07 |
| CS-09-AC7 (lỗi PII) | — | Ghi `note` có số tài khoản 12 chữ số | 400 `BR-GH-19` (như CS-06-AC6) | BR-GH-19 |
| CS-09-AC8 | Màn nhắc việc | Hiển thị | Có dòng hướng dẫn cố định cho nhân viên: "Không ghi số tài khoản khách vào hệ thống." (nội dung kênh nhận STK chờ câu hỏi D5) | Bất biến 9 |

## CS-10 — Shop báo trước luật gọi xác nhận và báo lý do khi đơn bị tự huỷ · Must · BE+FE (Shop)
**Là** Khách, **tôi muốn** biết trước vựa sẽ gọi xác nhận, và nếu đơn bị huỷ vì không liên lạc được thì biết lý do,
số tiền được hoàn và cách liên hệ, **để** không lo mất tiền.
Bối cảnh: Q-C9 (theo BA), BR-GH-21, NĐ 356/2025 (quyết định tự động bất lợi → **`legal-vn` kiểm câu chữ** trước khi lên
production). Các con số trong câu lấy từ API cấu hình, không viết cứng ở FE. Tra đơn vẫn là `AllowAny`, chỉ trả trạng
thái, **không** trả tên/SĐT/địa chỉ.

**Contract**
```
GET /api/shop/config/     (thêm)
200 {..., "cskh_notice": {"working_hours": "07:00-21:00", "max_attempts": 3, "window_minutes": 30,
       "decision_minutes": 30, "hotline": "<SHOP_HOTLINE>", "refund_deadline_days": 30}}
GET /api/shop/orders/DH-260928-0001/?phone_last4=0123
200 {"code": "DH-…", "status_label": "Đã thanh toán – chờ vựa gọi xác nhận", "fulfilment": "CONFIRMING", "lines": [...], "total_amount": "540000"}
200 {"code": "DH-…", "status_label": "Đã huỷ", "fulfilment": "CANCELLED",
     "cancel_notice": {"reason_code": "UNREACHABLE_AUTO",
        "message": "<câu do legal-vn duyệt: vựa không liên lạc được qua số đã đăng ký sau 3 lần gọi trong 30 phút…>",
        "refund": {"amount": "540000", "status_label": "Đang chờ hoàn", "deadline": "2026-10-28"},
        "contact": "<SHOP_HOTLINE>"}}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-10-AC1 | Cấu hình mặc định | Khách mở bước đặt hàng và trang đặt xong | Có câu báo trước gồm giờ gọi, "3 lần trong 30 phút", việc đơn có thể bị huỷ và **hoàn đủ tiền**. Đổi `CSKH_MAX_UNREACHABLE_ATTEMPTS=2` thì câu hiện "2 lần" mà không build lại FE | BR-GH-21, bất biến 7 |
| CS-10-AC2 | Phiếu `CONFIRMING` | Khách tra đơn đúng mã + 4 số cuối | `status_label` "Đã thanh toán – chờ vựa gọi xác nhận" | UC-CS-1 bước 4 |
| CS-10-AC3 | Đơn tự huỷ (CS-08-AC1) | Khách tra đơn | Có `cancel_notice` đủ 4 phần: lý do, số tiền hoàn, trạng thái + hạn hoàn, cách liên hệ | BR-GH-21 |
| CS-10-AC4 | Chủ đã xác nhận hoàn | Khách tra lại | `refund.status_label` "Đã hoàn", có ngày | BR-HT-03 |
| CS-10-AC5 | Đơn do Quản lý huỷ tay (khách yêu cầu) | Khách tra đơn | Không hiện câu "không liên lạc được"; hiện "Đã huỷ" + trạng thái hoàn | BR-GH-21 |
| CS-10-AC6 (PII) | Mọi trạng thái | Tra đơn (AllowAny) | JSON không có key tên, SĐT, địa chỉ, người nhận hộ, ghi chú gọi | Bất biến 9 |
| CS-10-AC7 (lỗi) | — | Sai 4 số cuối | 404 như hiện nay, không lộ đơn có tồn tại | Bất biến 9 |
| CS-10-AC8 (giá vốn) | — | Tra đơn | Không key giá vốn (X-AC3) | Bất biến 1 |

---

# LÔ 4 — Hoàn thiện vận hành

## CS-12 — Đổi địa chỉ hoặc người nhận khi gọi · Should · BE+FE
**Là** NV CSKH, **tôi muốn** sửa địa chỉ giao và người nhận hộ ngay trong cuộc gọi, **để** khách không phải huỷ đơn
chỉ vì đổi chỗ nhận.
Bối cảnh: UC-CS-4, BR-GH-15, Q-C10 (không đổi địa chỉ mặc định), **Q-C11 (field người nhận hộ trên phiếu giao — field
PII mới, Duy đã duyệt theo đề xuất BA)**. `order.phone` không đổi để khách vẫn tra đơn được. Kiểm vùng giao (BR-BH-12)
chỉ áp khi tính năng vùng giao (N1/N2 hồ sơ hop-duy-loc) đã có.
Why Should: thiếu story này thì vẫn xử lý được bằng huỷ + đặt lại, nhưng tốn công và khách khó chịu.

**Contract**
```
POST /api/cskh/queue/31/recipient
{"delivery_address": "Số 2 Đường Thử, P. Thử, Lâm Đồng", "recipient_name": "Người Nhận Thử", "recipient_phone": "0900000456", "request_id": "…"}
200 {"changed": ["delivery_address", "recipient_name", "recipient_phone"], "label_invalidated": false}
400 {"code": "BR-GH-15", "detail": "Hàng đã soạn xong/đang đi giao — liên hệ Quản lý."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-12-AC1 | Phiếu `CONFIRMING` | `cs1` đổi địa chỉ + người nhận | Lưu; `order.phone` và `Customer.default_address` không đổi; AuditLog `recipient_changed` chỉ ghi **tên field**, không ghi giá trị cũ/mới | BR-GH-15, Q-C10 |
| CS-12-AC2 | Như AC1 | Ghi kết quả `CONFIRMED_CHANGED` | Như `CONFIRMED` (CS-06-AC1) | BR-GH-12 |
| CS-12-AC3 | Phiếu PREPARING đã in tem lần 1 | Đổi địa chỉ | `label_invalidated: true`; tem lần 1 hết hiệu lực; CS-02 hiện "Tem cũ hết hiệu lực – in tem mới, huỷ tem cũ" | BR-GH-16, BR-GH-17 |
| CS-12-AC4 (lỗi) | Phiếu READY hoặc DELIVERING | Đổi | 400 `BR-GH-15` | BR-GH-15 |
| CS-12-AC5 (lỗi) | — | `recipient_phone` không phải 10 số bắt đầu bằng 0 sau chuẩn hoá; hoặc `delivery_address` rỗng | 400 | BR-BH-14 |
| CS-12-AC6 | Sau AC1 | Khách tra đơn Shop bằng 4 số cuối **SĐT cũ** của đơn | Vẫn tra được | UC-CS-4 E1 |
| CS-12-AC7 (thu tối thiểu) | Sau AC1 | Tìm chuỗi địa chỉ cũ trong AuditLog, bản ghi gọi, mọi bảng lịch sử | Không có | Bất biến 9 |
| CS-12-AC8 | Có người nhận hộ | Mở tem (CS-11) | Tem in tên người nhận hộ và SĐT người nhận hộ đã che | BR-GH-15 |
| CS-12-AC9 (quyền) | `kho1`, `giao1` | `POST recipient` | 403 | BR-GH-15 |

## CS-13 — Khách muốn huỷ hoặc đổi món khi gọi → Quản lý huỷ + hoàn · Should · BE+FE
**Là** NV CSKH, **tôi muốn** ghi "khách muốn huỷ / đổi món" để đơn chuyển thẳng tới Quản lý, **để** việc huỷ và hoàn
tiền do người có quyền làm, còn khách được hướng dẫn đặt lại.
Bối cảnh: Q-C3 (a), UC-CS-6, BR-GH-14. Dùng lại khối "Cần quyết định" và `decide` của CS-07.
Why Should: không có thì CSKH báo Quản lý bằng lời, Quản lý vẫn huỷ được qua S14.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-13-AC1 | Phiếu `PENDING` | `cs1` ghi `WANT_CANCEL` có ghi chú | `ESCALATED` với nhãn "Khách muốn huỷ"; `decide_deadline` **rỗng** (không tự huỷ) | UC-CS-6, BR-GH-13 |
| CS-13-AC2 | Như AC1 | Quản lý `decide` `CANCEL` | Đơn CANCELLED, hoàn kho; FE mở S15 điền sẵn toàn phần; AuditLog | BR-HT-05, BR-HT-07 |
| CS-13-AC3 | Phiếu `PENDING` | Ghi `WANT_CHANGE` | `ESCALATED` nhãn "Khách muốn đổi món – huỷ + hoàn + đặt lại"; màn CSKH hiện câu hướng dẫn cố định "Mời khách đặt đơn mới trên Shop sau khi đơn cũ được huỷ" | BR-GH-14, Q-C3 |
| CS-13-AC4 (quyền) | `cs1` | `POST /api/sales/orders/{id}/cancel` | 403 | BR-HT-07 |
| CS-13-AC5 (lỗi) | `cs1` | Gửi sửa dòng hàng/số kg của đơn (bất kỳ endpoint) | 405 hoặc 400 `BR-PQ-14`; đơn không đổi | BR-GH-14, BR-PQ-11 |

## CS-14 — In lại tem, tem hết hiệu lực, xác nhận đã huỷ tem giấy · Should · BE+FE
**Là** NV kho, **tôi muốn** in lại tem khi hỏng và được nhắc xé những tem không còn hiệu lực, **để** không dán nhầm
tem cũ và không để giấy có thông tin khách nằm trong thùng rác.
Bối cảnh: UC-CS-3 3b, E3, E5; BR-GH-10, BR-GH-16, BR-GH-17; Q-C12 (nút "Đã huỷ tem").

**Contract**
```
POST /api/delivery/notes/31/label/print  {"request_id": "…"}        → 201 {"print_no": 2, "is_reprint": true}
POST /api/delivery/notes/31/label/void   {"print_no": 1}            → 200 {"print_no": 1, "voided_at": "...", "already": false}
400 {"code": "BR-GH-16", "detail": "Tem lần 2 đang có hiệu lực, không huỷ được."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-14-AC1 | Tem lần 1 đã in | NV kho bấm "In lại" | `print_no=2`; trang in có dấu "IN LẠI – lần 2"; tem lần 1 vào danh sách "cần huỷ"; AuditLog `label_reprinted` | BR-GH-10, BR-GH-16 |
| CS-14-AC2 | Như AC1 | Bấm "Đã huỷ tem" lần 1 | `voided_at/by` lưu; AuditLog; hết nhắc | BR-GH-17 |
| CS-14-AC3 | Đơn có tem lần 1 bị huỷ (S14, CS-08) | NV kho mở phiếu | Hiện đỏ "Đơn đã huỷ – xé tem lần 1", nút "Đã huỷ tem" | BR-GH-07, BR-GH-17 |
| CS-14-AC4 (lỗi) | Tem lần 2 đang hiệu lực, đơn còn hoạt động | `void` lần 2 | 400 `BR-GH-16` | BR-GH-16 |
| CS-14-AC5 (trùng) | Lần 1 đã huỷ | `void` lần 1 lại | 200 `already: true`, không thêm AuditLog | UC-CS-3 E5 |
| CS-14-AC6 (lỗi) | Đơn CANCELLED | "In lại" | 400 `BR-GH-07` | BR-GH-07 |
| CS-14-AC7 (quyền) | `cs1`, `giao1` | `print` / `void` | 403 | BR-GH-10 |

## CS-15 — "Cần chú ý" cho việc gọi và tem · Should · BE+FE
**Là** Quản lý / Chủ vựa / NV kho / NV CSKH, **tôi muốn** thấy số việc đang chờ mình trong luồng gọi và tem, **để**
không đơn nào kẹt mà không ai biết.
Bối cảnh: UC-CS-3 E4, UC-CS-5, CS-08-AC7, CS-09-AC3. Endpoint `GET /api/dashboard/attention/` **chưa có** (S24 chưa
làm, đã kiểm 28/09). Story này tạo endpoint với **chỉ các key dưới đây**; S24 về sau thêm key của nó. Key nào người hỏi
không có quyền xử lý thì không có trong JSON.
Why Should: thiếu khối này thì vẫn thấy việc qua bộ lọc của từng màn.

**Contract**
```
GET /api/dashboard/attention/
200 {"cskh_queue_waiting": 2, "cskh_escalated": 1, "cskh_auto_cancel_blocked": 0,
     "refund_calls_open": 1, "labels_not_printed": 1, "labels_to_void": 2}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-15-AC1 | Dữ liệu có đủ loại | Chủ gọi | Đủ 6 key, số khớp danh sách lọc tương ứng | |
| CS-15-AC2 | Phiếu `PENDING` trả tiền 61 phút trước, chưa ai gọi | Gọi | `cskh_queue_waiting` tính phiếu này; phiếu trả 59 phút trước thì không (`CSKH_QUEUE_ALERT_MINUTES`) | Bất biến 7 |
| CS-15-AC3 | Phiếu PREPARING xác nhận 16 phút trước, chưa in | Gọi | `labels_not_printed` tính; 14 phút thì không | UC-CS-3 E4 |
| CS-15-AC4 (quyền) | `cs1` / `kho1` / Quản lý | Gọi | `cs1`: chỉ `cskh_queue_waiting`, `refund_calls_open`. `kho1`: chỉ `labels_not_printed`, `labels_to_void`. Quản lý: cả 6 | BR-PQ-12 |
| CS-15-AC5 (quyền) | `giao1` | Gọi | 403 | BR-PQ-12 |
| CS-15-AC6 (lỗi) | API lỗi | Mở Tổng quan | Khối hiện "Chưa tải được", phần còn lại vẫn hiện | |

---

# LÔ 5 — Could

## CS-16 — In phiếu soạn nội bộ, không có thông tin khách · Could · FE
**Là** NV kho, **tôi muốn** in tờ phiếu soạn ghi mặt hàng, kg, lô, hạn dùng, **để** cầm vào kho lạnh không cần điện thoại.
Bối cảnh: Q-C6 (phiếu soạn nội bộ, không PII). Dùng dữ liệu CS-03, không cần API mới.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-16-AC1 | Phiếu PREPARING 5 dòng | Bấm "In phiếu soạn" | PDF 1 trang 100×150 mm, đủ mã phiếu, dòng hàng, kg, mã lô, HSD | BR-BH-06 |
| CS-16-AC2 (PII) | Dữ liệu X-AC1 | Đọc DOM trang in | Không có tên, SĐT, địa chỉ, người nhận hộ | BR-GH-17, bất biến 9 |
| CS-16-AC3 (giá vốn) | — | Đọc DOM | Không giá bán, không giá vốn | BR-GH-10 |
| CS-16-AC4 (quyền) | `cs1`, `giao1` | Mở `/deliveries/31/pick-sheet` | Màn "Không có quyền" (API chi tiết trả 403) | BR-PQ-12 |

## CS-17 — Quét hoặc gõ mã tem để mở phiếu soạn · Could · BE+FE
**Là** NV kho, **tôi muốn** quét mã trên tem (máy quét USB hoặc camera) để mở đúng phiếu, **để** không mở nhầm và biết
ngay tem cũ hay đơn đã huỷ.
Bối cảnh: UC-CS-8, BR-GH-16, BR-GH-07. Mã tem chỉ gồm mã phiếu + số lần in.

**Contract**
```
GET /api/delivery/notes/lookup?code=GH-HD-0001-AB12C.1
200 {"note_id": 31, "status": "PREPARING", "print_no": 1, "valid_print_no": 2, "warning": "BR-GH-16"}
404
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-17-AC1 | Tem lần 1 còn hiệu lực | Quét | Mở chi tiết phiếu (CS-03) | UC-CS-8 |
| CS-17-AC2 | Đã in lại lần 2 | Quét tem lần 1 | Cảnh báo vàng "Tem này không còn hiệu lực, dùng tem lần 2" | BR-GH-16 |
| CS-17-AC3 | Đơn đã huỷ | Quét | Cảnh báo đỏ "Đơn đã huỷ, không soạn, xé tem" | BR-GH-07, BR-GH-17 |
| CS-17-AC4 (lỗi) | — | Mã không tồn tại / sai định dạng | 404 / 400; FE "Không tìm thấy phiếu" | |
| CS-17-AC5 (quyền) | `cs1`, `giao1` | `lookup` | 403 | BR-PQ-12 |

## CS-18 — Kịch bản gọi soạn sẵn · Could · BE+FE
**Là** Chủ vựa, **tôi muốn** soạn sẵn câu gọi và nội dung tư vấn (rã đông, bảo quản) theo tình huống, **để** CSKH nói
đúng và đồng đều.
Bối cảnh: UC-CS-7 phần không AI, Q-C14 (Chủ soạn). **Không AI.** **Schema:** bảng kịch bản mới (tình huống, nội dung,
đang dùng) + migration.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| CS-18-AC1 | Chủ tạo kịch bản "Khách mua lần đầu" | `cs1` mở chi tiết gọi của khách lần đầu | Kịch bản hiện dưới nút kết quả | UC-CS-7 |
| CS-18-AC2 | Chủ tắt kịch bản | `cs1` mở lại | Không hiện | |
| CS-18-AC3 (lỗi) | — | Nội dung rỗng hoặc > 2.000 ký tự | 400 | |
| CS-18-AC4 (quyền) | Quản lý, `cs1` | Tạo/sửa kịch bản | 403; `cs1` chỉ đọc | BR-PQ-02 |

---

## Thứ tự làm đề xuất (BE ∥ FE theo lô)

| Lô | BE | FE (mock theo contract) | Ghi chú |
|---|---|---|---|
| 1 | CS-01 → CS-02, CS-03 | CS-02, CS-03 | CS-01 trước vì mọi AC quyền cần Group `cskh` |
| 2 | CS-04 → CS-05 → CS-06 → CS-11 | CS-05, CS-06, CS-11 | **Chạy được sớm nhất có giá trị**: gọi → xác nhận → in tem tay → soạn. Lên staging được; production chờ Lô 3 |
| 3 | CS-07 → CS-08 → CS-09, CS-10 | CS-07 (khối quyết định), CS-09, CS-10 (Shop) | Lên production **cùng nhau**, sau khi `legal-vn` duyệt câu chữ CS-10 |
| 4 | CS-12, CS-13, CS-14, CS-15 | như BE | Độc lập nhau, làm song song được |
| 5 | CS-17, CS-18 | CS-16, CS-17, CS-18 | Làm khi còn thời gian |

## Phụ thuộc & rủi ro

- **Tiền đề S17, S19** đưa vào CS-02, CS-03 (bản thu gọn). **S18 (gán NV giao), S20, S21** vẫn ở hồ sơ
  `2026-09-24-erp-console-noi-that`, chưa làm. Không có chúng thì phiếu READY chưa tới tay NV giao trên điện thoại →
  Duy cân nhắc làm ngay sau lô 2 (câu hỏi D7).
- **`legal-vn`**: (1) câu thông báo tự huỷ và quyền phản hồi của khách theo NĐ 356/2025 (CS-10, CS-09); (2) quy định ghi
  nhãn hàng hoá thực phẩm trên tem (CS-11, Q-C6). CS-10 không lên production khi chưa có (1). Nếu (2) buộc thêm trường
  thì bổ sung AC CS-11 trước khi lên production.
- **`decisions.md`**: Duy ghi 3 quyết định: chuỗi phiếu giao có "Chờ xác nhận"; Group thứ năm `cskh`; tự huỷ đơn đã trả
  tiền khi Quản lý không xử lý (lật "không bao giờ tự huỷ" của BA, không lật quyết định cũ nào trong `decisions.md`).
- **Tech Lead (`02b`)**: chỗ đặt trạng thái gọi (trên phiếu giao hay bảng riêng), bảng bản ghi gọi, bảng lượt in, khoá
  dòng cho CS-08-AC6, service token cho job, Q-C17 (kiểm kê khi còn hàng "đã trừ sổ, chưa soạn").
- **Rủi ro vận hành**: CSKH thành nút cổ chai. Đơn trả lúc 22:00 nằm chờ tới ca sau (không tự huỷ vì đồng hồ chỉ chạy từ
  lần gọi đầu). Nhưng đồng hồ 30' của Quản lý chạy theo giờ thật, nên đơn chuyển Quản lý lúc 20:50 có thể tự huỷ lúc
  21:20 (câu hỏi D2).
- **Rủi ro PII**: tem giấy (CS-14 nhắc huỷ), điện thoại cá nhân của CSKH (Q-C7: dùng máy/SIM vựa, quy định nội bộ),
  ghi chú tự do (CS-06-AC6 chặn chuỗi số).

## Câu hỏi cho Duy (không chặn Lô 1–2; D1–D3 cần trước khi làm Lô 3)

| # | Câu hỏi | PO đang làm theo |
|---|---|---|
| D1 | Khi tự huỷ, **Hệ thống tự lập phiếu hoàn PENDING** hay chỉ nhắc Quản lý lập? | Hệ thống tự lập (BR-HT-10) để nợ khách được ghi ngay, không ai quên. Tiền vẫn chỉ rời túi khi Chủ xác nhận |
| D2 | Đồng hồ 30' của Quản lý **tính cả ngoài giờ làm** không? | Tính giờ thật, đúng lời Duy. Nếu muốn chỉ tính trong `CSKH_WORKING_HOURS` thì thêm 1 AC ở CS-08 |
| D3 | "Khách muốn huỷ/đổi món" chuyển Quản lý thì có **tự huỷ sau 30'** không? | Không (CS-08-AC10, CS-13-AC1). Luật tự huỷ chỉ áp cho "không liên lạc được" |
| D4 | Nhắc việc "gọi báo hoàn" giao cho ai? Phạm vi PII của Duy chỉ cho người đã gọi đơn đó thấy SĐT. CSKH ca sau không thấy | Người đã gọi + Quản lý/Chủ. Muốn mọi CSKH thấy thì mở rộng BR-GH-18 thêm trạng thái `REFUND_CALL` |
| D5 | Khách gửi **số tài khoản nhận hoàn** qua kênh nào (hệ thống không lưu STK)? | Chưa có. Màn nhắc việc chỉ ghi "không ghi STK vào hệ thống" |
| D6 | Duy ghi 3 quyết định mới vào `decisions.md` (mục Phụ thuộc)? | PO không sửa `decisions.md` |
| D7 | Làm S18 (gán NV giao) + S20/S21 ngay sau Lô 2 để khép vòng giao hàng? | Chưa đưa vào hồ sơ này (ngoài tiền đề tối thiểu) |

## Để sau (ý hay ngoài phạm vi)
In tự động qua trạm in kiosk hoặc chương trình ở kho (C6). AI gợi ý khi gọi, chỉ nhận mã kết quả (C9). Quy tắc bỏ qua
bước gọi cho khách cũ (Q-C8 🟢). SMS/Zalo khi không gọi được (Q-C15). Nhãn lô trong kho (Q-C16). Báo cáo CSKH (Q-C18).
Gộp nhiều đơn cùng khách một chuyến.

## Phủ use case (tự kiểm)
UC-CS-1 → CS-04, CS-10 · UC-CS-2 → CS-05, CS-06 · UC-CS-3 → CS-11, CS-14, CS-15 (tự động: Won't) · UC-CS-4 → CS-12 ·
UC-CS-5 → CS-07, CS-08, CS-09 · UC-CS-6 → CS-13 · UC-CS-7 → CS-18 (phần AI: Won't) · UC-CS-8 → CS-03, CS-16, CS-17.
Mọi ngoại lệ E1–E5 của từng UC có AC tương ứng, trừ UC-CS-3 E2/E4 bản thiết bị (Won't) và UC-CS-8 E3/E4 (hàng hỏng khi
soạn, đi luồng P-07 hiện có qua S14).
