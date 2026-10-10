# Đề xuất cấu trúc lại mã nguồn theo HỆ THỐNG

> Tech Lead · 2026-10-10 · Trạng thái: **ĐỀ XUẤT, chờ Duy duyệt** (mục 7 có các câu hỏi).
> Đo trên nhánh `shop/lo-0-quyet-dinh` (`7b165e9`). Tài liệu này chỉ nghiên cứu và đề xuất, chưa di chuyển file nào.

Yêu cầu của Duy: *"cấu trúc lại code cho hợp lý… nhiều hệ thống khác nhau, không gộp chung một folder BE hoặc FE… chia sao để
mốt tách source oke"*.

**Trả lời ngắn:**
- Giữ **một repo**, nhưng mỗi thư mục gốc là **một hệ thống** có tên rõ, tự build, tự test và tự deploy được:
  `core-api/`, `shop-web/`, `erp-web/`, `payment-adapter/`.
- Giữa các hệ thống chỉ có **hợp đồng API** (thư mục `contracts/`), không import code của nhau. Nhờ vậy mai muốn tách
  hệ thống nào ra repo riêng thì chỉ cần cắt thư mục đó kèm hợp đồng.
- **Lõi Django không tách thành nhiều service.** Lý do: giữ chỗ hàng, FEFO, giá vốn và lãi lỗ cần chung một giao dịch DB.
  Bên trong lõi thì vẽ ranh giới rõ hơn: Shop có cửa API riêng, adapter có cửa riêng, và có máy kiểm "ai được import ai".
- Nên làm **trước lô 1 của Shop**. Shop đang làm lại từ đầu nên code mới dựng thẳng vào chỗ mới. Tổng cộng 8 bước nhỏ,
  bước nào test cũng phải xanh, không đổi hành vi, không đổi migration.

---

## 0. Thuật ngữ (mỗi từ một dòng)

| Từ | Nghĩa trong tài liệu này |
|---|---|
| Hệ thống (system) | Một phần mềm **triển khai riêng**, có địa chỉ chạy riêng: Shop web, ERP web, API lõi, adapter. |
| Ranh giới (bounded context) | Đường chia "phần này lo việc gì, nói chuyện với phần khác qua cửa nào". |
| Monorepo | Một kho git chứa nhiều hệ thống, mỗi hệ thống một thư mục. |
| Polyrepo | Mỗi hệ thống một kho git riêng. |
| Modular monolith | Một ứng dụng (một lần deploy, một DB) nhưng bên trong chia module có luật phụ thuộc rõ ràng. |
| Microservice | Mỗi phần là một dịch vụ riêng, DB riêng, gọi nhau qua mạng. **Không hợp** với dự án này (xem mục 2.3). |
| Hợp đồng API (contract) | Văn bản và ví dụ JSON mô tả endpoint: gửi gì, nhận gì. Hai bên cùng bám theo. |
| Import chéo | File của module A gọi `import` code của module B. Nhiều import chéo hai chiều nghĩa là khó tách. |
| Vòng phụ thuộc (cycle) | A import B và B cũng import A. Khi đó không thể tách A khỏi B. |
| Baseline | Danh sách vi phạm đang có, được "ân xá". Máy chỉ chặn vi phạm **mới**. Cách này đang dùng cho `check_naming.py`. |
| App label | Tên nội bộ của một app Django (`sales`, `inventory`…). Tên này gắn với bảng DB và migration nên **không bao giờ đổi**. |

---

## 1. Hiện trạng

### 1.1 Sơ đồ thư mục hiện tại và hệ thống nằm ở đâu

```
loc/
├─ backend/          ← API lõi Django (Cloud Run cangca-api + Cloud Run Job chạy manage.py)
│   ├─ config/api_urls.py   194 dòng: MỘT danh bạ chứa chung route của Shop, ERP và adapter
│   ├─ apps/ accounts ai catalog common content delivery inventory purchasing reports sales
│   │        (~32.300 dòng code, ~57.800 dòng test, 75 migration)
│   ├─ spikes/       (rỗng, chỉ có __init__.py)
│   └─ media/        111 MB ảnh thử ở máy (đã gitignore, nhưng .dockerignore KHÔNG loại trừ)
├─ frontend/         ← Shop web cho khách (Firebase cangca-loc) — 4.700 dòng, cấu trúc cũ components/ + lib/
├─ erp-console/      ← ERP web nội bộ (Firebase cangca-erp) — 74.700 dòng, đã chia features/ + shared/
├─ adapter/          ← FastAPI nhận IPN SePay (Cloud Run cangca-adapter) — 833 dòng
├─ scripts/          check_naming.py (quét cả 4 thư mục trên)
├─ doc/  .claude/  .agents/  .gemini/
└─ (rác ở gốc: sepay.env, supabase.env, firebase2_Reports…csv, scratchpad/ — đã gitignore nhưng nằm lẫn)
```

**Hệ thống "ẩn" không có thư mục riêng.** Đây là chỗ Duy thấy rối.

