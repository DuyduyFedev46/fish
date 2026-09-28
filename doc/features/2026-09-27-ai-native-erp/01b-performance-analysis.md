# AI Native ERP — Phân tích lại dưới lăng kính hiệu năng
> BA · 2026-09-27 · Trạng thái: **CHỜ DUYỆT**
>
> **Bối cảnh:** Duy chốt khi duyệt story: *"việc tích hợp AI mà đánh đổi performance là KHÔNG ĐÁNG"*
> (ghi thành BR-AI-17, ADR điểm 10) và yêu cầu đội phân tích lại nghiêm túc dưới góc hiệu năng
> trước khi cho code. File này là bản phân tích đó — bổ sung cho `01-analysis.md`, không thay thế.
>
> **Nguồn đối chiếu:** `00-adr-ai-native.md` (điểm 9–10), `01-analysis.md` (BR-AI-01…17, UC-AI,
> §8/§9), `02-stories.md` (S01–S17, 7 lô, rủi ro), `02b-tech-design.md` (mục 1, 5, 7, 8, phụ lục A),
> `05-deep-research.md` (mục D; research 4.1/4.2/5.3 về giới hạn RAM trình duyệt); đối chiếu code
> hiện trạng ngày 2026-09-27: `frontend/` (Next 14.2.35 static export, React 18 + `qrcode`, Shop +
> Landing, không AI), `erp-console/` (Next 14.2.35 static export, React 18, cấu trúc
> `app/(console)/` + `features/auth/` + `shared/`, chưa có `features/ai/`, chưa có dependency AI nào,
> đang dùng Google Fonts render-blocking trong `app/layout.tsx`, chưa có header COOP/COEP).

---

## 1. Tuyên bố nguyên tắc

1. **Không lật quyết định AI Native.** ADR đã chốt (Duy + PA), model on-device Gemma 3n (32k)
   đã chốt khi duyệt story (ADR điểm 9), Q1–Q6 và T1–T6 giữ nguyên. File này không mở lại bất kỳ
   quyết định nào trong số đó.
2. **Hiệu năng thắng, không thương lượng.** Đây là diễn giải chi tiết của BR-AI-17 (chốt của
   Duy): website/ERP chạy mượt như khi chưa có AI. Mọi story AI phải đạt ngân sách hiệu năng ở
   mục 3; story nào không đạt → cắt hoặc hoãn theo thứ tự thoái lui ở mục 6. Hiệu năng không phải
   là một AC "nên có" mà là **điều kiện nghiệm thu** ngang với không-rò-giá-vốn.
3. **AI là lớp cộng thêm.** Tắt `AI_ENABLED` hoặc người dùng không mở màn AI → hệ thống y hệt cũ:
   không tải code/model AI, không chạy runtime, không request mới. Nghiệp vụ (kênh `ui`) không bao
   giờ phụ thuộc AI (BR-AI-10).
4. **Mọi con số ở mục 3 là ĐỀ XUẤT để Duy chốt.** Chưa chốt thì không phải ngưỡng chặn; QA đo và
   báo cáo theo khung này, Duy chốt số cuối cùng.
5. **Đo trước khi code.** Lô 1 phải ghi baseline hiệu năng thật của ERP console (bundle khởi đầu,
   TTI, CLS) trước khi thêm bất kỳ dòng AI nào — không có baseline thì mọi so sánh "không đánh đổi"
   về sau là không kiểm chứng được.

---

## 2. Kiểm kê bề mặt hiệu năng — AI chạm vào đâu

### 2.1 Shop/Landing của KHÁCH (`frontend/`) — AI KHÔNG chạm, phải giữ nguyên một byte

