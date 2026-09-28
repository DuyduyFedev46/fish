# Research: "Mỗi function là một MCP tool" thay cho registry viết tay

> Research kiến trúc · 2026-09-28 · Người hỏi: Duy (PO) · Trạng thái: **để Duy đọc, chưa phải quyết định**.
> Chỉ research. Không sửa code, không sửa 01-analysis/02b.
> Câu hỏi nguyên văn: *"hình như tiếp cận sai rồi á, nếu đúng thì nên biết mỗi Function đều coi như là
> 1 mcp á, có thể research thử, chứ bị hard vào schema là ko ổn"*.

Quy ước mức tin cậy nguồn:
- **Cao**: đọc thẳng văn bản spec trong repo chính thức (đã clone `modelcontextprotocol/modelcontextprotocol`,
  thư mục `docs/specification/2026-07-28`) hoặc metadata PyPI/npm lấy trực tiếp ngày 28/09/2026.
- **Trung bình**: đọc qua WebFetch trang GitHub/README, hoặc blog chính thức.
- **Thấp**: chỉ có đoạn trích WebSearch, chưa đọc gốc.

---

## 0. Trả lời ngắn cho Duy

1. Duy nói đúng một nửa. **MCP vẫn dùng JSON Schema** cho input/output của từng tool. Bỏ registry
   thì schema vẫn phải có. Cái "hard" thật sự nằm ở chỗ khác:
   - Schema và mô tả lệnh viết **tách xa service**, nên phải sửa hai nơi khi service đổi.
   - Danh mục là **định dạng tự chế**, chỉ console của mình đọc được.
   - FE và router phải biết từng lệnh; thêm lệnh là phải sửa FE.
2. MCP giải quyết đúng ba điểm đó: tool **tự mô tả**, client **tự khám phá** qua `tools/list`, danh sách
   **lọc theo quyền của người gọi**, và client bên ngoài dùng được.
3. MCP **không** giải quyết phần khó nhất của Cá Về: kiểm quyền 3 tầng, mức "AI của tôi", sàn cứng
   H1–H16, vùng đỏ, không rò giá vốn, không PII. Các phần này **vẫn phải nằm ở server Django**. Spec
   còn nói rõ: annotations của tool chỉ là gợi ý, không được tin.
4. Khuyến nghị: **phương án B+** (§7). Khai báo lệnh bằng **decorator đặt ngay cạnh service**, schema
   sinh từ serializer đầu vào, catalog trả **đúng định dạng MCP Tool**. Endpoint MCP đặt trong Django,
   chỉ cho console nội bộ. Chưa mở cho agent bên ngoài. Nếu sau này mở thì phải qua FastAPI.
5. Không nên sinh tool tự động từ DRF viewset hay OpenAPI. Chính tác giả FastMCP khuyên không đưa bản
   sinh tự động lên production. Thư viện Django MCP hiện có còn non hoặc tụt spec.
6. Tổ chức tool theo 3 mảng Thu mua / Bán hàng / CSKH (§8): một server nội bộ, ba nhóm tool. Nhiều
   function đã có sẵn trong service nhưng chưa là lệnh. CSKH **cho khách** là thay đổi phạm vi (đụng PII
   và NĐ 142), nên tách endpoint riêng và cần hồ sơ riêng. Chưa có tính năng khiếu nại. Tra đơn trên Shop
   chưa có rate limit.

---

## 1. MCP hiện tại (spec 2026-07-28)

### 1.1 Phiên bản