| Hệ thống / mảng | Nằm rải ở |
|---|---|
| **AI** | `backend/apps/ai` (lớp lệnh), `erp-console/features/ai` (giao diện + runtime trên trình duyệt), cộng 10 file API nghiệp vụ import `apps.ai.declare` |
| **CMS nội dung** | `backend/apps/content`, `erp-console/features/content` (soạn bài), `frontend/features/content` (hiển thị) |
| **API cho Shop** | `apps/catalog/items/shop_api.py`, `apps/sales/orders/shop_api.py`, `apps/sales/payments/shop_api.py`, `apps/content/public/`, `apps/content/site/`. Tổng cộng 5 nơi, lẫn với API của ERP |
| **API cho adapter** | `apps/sales/payments/internal_api.py` |
| **Job nền** | `apps/*/management/commands/` + `apps/sales/tasks.py`. Chạy chung image với API (Cloud Run Job), **không phải hệ thống riêng** |
| **Công cụ dữ liệu demo/QA** | `apps/accounts/management/commands/seed_demo.py`, `seed_qa.py`, `bootstrap_masterdata.py`, `apps/accounts/qa_fixture/` nằm trong app phân quyền nhưng import mọi miền |

### 1.2 Ở mức HTTP: ranh giới ĐÃ sạch

Đo bằng grep các đường `/api/...` trong code FE và adapter:

| Bên gọi | Tiền tố API dùng | Số route phía Django |
|---|---|---|
| Shop (`frontend/`) | chỉ `/api/shop/*` và `/api/public/*` | 5 + 6 |
| Adapter | chỉ `/api/internal/payments/*` | 2 |
| ERP (`erp-console/`) | mọi tiền tố còn lại (`catalog/ inventory/ purchasing/ sales/ delivery/ confirmation/ ai/ content/ staff/ auth/ reports/ dashboard/ guidance/ audit-logs/`) | ~75 |

Như vậy **tách repo các web và adapter là khả thi ngay**, vì chúng chỉ nói chuyện với lõi qua HTTP. Phần rối nằm ở
**bên trong** lõi Django và ở việc **ai đọc file của ai**.

### 1.3 Import chéo giữa các app Django (đo bằng script, không tính test và migration)

Mỗi ô là số dòng `import apps.<cột>` nằm trong app `<hàng>`.

| từ \ tới | accounts | ai | catalog | common | content | delivery | inventory | purchasing | reports | sales |
|---|---|---|---|---|---|---|---|---|---|---|
| **accounts** | | 5 | 4 | 31 | | 10 | 9 | 5 | | 11 |
| **ai** | 4 | | | 17 | | | 4 | 1 | | 2 |
| **catalog** | | 1 | | 12 | | | 1 | | | 1 |
| **common** | 3 | 3 | | | 1 | | | | | |
| **content** | | | 9 | 14 | | | | | | |
| **delivery** | 3 | | | 28 | | | 3 | | | 13 |
| **inventory** | 7 | 2 | 1 | 47 | | 3 | | | | 6 |
| **purchasing** | 2 | 1 | 1 | 22 | | | 13 | | | |
| **reports** | | 2 | | 3 | | | 6 | | | 7 |
| **sales** | 8 | 4 | 1 | 62 | 1 | 15 | 10 | | | |

**16 cặp vòng phụ thuộc**, trong đó đáng lo nhất:

| Vòng | Vì sao xấu | Bằng chứng |
|---|---|---|
| `common` → `ai`, `accounts`, `content` | `common` là "lõi chung" mà lại phụ thuộc lớp trên, nên không có tầng nào thật sự ở đáy | `apps/common/api.py:31` import `apps.ai.declare`; `apps/common/audit.py:115` import `AuditLog` từ accounts; `apps/common/guidance/steps.py:55-56` import ai; `apps/common/site_info_api.py:7` import content |
| `accounts` ↔ mọi miền | App phân quyền biết chi tiết đơn, phiếu giao, lô, phiếu nhập | `apps/accounts/data_scopes/services.py:290-315` (7 import muộn), `apps/accounts/staff/services.py:255`, `apps/accounts/audit/serializers.py:36` |
| `sales` ↔ `delivery` (15 / 13) | Đơn và phiếu giao gắn chặt. Đây là **một ngữ cảnh nghiệp vụ** đang bị chia làm hai app | `apps/sales/orders/services.py:26`, `orders/api.py:34-35`, `orders/scope.py:18,41`, `customers/scope.py:14-15` |
| `inventory` → `sales`, `delivery` | Kho (tầng dưới) biết đơn bán và phiếu giao | `apps/inventory/batches/timeline.py:17-18` (mượn `TimelineEvent`, `kg_str` của sales), `apps/inventory/returns/creation.py:19-22`, `apps/inventory/stock/references.py:72` |
| `catalog` → `sales`, `inventory` | Danh mục (đáy) biết đơn bán | `apps/catalog/pricing/services.py:101` (ghi chú "nhập muộn: tránh vòng catalog <-> sales"), `apps/catalog/items/services.py:16` |
| Mọi miền → `ai` | Mỗi API nghiệp vụ phải import app AI chỉ để gắn nhãn | 10 file import `apps.ai.declare` hoặc `apps.ai.command_groups`, ví dụ `apps/inventory/batches/api.py:9-10`, `apps/catalog/items/api.py:5` |