- Phạm vi đã chốt: AI Native chỉ trong ERP nội bộ (01-analysis §5, 🟡 G1; 02-stories "Ngoài phạm
  vi"). Khách không có tài khoản/quyền để cấp cho AI.
- Hiện trạng: `frontend/package.json` chỉ có Next/React/`qrcode` — không dependency AI.
- **Yêu cầu hiệu năng:** sau toàn bộ dự án AI Native, bundle/TTI/CLS/request của Shop và Landing
  **không đổi một byte, một mili-giây, một request**. Đây là bề mặt nhạy nhất vì nó là doanh thu.
- Điều kiện giữ được: hai app là hai `package.json` độc lập, không shared package. **Kẽ hở tiềm ẩn:**
  nếu sau này đội gộp shared lib UI giữa 2 app (vd package nội bộ) thì phải có test build chặn
  chunk AI lọt vào `frontend/` — đề xuất rule ở mục 3.
- Header COOP/COEP (nếu phải thêm cho wllama — xem K1) **chỉ áp cho `erp-console`**, không áp cho
  `frontend/` (đổi header site khách = rủi ro tương thích + font bên thứ 3, không cần thiết vì Shop
  không có AI).

### 2.2 ERP console của nhân viên (`erp-console/`) — bề mặt chịu toàn bộ chi phí AI

Đặc điểm môi trường thật (từ hồ sơ + research):
- Máy nhân viên: **Duy chốt 27/09 — Android ≥ 8GB RAM, Windows ≥ 8GB RAM** (thay mục tiêu 12–16GB cũ).
- Mạng tại cảng: 4G, yếu và không ổn định (01-analysis §9 "Mạng yếu tại cảng").
- **iPhone tạm chưa hỗ trợ (Duy, 27/09)** — chi phí lên App Store quá cao. Console là web app (mở được
  qua Safari) nhưng không cam kết AI local trên iOS; không cần spike Sailor2-1B cho iPhone (giới hạn
  tab Safari ~1–1,5GB RAM — research 4.1 — vẫn đúng nếu sau này mở lại hỗ trợ).
- Hiện trạng console: gọn (React + Next 14, không lib nặng), nhưng `app/layout.tsx` đang tải
  Google Fonts (Inter + JetBrains Mono + Material Symbols) render-blocking — **nền TTI hiện tại đã
  phụ thuộc mạng bên thứ 3**, cần lưu ý khi đo TTI < 2s (xem K8).

Các thành phần AI sẽ sống ở đây (theo 02b mục 1.2): runtime wllama, ASR, chat, voice, alerts,
usage, components — đều là chi phí FE tập trung vào console.

### 2.3 Django Admin — chi phí ≈ 0

- Admin chạy server-side; không có kế hoạch nhúng runtime AI vào template Admin (01-analysis §11).
- Việc "chuyển dần Admin qua lớp lệnh" (ADR 3.3) là refactor backend gọi service — không thêm JS,
  không ảnh hưởng FE nào.
- Ngân sách duy nhất cho Admin: **0 thay đổi hiệu năng** — giữ nguyên.

### 2.4 Điểm kỹ thuật — nơi chi phí nằm

| Điểm | Chi phí | Đặc điểm cần quản |
|---|---|---|
| **Bundle JS** | Chunk AI lazy (runtime wllama WASM ~2–4MB PA; ASR model riêng) + code gating nhỏ trong bundle khởi đầu | Phải chặn prefetch chunk AI; không import AI trong đường khởi động (xem K2, K9) |
| **TTI / CLS** | 0 nếu lazy đúng; rủi ro CLS ở khối insights S13 + font nếu COEP làm hỏng font (K1) | TTI < 2s (chốt BR-AI-17); đo trên mạng thật |
| **Main-thread blocking** | Suy luận wllama (CPU WASM), ASR nhận dạng, summarization — tất cả phải trong Web Worker | Ngân sách: long task do AI = 0ms trên main thread |
| **RAM trình duyệt** | Model Gemma 3n Q4 **~1,9–2,8GB** (E2B 2,6B / E4B 4,4B — ADR điểm 9) + KV cache theo `n_ctx` + runtime + ASR 50–70MB (T2) + trang ERP | iPhone ngoài phạm vi hỗ trợ (Duy 27/09) nên ngưỡng so = máy 8GB; KV cache 32k cấp phát đủ có thể thêm ~0,5–1,5GB (PA — **S17 phải đo**, không tin số này) |
| **Tải model qua mạng** | 1,9–2,8GB một lần; Wi-Fi cảng 10–20Mbps → **hàng chục phút**; cache hỏng → tải lại | Chỉ Wi-Fi + đồng ý (BR-AI-12); phải có % + ước lượng thời gian + hủy được (K6) |
| **Độ trễ lệnh cloud** | MiMo-V2.6-Flash 15B active qua adapter: ước tính p50 ~2–5s, p95 ~10–20s (PA) | Gọi async, không chặn render; timeout; fallback số liệu thô (S13-AC2) |
| **Suy luận local (độ trễ)** | CPU WASM **5–20 tok/s** (research 4.2), WebGPU "nhanh hơn nhiều" nhưng **chưa từng đo trên Adreno/VN model** (research 01 mục 2) | Câu trả lời phải stream từng token; ngưỡng phản hồi ở mục 3 |
| **Polling alerts (S12)** | Request định kỳ trên 4G cảng | Tần suất ≤ 1 lần/phút, chỉ khi màn liên quan mở (mục 3) |

---

## 3. Ngân sách hiệu năng đề xuất (để Duy chốt)

> Nguyên tắc chung: người không bật AI / không mở màn AI có chi phí = 0 (0KB tải, 0ms main-thread,
> 0 request AI). "AI tắt" = `AI_ENABLED=false` **hoặc** người dùng chưa từng mở màn AI trong phiên.

### A. Shop/Landing (`frontend/`) — ngân sách cứng, không thương lượng

| Chỉ số | Ngân sách |
|---|---|
| Delta bundle (gzip) | **0KB** |
| Delta TTI / CLS | **0ms / 0** |
| Request mới | **0** |
| Header đổi (COOP/COEP…) | **Không áp** cho `frontend/` |
| Kiểm chứng | Build `frontend/` trước/sau dự án AI: diff danh sách chunk = rỗng. Nếu sau này có shared package giữa 2 app → phải kèm test này trong CI |

### B. ERP console — người không bật AI

| Chỉ số | Ngân sách đề xuất | Ghi chú |
|---|---|---|
| Delta bundle khởi đầu (gzip) | **≤ 5KB** | Do code gating (ẩn màn AI, fetch status). 0KB tuyệt đối không khả thi với 1 bản build vì `AI_ENABLED` là env server-side — xem K2 và câu hỏi 🔴 P2 |
| Delta TTI | **≤ +100ms**, TTI tổng < 2s | Đo trên máy tham chiếu, mạng thật (K8) |
| Main-thread block do code AI | **0ms** (không long task do AI) | Mọi module AI chỉ qua dynamic import sau khi kiểm `ai_enabled` |
| Request AI khi tắt | **0** (chỉ 1 request `GET /api/ai/status` lúc đăng nhập — S05; thất bại → coi tắt) | |

### C. ERP console — người dùng AI (bật AI, đã đồng ý tải model)

| Chỉ số | Ngân sách đề xuất | Ghi chú |
|---|---|---|
| TTI khi model đang tải background | vẫn < 2s | Tải model không bao giờ chặn tương tác (BR-AI-12, S08-AC1) |
| Chunk AI (wllama runtime) | chỉ tải khi mở màn AI lần đầu; **không prefetch** (K9) | |
| Model load từ cache (lần 2 trở đi) | < 30s (ADR 3.2) | Cache Storage ưu tiên, IndexedDB fallback; đọc theo chunk trong worker, không đọc 2GB vào ArrayBuffer |
| Tải model lần đầu | chỉ Wi-Fi + đồng ý; hiện % + ước lượng thời gian + nút hủy; không cam kết "core ~200MB trước" (K5) | |
| RAM trình duyệt khi suy luận | ≤ 3GB (E2B) / ≤ 4GB (E4B) tổng cộng — máy < 8GB (`navigator.deviceMemory` best-effort) → không cho tải | S17 đo RAM đỉnh thật, số này là khung cảnh báo |
| `n_ctx` khi load model | **2048 (mặc định) / 4096 — KHÔNG load 32k** kể cả model hỗ trợ (K3) | Đúng BR-AI-13; 32k chỉ đo thử trong S17 |
| Long task main thread khi đang suy luận/ASR | **0ms** — wllama + ASR + summarization trong Web Worker (tách 2 worker ASR/LLM, K4) | |
| Phản hồi chat (câu tra cứu) | **≤ 5s** stream token đầu ≤ 3s, trên máy tham chiếu | Trả lời theo mẫu từ kết quả API — không bắt LLM viết lại (mục 5, S09) |
| Voice → form điền xong | **≤ 8s** trên máy tham chiếu | |
| Intent-classify | ≤ 2s | |
| Khối insights (S13) | gọi async, không chặn render; timeout 10s; quá → số liệu thô; không retry quá 1 lần (đã chốt S11) | |
| Polling alerts (S12) | ≤ 1 lần/phút, chỉ khi mở màn liên quan | |

### D. Django Admin + backend

| Chỉ số | Ngân sách đề xuất |
|---|---|
| Admin FE | 0 thay đổi |
| API mới (`catalog`, `context`, `execute`, `alerts`) | p95 ≤ 300ms; không đáng kể so với API hiện tại (registry in-memory, context tái dùng serializer hiện có) |
| `cloud/complete` | chờ provider (p95 ~20s) — timeout server 20s, không retry quá 1 lần; gọi FE luôn async |

### E. Mạng / dữ liệu

| Chỉ số | Ngân sách đề xuất |
|---|---|
| Tải model qua 4G/5G | **Cấm tuyệt đối** (BR-AI-12 — đã chốt) |
| Dữ liệu lệnh cloud/câu | vài KB–chục KB — nhỏ, qua adapter |
| Suy luận local | 0 byte ra mạng (S08-AC4 — QA bắt bằng E2E) |

---

## 4. Đối chiếu thiết kế hiện tại (BR-AI-17 và các rule liên quan)

### 4.1 Đã bảo đảm bởi thiết kế hiện có

| Điểm | Cơ chế đã có | Nguồn |
|---|---|---|
| Lazy-load code AI | import động `@wllama/wllama`, module `features/ai/` tách riêng; mock LLMock cho dev | BR-AI-17, 02b mục 3 S08 |
| Runtime + suy luận ngoài main thread | "runtime + suy luận chạy trong Web Worker" | BR-AI-17, 02b S08 ghi chú |
| Người không bật AI không tải model | BR-AI-12 + S08-AC2/AC3/AC7 + gating nav theo `ai_enabled` | 02b Lô 2 |
| TTI < 2s, tải model background sau khi tương tác được | ADR 2.10/3.2, S08-AC1 | — |
| AI tắt = hệ thống y hệt | AC "AI tắt" trong S02/S05/S07/S08/S09/S10/S11/S12/S13/S14 | 02b mục 7 |
| Máy yếu → không cố tải, nhập tay (không "local giả") | BR-AI-12, S08-AC3, router chặn ngược BR-AI-02 | — |
| Cloud không chặn luồng nghiệp vụ | S13-AC2 (cloud lỗi → số liệu thô), lệnh cloud async | BR-AI-17 |
| Status/usage không gating nhầm | D3: `status`/`usage` luôn 200 kể cả AI tắt; D4: alerts ngoài `/api/ai/` | 02b mục 9 |
| QA đo perf mỗi lô | 02b mục 7, dòng "AI kéo tụt hiệu năng website" | — |
| Không chạy model > ~1GB trên iPhone | S08 ghi chú: "chỉ phép model ≤ ~1GB trên iPhone — research 5.3" — iPhone đã ngoài phạm vi (Duy 27/09), giữ nếu sau này mở lại | — |

### 4.2 Kẽ hở — chưa được thiết kế/chốt (cần xử lý trước khi code FE AI)

| # | Kẽ hở | Vì sao là vấn đề hiệu năng | Đề xuất xử lý |
|---|---|---|---|
| **K1** | **COOP/COEP chưa được thiết kế.** wllama v3 (JSPI + Memory64, multi-thread) cần header `Cross-Origin-Opener-Policy`/`Cross-Origin-Embedder-Policy` (research 01: "cần header COOP/COEP, memory64 → loại Safari"). 02b nhắc "xem rủi ro R7" nhưng bảng rủi ro mục 7 không có hàng R7 — chưa ai thiết kế. | Nếu bật COEP toàn trang ERP → mọi tài nguyên bên thứ 3 (Google Fonts đang render-blocking ở `layout.tsx`) cần CORP/CORS; cấu hình sai → font hỏng → CLS/TTI tệ hơn lúc chưa có AI. Nếu không có COEP → wllama multi-thread/WebGPU có thể không chạy hoặc rớt về single-thread chậm. | Lô 1 (cùng S08): spike header trên Firebase Hosting (`firebase.json` custom headers cho `erp-console`), tự host font (hoặc crossorigin đúng) khi bật COEP; đo TTI trước/sau. **Không bật COEP cho `frontend/`.** Ghi vào S08 hoặc tài liệu triển khai. |
| **K2** | **"Chi phí = 0 khi AI tắt" chưa được định nghĩa đo được.** `AI_ENABLED` là env server-side → mọi user dùng cùng 1 bản build, code AI vẫn nằm trong artifact. | Nếu QA không có chuẩn đo thì AC "AI tắt = y hệt cũ" không kiểm chứng được — đúng điều Duy lo. | Chốt chuẩn (mục 3.B): không tải chunk AI + không chạy code AI (kiểm `ai_enabled` trước khi dynamic import) + delta bundle khởi đầu ≤ 5KB gzip + 0 request AI. Nếu Duy muốn 0KB tuyệt đối → phương án 2 bản build (câu hỏi 🔴 P2). |
| **K3** | **"Context 32k" có thể bị FE hiểu nhầm thành `n_ctx=32768` khi load model.** KV cache cấp phát đủ 32k có thể chiếm thêm ~0,5–1,5GB RAM (PA) — trên máy 12–16GB desktop còn đỡ, trên mobile browser là crash. | Load `n_ctx=32768` trong khi BR-AI-13 chỉ cho dùng 2048/4096 = lãng phí RAM lớn, không đổi chất lượng câu trả lời. | Chốt: **`n_ctx` = `AI_MAX_CONTEXT_TOKENS` (2048 mặc định), không dùng 32k**; S17-AC2 đo cả "context 2K/32K" chỉ để báo cáo, không phải để bật. Ghi vào S08 ghi chú kỹ thuật. |
| **K4** | **ASR + LLM cùng lúc chưa được quy định tách worker.** S10 = Vosk ASR (50–70MB) + wllama suy luận — nếu cùng 1 worker, LLM chiếm CPU → ASR trễ, mic buffer tràn, voice "đơ". | Voice là entry point ưu tiên 1 (ADR 2.8) — hỏng trải nghiệm = đánh đổi hiệu năng thực tế. | Tách 2 worker (ASR worker / LLM worker); RAM tăng nhẹ (~ASR model), chấp nhận trên desktop; trên iPhone không chạy voice (BR-AI-12 nhập tay). |
| **K5** | **"Tải core ~200MB trước, full sau" (ADR 2.10) không khả thi với GGUF/wllama** — cần gần đủ file mới load được, wllama không hỗ trợ suy luận giữa chừng khi tải dở. | Nếu FE cố làm "progressive" theo ADR chữ nghĩa sẽ kẹt thiết kế; nếu làm sai còn hỏng cache. | Giữ nguyên tắc ADR (đồng ý + Wi-Fi + background), đổi cơ chế: tải tuần tự toàn file + % + ước lượng thời gian + hủy + resume theo chunk. Không coi đây là lật ADR — chỉ làm rõ cơ chế với GGUF. |
| **K6** | **Chưa có UX/quy định cho tải model 2GB trên Wi-Fi yếu.** Wi-Fi cảng 10–20Mbps → 2GB mất ~15–30 phút; đóng tab giữa chừng → cache hỏng → tải lại; đổi model (S17) → tải lại toàn bộ. | Người dùng tưởng treo; tốn băng thông; ấn tượng "AI làm máy chậm". | Phải có: % tiến trình + dung lượng + thời gian ước tính + nút hủy; cache key theo version/URL model; thông báo trước khi xoá cache cũ. Thêm vào S08-AC. |
| **K7** | **Chưa có baseline hiệu năng trước khi có AI.** "QA đo perf mỗi lô" (02b mục 7) nhưng không có số khởi điểm → không chứng minh được "không đánh đổi". | Mọi tranh cãi về sau đều không có dữ kiện. | Lô 1: QA đo và ghi baseline (bundle gzip, TTI, CLS, long task) của màn overview/danh sách ERP console + ghi vào `04-qa-report.md`. |
| **K8** | **TTI < 2s hiện tại đã phụ thuộc Google Fonts render-blocking** (Inter, JetBrains Mono, Material Symbols ở `erp-console/app/layout.tsx`). | Đo trên localhost/Wi-Fi văn phòng thì đẹp, đo tại cảng 4G thì font bên thứ 3 kéo TTI — và sẽ bị đổ lỗi cho AI. | Tách việc: (a) tối ưu font (tự host hoặc `display=swap` + preload) là việc hiệu năng nền, làm cùng Lô 1; (b) chuẩn đo TTI: Wi-Fi văn phòng làm ngưỡng chặn, 4G cảng đo tham khảo (câu hỏi 🔴 P3). |
| **K9** | **Prefetch chunk AI chưa được chặn.** Next static export prefetch chunk khi route/link — nếu màn AI nằm trong router prefetch, chunk wllama vài MB tải ngầm khi hover menu → vi phạm "0KB cho người không dùng". | Chunk nặng tải ngầm qua 4G = đúng thứ Duy cấm. | Không dùng `<Link prefetch>` vào màn AI / `prefetch={false}`; QA kiểm network khi `ai_enabled=false`: không có request chunk/model. |
| **K10** | **Feature-detect RAM không chuẩn.** `navigator.deviceMemory` chỉ có trên Chrome/Android; desktop/iOS không có — không biết chắc "máy đủ RAM" trước khi tải 2GB. | Tải 2GB trên máy thiếu RAM = crash tab giữa chừng (research 4.1 đã ghi nhận crash khi sinh). | Kết hợp: deviceMemory (best-effort) + UA/iOS detection (iOS → chỉ model ≤ ~1GB) + **guard tải an toàn**: tải trong worker, nếu load/sinh gây crash → lần sau không tự thử, hiện "máy này không chạy AI local" (BR-AI-12). |

---

## 5. Rủi ro theo story + van an toàn

> Nguyên tắc van an toàn: van phải để FE/BE **có thể tắt mà không sửa kiến trúc**, và luôn tuân
> BR-AI-16 (không bao giờ đẩy lệnh local lên cloud thay thế).

| Story | Nguy cơ hiệu năng | Biện pháp | Van an toàn (nếu không đạt ngân sách mục 3) |
|---|---|---|---|
| **S01–S06, S11** (BE) | Gần như không có cho FE. API mới phải nhẹ (registry in-memory). | Đo p95 catalog/context/execute ≤ 300ms; cloud complete có timeout 20s + không retry quá 1 (đã chốt). | Không cần van — đây là phần "miễn phí hiệu năng" (mục 6.1). |
| **S07** (màn nhập lô) | Màn mới — hiệu năng như màn thường; rủi ro duy nhất là form nặng nếu nhồi thêm. | Form theo pattern màn hiện có; auto-fill S14 validate schema client-side (nhẹ). | Không phụ thuộc AI (S07-AC5) — màn chạy 100% khi AI tắt. |
| **S08** (runtime + tải model) | **Lớn nhất.** Tải 2GB; RAM; COOP/COEP (K1); prefetch chunk (K9); cache hỏng (K6); n_ctx sai (K3). | Mục 4.2: K1, K3, K5, K6, K9, K10; tải chỉ khi đồng ý + Wi-Fi; tách worker (K4); QA kiểm không-request khi tắt. | Runtime không tải được/crash → toàn bộ màn AI local ẩn, lệnh local nhập tay, lệnh cloud vẫn chạy (BR-AI-12/02). Không đổi kiến trúc. |
| **S09** (chat 3 lệnh local) | Suy luận CPU 5–20 tok/s → câu trả lời 5–15s nếu bắt LLM sinh văn bản; intent-classify thêm 1 lượt suy luận mỗi câu. | **Trả lời theo mẫu từ kết quả API** (số liệu + câu mẫu tiếng Việt), chỉ 1 lần suy luận intent; stream token; `max_tokens` nhỏ; sliding window đã chốt (BR-AI-13). | Chậm hơn ngưỡng 5s → (1) cắt phần sinh văn bản, chỉ intent + mẫu; (2) vẫn chậm → hoãn chat (ẩn màn), KHÔNG đẩy lên cloud (BR-AI-16). |
| **S10** (voice) | ASR + LLM cùng lúc (K4); WebGPU trên Adreno chưa từng đo; độ trễ giọng→JSON không chắc. | Tách worker ASR/LLM; ASR on-device bắt buộc (BR-AI-15 — audio chứa giá mua không rời máy); đo S17 50 câu. | Không đạt ≤ 8s hoặc model sai field ≥ ngưỡng V1 → **hoãn voice, form tay vẫn đầy đủ (S07 độc lập)**. Voice là phần đắt nhất, cắt không mất gì khác. |
| **S12** (alerts) | Polling tốn data 4G; NLG qua cloud thêm độ trễ. | Endpoint thuần (`/api/alerts/`, D4); poll ≤ 1/phút chỉ khi mở màn; NLG (S13) async + fallback danh sách thô (S12-AC4). | Bỏ NLG — danh sách thô đã là giá trị; alerts không phụ thuộc AI (AC4). |
| **S13** (insights cloud) | Chờ cloud 5–20s; CLS khi khối tóm tắt hiện sau. | Async, không chặn render; reserve chỗ hoặc append; timeout 10s → số liệu thô; không retry quá 1. | Cloud tắt/chậm/trần → số liệu thô (AC2/AC3) — chi phí FE của S13 ≈ một khối hiển thị, gần như miễn phí. |
| **S14** (gợi ý + auto-fill) | Rủi ro gần như 0: search API thuần, debounce 200–300ms; LLM tuỳ chọn. | Dùng `GET /api/catalog/items/suggest` — không LLM cho MVP (đã ghi trong story). | Không cần van. |
| **S15** (nút FEFO) | Rủi ro 0: gọi service `sellable_batches` — không LLM (đã ghi rõ trong story). | Nút chạy cả khi AI tắt (S15-AC6). | Không cần van. |
| **S16** (summarization) | Thêm 1 lượt suy luận local trên hội thoại dài; Could story. | Chạy trong worker; thất bại → cắt thô (S16-AC4). | **Cắt đầu tiên** trong thứ tự thoái lui — fallback cắt thô đã là hành vi chuẩn. |
| **S17** (spike) | Đây chính là **cổng kiểm tra** của toàn bộ ngân sách mục 3. | Đo: tỉ lệ đúng field, độ trễ giọng→JSON, RAM đỉnh (cả 2K và 32K — chỉ để báo cáo), crash tab, tốc độ WebGPU vs CPU, trên máy thật (Q4). | S17 không đạt → chạy thứ tự thoái lui mục 6; đổi model chỉ là đổi GGUF URL, không sửa kiến trúc (ADR 2.4). |

---

## 6. Thứ tự thoái lui "không đáng"

> Áp khi S17 hoặc QA ở bất kỳ lô nào đo thấy không đạt ngân sách mục 3. Thứ tự từ dễ cắt đến
> khó; cắt theo thứ tự cho tới khi đạt. **Không bước nào được đẩy lệnh local lên cloud**
> (BR-AI-16 — "local giả" bị cấm tuyệt đối, kể cả khi đang thoái lui).

### 6.1 Phần "miễn phí hiệu năng" — giữ trong mọi kịch bản

| Thành phần | Vì sao miễn phí |
|---|---|
| Lớp lệnh dùng chung + catalog + router tĩnh (S01/S02) | BE thuần, in-memory, không FE |
| Audit `ai:<user>` (S03), trần chi phí + ledger (S04), công tắc (S05), context builder (S06) | BE thuần |
| Chốt chặn PII + proxy cloud (S11) | Server-side, không FE |
| Alerts (S12) | Endpoint thường, chạy khi AI tắt |
| Gợi ý mã hàng (S14) + nút FEFO (S15) | Search/service thuần, không LLM |
| Insights cloud (S13) | Async + fallback số liệu thô; chi phí FE ≈ một khối hiển thị; độ trễ chờ không chặn render |
| Màn nhập lô S07 | Độc lập AI, form tay đầy đủ |

→ Kể cả khi **toàn bộ phần "đắt" bị hoãn**, dự án vẫn giữ được giá trị kiến trúc AI Native:
mọi kênh (UI/Admin/AI) qua một lớp lệnh, phân quyền 3 tầng, audit truy vết, trần chi phí — đúng
tinh thần ADR 2.5/2.6/2.7. AI Native ở tầng kiến trúc, không phụ thuộc runtime nào.

### 6.2 Phần "đắt" — thứ tự cắt khi không đạt ngân sách

| # | Cắt/hoãn | Chi phí hiệu năng trả lại | Mất gì | Ghi chú |
|---|---|---|---|---|
| 1 | **S16 summarization local** | 1 lượt suy luận mỗi lần tóm tắt | Tiện ích hội thoại dài (fallback cắt thô đã có) | Could — cắt đầu tiên, không ai bị ảnh hưởng |
| 2 | **Hoãn voice (S10)** | ASR 50–70MB + suy luận giọng→JSON + độ phức tạp 2 worker | Entry point ưu tiên 1 của ADR — nhưng **form tay S07 đầy đủ, nhập lô vẫn chạy** | Đây là quyết định lớn nhất trong thoái lui; chỉ khi spike chứng minh voice không đạt độ trễ/độ đúng |
| 3 | **Hoãn chat (S09)** | Toàn bộ suy luận local tương tác | Tra cứu bằng câu hỏi tự nhiên — tra cứu tay qua màn vẫn còn | Chỉ khi kể cả "mẫu trả lời cố định" vẫn chậm; KHÔNG chuyển chat sang cloud cho 3 lệnh local |
| 4 | **Đổi model nhỏ hơn** (chỉ đổi cấu hình GGUF URL) | RAM/tốc độ tải giảm | Chất lượng tiếng Việt có thể giảm — spike phải đo lại | Thứ tự: Gemma 3n E4B → E2B → Sailor2-1B (0,74GB — dự phòng máy yếu; iPhone đã ngoài phạm vi); không sửa kiến trúc (ADR 2.4) |
| 5 | **Tắt hoàn toàn runtime on-device** (mọi lệnh local nhập tay, chỉ giữ cloud) | Toàn bộ chi phí model on-device | "Local-first" của Q1 — **chỉ khi không model nào chạy được trên máy nhân viên**; lệnh local chuyển nhập tay (BR-AI-12), lệnh cloud vẫn chạy | Đây là giới hạn cuối của BR-AI-16 (thay model tới khi hết lựa chọn) — không phải "local giả"; phải ghi quyết định vào decisions.md |

### 6.3 Ranh giới cứng (không bao giờ cắt)

1. Shop/Landing không đổi một byte (mục 3.A) — không có kịch bản "hy sinh" nào ở đây.
2. Không đẩy lệnh `local` lên cloud (BR-AI-02/16).
3. TTI < 2s và "AI tắt = y hệt cũ" (BR-AI-17) — nếu một story FE AI làm vỡ điều này mà không có van
   nào đạt, story đó không được QA APPROVED, kể cả khi tính năng AI của nó "chạy đúng".

---

## 7. Câu hỏi cho Duy

### 🔴 Chặn (trả lời trước khi code FE AI — Lô 1)

| # | Câu hỏi | Đề xuất của BA (để Duy chọn nhanh) |
|---|---|---|
| **P1** | ~~**Máy tham chiếu (Q4) là Android, iPhone hay máy tính?**~~ **ĐÃ CHỐT (Duy, 27/09): Android ≥ 8GB RAM, Windows ≥ 8GB RAM; iPhone tạm chưa hỗ trợ** (chi phí lên App Store quá cao). | S17 spike trên máy 8GB thật; không cần spike Sailor2-1B cho iOS. Máy chuẩn QA = Android/Windows 8GB. |
| **P2** | ~~**"Chi phí = 0 khi AI tắt" đo theo chuẩn nào?**~~ **ĐÃ CHỐT (Duy, 27/09): chuẩn (a) — 1 bản build duy nhất.** Duy: "AI là 1 add-on thôi, bật/tắt agent theo từng user được." | Delta bundle khởi đầu ≤ 5KB gzip + 0 request AI (trừ 1 status) + 0ms main-thread do AI — cổng 02b C.4. Không build 2 bản. |
| **P3** | **TTI < 2s đo trên mạng nào?** Console hiện tại đang tải Google Fonts render-blocking — TTI trên 4G cảng có thể không đạt dù không có AI. | Đề xuất: Wi-Fi văn phòng là ngưỡng chặn QA (kiểm soát được); 4G cảng đo tham khảo và báo cáo, không chặn; đồng thời tối ưu font (tự host) trong Lô 1 để 4G cảng cũng gần đạt. |
| **P4** | **Ngưỡng phản hồi chấp nhận được cho chat/voice** (để QA có số chặn, tránh tranh cãi "chậm tí có sao đâu"): | Đề xuất: chat câu tra cứu ≤ 5s (token đầu ≤ 3s); voice giọng→form điền ≤ 8s; cả hai trên máy tham chiếu. Không đạt → tự động chạy thứ tự thoái lui mục 6.2 (không cần hỏi lại Duy). |

### 🟡 Đã giả định (Duy lật được)

| # | Giả định PA | Mặc định |
|---|---|---|
| G10 | Long task do code AI trên main thread | 0ms — mọi thứ nặng trong Web Worker |
| G11 | `n_ctx` khi load model | = `AI_MAX_CONTEXT_TOKENS` (2048/4096), không load 32k |
| G12 | Chuẩn "0 chi phí khi tắt" | Mục 3.B: ≤ 5KB gzip delta, 0 request AI, 0ms main-thread |
| G13 | Tải model lần đầu | Không giữ cơ chế "core ~200MB trước" của ADR 2.10 (GGUF không cho phép) — thay bằng tiến trình % + hủy + resume |
| G14 | Cache model | Cache Storage ưu tiên (file lớn), IndexedDB fallback; key theo version model |
| G15 | Tách worker | 2 worker riêng: ASR / LLM (voice không đơ khi suy luận) |
| G16 | Polling alerts | ≤ 1 lần/phút, chỉ khi mở màn liên quan |
| G17 | COEP | Chỉ bật cho `erp-console` (nếu wllama cần), không bao giờ cho `frontend/`; font tự host khi bật |

---

*Bản phân tích này không thay đổi ADR/Q1–Q6/D1–D9/T1–T6 — chỉ bổ sung khung hiệu năng để các
chốt đó được thực hiện đúng cam kết BR-AI-17. Khi Duy trả lời P1–P4, BA cập nhật file này và báo
PO để bổ sung AC/ghi chú vào `02-stories.md` (chủ yếu S08, S09, S10, S17).*