- Spec mới nhất là **2026-07-28**, phát hành ngày 28/07/2026. Đây là bản sửa lớn nhất từ khi ra mắt.
  (Cao · [changelog](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx) ·
  [blog](https://blog.modelcontextprotocol.io/posts/2026-07-28/))
- Thay đổi chính:
  - **Không còn handshake `initialize`**, không còn `Mcp-Session-Id`. Mỗi request tự mang phiên bản giao
    thức, thông tin client, capabilities trong `_meta`. Có method mới `server/discover`.
  - **Stateless**: request nào cũng vào được instance nào. Cần trạng thái thì server trả một "handle" từ
    tool, model truyền lại ở lần gọi sau.
  - **MRTR** (Multi Round-Trip Requests) thay cho việc server chủ động gửi request. Tool cần hỏi thêm
    người dùng thì trả `resultType: "input_required"`; client hỏi xong gọi lại kèm `inputResponses`.
  - `tools/list` có `ttlMs` + `cacheScope` để client cache.
  - Header `Mcp-Method`, `Mcp-Name` cho gateway định tuyến mà không cần đọc body.
  - **Tasks** (việc chạy lâu) và **MCP Apps** (server trả UI HTML) thành extension chính thức.
  - **Deprecated**: Roots, **Sampling**, Logging, HTTP+SSE cũ, Dynamic Client Registration (thay bằng
    Client ID Metadata Documents). Gỡ sớm nhất từ bản sau 2027-07-28.
  (Cao · [deprecated.mdx](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/deprecated.mdx))
- SDK Tier 1 (TypeScript, Python, Go, C#) đã hỗ trợ bản này. (Trung bình · blog trên)

### 1.2 Ba loại "primitive" phía server

| Primitive | Là gì | Ứng với Cá Về |
|---|---|---|
| **Tools** | Hàm model gọi được. Có `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, `icons`, `_meta` | 14 lệnh (`nhap_lo`, `tra_ton`…) |
| **Resources** | Dữ liệu đọc được theo URI | Có thể dùng cho "Đã làm" của một chứng từ (`cave://don/DH-001/timeline`) — không bắt buộc |
| **Prompts** | Mẫu prompt server cung cấp | Mẫu "tóm tắt chứng từ", "giải thích bước tiếp" — không bắt buộc |

Nguồn: (Cao · [server/tools.mdx](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx))

### 1.3 Điểm khớp nhu cầu "mỗi function tự mô tả, client tự khám phá"

Trích spec `server/tools.mdx` (Cao):
- `tools/list` trả "the set of tools currently available to the requesting client". Tập này **MAY vary
  by the authorization presented on the request**, ví dụ chỉ trả tool mà scope của người gọi cho phép.
  → Khớp đúng catalog lọc theo `min_permissions` hiện nay (S01-AC2).
- `listChanged: true` + đăng ký `subscriptions/listen` với `toolsListChanged` → server báo khi danh sách
  đổi. → Khớp nhu cầu "đổi cấu hình AI của tôi có hiệu lực tức thì" (01-analysis §4.5).
- `inputSchema`, `outputSchema` nhận **mọi từ khoá JSON Schema 2020-12**. Kết quả có `structuredContent`
  phải khớp `outputSchema`; lỗi nghiệp vụ trả `isError: true` để model tự sửa.
- Tên tool: 1–128 ký tự, chỉ `A-Z a-z 0-9 _ - .`. Tên hiện tại (`nhap_lo`) hợp lệ.

### 1.4 Tool annotations

`ToolAnnotations` gồm `title`, `readOnlyHint` (mặc định false), `destructiveHint` (mặc định true),
`idempotentHint` (mặc định false), `openWorldHint`. Spec ghi: **"all properties in ToolAnnotations are
hints"** và **"clients MUST consider tool annotations to be untrusted unless they come from trusted
servers"**. (Cao · `schema.mdx`, `server/tools.mdx`)

→ Hệ quả cho Cá Về: annotations chỉ để **hiển thị và gợi ý**. Không bao giờ dùng để kiểm quyền.

### 1.5 `_meta` cho metadata riêng

`_meta` cho phép gắn metadata tự do. Khoá có tiền tố dạng reverse-DNS, vd `vn.cave/sensitivity`. Tiền
tố có nhãn thứ hai là `modelcontextprotocol` hoặc `mcp` là dành riêng. (Cao · `basic/index.mdx` mục `_meta`)

→ Chỗ hợp lệ để công bố nhãn `local/cloud`, nhạy cảm, trần mức, vùng đỏ ra client.

### 1.6 Transport

- **stdio**: client chạy server như tiến trình con. Dùng cho công cụ trên máy (Claude Desktop, IDE).
  Không hợp với ERP web.
- **Streamable HTTP**: một endpoint, client gửi mỗi message bằng một **HTTP POST**. Server trả
  `application/json` (một object) **hoặc** `text/event-stream`; **client phải hỗ trợ cả hai** → server
  chỉ cần trả JSON là đủ. Server **MUST validate `Origin`** chống DNS rebinding. Mỗi POST phải có header
  metadata (`Mcp-Method`…). (Cao · `basic/transports/streamable-http.mdx`)

→ Một view Django/DRF nhận POST JSON-RPC và trả JSON là đủ làm MCP server (stateless). Không cần ASGI,
không cần giữ kết nối. Hợp gunicorn/Cloud Run hiện có.

### 1.7 Authorization

- Authorization là **OPTIONAL**. Transport HTTP thì **SHOULD** theo OAuth 2.1; stdio thì lấy credential
  từ môi trường. (Cao · `basic/authorization/index.mdx`)
- Khi dùng: MCP server là **OAuth 2.1 resource server**, phải có Protected Resource Metadata (RFC 9728).
  Client phải gửi `resource` (RFC 8707) để token gắn đúng audience. Token gửi trong header
  `Authorization` ở **mọi** request.
- Server **MUST chỉ nhận token cấp cho chính nó** (kiểm audience). **Cấm token passthrough** (nhận
  token rồi chuyển tiếp nguyên token cho dịch vụ phía sau). (Cao · `security-considerations.mdx`)
- Mỗi token là của **một người dùng** → `tools/list` và `tools/call` chạy theo đúng người đó. Khớp
  nguyên tắc "AI có đúng quyền người đăng nhập" (ADR §2.6).

### 1.8 Elicitation và Sampling

- **Elicitation** (server xin người dùng nhập/đồng ý): có form mode và URL mode. Nay đi qua MRTR. Cấm dùng
  form mode xin mật khẩu/token. (Cao · `client/elicitation.mdx`)
- **Sampling** (server nhờ model của client sinh chữ): **đã deprecated** ở 2026-07-28, hướng thay là gọi
  thẳng API nhà cung cấp model. (Cao · `deprecated.mdx`)
- Spec khuyên **"there SHOULD always be a human in the loop with the ability to deny tool invocations"**
  và client nên hiện input cho người xem trước khi gọi. (Cao · `server/tools.mdx`)

→ Elicitation **có thể** làm khung xác nhận mức C. Nhưng xác nhận nằm ở **client**; một agent bên ngoài
có thể tự trả lời. Với Cá Về, xác nhận phải là người bấm trên ERP (BR-AI-06, H5). Nên giữ mô hình
**proposal handle** hiện có: tool ghi ở mức C trả `{proposal_id, trang_thai: "cho_duyet"}`. Đây chính là
mẫu "handle" spec khuyến nghị cho trạng thái nhiều bước.

---

## 2. Registry tự chế vs MCP server chuẩn

### 2.1 Làm rõ hiểu lầm "hard vào schema"

- MCP **bắt buộc** `inputSchema` là JSON Schema hợp lệ. `outputSchema` là tuỳ chọn nhưng nên có.
- Nên câu hỏi đúng không phải "có schema hay không". Câu hỏi đúng là **schema sinh ra từ đâu**:
  - Hiện nay: viết tay trong `registry.py`, tách khỏi service. Vd schema `nhap_lo` (dòng lô, giá mua…)
    trùng ý với `PurchaseReceiptLineSerializer` nhưng viết lại riêng → dễ lệch.
  - Nên: sinh từ **serializer đầu vào** của lệnh (DRF serializer hoặc pydantic model), đặt cạnh service.

### 2.2 So sánh

| Tiêu chí | Registry hiện tại (S01) | MCP server chuẩn |
|---|---|---|
| Mô tả tool | `CommandSpec` tự chế, 12 trường | `Tool` chuẩn: name/title/description/inputSchema/outputSchema/annotations/_meta |
| Schema | JSON Schema viết tay | JSON Schema (vẫn phải có) — có thể sinh từ type hint/serializer |
| Khám phá | `GET /api/commands/catalog/` (định dạng riêng) | `tools/list` chuẩn + cache `ttlMs` + báo đổi `toolsListChanged` |
| Gọi | `execute`/`propose`/`confirm` (S02, chưa xây) | `tools/call` (+ MRTR nếu cần hỏi thêm) |
| Lọc theo quyền | Có (`active_commands_for`) | Spec cho phép lọc theo credential của request — **vẫn phải tự viết** |
| Client bên ngoài | Không dùng được | Claude Desktop, agent khác, SDK mọi ngôn ngữ dùng được |
| Thêm lệnh mới | Sửa registry + FE (types/mock/nút) | Sửa server; client đọc lại `tools/list` — FE không cần biết tên lệnh |
| Kiểm quyền 3 tầng, H1–H16, vùng đỏ, AI của tôi | Server Django | **Vẫn server Django** — MCP không làm hộ |
| Metadata nghiệp vụ (local/cloud, nhạy cảm, trần) | Trường riêng | Không có chuẩn → đặt trong `_meta` với tiền tố riêng |

### 2.3 Cái giữ nguyên dù chọn gì

- JSON Schema cho input/output, validate bằng `jsonschema` ở server.
- Kiểm quyền 3 tầng + "quyền hiệu lực = quyền người ∩ cấu hình ∩ trần ∩ công tắc" tại **thời điểm gọi**.
- Context builder allowlist default-deny (S06), chặn giá vốn 4 lớp, chặn PII ở adapter (S11).
- AuditLog `actor_kind=ai`, `ai_actor`, `proposal_ref` (S03).
- Router tĩnh theo nhãn (ADR §2.4): nhãn vẫn nằm ở server, chỉ đổi chỗ công bố.

---

## 3. Sinh tool tự động thay vì viết tay

### 3.1 Thư viện thật (kiểm PyPI/npm ngày 28/09/2026)

| Thư viện | Bản mới nhất | License | Làm gì | Độ trưởng thành | Rủi ro với Cá Về |
|---|---|---|---|---|---|
| **`mcp`** (Python SDK chính thức) | 2.2.0 (07/09/2026) | MIT | SDK server/client; FastMCP tích hợp sẵn; sinh `inputSchema` từ type hint | Production/Stable (classifier) | Kéo theo Starlette/anyio/pydantic ≥2.12; cần kiểm cách gắn vào Django WSGI. Có `jsonschema>=4.20` trùng với dự án |
| **`fastmcp`** (PrefectHQ) | 4.0.10 (25/09/2026) | Apache-2.0 | Framework server/client; có `from_openapi`, `from_fastapi`, ToolTransform | Rất nhiều bản phát hành (127) | Đổi major nhanh (3.x → 4.x trong 2026); tác giả tự khuyên **không** đưa bản sinh từ OpenAPI lên production |
| **`django-mcp-server`** | 0.5.7 (10/10/2025) | MIT | `MCPToolset`, `ModelQueryToolset`, decorator publish DRF view thành tool; endpoint `/mcp` | ~381 sao; bám spec **2025-03-26**; phụ thuộc `mcp>=1.8` (SDK 1.x) | **Tụt 3 bản spec**, chưa có bản mới gần 1 năm. Khi publish DRF view thì **auth class của DRF bị tắt**, phân trang tắt → phải tự đảm bảo kiểm quyền lại |
| **`drf-mcp`** | 0.1.1 (01/2026) | MIT | DRF + FastMCP 3 + drf-spectacular | **Alpha**, 2 bản | Quá non; kéo thêm drf-spectacular, OpenTelemetry/Jaeger |
| **`mcp-django`** (Josh Thomas) | 0.14.0 (07/2026) | MIT | MCP server cho **lập trình viên** khám phá project Django (shell, model) | Beta | Sai mục đích — là công cụ dev, không phải kênh nghiệp vụ. Đòi Django ≥5.2 (dự án đang <5.2) |
| **`django-mcp`** (kitespark) | 0.3.1 (05/2025) | MIT | Host tool MCP trong Django | Ít bản, ghim `mcp~=1.9.2` | Bỏ dở, tụt spec |
| **`@modelcontextprotocol/client`** (TS) | 2.1.0 (23/09/2026) | MIT | Client TS, có export điều kiện **`browser`** | Chính thức | Kéo `zod`, `jose`, `eventsource` → phải lazy-load (BR-AI-17) |
| **`@modelcontextprotocol/sdk`** (TS, gói gộp cũ) | 1.30.1 | MIT | Client+server gộp | Chính thức, dòng 1.x | Dòng cũ; bản 2.x đã tách `client`/`server` |
| **`@wllama/wllama`** | 3.6.1 | MIT | llama.cpp WASM; v3 có API kiểu OpenAI và **tool calling** | Dùng sẵn trong dự án | Tool calling chỉ "works out of the box" với model có chat template hỗ trợ tool |

Nguồn: PyPI JSON API `https://pypi.org/pypi/<tên>/json`, npm registry `https://registry.npmjs.org/<tên>` (Cao);
[django-mcp-server README](https://github.com/omarbenhamid/django-mcp-server) (Trung bình);
[FastMCP OpenAPI](https://gofastmcp.com/integrations/openapi), [Stop Converting Your REST APIs to MCP](https://jlowin.dev/blog/stop-converting-rest-apis-to-mcp) (Thấp — chỉ đoạn trích WebSearch, trang bị proxy chặn);
[wllama v3 guide](https://github.com/ngxson/wllama/blob/master/guides/intro-v3.md) (Cao).

### 3.2 Sinh từ DRF viewset / OpenAPI có hợp Cá Về không?

Không, vì 4 lý do:

1. **Dự án chưa có OpenAPI.** Không có `drf-spectacular`/`drf-yasg` trong `requirements.txt`. Phải thêm
   một tầng nữa.
2. **Viewset là CRUD, lệnh nghiệp vụ không phải CRUD.** Có 32 view và 18 custom action. Sinh tự động sẽ
   ra hàng chục tool mức thấp (`create_purchasereceipt`, `partial_update_…`, `submit`…). Model nhỏ chọn
   sai nhiều hơn khi nhiều tool (§4.2). Tool "nhập lô" là một hành động nghiệp vụ, gồm nhiều bước API.
3. **Service nhận model instance, không nhận args phẳng.** Vd `submit_receipt(*, receipt, actor)`. Không
   thể sinh schema thẳng từ chữ ký hàm. Cần một **serializer đầu vào** cho từng lệnh.
4. **Rủi ro quyền.** `django-mcp-server` tắt auth class của DRF khi publish view. Với dự án mà rò giá vốn
   hay PII là lỗi Critical, bất kỳ lối tắt nào qua kiểm quyền đều không chấp nhận được.

Tác giả FastMCP cũng khuyên: sinh từ OpenAPI chỉ để **mồi, thử nghiệm**; LLM chạy tốt hơn rõ với server
**được tuyển chọn** (curated). (Thấp — đoạn trích WebSearch từ gofastmcp.com, jlowin.dev)

### 3.3 Cách "không hard" thực tế: decorator cạnh service

Ý tưởng (minh hoạ, **không phải code đã chốt**):

```python
# apps/purchasing/receipts/commands.py  (cạnh services.py)
@ai_command(
    name="nhap_lo", title="Nhập lô mua tại cảng",
    input=NhapLoInput,            # DRF serializer / pydantic → sinh inputSchema
    output=NhapLoOutput,
    channel="local", sensitivity="cao",
    min_permissions=("purchasing.add_purchasereceipt",),
    max_autonomy="B", undo="huy_trang_thai", red_zone=False,
)
def nhap_lo(*, args, actor):
    ...  # gọi submit_receipt hiện có
```

- Registry **tự gom** từ decorator khi app load. Không còn danh sách 14 lệnh viết tay ở một file xa.
- `inputSchema` sinh từ serializer đầu vào → một nguồn duy nhất cho form UI, validate và AI.
- Test bất biến S01 vẫn chạy trên registry đã gom (tên duy nhất, 3 lệnh vùng đỏ, không PII trong context…).

### 3.4 Metadata nghiệp vụ đặt ở đâu

| Metadata | Nguồn sự thật (server) | Công bố ra client | Ghi chú |
|---|---|---|---|
| `min_permissions` | Decorator | Không cần công bố (đã lọc `tools/list`) | Kiểm lại lúc `tools/call` |
| Đọc/ghi | Decorator | `annotations.readOnlyHint` | Chỉ để UI/model biết. Không dùng kiểm quyền |
| Không đảo ngược (`chot_lo`) | Decorator | `annotations.destructiveHint=true`, `idempotentHint=false` | Gợi ý |
| `local`/`cloud` | Decorator | `_meta["vn.cave/channel"]` | FE chọn runtime; **BE vẫn chặn ngược chiều** (BR-AI-02) |
| Nhạy cảm | Decorator | `_meta["vn.cave/sensitivity"]` | |
| Trần mức, kiểu hoàn tác | Decorator | `_meta["vn.cave/max_autonomy"]`, `["vn.cave/undo"]` | Màn "AI của tôi" đọc để vẽ lựa chọn |
| Vùng đỏ | Decorator | `_meta["vn.cave/red_zone"]` | Công tắc Chủ nằm ở DB, kiểm lúc gọi |
| Mức hiện tại của user (Tắt/A/B/C) | **DB** (cấu hình AI của tôi, có phiên bản) | `_meta["vn.cave/autonomy"]` theo người gọi | Tool mức Tắt thì **không có** trong `tools/list` |
| `context_fields` | Decorator | **Không công bố** | Nội bộ BE như hiện nay |

Tiền tố `vn.cave/` chỉ là ví dụ; spec yêu cầu dạng reverse-DNS, nên dùng tên miền dự án thật nắm giữ.

---

## 4. Phía client

### 4.1 (a) ERP console trong trình duyệt làm MCP client

- **Được về kỹ thuật.** `@modelcontextprotocol/client` 2.1.0 có export điều kiện `browser`
  (`shimsBrowser.mjs`). (Cao — đọc `exports` từ npm registry). Streamable HTTP chỉ là POST + JSON/SSE,
  trình duyệt làm được bằng `fetch`.
- Console và API cùng quản trị, nên dùng session/token DRF hiện có là đủ. **Không cần OAuth** cho kênh nội
  bộ (spec để authorization là tuỳ chọn).
- Cần chú ý:
  - CORS và header `Mcp-Method`, `Mcp-Name`, `Authorization` phải được `django-cors-headers` cho phép.
  - Server phải kiểm `Origin` (MUST) — hiện dự án đã có danh sách origin cho CORS, dùng lại được.
  - Kích thước bundle: SDK kéo `zod`, `jose`, `eventsource`. Phải nằm trong chunk AI lazy-load (BR-AI-17).
  - **Phương án nhẹ hơn**: không dùng SDK, chỉ `fetch` hai method `tools/list` và `tools/call` (JSON-RPC
    rất mỏng). Nên spike đo cả hai.
- Tuỳ chọn tương lai: **WebMCP** (`document.modelContext.registerTool`) — chuẩn W3C Community Group để
  trang web đăng ký tool cho agent trong trình duyệt. Chrome đang origin trial, API vừa đổi từ `navigator`
  sang `document` (05/2026). **Chưa ổn định, chưa nên dùng.** (Thấp — chỉ đoạn trích WebSearch:
  [dev.to](https://dev.to/ai-agent-economy/webmcp-in-2026-which-browsers-support-navigatormodelcontext-complete-compatibility-status-1oe4),
  [openhermit](https://www.openhermit.com/blog/navigator-modelcontext-2026))

### 4.2 (b) Gemma 3n trên máy gọi tool

**Khả năng function calling:**
- Họ Gemma 3 **không có token tool riêng** trong chat template. Google hướng dẫn function calling bằng
  **prompt**: đưa danh sách hàm dạng JSON Schema vào prompt, model trả lời theo định dạng quy ước.
  (Thấp–Trung bình · [Simon Willison](https://simonwillison.net/2025/Mar/26/function-calling-with-gemma/),
  [HF discussion](https://huggingface.co/google/gemma-3-27b-it/discussions/24)). Chưa tìm được nguồn gốc
  khẳng định riêng cho **Gemma 3n**; giả định giống Gemma 3 — **phải spike**.
- wllama v3 có `createChatCompletion({tools, tool_choice})` kiểu OpenAI, nhưng chỉ chạy sẵn với model có
  template hỗ trợ tool (vd Qwen, Llama). (Cao · wllama v3 guide). Với Gemma 3n có thể phải tự dựng prompt
  và tự parse, hoặc ép JSON bằng grammar.
- Tin tốt: MCP `inputSchema` **chính là** `parameters` của định dạng OpenAI. Chuyển đổi 1-1, không mất gì.
- Dự phòng: **FunctionGemma 270M** (Google, 12/2025) là Gemma 3 270M huấn luyện riêng cho function
  calling, 32k context, thiết kế để **fine-tune** thành agent riêng. (Trung bình · [Google AI docs](https://ai.google.dev/gemma/docs/functiongemma),
  [HF model](https://huggingface.co/google/functiongemma-270m-it)). Có thể làm "bộ chọn lệnh" siêu nhẹ,
  nhưng tiếng Việt chưa được chứng minh.

**Ngân sách context:**
- Ước lượng từ registry hiện tại: 12 lệnh active, định dạng tool OpenAI = **~3.360 ký tự ≈ 950–1.100
  token** (chia 3,5 ký tự/token; mô tả tiếng Việt thường tốn hơn). `nhap_lo` riêng ~740 ký tự. (Đo trong
  repo ngày 28/09, ước lượng thô.)
- `engine.ts` mặc định `n_ctx = 2048` (trần 8192). Đưa cả 12 tool vào là **mất ~một nửa context**, còn chưa
  tính prompt hệ thống, câu hỏi, kết quả tool.
- Nghiên cứu RAG-MCP: độ chính xác chọn tool giảm **từ 85% với 5 tool xuống 45% với 20 tool**; lọc tool
  bằng truy hồi trước khi đưa vào model tăng độ chính xác hơn 3 lần trên benchmark của họ. Số liệu đo trên
  model lớn, model 2–4B còn nhạy hơn. (Trung bình · [arXiv 2505.03275](https://arxiv.org/abs/2505.03275))

**Cách chọn tập con tool (đề xuất, xếp theo thứ tự lọc):**
1. `tools/list` đã lọc theo **quyền** + **mức AI của tôi ≠ Tắt** (server).
2. Lọc `vn.cave/channel = local` (router tĩnh).
3. Lọc theo **màn hình đang mở**: màn Mua hàng → `nhap_lo`, `tra_hang`; màn Tồn kho → `tra_ton`, `tra_lo`.
   Mục tiêu **≤ 5 tool** mỗi lượt.
4. Nếu vẫn nhiều: hai bước — bước 1 model chỉ chọn **tên lệnh** từ danh sách tên + mô tả 1 dòng; bước 2 mới
   nạp schema của lệnh được chọn để điền args.
5. Luôn validate args bằng schema ở client (để hỏi lại nhanh) **và** ở server (để chặn thật).

### 4.3 (c) Cloud model gọi tool

- MiMo-V2.6-Flash là API kiểu OpenAI. Nó không nói MCP. Bên gọi (Django orchestrator, S11) phải làm
  "host": đổi `tools/list` sang `tools` của OpenAI, nhận `tool_calls`, gọi tool **trong Django**, gửi kết quả
  lại. Không cần MCP chạy qua mạng cho vòng này; gọi hàm nội bộ cùng registry là đủ.
- Mọi kết quả tool đi ra cloud **phải qua adapter** (allowlist, redaction, hard-block PII — S11). Vòng lặp
  agentic nhiều bước làm tăng số lần dữ liệu đi ra → chặn PII phải áp cho **từng** kết quả tool, không chỉ
  prompt đầu.
- Sampling của MCP (server mượn model của client) đã deprecated. Không xây theo hướng đó.

---

## 5. Bảo mật và quyền: MCP giúp hay gây khó

| Điểm | MCP giúp | MCP gây khó / không giúp | Việc phải làm ở Cá Về |
|---|---|---|---|
| Kiểm quyền 3 tầng | Spec cho `tools/list` lọc theo credential; spec yêu cầu server "implement proper access controls" | Không có cơ chế quyền nào sẵn | `tools/call` luôn chạy lại T1/T2/T3 + quyền hiệu lực tại thời điểm gọi (H1) |
| Mức AI của tôi + sàn cứng H1–H16 | `_meta` công bố được mức; `toolsListChanged` báo khi đổi | Annotations/`_meta` là **gợi ý, không tin được** | Kiểm ở server. Không dựa vào client ẩn nút |
| Per-user token | OAuth 2.1 + RFC 8707 + kiểm audience: token đúng người, đúng server | Dựng OAuth AS là việc lớn (django-oauth-toolkit hoặc bên ngoài) | Console: dùng session/token DRF có sẵn. OAuth chỉ khi mở cho agent ngoài |
| Không lộ giá vốn | — | Tool trả `structuredContent` → đi thẳng vào model | Serializer đầu ra dùng `CostFieldSerializerMixin`; `outputSchema` khác nhau theo quyền là không được — trả field `null`/bỏ field |
| PII khách không vào prompt | — | Client bên ngoài nhận nguyên kết quả tool, mình không kiểm soát nó gửi đi đâu | Tool không bao giờ trả PII (allowlist như `context_fields`); adapter vẫn chặn cho cloud |
| Prompt injection qua tool output | Spec: client nên validate kết quả, server nên "sanitize tool outputs" | Tool poisoning, rug pull là rủi ro đã biết của hệ sinh thái MCP | H10 giữ nguyên: chữ tự do (ghi chú khách, nội dung CK) không bao giờ quyết số tiền/đối tượng ở mức A/B. Chỉ tin server của mình (không cài MCP server lạ vào cùng agent) |
| Mô tả tool bị sửa | — | Model đọc `description` như lệnh | `description` là code trong repo, review qua PR. Không cho sửa từ DB/Admin |
| Audit `ai:<user>` | `_meta` mang `clientInfo` (client nào gọi) và trace OpenTelemetry | — | Ghi thêm `clientInfo.name` vào AuditLog note để phân biệt console vs agent ngoài |
| Xác nhận mức C | Elicitation/MRTR chuẩn hoá việc hỏi người | Client ngoài có thể tự trả lời elicitation | Giữ proposal + confirm trên ERP UI (BR-AI-06) |

Nguồn: spec `server/tools.mdx` mục Security, `basic/authorization/security-considerations.mdx` (Cao);
tổng quan rủi ro tool poisoning ([CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/),
[Practical DevSecOps](https://www.practical-devsecops.com/mcp-security-vulnerabilities/)) (Thấp — đoạn trích WebSearch).

**Kết luận mục 5:** MCP không làm hệ thống an toàn hơn hay kém đi ở phía server. Nó chỉ **mở thêm cửa**.
Cửa nội bộ (console) rủi ro như API hiện có. Cửa cho agent bên ngoài là rủi ro mới lớn (mất kiểm soát dữ
liệu sau khi tool trả về, đụng H14).

---

## 6. Đụng quyết định kiến trúc nào

Quyết định `decisions.md` 2026-09-09: Django 100% lõi. FastAPI **chỉ** nhận call từ bên thứ 3, không đụng
DB, gọi vào API nội bộ Django. **Không bên thứ 3 nào nối thẳng Django.**

### 6.1 Phương án 1 — MCP server trong Django, chỉ console nội bộ gọi

- Console là client của chính mình, như Shop/ERP đang gọi DRF. **Không vi phạm** 09/09.
- Endpoint là một view DRF (`POST /api/mcp`), dùng auth/permission hiện có. Không cần ASGI.
- Đây là chỗ đúng vì kiểm quyền, context builder, AuditLog đều ở Django.

### 6.2 Phương án 2 — Mở MCP cho agent bên ngoài (Claude Desktop, agent khác)

- **2a. Agent ngoài nối thẳng `/api/mcp` của Django → VI PHẠM 09/09.** Agent ngoài là bên thứ 3.
- **2b. Agent ngoài → MCP gateway ở FastAPI → Django → Không vi phạm**, nhưng khó:
  - Spec **cấm token passthrough**: FastAPI không được chuyển nguyên OAuth token của người dùng xuống Django.
    Cần token exchange hoặc Django cấp token riêng cho chặng sau; và Django phải biết "đang chạy thay ai"
    mà không mở lỗ "service token được đóng vai bất kỳ user" (confused deputy).
  - Cần OAuth Authorization Server (Protected Resource Metadata, CIMD, PKCE). Việc lớn.
  - Dữ liệu ra khỏi ERP tới nhà cung cấp model của agent ngoài → đụng **H14** (không gửi dữ liệu ra ngoài
    ERP khi Duy chưa duyệt), đụng memo pháp lý và hồ sơ phân loại rủi ro.
  - Hợp với vai "anti-corruption layer" của FastAPI, nên nếu làm thì làm theo 2b.

**Khuyến nghị:** làm Phương án 1 bây giờ. Phương án 2b để sau, là **quyết định riêng** của Duy (có pháp lý).

---

## 7. Ba phương án

- **(A) Giữ registry như hiện tại.**
- **(B) Registry vẫn là nguồn, xuất thêm endpoint MCP.** `CommandSpec` giữ nguyên; thêm `/api/mcp` dịch
  sang `Tool`.
- **(B+) — khuyến nghị.** Như B, nhưng **khai lệnh bằng decorator cạnh service**, schema sinh từ serializer
  đầu vào; registry tự gom; catalog trả đúng định dạng MCP `Tool` (+ `_meta vn.cave/*`); FE đọc `tools/list`
  thay vì biết tên lệnh.
- **(C) Mỗi function là MCP tool sinh tự động từ service/viewset, bỏ registry tay**, dùng thư viện
  (django-mcp-server / FastMCP).

### 7.1 Bảng so sánh

| Tiêu chí | A | B | **B+** | C |
|---|---|---|---|---|
| Thêm lệnh mới phải sửa | registry + FE | registry + (FE ít hơn) | **1 chỗ cạnh service**; FE không sửa | service (+ tinh chỉnh tool sinh ra) |
| Schema | viết tay | viết tay | **sinh từ serializer đầu vào** | sinh tự động (thô, cần curate) |
| Client ngoài dùng được | Không | Có (qua cửa sau) | Có (qua cửa sau) | Có |
| Kiểm quyền/sàn cứng | server | server | server | **dễ hổng**: thư viện tắt auth DRF, tool CRUD mức thấp |
| Số tool cho model nhỏ | 12–16 | 12–16 | 12–16 + lọc theo màn | **hàng chục** → Gemma chọn sai |
| Phụ thuộc thư viện mới | Không | Không bắt buộc (JSON-RPC mỏng) hoặc `mcp` | Như B | django-mcp-server (tụt spec) / fastmcp (đổi major nhanh) |
| Công sức (ước lượng thô) | 0 | BE ~2–3 ngày, FE ~1 ngày | BE ~4–6 ngày (decorator + serializer đầu vào 12 lệnh + endpoint), FE ~2 ngày | BE ~6–10 ngày + viết lại test quyền; rủi ro cao |
| Rủi ro | Duy thấy "hard"; lệch schema với service | Hai định dạng song song (catalog cũ + MCP) | Đổi contract S01 (FE types/mock) | Rò quyền/giá vốn; phụ thuộc thư viện non |
| Hợp decisions 09/09 | Có | Có (nếu chỉ console) | Có (nếu chỉ console) | Có nếu chỉ console; thư viện dễ dụ mở ra ngoài |

Con số ngày chỉ là ước lượng của người research, Tech Lead cần ước lại.

### 7.2 Phải đổi gì trong hồ sơ và code đã có

**Code đã xây (Lô 1):**
- **S01** (`backend/apps/ai/commands/`):
  - `registry.py`: `CommandSpec` giữ làm kiểu nội bộ; danh sách `SPECS` chuyển thành gom từ decorator.
    Thêm trường `title`, `max_autonomy`, `undo`, `red_zone` (01-analysis §11 vốn đã đòi thêm trần mức và
    kiểu hoàn tác — nên làm luôn một lần).
  - `serializers.py`: `command_item` → trả `Tool` MCP (`inputSchema`/`outputSchema` camelCase,
    `annotations`, `_meta`).
  - `api.py`: giữ `GET /api/commands/catalog/` một thời gian hoặc thay bằng `POST /api/mcp` (`tools/list`).
  - Test `test_registry.py` giữ gần nguyên; `test_catalog.py` sửa theo định dạng mới.
  - FE: `erp-console/features/ai/types.ts`, `api.ts`, `mock.ts` đổi theo contract mới.
- **S03** (AuditLog): **không phải đổi**. Có thể thêm tên client MCP vào `note`. Trường "phiên bản cấu hình"
  và "mức" là yêu cầu của 01-analysis, không do MCP.
- **S02** (chưa xây): thiết kế `execute`/`propose` thành `tools/call`. Mức C trả handle `proposal_id`;
  `confirm` vẫn là endpoint UI thường (không phải tool — AI không được tự confirm). Đây là thời điểm rẻ nhất.

**02b-tech-design (AI Native):**
- §2.1 Command registry: nguồn là decorator; schema từ serializer đầu vào.
- §3 S01/S02 contract: định dạng MCP `Tool`, `tools/call`, map mã lỗi (`isError` cho lỗi nghiệp vụ để model
  tự sửa; lỗi quyền là lỗi JSON-RPC/HTTP 403, không cho model "thử lại").
- Thêm mục "Endpoint MCP nội bộ": stateless, JSON response, kiểm `Origin`, header `Mcp-Method`.
- §2.2 ma trận chặn channel giữ nguyên; thêm dòng "annotations không phải kiểm quyền".
- S09 (chat tra cứu local): intent router chọn tool từ `tools/list` đã lọc theo màn hình.

**01-analysis (AI digital worker):**
- §11 "Registry: thêm trần mức…": ghi rõ metadata khai ở decorator, công bố qua `_meta`.
- §6 thêm sàn **H17**: "Nhãn/annotation công bố cho client chỉ là gợi ý; mọi chặn đều ở server."
- §14 Ngoài phạm vi: thêm "mở MCP cho agent bên ngoài ERP" (đụng H14, decisions 09/09).
- §4.1 "Tắt" = tool không có trong `tools/list` của AI người đó.

### 7.3 Khuyến nghị

1. Chọn **B+**, làm cùng lúc với S02 (chưa xây) để không phải sửa hai lần.
2. Endpoint MCP **trong Django**, chỉ cho console. Tự viết JSON-RPC mỏng hoặc dùng SDK `mcp` 2.x — quyết sau
   spike 2. **Không** dùng django-mcp-server (tụt spec, tắt auth DRF). **Không** sinh từ OpenAPI.
3. Không mở cho agent bên ngoài ở giai đoạn này. Khi cần: FastAPI gateway (2b), là quyết định riêng.
4. Không đổi quyết định đã chốt nào trong `decisions.md`. Router tĩnh theo nhãn, kiểm quyền server, PII
   chặn ở adapter đều giữ.

### 7.4 Spike cần làm để chứng minh

| # | Spike | Cách đo | Tiêu chí đạt (đề xuất) |
|---|---|---|---|
| 1 | **Gemma 3n gọi đúng tool với N tool** | 50 câu tiếng Việt giả (tái dùng bộ S17), N = 3, 5, 8, 12; n_ctx 2048 và 4096; E2B và E4B; wllama v3 `tools` vs prompt tự dựng vs grammar JSON | Chọn đúng tool ≥ 90% và args hợp lệ schema ≥ 90% ở N ≤ 5; đo độ trễ token đầu trên máy tham chiếu 8GB |
| 2 | **Endpoint MCP stateless trong Django** | View DRF xử lý `server/discover`, `tools/list`, `tools/call` theo 2026-07-28; kiểm bằng `@modelcontextprotocol/client` và MCP Inspector | Client chính thức nối được; `tools/list` khác nhau đúng theo 4 Group; `tools/call` bị 403 khi thiếu quyền dù client "biết" tên tool |
| 3 | **Client trong trình duyệt** | So SDK TS vs `fetch` tay: kích thước chunk gzip, có nằm trong chunk lazy-load không | Không tăng bundle trang không bật AI (BR-AI-17) |
| 4 | **Schema sinh từ serializer đầu vào** | Làm cho `nhap_lo` và `tra_ton`; so với schema viết tay hiện có | Test S01 xanh; form UI và AI dùng chung một schema |
| 5 | (tuỳ chọn) FunctionGemma 270M làm bộ chọn lệnh | Như spike 1, chỉ bước chọn tên | Chỉ đáng nếu Gemma 3n không đạt spike 1 |

---

## 8. Tổ chức tool theo 3 mảng nghiệp vụ (bổ sung theo Duy 28/09)

Duy nhận xét: *"Thiếu mất thu mua, bán hàng, customer service"*. Đúng: 14 lệnh hiện tại lệch về kho và
báo cáo. Dưới đây là bản đồ **function thật trong code** (đọc `backend/apps/*/services.py`,
`config/api_urls.py` ngày 28/09) có thể bọc thành tool, và phần còn thiếu.

Ký hiệu cột "Đã có trong registry": ✓ = đã là lệnh; — = chưa. "Ai dùng": NB = nhân viên nội bộ qua ERP;
KH = khách trên Shop.

### 8.1 Mảng 1 — Thu mua

| Tool đề xuất | Function/API thật đang có | Đã có trong registry | Đọc/Ghi | Ai dùng |
|---|---|---|---|---|
| `nhap_lo` | `purchasing/receipts/services.py::submit_receipt`; `PurchaseReceiptViewSet` + action `submit` | ✓ | Ghi | NB (kho) |
| `ghi_chi_phi_mua` (landed cost) | `purchasing/costs/services.py::record_purchase_cost`; `inventory/batches/services.py::recompute_landed_cost`; `PurchaseCostViewSet` | — (01-analysis §5 đề xuất trần C) | Ghi, **giá vốn** | NB (Chủ) |
| `tra_nha_cung_cap` | `SupplierViewSet` (CRUD) | — | Đọc | NB |
| `tao_nha_cung_cap` | `SupplierViewSet` create | — | Ghi | NB |
| `tra_hoa_don_mua` | `PurchaseInvoiceViewSet` (DocumentViewSet) | — | Đọc, **giá vốn** | NB (Chủ) |
| `lai_lo_theo_lo` / `theo_ky` | `reports/services.py::batch_pnl`, `period_pnl` | ✓ (`bao_cao_lo`, `bao_cao_ky`) | Đọc, **giá vốn** | NB (Chủ) |
| `mo_ban_lo` (publish) | `inventory/batches/services.py::publish_batch`; `BatchViewSet` action | — (01-analysis §5 "ngoài registry") | Ghi | NB |
| `chot_lo` | `close_batch` | ✓ (vùng đỏ) | Ghi | NB (Chủ) |

**Còn thiếu (chưa có service):**
- **Giá mua theo mùa**: không có bảng lịch sử giá mua. Giá mua nằm trên từng dòng phiếu nhập
  (`purchase_rate`). Tool `xu_huong_gia_mua` (so giá mua cùng mặt hàng qua các lô) cần **service đọc mới**
  gộp từ phiếu nhập. Nhạy cảm cao (giá vốn), chỉ Chủ.
- Huỷ phiếu nhập bằng trạng thái (01-analysis §3.1: chưa có) — điều kiện để `nhap_lo` lên mức B.
- Gợi ý nhà cung cấp/giá khi nhập (S14 auto-fill) — mới chỉ có thiết kế.

### 8.2 Mảng 2 — Bán hàng

| Tool đề xuất | Function/API thật đang có | Đã có trong registry | Đọc/Ghi | Ai dùng |
|---|---|---|---|---|
| `tra_hang` (sản phẩm, giá) | `catalog/pricing/services.py::effective_price`; `ItemViewSet`, `ItemPriceViewSet` (có `valid_from/valid_upto`) | ✓ | Đọc | NB; KH qua `ShopCatalogView` |
| `tra_combo` | `BundleLineViewSet`; `catalog/items/services.py::sellable_qty` (combo = min theo thành phần, BR-DM-06) | — | Đọc | NB, KH |
| `tra_ton_kha_dung` | `sellable_qty`, `inventory/batches/services.py::sellable_batches` | ~ (`tra_ton` trả theo lô, không phải "bán được bao nhiêu") | Đọc | NB, KH (chỉ số bán được, không lô/giá vốn) |
| `doi_gia_ban` | `ItemPriceViewSet`, `PricingRuleViewSet` (CRUD) | — (01-analysis đề xuất trần C) | Ghi | NB (Chủ/QL) |
| `tra_don` | `SalesOrderViewSet` (read-only) + `sales/orders/timeline.py` + `available_actions` | ✓ | Đọc | NB |
| Tạo đơn / giữ chỗ | `sales/orders/services.py::create_order` (giữ chỗ TTL 30'), `allocate_fefo`, `reserve`/`release`; chỉ qua `ShopOrderCreateView` | — | Ghi | **KH tự đặt**. **AI không được tạo đơn** (H7, BR-PQ-11) |
| Thanh toán | `confirm_payment` (IPN, Hệ thống), `confirm_payment_manual`, `resolve_payment`, `payment_available_actions` | ✓ (`xac_nhan_thanh_toan_tay`, vùng đỏ) | Ghi | NB (Chủ) |
| `huy_don_da_tra` | `cancel_paid_order` | — (vùng đỏ theo memo) | Ghi | NB (Chủ) |
| Giao hàng | `delivery/services.py::create_delivery_note`, `advance_status`, `mark_failed`, `return_to_warehouse`; `DeliveryNoteViewSet` action `status` | ~ (`cap_nhat_giao` draft) | Ghi | NB (NV giao) |
| `goi_y_fefo` | `allocate_fefo` | — (S15 thiết kế) | Đọc | NB |

**Còn thiếu:**
- `tra_ton_kha_dung` đúng nghĩa bán hàng (kg bán được theo mặt hàng/combo, không lộ lô): service đã có
  (`sellable_qty`), chỉ thiếu lệnh.
- Không có "tư vấn bán hàng" cho khách — ngoài phạm vi (xem 8.3).

### 8.3 Mảng 3 — Chăm sóc khách hàng (CSKH)

| Tool đề xuất | Function/API thật đang có | Đã có trong registry | Ai dùng |
|---|---|---|---|
| `tra_don_cua_toi` | `sales/orders/shop_api.py::ShopOrderLookupView` — mã đơn + **4 số cuối SĐT**; trả mã, trạng thái, tổng tiền, dòng hàng, trạng thái giao, hạn giữ chỗ. **Không trả tên/SĐT/địa chỉ** | — | KH |
| `trang_thai_giao` | Nằm trong kết quả trên (`delivery.status`) | — | KH, NB |
| `dong_thoi_gian_don` | `sales/orders/timeline.py` (đã bỏ `changes` thô, không giá vốn) | — (01-analysis §4.7 đề xuất `tom_tat_chung_tu`) | NB |
| Hoàn tiền | `refundable_amount`, `create_refund`, `create_invoice_refund`, `create_refund_for_payment`, `confirm_refund`, `mark_refund_failed`, `retry_refund`, `refund_available_actions` | ✓ (`tao_phieu_hoan`, `xac_nhan_hoan`) | NB (Chủ/QL) |
| Đổi trả / hàng hoàn về kho | `inventory/returns/services.py::apply_return`; `ReturnToStockViewSet` action `approve` | — | NB |
| Khiếu nại | **Không có** model/service nào (đã grep `complaint`, `ticket`, `khiếu nại`: 0 kết quả) | — | — |

**Còn thiếu:** toàn bộ phần **khiếu nại/ticket** (ghi nhận, phân loại, gán người, trạng thái, liên kết đơn).
Đây là tính năng nghiệp vụ mới, phải qua BA trước, không phải việc của lớp tool.

### 8.4 CSKH hướng tới khách là **thay đổi phạm vi**

Hiện đã chốt: *"Shop/khách hàng: không có AI"* (AI Native 01-analysis dòng 96, 275, 430; khách không có
tài khoản để cấp quyền cho AI). Đưa AI ra cho khách đụng ba thứ:

1. **Phạm vi**: lật một mặc định đã duyệt (🟡 PA trong AI Native 01-analysis). Duy phải chốt riêng.
2. **PII khách (bất biến 9, BR-AI-09, H2)**: tên, SĐT, địa chỉ không được vào prompt. Khi khách chat, chính
   khách có thể **tự gõ** SĐT/địa chỉ vào câu hỏi → PII vào prompt dù hệ thống không đưa.
3. **Pháp lý (NĐ 142/2026)**: mất miễn gắn nhãn nội bộ (Đ.18(4)). Phải cho khách **biết đang nói với AI**
   và gắn nhãn nội dung AI (Luật AI 134/2025 + NĐ 142 Đ.18). Hồ sơ phân loại phải viết lại và thông báo lại
   Bộ KH&CN (thay đổi làm tăng rủi ro → 15 ngày làm việc). Memo `01c-phap-ly.md` đã xếp "AI tự nhắn khách"
   là **ngoài phạm vi, cần hồ sơ riêng**. Nếu dùng cloud cho khách thì thêm nghĩa vụ không-huấn-luyện +
   zero retention như Q5.

**Cách làm an toàn nếu Duy muốn mở (đề xuất, theo thứ tự ưu tiên):**

| # | Biện pháp | Chi tiết |
|---|---|---|
| 1 | **Bắt đầu không có AI** | Trang "Tra đơn" tất định đã có (`ShopOrderLookupView`). Thêm "câu trả lời soạn sẵn" theo trạng thái (như bảng "vì sao" ở §4.7) → giải quyết phần lớn câu hỏi CSKH mà **không** vướng Luật AI |
| 2 | **Tool CSKH chỉ trả mã và trạng thái** | Output allowlist: mã đơn, trạng thái, tổng tiền, dòng hàng, trạng thái giao, hạn giữ chỗ. Không tên, SĐT, địa chỉ, ghi chú khách, nội dung CK, giá vốn. `outputSchema` khoá cứng, test bất biến như `PII_FORBIDDEN_KEYS` |
| 3 | **Xác minh ngoài model** | Khách nhập mã đơn + 4 số cuối SĐT (hoặc OTP) vào **ô form riêng**, không qua chat. Server xác minh rồi cấp **handle ngắn hạn** gắn đúng 1 đơn. Model chỉ thấy handle, không thấy số điện thoại. Tool từ chối mọi mã đơn khác handle |
| 4 | **Chặn PII ở đầu vào chat** | Redaction SĐT/email/địa chỉ trên câu khách gõ **trước khi** vào model (dùng lại bộ lọc adapter S11). Ưu tiên model **on-device** trên máy khách? Không khả thi: Shop phải nhẹ (BR-AI-17), khách không tải model 2–3GB → thực tế phải dùng cloud → chặn PII là bắt buộc |
| 5 | **Chỉ đọc** | AI cho khách không có tool ghi. Yêu cầu hoàn/đổi/khiếu nại → AI tạo **yêu cầu chờ người xử lý** (cần tính năng khiếu nại mới), không tự hoàn (H9: quyết định ảnh hưởng khách trần C) |
| 6 | **Gắn nhãn + đường gặp người** | Nhãn "Trợ lý AI" rõ ràng, nút "Gặp nhân viên", ghi chính sách quyền riêng tư về xử lý tự động (NĐ 356/2025) |
| 7 | **Chống dò** | `ShopOrderLookupView` hiện dùng 4 số cuối SĐT, **không có throttle/rate limit nào** trong toàn bộ `backend/` (grep `throttl|ratelimit|rate_limit`, trừ test: 0 kết quả). 4 chữ số = 10.000 tổ hợp. Mở cho AI thì kẻ xấu dò nhanh hơn. Cần rate limit (theo IP + theo mã đơn) **trước** khi gắn AI. Đây là lỗ hổng riêng, nên báo Tech Lead dù có làm AI hay không |

### 8.5 Có nên tách 3 MCP server theo mảng?

| Cách | Ưu | Nhược |
|---|---|---|
| **1 server, 3 nhóm tool** (nội bộ) | Một endpoint, một chỗ kiểm quyền/AuditLog; nhóm dùng để lọc tool theo màn hình (§4.2 bước 3) | Cần quy ước nhóm trong `_meta` (vd `vn.cave/domain = thu_mua / ban_hang / cskh`) |
| 3 server nội bộ riêng | "Sạch" về khái niệm | Không thêm an toàn gì: cùng Django, cùng DB, cùng user. Thêm 3 endpoint, 3 bộ test. Client phải nối 3 nơi |
| **Server riêng cho khách (CSKH công khai)** | Tách hẳn mặt tấn công: auth khác (handle đơn, không phải user nội bộ), tool chỉ đọc, allowlist cứng, rate limit riêng. Không bao giờ lộ tool nội bộ dù lỗi lọc quyền | Thêm một endpoint; phải chốt đặt ở đâu |

**Đề xuất:**
- Nội bộ: **1 MCP server trong Django, 3 nhóm tool** theo mảng (`_meta` domain). Nhóm dùng để lọc theo màn
  hình và để màn "AI của tôi" chia tab Thu mua / Bán hàng / CSKH. Quyền vẫn theo từng tool.
- Khách (nếu Duy mở): **tách riêng** một endpoint công khai, chỉ vài tool đọc (`tra_don_cua_toi`,
  `trang_thai_giao`, `tra_hang`, `tra_combo`, `tra_ton_kha_dung`). Khách vào qua Shop (Next.js gọi Django như
  hiện nay) → **không vi phạm** decisions 09/09. Không dùng chung danh sách tool với nội bộ.

**Tool nên thêm vào registry theo thứ tự (chỉ nội bộ, rủi ro thấp trước):**
1. Đọc, không giá vốn: `tra_ton_kha_dung`, `tra_combo`, `tra_nha_cung_cap`, `trang_thai_giao`,
   `tom_tat_chung_tu`, `giai_thich_buoc_tiep`.
2. Đọc, giá vốn (chỉ Chủ): `tra_hoa_don_mua`, `xu_huong_gia_mua` (cần service mới).
3. Ghi, trần C: `ghi_chi_phi_mua`, `doi_gia_ban`, `mo_ban_lo`, `huy_don_da_tra` (vùng đỏ).
4. CSKH cho khách: **sau** khi Duy chốt phạm vi + có hồ sơ pháp lý + có rate limit + có tính năng khiếu nại.

---

## 9. Câu hỏi cần Duy chốt

| # | Câu hỏi | Phương án | Đề xuất |
|---|---|---|---|
| M1 | Đi theo hướng nào? | A giữ nguyên · B xuất thêm MCP · **B+** decorator + định dạng MCP · C sinh tự động | **B+** |
| M2 | Có mở cho agent bên ngoài ERP (Claude Desktop, agent khác) không? | (a) Không, chỉ console · (b) Có, qua FastAPI gateway + OAuth, là hồ sơ riêng có pháp lý | **(a)** giai đoạn này |
| M3 | Làm lúc nào? | (a) Gộp vào S02 (chưa xây) · (b) Sau khi xong AI Native Lô 2 | **(a)** — rẻ nhất |
| M4 | Có chạy spike 1 (Gemma gọi tool) trước khi viết 02b bản mới không? | (a) Có, chặn thiết kế S09 · (b) Không, làm song song | **(a)** — nếu Gemma không gọi tool ổn, cần kiến trúc "chọn tên trước, điền args sau" |
| M5 | Mức C khi AI được gọi qua MCP xác nhận ở đâu? | (a) Proposal + bấm trên ERP (như BR-AI-06) · (b) Elicitation MCP ở client | **(a)** — client ngoài có thể tự trả lời elicitation |
| M6 | Có mở AI CSKH cho **khách** trên Shop không? (lật "Shop không có AI") | (a) Không, CSKH chỉ là tool nội bộ cho nhân viên trả lời khách · (b) Có, chỉ đọc, endpoint riêng, xác minh mã đơn/OTP, hồ sơ pháp lý riêng · (c) Trước mắt làm "câu trả lời soạn sẵn" không AI trên trang Tra đơn | **(a) + (c)** giai đoạn này; (b) là hồ sơ riêng |
| M7 | Tổ chức tool | (a) 1 server nội bộ, 3 nhóm theo mảng · (b) 3 server nội bộ | **(a)**; server khách tách riêng nếu M6 = (b) |
| M8 | Khiếu nại/ticket chưa có trong hệ thống | (a) Mở hồ sơ BA riêng · (b) Để sau | **(a)** nếu muốn CSKH thật; tool không thay được tính năng thiếu |

---

## 10. Danh sách nguồn

Spec MCP 2026-07-28 (Cao — đọc bản clone repo chính thức ngày 28/09/2026):
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/index.mdx (mục `_meta`)
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/transports/streamable-http.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/index.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/authorization/security-considerations.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/basic/patterns/mrtr.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/client/elicitation.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/deprecated.mdx
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/schema.mdx (`ToolAnnotations`)

Blog/tổng quan (Trung bình):
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://github.com/omarbenhamid/django-mcp-server
- https://github.com/ngxson/wllama/blob/master/guides/intro-v3.md (Cao)

Metadata gói (Cao — API registry, lấy 28/09/2026):
- https://pypi.org/pypi/mcp/json · https://pypi.org/pypi/fastmcp/json · https://pypi.org/pypi/django-mcp-server/json
- https://pypi.org/pypi/drf-mcp/json · https://pypi.org/pypi/mcp-django/json · https://pypi.org/pypi/django-mcp/json
- https://registry.npmjs.org/@modelcontextprotocol/client · https://registry.npmjs.org/@modelcontextprotocol/sdk
- https://registry.npmjs.org/@wllama/wllama

Chỉ đoạn trích WebSearch (Thấp — trang gốc bị proxy chặn hoặc chưa đọc):
- https://gofastmcp.com/integrations/openapi · https://jlowin.dev/blog/stop-converting-rest-apis-to-mcp
- https://arxiv.org/abs/2505.03275 (RAG-MCP) — Trung bình (abstract nhất quán nhiều nguồn)
- https://simonwillison.net/2025/Mar/26/function-calling-with-gemma/ · https://huggingface.co/google/gemma-3-27b-it/discussions/24
- https://ai.google.dev/gemma/docs/functiongemma · https://huggingface.co/google/functiongemma-270m-it
- https://dev.to/ai-agent-economy/webmcp-in-2026-which-browsers-support-navigatormodelcontext-complete-compatibility-status-1oe4
- https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-auto-execution-20260701/
- https://www.practical-devsecops.com/mcp-security-vulnerabilities/

Chưa kiểm được (ghi để không bịa):
- Gemma 3n có template tool riêng hay không — chưa có nguồn gốc; giả định giống Gemma 3.
- wllama v3 có nhận `response_format`/grammar JSON Schema hay không — chưa kiểm; spike 1 kiểm.
- SDK Python `mcp` 2.x gắn vào Django WSGI thế nào — chưa kiểm; spike 2 kiểm.