Có tổng cộng **22 cặp import muộn** (import đặt trong thân hàm), là dấu hiệu đang né vòng phụ thuộc.

### 1.4 Chỗ rối khác (file:dòng)

| # | Chỗ | Vấn đề |
|---|---|---|
| R1 | `backend/config/api_urls.py:1-194` | Một file chứa route của 3 kênh (Shop công khai, ERP, adapter). Muốn biết "Shop dùng API nào" phải đọc 194 dòng. Dòng 33 import một module chỉ để **đăng ký** provider. |
| R2 | `backend/apps/common/site_info_api.py:1-9` | Code chết: `PublicSiteInfoView` không được dùng ở đâu, route trỏ thẳng `apps.content.site.api` (`api_urls.py:126`). |
| R3 | `backend/apps/ai/registry/discovery.py:52,148` | Nhóm lệnh AI suy ra từ **đường dẫn module Python** của view. Nếu di chuyển file `api.py` của ERP, nhóm/mã lệnh AI có thể đổi theo (rủi ro, xem mục 5). |
| R4 | `erp-console/features/audit/auditModel.test.ts:148` | Test ERP đọc thẳng file Python `../../../backend/apps/accounts/capabilities/services.py`. Hai hệ thống dính nhau qua đường dẫn file, tách repo là vỡ. |
| R5 | `frontend/features/content/safeHref.ts:5`, `erp-console/features/content/editor/safeHref.ts` | Luật lọc link được **chép tay** sang hai nơi, bộ ca test 40 payload cũng chép đôi. Không có máy nào bắt khi hai bản lệch nhau. |
| R6 | `frontend/lib/format.ts` và `erp-console/shared/lib/format.ts` | Hai bộ hàm format tiền/giờ, tên khác nhau (`formatVnd` và `vnd`), cùng hằng `VN_TIME_ZONE`. |
| R7 | `frontend/scripts/check-no-mock.mjs` và `erp-console/scripts/check-no-mock.mjs` | Hai bản đã lệch nhau. |
| R8 | `erp-console/shared/ui/detail/{Timeline,AiBlockFrame,DetailPage}.tsx:5-7` | `shared/` (tầng dùng chung) import `features/auth`, tức là ngược tầng. |
| R9 | `erp-console/features/*` | 112 import chéo giữa các feature (không tính `auth`), ví dụ `features/accounting/components/PurchaseInvoiceForm.tsx:9` gọi `features/purchasing/api`, và `staff` ↔ `permissions` import lẫn nhau. Skill ghi "module không import vào ruột module khác" nhưng chưa có máy kiểm. |
| R10 | `erp-console/e2e/` (99 file), `frontend/e2e/` (14 file) | Kịch bản Playwright **Python** nằm trong app Node. Tên theo **mã lô** (`qa_ed_batch10_real.py`, `p8_lo5_qa_real_backend.py`, `ra_soat_cms04_autosave.py`), trái luật đặt tên. 17 file cần backend thật + `seed_qa`, tức là test xuyên hệ thống nhưng lại nằm trong ERP. Không có file chạy chung. |
| R11 | `backend/.dockerignore` | Không loại `media/` (111 MB ảnh thử). Image được build bằng `gcloud builds submit backend`. **Cần kiểm** xem ảnh thử có lọt vào image không. |
| R12 | Gốc repo | Không có CI. Kiểm chứng hoàn toàn bằng tay (điều phối viên tự chạy). |
| R13 | `doc/design/shop/COMPONENTS.md` (102 chỗ), `HUONG-DAN-CODE.md` | Thiết kế Shop mới vẫn chỉ file vào `components/ui/*`, `components/catalog/*` theo cấu trúc cũ, ngược với luật `features/<module>` của skill. |

**Phần đang ổn, giữ nguyên:** mỗi app Django đã chia module tính năng và có README. ERP đã có `features/` + `shared/`.
Adapter đã độc lập hoàn toàn (không import gì từ backend). Route HTTP đã tách tiền tố theo kênh. Firebase và Dockerfile đều
dùng đường dẫn tương đối nên đổi tên thư mục không làm vỡ cấu hình deploy.

---

## 2. Ranh giới hệ thống

### 2.1 Bốn hệ thống triển khai riêng

| Hệ thống | Thư mục đề xuất (hiện tại) | Chạy ở đâu | Nói chuyện với ai | Tách repo được? |
|---|---|---|---|---|
| **API lõi** | `core-api/` (`backend/`) | Cloud Run `cangca-api` + Cloud Run Job (cùng image) | DB, bucket ảnh. Phục vụ 3 kênh | Là **repo gốc**, nơi giữ hợp đồng |
| **Shop web** | `shop-web/` (`frontend/`) | Firebase `cangca-loc` | Chỉ `/api/shop/*`, `/api/public/*` | **Có**, ngay sau bước 6 |
| **ERP web** | `erp-web/` (`erp-console/`) | Firebase `cangca-erp` | API ERP + token | **Có**, khi có hợp đồng ERP (bước 6, đầy đủ hơn nếu sinh OpenAPI) |
| **Adapter thanh toán** | `payment-adapter/` (`adapter/`) | Cloud Run `cangca-adapter` | SePay → `/api/internal/*` | **Có**, dễ nhất, tách được ngay hôm nay |

Không phải hệ thống riêng:
- **Job nền**: cùng code, cùng DB, khác lệnh chạy, nên thuộc `core-api`.
- **AI**: phía server là lớp lệnh bọc mọi service nghiệp vụ, tách ra thì mất phân quyền 3 tầng và AuditLog. Phía trình
  duyệt là một feature của ERP. Proxy MiMo (nếu làm) thuộc adapter.
- **CMS**: một miền nghiệp vụ trong lõi (`apps.content`) + màn soạn ở ERP + màn đọc ở Shop.
- **Django Admin**: thuộc `core-api`.

### 2.2 Bên trong API lõi: một lõi nghiệp vụ, ba cửa vào

```
                 ┌──────────── core-api (một deploy, một DB) ─────────────┐
 Shop web ──────►│ storefront/   cửa công khai (AllowAny, có throttle)     │
 ERP web  ──────►│ apps/<miền>/<module>/api.py   cửa nội bộ (token + quyền) │
 Adapter  ──────►│ integrations/ cửa cho hệ thống ngoài (service token)    │
                 │        │  cả ba chỉ gọi services.py, không tự viết nghiệp vụ│
                 │        ▼                                                │
                 │ Lõi nghiệp vụ: catalog · purchasing · inventory ·       │
                 │   sales+delivery · reports · content · ai               │
                 │ Nền chung: common · accounts (người dùng, quyền, AuditLog)│
                 └─────────────────────────────────────────────────────────┘
```

Thứ tự tầng đề xuất. Tầng trên được import tầng dưới, **không** được ngược lại:

| Tầng | Gồm | Ghi chú |
|---|---|---|
| 5. Cửa vào | `storefront/`, `integrations/`, `config/routes/` | Không chứa nghiệp vụ |
| 4. Điều phối | `apps.ai`, `guidance` (khung "Tiếp theo · Đã làm") | Ghép nhiều miền lại |
| 3. Báo cáo | `apps.reports` | Chỉ đọc |
| 2. Nghiệp vụ | `apps.sales` + `apps.delivery` (**một ngữ cảnh "Đơn & giao"**, cho phép import hai chiều), `apps.purchasing`, `apps.inventory`, `apps.catalog`, `apps.content` | Trong tầng có thứ tự con: sales/delivery → inventory → catalog; purchasing → inventory → catalog; content → catalog |
| 1. Nền chung | `apps.common`, `apps.accounts` | Không biết đến miền nào. Miền nào cần thì tự **đăng ký** vào nền (mẫu registry, như guidance provider đang làm) |

### 2.3 Đánh giá thẳng: chỗ nào tách được, chỗ nào không nên

| Ý tưởng | Kết luận | Lý do |
|---|---|---|
| Tách Shop, ERP, adapter thành repo riêng | **Được** | Chỉ phụ thuộc HTTP. Cần hợp đồng thành văn và bỏ R4. |
| Tách `sales`, `inventory`, `purchasing` thành service riêng | **Không** | Đặt hàng khoá dòng lô (`select_for_update`) và trừ tồn trong **cùng một giao dịch**. Giá vốn chảy từ phiếu nhập qua lô vào lãi lỗ. Tách ra thì phải làm saga hoặc bù trừ phân tán: rất khó đúng, một người không bảo trì nổi, và dễ sai tiền. |
| Tách `sales` khỏi `delivery` gọn gàng | **Không đáng** | 28 import hai chiều phản ánh nghiệp vụ thật: trạng thái đơn phụ thuộc phiếu giao. Coi là một ngữ cảnh. |
| Tách CMS (`content`) thành service | **Chưa** | Kỹ thuật thì làm được (chỉ đọc catalog), nhưng vẫn cần chung đăng nhập, quyền và AuditLog. Lợi ích bằng không ở quy mô một vựa. |
| Tách AI thành service | **Không** | AI phải có đúng quyền người dùng và đi qua service nghiệp vụ. Tách ra là nhân đôi phân quyền. |
| Gom code TS chung Shop+ERP thành package | **Chưa** | Chỉ ~4 file nhỏ trùng (format, safeHref, check-no-mock). Hai giao diện cố ý khác nhau (Shop kiểu bán lẻ, ERP kiểu Linear; decisions 10/10). Package chung làm việc tách repo **khó hơn** (phải publish npm). Dùng bộ ca test chung thay thế (mục 3). |

---

## 3. Ba phương án

### Phương án A: Giữ tên thư mục, chỉ siết ranh giới

```
loc/ backend/ frontend/ erp-console/ adapter/   (giữ nguyên tên)
     + backend/config/routes/{storefront,erp,integrations}.py
     + contracts/  + máy kiểm phụ thuộc + README bản đồ hệ thống
```
- Ưu: rẻ nhất (khoảng 4 bước), gần như không phải sửa tài liệu.
- Nhược: **không giải quyết điều Duy phàn nàn**. Tên `frontend/`, `backend/` vẫn là tên tầng. Nhìn vào không biết
  `frontend` là Shop, và hệ thống thứ hai (ERP) cũng là "frontend".

### Phương án B (KHUYẾN NGHỊ): Monorepo theo hệ thống, lõi là modular monolith

```
loc/
├─ README.md                 bản đồ: 4 hệ thống, mỗi cái chạy ở đâu, build/test/deploy bằng lệnh gì
├─ core-api/                 ← backend/   API lõi Django (+ Admin + job). Một deploy, một DB.
│   ├─ README.md
│   ├─ config/
│   │   ├─ settings.py  urls.py
│   │   └─ routes/           danh bạ API tách theo kênh, URL GIỮ NGUYÊN
│   │       ├─ storefront.py     /api/shop/*, /api/public/*
│   │       ├─ erp.py            mọi route nội bộ
│   │       └─ integrations.py   /api/internal/*
│   ├─ storefront/           cửa API công khai cho Shop (không model). API Shop MỚI viết thẳng vào đây
│   │   ├─ catalog/  orders/  checkout/  vouchers/  content/  site/   (api.py · serializers.py · tests/)
│   │   └─ README.md         luật: AllowAny + throttle, chỉ serializer riêng, không dữ liệu cá nhân, không giá vốn
│   ├─ integrations/         cửa cho hệ thống ngoài (adapter): sepay/ (từ sales/payments/internal_api.py)
│   ├─ apps/                 GIỮ NGUYÊN app label + migration: accounts ai catalog common content delivery
│   │                        inventory purchasing reports sales (+ devtools: seed_demo, seed_qa, bootstrap — không model)
│   ├─ Dockerfile  requirements.txt  .dockerignore (+ media/)
├─ shop-web/                 ← frontend/  Shop cho khách (làm lại theo thiết kế 06/10)
│   ├─ app/                  route mỏng
│   ├─ features/  catalog/ cart/ checkout/ orders/ vouchers/ content/ site/
│   ├─ shared/    ui/ (Sheet, Dialog, Toast, Icon…)  lib/ (http.ts, format.ts)
│   ├─ e2e/                  kịch bản chạy trên mock (giữ trong app)
│   └─ firebase.json  firebase.staging.json  package.json
├─ erp-web/                  ← erp-console/  ERP nội bộ (giữ features/ + shared/)
├─ payment-adapter/          ← adapter/
├─ contracts/                hợp đồng giữa các hệ thống (nguồn sự thật do core-api giữ)
│   ├─ README.md
│   ├─ shop-api.md           endpoint + JSON mẫu (lấy từ 02b của Shop)
│   ├─ integrations-api.md   adapter → lõi (lấy từ adapter/README)
│   └─ test-vectors/         safe-href.json, format-vnd.json… cả Shop và ERP cùng chạy
├─ e2e/                      test xuyên hệ thống trên backend thật (seed_qa), gom theo LUỒNG, không theo lô
│   └─ order-to-payment/  erp-permissions/  content-publish/ …
├─ tools/                    ← scripts/   check_naming.py, check_boundaries.py, check-boundaries.mjs
├─ doc/                      (giữ nguyên)
└─ CLAUDE.md  AGENTS.md  .claude/  DESIGN.md  PRODUCT.md
```

**Luật phụ thuộc và cách máy kiểm:**

| Luật | Kiểm bằng |
|---|---|
| Hệ thống không đọc/import file của hệ thống khác (chỉ được đọc `contracts/`) | `tools/check_boundaries.py` (Python stdlib): quét `import`, `readFileSync`, `../` vượt thư mục hệ thống |
| Trong `core-api`: theo bảng tầng ở mục 2.2 | Cùng script, có **baseline** liệt kê vi phạm hiện có, chỉ chặn vi phạm mới (giống `check_naming.py`). Nâng lên `import-linter` sau nếu Duy duyệt thư viện |
| `storefront/` không import `apps/*/…/serializers.py` của ERP | Cùng script, kèm test Django: mọi view dưới `/api/shop/`, `/api/public/` có `AllowAny` + throttle; mọi view ngoài đó **không** `AllowAny` (trừ `auth/token/`) |
| FE: `shared/` không import `features/`; feature chỉ import `api.ts`/`types.ts` của feature khác, không import `components/` | `tools/check-boundaries.mjs` (Node thuần, không thêm thư viện), có baseline cho 112 chỗ hiện có của ERP |
| Shop chỉ gọi `/api/shop/*`, `/api/public/*` | Cùng script `.mjs`: grep chuỗi `/api/` trong `shop-web` |

**Build, test, deploy độc lập** (mỗi hệ thống đứng trong thư mục của nó, lệnh không đổi so với hiện nay):

| Hệ thống | Test | Build/deploy |
|---|---|---|
| core-api | `cd core-api && .venv/bin/python manage.py test` | `gcloud builds submit core-api --tag …/api:vNN` |
| payment-adapter | `cd payment-adapter && .venv/bin/python -m pytest -q` | `gcloud builds submit payment-adapter …` |
| shop-web | `cd shop-web && npm test && npx tsc --noEmit && npm run build` | `firebase deploy` trong `shop-web/` |
| erp-web | `cd erp-web && npm test && npx tsc --noEmit && npm run build` | `firebase deploy` trong `erp-web/` |
| Xuyên hệ thống | `e2e/` (cần core-api thật + `seed_qa`) | — |

Nếu Duy duyệt thì thêm CI (GitHub Actions) chạy theo đường dẫn: sửa `shop-web/**` chỉ chạy test Shop. Câu hỏi Q6.

**Lộ trình "mốt tách source"** (khi nào cần mới làm, không làm bây giờ):
1. `payment-adapter`: `git subtree split --prefix=payment-adapter -b adapter-only` → đẩy sang repo mới, chép
   `contracts/integrations-api.md`. Giữ secret `INTERNAL_SERVICE_TOKEN` như cũ.
2. `shop-web`: tương tự, chép `contracts/shop-api.md` + `test-vectors/`. Kịch bản xuyên hệ thống của Shop thì giữ ở repo
   lõi, hoặc chuyển theo.
3. `erp-web`: tương tự, cần hợp đồng ERP đầy đủ. Lúc đó nên sinh OpenAPI tự động (Q5).
4. `core-api` ở lại repo gốc, là chủ của `contracts/`. Mỗi khi đổi hợp đồng thì ghi phiên bản, và repo con cập nhật theo.

Lịch sử git của từng thư mục giữ được nhờ `subtree split`. Vì vậy **đổi tên thư mục bây giờ** là rẻ nhất: tách sau
này sẽ được tên đúng ngay.

- Ưu: thư mục gốc đọc là hiểu (4 hệ thống + hợp đồng + test xuyên hệ thống). Mỗi hệ thống tự đủ, tách repo bằng một lệnh.
  Lõi vẫn một giao dịch DB. Không thêm thư viện. Shop mới dựng thẳng vào cấu trúc đúng.
- Nhược: một lần đổi tên chạm khoảng 29 file tài liệu/cấu hình đang dùng (131 chỗ ghi đường dẫn trong `CLAUDE.md`,
  `README.md`, `AGENTS.md`, `.claude/agents|skills|commands`, `doc/he-thong/`, `doc/ops/`), cộng `tools/` và khoá trong
  `naming_baseline.json` (183 dòng, đổi bằng script). Hồ sơ cũ trong `doc/features/` **để nguyên** vì là lịch sử, chỉ thêm
  một dòng chú thích ở `doc/he-thong/README.md`: "`backend/` = `core-api/`…".

### Phương án C: Workspace + package dùng chung + tách service

```
apps/shop  apps/erp  services/catalog-api  services/order-api  services/cms-api  packages/ui  packages/api-client  packages/format
```
- Ưu: trông "chuẩn doanh nghiệp".
- Nhược: tách service phá giao dịch chung (mục 2.3). Package chung bắt phải dùng npm workspaces và cấu hình
  `transpilePackages` cho Next 14 static export, lockfile gộp, và phải publish package khi tách repo. Tốn gấp nhiều lần
  phương án B mà một người không bảo trì nổi. **Không khuyến nghị.**

### So sánh

| | A. Siết ranh giới | **B. Monorepo theo hệ thống** | C. Workspace + service |
|---|---|---|---|
| Giải quyết "nhìn thư mục là hiểu" | Không | **Có** | Có |
| Dễ tách repo sau này | Trung bình | **Cao** (một lệnh/hệ thống) | Thấp (phải publish package) |
| Giữ giao dịch DB chung | Có | **Có** | Không |
| Thêm thư viện | Không | **Không** | Nhiều |
| Số bước | ~4 | **8** | >20 |
| Rủi ro đổi hành vi | Rất thấp | **Thấp** (có ảnh chụp route + migration + registry AI) | Cao |
| Hợp một người bảo trì | Có | **Có** | Không |

---

## 4. Thứ tự thực hiện (Phương án B), gắn với Shop làm lại

**Khuyến nghị: làm bước 0–3 TRƯỚC lô 1 của Shop, bước 4–7 song song với Shop.**

Lý do:
1. Shop làm lại từ đầu. Nếu đổi tên sau thì mọi file mới của lô 1–7 lại phải dời thêm lần nữa.
2. Production chưa chạy và chưa có CI, nên đổi đường dẫn không làm vỡ pipeline nào.
3. Hiện không có worktree đang dở (`git worktree list` chỉ có thư mục chính). Nhánh chưa gộp duy nhất là
   `design/shop-ui` và `shop/lo-0-quyet-dinh`, cả hai chỉ sửa `doc/`, nên không xung đột với việc đổi tên code.
4. Càng để lâu, số chỗ ghi đường dẫn càng tăng (mỗi lô thêm tài liệu).

| Bước | Việc | Ai | Điều kiện xong (ngoài "test xanh y như số gốc") | Chặn Shop? |
|---|---|---|---|---|
| **0** | Ghi số gốc + 3 "ảnh chụp" làm lưới an toàn: (a) danh sách mọi route + view + permission + throttle, (b) danh sách migration theo app label (`showmigrations`), (c) chỉ mục lệnh AI (id, nhóm, quyền). Viết thành test so khớp | be-dev | 3 test ảnh chụp xanh; `makemigrations --check` sạch | Có |
| **1** | **Đổi tên 4 thư mục** bằng `git mv` (`backend→core-api`, `frontend→shop-web`, `erp-console→erp-web`, `adapter→payment-adapter`, `scripts→tools`). Sửa `tools/check_naming.py` (`SCAN_DIRS`, allowlist), đổi khoá `naming_baseline.json`, `.gitignore`, `.dockerignore` (+`media/`), R4 (test ERP đọc file Python) đổi sang đọc `contracts/`. Sửa tài liệu đang dùng (29 file) + `doc/design/shop/*` + `doc/ops/moi-truong.md` (lệnh build). Dọn rác: xoá `core-api/spikes/` rỗng, chuyển `*.env` và file csv ở gốc ra ngoài repo | điều phối + be-dev + fe-dev, **một commit**, không ai khác đang code | 4 bộ test + 2 build + `check_naming` xanh; `grep -r "erp-console/\|frontend/\|backend/"` trong tài liệu đang dùng = 0 | Có |
| **2** | Máy kiểm ranh giới: `tools/check_boundaries.py` + `tools/check-boundaries.mjs`, mỗi cái có baseline = vi phạm hiện tại (mục 1.3, R8, R9). Thêm vào "lệnh kiểm chứng" trong CLAUDE.md và các skill | be-dev ∥ fe-dev | Chạy dưới 10 giây, exit 0 trên code hiện tại, exit 1 khi thử thêm một import ngược | Có |
| **3** | Tách cửa API: `config/routes/{storefront,erp,integrations}.py`; chuyển 3 file `shop_api.py` + `content/public` + `content/site` vào `storefront/`, `internal_api.py` vào `integrations/` (test đi theo). Xoá code chết R2. Thêm test "storefront chỉ AllowAny, ngoài storefront không AllowAny" | be-dev | Ảnh chụp route **không đổi một dòng**; ảnh chụp lệnh AI không đổi | Chặn **lô 2** (BE Shop) |
| 4 | Dọn nền chung: chuyển `AiDeclarable`/`AiMeta`/`command_groups` từ `apps/ai` xuống `apps/common` (bỏ `common→ai`); chuyển `TimelineEvent`, `kg_str` xuống `common` (bỏ `inventory→sales` ở `timeline.py:17-18`); đưa `guidance` lên tầng điều phối | be-dev | Baseline giảm; ảnh chụp lệnh AI không đổi | Không |
| 5 | `accounts` thôi biết miền: `data_scopes` dùng registry (mỗi miền tự đăng ký hàm phạm vi); chuyển `seed_demo`, `seed_qa`, `bootstrap_masterdata`, `qa_fixture` sang app mới `apps.devtools` (**không model, không migration**, tên lệnh giữ nguyên) | be-dev | Baseline giảm; lệnh `manage.py seed_qa` chạy y như cũ trên SQLite tạm | Không |
| 6 | `contracts/`: `shop-api.md` (sinh từ 02b Shop), `integrations-api.md`, `test-vectors/` (safe-href 40 ca, format tiền/giờ). Test Shop và ERP cùng đọc. Gộp `check-no-mock` về `tools/` (R7) | fe-dev | Hai bản safeHref chạy cùng một bộ ca | Không (nên xong trước lô 3) |
| 7 | `e2e/`: chuyển 17 kịch bản cần backend thật ra `e2e/<luồng>/`, đặt tên theo luồng, bỏ mã lô (R10). Thêm `e2e/README.md` + một lệnh chạy. Kịch bản chạy trên mock thì giữ trong app, đổi tên dần | qa-tester | Kịch bản chuyển chạy xanh như trước | Không |

Khoảng **8 bước**. Bước 0–3 nằm trên đường găng của Shop. Bước 4–7 chen vào giữa các lô Shop, mỗi bước một commit.

**Điều kiện chung cho mọi bước:** không đổi app label, không đổi hay thêm migration (trừ khi chạy
`makemigrations --check` vẫn "No changes"), không đổi URL, không đổi tên lệnh `manage.py`, không đụng dữ liệu, không deploy.
Mỗi bước: điều phối viên tự chạy lại toàn bộ lệnh kiểm chứng, techlead review diff, rồi mới commit.

**Ghi chú cho 02b của Shop:** Shop mới theo `features/<module>` + `shared/ui` như ERP. Cột file trong
`doc/design/shop/COMPONENTS.md` (`components/ui/*`, `components/catalog/*`) sẽ được ánh xạ lại trong 02b, ví dụ
`components/ui/Sheet` → `shop-web/shared/ui/Sheet.tsx`, `components/catalog/*` → `shop-web/features/catalog/components/*`.
API Shop mới (BE-1, 3, 4, 5, 11) viết thẳng vào `core-api/storefront/`.

---

## 5. Rủi ro và cách chặn

| Rủi ro | Mức | Cơ chế chặn | Test bắt lỗi |
|---|---|---|---|
| Đổi app label hoặc migration → Django tưởng là app mới, tạo bảng mới hoặc mất bảng | Critical | Chỉ di chuyển **module Python không chứa model**. Không chuyển class model giữa app. Migration cũ không import module bị dời (đã kiểm: migration chỉ dùng `apps.get_model`) | Ảnh chụp `showmigrations`; `makemigrations --check --dry-run` |
| Nhóm/mã lệnh AI đổi vì suy ra từ đường dẫn module (`discovery.py:52,148`) → cấu hình AI đã lưu trỏ sai | High | **Không** dời `api.py` của ERP. View Shop và adapter dời được vì đã nằm trong `FORBIDDEN_PREFIXES` (`apps/ai/policy/rules.py:9-10,16`) | Ảnh chụp chỉ mục lệnh AI |
| Endpoint Shop mất `AllowAny`/throttle hoặc ERP vô tình thành công khai khi tách route | Critical (rò dữ liệu) | Route tách theo file nhưng URL giữ nguyên | Ảnh chụp route + test bất biến "AllowAny chỉ ở storefront" |
| Chuỗi đường dẫn lưu trong cấu hình bị vỡ: `CELERY_BEAT_SCHEDULE` (`apps.sales.tasks…`), `MIDDLEWARE` (`apps.accounts.auth.middleware…`), `_LAZY_MODULES` của guidance (`apps/common/guidance/api.py:27-35`) | High | Giữ nguyên các module đó, hoặc đổi chuỗi cùng commit | `manage.py check`; test guidance hiện có |
| Agent và skill còn trỏ đường dẫn cũ → dev sửa nhầm chỗ, tạo lại `backend/` | Medium | Bước 1 sửa toàn bộ tài liệu đang dùng trong cùng commit; `check_boundaries` báo lỗi khi thấy thư mục gốc lạ | Grep đường dẫn cũ = 0 trong `CLAUDE.md`, `.claude/`, `AGENTS.md`, `doc/he-thong`, `doc/ops` |
| Nhánh hoặc worktree đang dở bị xung đột đổi tên | Medium | Làm bước 1 khi không ai đang code. Nhánh Shop hiện chỉ sửa `doc/` | `git worktree list`, `git branch --no-merged main` trước khi làm |
| Lệnh deploy cũ (`gcloud builds submit backend`) trong runbook | Low | Sửa `doc/ops/moi-truong.md`. Runbook cũ trong `doc/features/` có chú thích ánh xạ tên | Staging deploy lần tới là kiểm chứng thật |
| `.venv`, `node_modules` và đường dẫn tuyệt đối trên máy Duy | Low | `git mv` không dời file bị ignore. Cài lại `.venv` (`python -m venv`) và `npm ci` trong thư mục mới | Lệnh kiểm chứng của bước 1 |
| Rò dữ liệu cá nhân hoặc giá vốn | — | Không đổi logic hay serializer. Bước 3 còn thêm lớp chặn mới | Test giá vốn và dữ liệu cá nhân hiện có phải xanh y nguyên |

---

## 6. Việc KHÔNG làm trong đợt này
- Không tách DB, không tách service trong lõi, không đổi URL công khai.
- Không dời model giữa app, không gộp `sales` với `delivery` ở mức app (chỉ coi là một ngữ cảnh trong luật phụ thuộc).
- Không thêm thư viện (import-linter, eslint-plugin-boundaries, drf-spectacular, npm workspaces) khi Duy chưa duyệt.
- Không sửa hồ sơ tính năng cũ trong `doc/features/` (là lịch sử).

---

## 7. Câu hỏi cho Duy 🔴

| # | Câu hỏi | Khuyến nghị |
|---|---|---|
| Q1 | Tên 4 thư mục hệ thống? | **`core-api/`, `shop-web/`, `erp-web/`, `payment-adapter/`** (tiếng Anh theo luật đặt tên, nhìn là biết chạy ở đâu). Phương án khác: `api/ shop/ erp/ adapter/` (ngắn hơn nhưng `api` dễ lẫn với thư mục API của Next). |
| Q2 | Làm trước hay sau Shop? | **Trước lô 1**: bước 0–3 (khoảng 1–2 ngày làm việc của đội), Shop chờ. Bước 4–7 làm xen giữa các lô Shop. |
| Q3 | Máy kiểm ranh giới dùng gì? | **Script tự viết, không thư viện** (giống `check_naming.py`), có baseline. Nâng lên `import-linter`/ESLint sau nếu thấy cần. |
| Q4 | Code TS dùng chung giữa Shop và ERP? | **Không làm package chung.** Mỗi web tự đủ, chỉ chia **bộ ca test** trong `contracts/test-vectors/`. Lý do: hai giao diện cố ý khác nhau, và package chung làm việc tách repo khó hơn. |
| Q5 | Sinh hợp đồng API tự động (OpenAPI bằng `drf-spectacular`, thêm 1 thư viện) để FE có type sinh sẵn? | **Để sau lô 3 Shop.** Trước mắt viết tay `contracts/shop-api.md` từ 02b. Sinh tự động khi tách ERP ra repo riêng. |
| Q6 | Bật GitHub Actions chạy test theo từng hệ thống (chỉ test, **không** deploy)? | **Có, sau bước 2.** Repo công khai nên miễn phí. Test không cần secret. Giúp không phải tin báo cáo "test xanh" của subagent. |
| Q7 | Khi nào tách repo thật? | **Chưa tách.** Giữ monorepo tới khi có người thứ hai phụ trách riêng một hệ thống, hoặc cần quyền truy cập khác nhau. Ứng viên đầu tiên là `payment-adapter`. |
