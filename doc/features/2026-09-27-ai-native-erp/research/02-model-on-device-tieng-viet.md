# Research 02 — Model On-Device cho tiếng Việt (ADR mục 5.1)

**Ngày:** 27/09/2026 · **Người thực hiện:** chuyên viên research (subagent)
**Mục đích:** Xác minh 2 model nêu trong ADR, tìm thêm 3–5 model on-device mở (≤ 4GB, GGUF) có bằng chứng tiếng Việt, so sánh runtime web (WebLLM / wllama / LiteRT.js), và chốt model nên spike cho tác vụ "nhập lô bằng giọng tiếng Việt" trên máy 12–16GB RAM.
**Quy ước:** mọi nguồn đều có URL và được truy cập **2026-09-27** (trừ khi ghi ngày khác). Dung lượng ghi theo file GGUF thực tế lấy từ Hugging Face API.

---

## 1. TL;DR

| Câu hỏi | Kết quả |
| :--- | :--- |
| `Gemma-SEA-LION-v4.5-E2B` có tồn tại? | ✅ Có — AI Singapore, tháng 5–6/2026, tên đầy đủ `Gemma-SEA-LION-v4.5-E2B-IT` |
| `Llama-3.2-3B-Frog` có tồn tại? | ✅ Có — `phamhai/Llama-3.2-3B-Instruct-Frog`, tháng 10/2024 |
| Model nên spike trước | **Llama-3.2-3B-Instruct-Frog** (1,88 GiB, function-calling tiếng Việt 95,79%) |
| Model so sánh cùng spike | **Gemma-SEA-LION-v4.5-E2B-IT** (3,19 GiB, SEA-native, có audio) — nhưng rủi ro runtime web |
| Phương án B máy yếu/iPhone | **Sailor2-1B** (0,74 GiB) hoặc **Qwen3-1.7B** (WebLLM prebuilt ~1,1 GiB) |
| Rủi ro lớn nhất | Runtime web chưa có cái nào chắc chắn chạy Gemma 4 (kiến trúc của SEA-LION) trên trình duyệt |

---

## 2. Xác minh 2 model trong ADR

### 2.1. Gemma-SEA-LION-v4.5-E2B — ✅ TỒN TẠI

| Thuộc tính | Giá trị | Nguồn |
| :--- | :--- | :--- |
| Nhà phát hành | AI Singapore (AI Products Pillar), bộ SEA-LION v4.5 | [docs.sea-lion.ai](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |
| Kiến trúc nền | `gemma-4-E2B-it` (Google), 2,3B tham số hiệu dụng (5,1B tính cả embeddings) | [HF model card](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT) |
| Context | **128K token** | [docs.sea-lion.ai](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |
| Ngôn ngữ | EN + **Tiếng Việt**, Burmese, Indonesia, Filipino, Malay, Tamil, Thái | [docs.sea-lion.ai](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |
| Đa phương thức | Text + Image + Video + **Audio gốc** (điểm cộng cho voice) | [docs.sea-lion.ai](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |
| GGUF Q4_K_M | **3,43 GB** (3.427.879.360 byte ≈ 3,19 GiB) | [HF API files](https://huggingface.co/api/models/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF/tree/main), đo ngày 27/09/2026 |
| Các bản GGUF | Q4_K_M 3,43 GB · Q6_K 3,85 GB · Q8_0 4,97 GB · F16 9,31 GB · + mmproj vision 0,99 GB | [HF API files](https://huggingface.co/api/models/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF/tree/main) |
| License | **MIT** trên HF / Apache-2.0 trên docs (mâu thuẫn, cần kiểm khi dùng) | [HF](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT), [docs](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |
| Ngày phát hành/cập nhật | Bộ v4.5 ra mắt 05–06/2026; repo GGUF cập nhật cuối 18/06/2026 | [HF GGUF](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF), [Ollama](https://ollama.com/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT) |
| Chạy được ở đâu | llama.cpp (`llama-server -ngl -1`), Ollama, LM Studio, Transformers | [HF GGUF README](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF) |
| **WebGPU/trình duyệt** | ❌ **WebLLM không hỗ trợ** (không có Gemma 4 trong danh sách prebuilt). wllama chạy GGUF nhưng **chưa xác minh được** bản llama.cpp đóng gói trong wllama hỗ trợ kiến trúc Gemma 4 → **rủi ro, phải thử khi spike** | [WebLLM config.ts](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts), [llama.cpp PR gemma3n/gemma4](https://git.codeproxy.net/ggml-org/llama.cpp/actions/runs/24137162042) |
| Điểm tiếng Việt | ⚠️ **Không có số benchmark tiếng Việt công bố cho E2B** — trang docs ghi "xem leaderboard" nhưng [leaderboard.sea-lion.ai](https://leaderboard.sea-lion.ai/) không hiển thị số theo ngôn ngữ công khai. Bằng chứng gián tiếp: huấn luyện trên ~8,54 triệu cặp instruction SEA + SEA-Instruct-2602 | [docs.sea-lion.ai](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5) |

**Kết luận xác minh:** model có thật, là bản Gemma 4 E2B được AI Singapore tinh chỉnh cho 7 ngôn ngữ Đông Nam Á (có tiếng Việt). Ưu điểm: kiến trúc mới 2026, audio gốc, context 128K. Nhược điểm: (1) không bằng chứng định lượng tiếng Việt, (2) runtime web không chắc chắn, (3) chưa safety-aligned (model card tự ghi).

### 2.2. Llama-3.2-3B-Frog — ✅ TỒN TẠI (tên đầy đủ: `Llama-3.2-3B-Instruct-Frog`)

| Thuộc tính | Giá trị | Nguồn |
| :--- | :--- | :--- |
| Tác giả | `phamhai` (Hugging Face), nền Meta `Llama-3.2-3B-Instruct` | [HF model card](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| Mục đích | **Tối ưu RAG tiếng Việt** (base Llama-3.2 yếu tiếng Việt) + function calling | [HF model card](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| Tham số | 3,2B | [HF](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| Context | **131K token** (model card); listing Featherless ghi 32K | [HF model card](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| GGUF Q4_K_M | **2,02 GB** (2.019.377.568 byte ≈ 1,88 GiB) | [HF API files](https://huggingface.co/api/models/phamhai/Llama-3.2-3B-Instruct-Frog-Q4_K_M-GGUF/tree/main), đo 27/09/2026 |
| Function calling tiếng Việt | **95,79% đúng tên hàm**, 51,05% exact-match trên Vietnamese Function Calling Benchmark → bằng chứng mạnh nhất cho use-case "giọng nói → JSON lệnh" | [HF model card](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| Ngày phát hành | Model: 22/10/2024 · GGUF: 12/11/2024 | [Featherless](https://featherless.ai/models/phamhai/Llama-3.2-3B-Instruct-Frog), [HF GGUF](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog-Q4_K_M-GGUF) |
| License | llama3.2 (Community License) | [HF](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |
| Chạy được ở đâu | llama.cpp, llama-cpp-python, Ollama, LM Studio, vLLM — GGUF chuẩn nên **wllama chạy trực tiếp** | [HF GGUF README](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog-Q4_K_M-GGUF) |
| **WebGPU/trình duyệt** | ✅ wllama (GGUF, CPU-WASM + WebGPU). WebLLM: base Llama-3.2-3B có trong prebuilt nhưng **không phải bản Frog** → muốn chạy WebLLM phải tự convert sang MLC | [WebLLM config.ts](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts) |
| Điểm tiếng Việt | Không có điểm VMLU công bố; bằng chứng qua thiết kế chuyên tiếng Việt (RAG + function calling + persona) và model card | [HF model card](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog) |

**Kết luận xác minh:** model có thật, GGUF nhẹ (1,88 GiB), chuyên tiếng Việt, có số function-calling tiếng Việt cụ thể — khớp chính xác nhu cầu "nhập lô bằng giọng" (giọng → text → gọi hàm `nhap_lo` với JSON). Nhược điểm: ra đời 10/2024 (kiến trúc cũ hơn), điểm tổng quát thấp hơn model 2026.

---

## 3. Bảng so sánh tổng — model ứng viên (≤ 4GB GGUF, có bằng chứng tiếng Việt)

| Model | Tham số | Q4 GGUF | Context | Runtime hỗ trợ | Bằng chứng tiếng Việt | Nguồn (truy cập 27/09/2026) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Llama-3.2-3B-Instruct-Frog** ⭐ | 3,2B | **1,88 GiB** | 131K | llama.cpp · Ollama · **wllama** · WebLLM phải convert | FC tiếng Việt 95,79%; RAG tiếng Việt | [HF](https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog), [GGUF](https://huggingface.co/api/models/phamhai/Llama-3.2-3B-Instruct-Frog-Q4_K_M-GGUF/tree/main) |
| **Gemma-SEA-LION-v4.5-E2B-IT** ⭐ | 2,3B eff | **3,19 GiB** | 128K | llama.cpp · Ollama · LM Studio · wllama **chưa chắc** · WebLLM ❌ | SEA-native 7 ngôn ngữ; chưa có số VI công bố | [docs](https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5), [GGUF](https://huggingface.co/api/models/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF/tree/main) |
| Qwen3-1.7B | 1,7B | ~1,1 GiB (MLC q4f16_1) | 32K | **WebLLM prebuilt** · llama.cpp · Ollama | Họ Qwen3 là nền được các đội Việt chọn fine-tune: MISA-AI-1.0 VMLU 81,26; Qwen3-8B VMLU 69–74 | [WebLLM config](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts), [VN-Bench](https://www.nrl.ai/en/bench), [Unicorn-R3](https://huggingface.co/unicorn-team/Unicorn-R3) |
| Qwen2.5-1.5B-Instruct | 1,5B | ~1,1 GiB (MLC q4f32_1) | 32K | **WebLLM prebuilt** · llama.cpp · Ollama | Như trên (đời cũ hơn, tiếng Việt khá cho slot-filling) | [WebLLM config](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts), [mlc-ai HF](https://huggingface.co/mlc-ai/Qwen2.5-1.5B-Instruct-q4f16_1-MLC) |
| Sailor2-1B | 1B | **0,74 GiB** | 8K | llama.cpp · Ollama · wllama | Huấn luyện 200–400B token SEA, riêng tiếng Việt 41,5B token; Sailor-7B-Chat VMMLU 51,3 | [GGUF](https://huggingface.co/tensorblock/sail_Sailor2-1B-GGUF), [Sailor](https://sea-sailor.github.io/blog/sailor1/), [SeaLLMs 3](https://aclanthology.org/2025.naacl-demo.10.pdf) |
| Gemma 3 1B (gemma3-1b-it) | 1B | ~0,9 GiB | 32K | **WebLLM prebuilt** · **LiteRT.js** (.task) · llama.cpp | 140+ ngôn ngữ; GMMLU-Lite 34,2 (điểm chung, không tách riêng VI) → tiếng Việt ở mức "hiểu được" | [WebLLM config](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts), [Gemma 3 tech report qua gitcode mirror](https://gitcode.com/hf_mirrors/unsloth/gemma-3-270m) |
| Vistral-7B-Chat | 7B | Q4_K_S 4,18 GB / Q4_K_M 4,41 GB (⚠️ vượt nhẹ trần 4GB) | 32K | llama.cpp · Ollama · LM Studio | Model tiếng Việt bản địa (Mistral), bằng chứng học thuật nhiều (VLSP 2025, nhiều bài đánh giá) | [GGUF](https://huggingface.co/tensorblock/vistral-7b-chat-GGUF), [VLSP 2025](https://aclanthology.org/2025.vlsp-1.39.pdf) |
| ~~ViGGO~~ | — | — | — | — | ❌ **Không xác minh được** là model tiếng Việt on-device có tên tuổi. Chỉ thấy `Meta-Llama-3-8B-VIGGO` (8B, Q4_K_M 4,92 GB > 4GB, 284 lượt tải, không mô tả tiếng Việt rõ ràng) → **loại khỏi danh sách** | [HF](https://huggingface.co/api/models/mradermacher/Meta-Llama-3-8B-VIGGO-GGUF/tree/main) |
| ~~SmolLM2-1.7B~~ | 1,7B | ~0,8 GiB | 8K | WebLLM prebuilt | Tập trung tiếng Anh, tiếng Việt yếu → chỉ dùng làm fallback cuối | [WebLLM config](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts) |

> Ghi chú: **MiMo-7B** (lựa chọn chính của ADR) nằm ngoài phạm vi bài này vì Q4_K_M ~5,3 GB vượt trần 4 GB của yêu cầu; vẫn cần spike riêng theo đúng mục 5.1 ADR. Kết quả bảng trên dùng để **so sánh** với MiMo-7B.

---

## 4. Runtime web phổ biến 2026 — phân tích

### 4.1. WebLLM (MLC AI, Apache-2.0) — [github.com/mlc-ai/web-llm](https://github.com/mlc-ai/web-llm)

- Chạy bằng **WebGPU**, định dạng **MLC riêng (không phải GGUF)**; ~32 họ model prebuilt được xác minh từ [config.ts](https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts) ngày 27/09/2026.
- Prebuilt liên quan: Llama-3.2-1B/3B, Qwen2.5-0.5B→7B, Qwen3-0.6B→8B, Qwen3.5-0.8B→9B, **gemma3-1b-it**, gemma-2-2b/9b, Phi-4-mini, SmolLM2, DeepSeek-R1-Distill.
- **KHÔNG có trong prebuilt:** Gemma 3n, **Gemma 4** (⇒ không chạy Gemma-SEA-LION-v4.5-E2B), Frog (chỉ có base Llama-3.2-3B — phải tự convert MLC nếu muốn dùng bản Frog).
- Giới hạn VRAM: Qwen3-0.6B cần ~4GB VRAM, Qwen3-1.7B cần ~8GB, Qwen3-4B cần 16GB (nguồn tổng hợp cộng đồng 2026). Model ~3B (Llama-3.2-3B ≈ 2,26GB tải) chạy được trên máy 12–16GB.
- **iPhone/Safari:** WebGPU có trên Safari 26 theo một số nguồn 2026 (localmode.dev), nhưng một nguồn khác (6/2026) cho rằng WKWebView vẫn chặn → **phải feature-detect `navigator.gpu`** và có fallback. Quan trọng hơn: **tab Safari trên iPhone bị giới hạn ~1–1,5GB RAM** → model > ~800MB rủi ro crash tab; thực tế iPad mini A17 Pro chạy được Qwen3-0.6B (40 tok/s) nhưng Qwen3.5-2B (1,1GB) thì crash khi sinh. Nguồn: [localmode.dev Safari iOS](https://localmode.dev/blog/compatibility/safari-ios), [gwaw.jp thử nghiệm](http://www.gwaw.jp/20260805-341.html), [intelligibberish 9/2026](https://intelligibberish.com/articles/run-llms-in-the-browser-with-webgpu/).

### 4.2. wllama (@wllama/wllama v3.5.1) — [github.com/ngxson/wllama](https://github.com/ngxson/wllama)

- Binding **llama.cpp sang WebAssembly** → chạy **GGUF trực tiếp** (ưu điểm lớn: không cần convert, chạy đúng file trong bảng mục 3).
- Chạy **CPU WASM-SIMD mọi trình duyệt** + **WebGPU từ v3.1**; tốc độ CPU ~5–20 tok/s, WebGPU nhanh hơn nhiều.
- **iPhone/Safari:** bản v3 mặc định dùng JSPI + Memory64 → Safari không chạy; dùng **`@wllama/wllama-compat`** (Asyncify) thì chạy được trên Safari/iOS với tốc độ "chấp nhận được" (🟡). Nguồn: [wllama README](https://github.com/ngxson/wllama), [@localmode/wllama](https://socket.dev/npm/package/%40localmode%2Fwllama).
- **Rủi ro:** wllama đóng gói một bản llama.cpp cố định; Gemma 4 (kiến trúc của SEA-LION) mới được llama.cpp hỗ trợ ~cuối 03/2026 → **chưa xác minh được wllama đã hỗ trợ Gemma 4 hay chưa** (repo wllama push cuối 08/05/2026). Cần thử trực tiếp khi spike. Frog (Llama-3.2) chắc chắn chạy được.

### 4.3. LiteRT.js (Google, MediaPipe LLM Inference / `@mediapipe/tasks-genai`) — [Google AI Edge](https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference)

- Chạy model định dạng **`.litertlm`/`.task` riêng của Google** (Gemma-3n E2B/E4B, Gemma-3 1B) — **không chạy GGUF tùy ý**, nên không dùng được Frog/SEA-LION/Qwen/Sailor.
- LLM Inference API **chuyển sang maintenance-only trong 2026**, Google khuyến nghị LiteRT-LM (bản chất native/Chrome built-in). Nguồn: [aiwiki MediaPipe](https://aiwiki.ai/wiki/mediapipe), [Google blog](https://developers.googleblog.com/ja/on-device-genai-in-chrome-chromebook-plus-and-pixel-watch-with-litert-lm/).
- Web nghiêng về Chrome (Chrome built-in AI); trên iOS phải đi đường SwiftPM (LiteRT-LM Swift) hoặc iOS 26 Apple Intelligence — không phù hợp website thuần của dự án.
- **Kết luận:** ADR ghi "LiteRT.js" nhưng với ràng buộc "website thuần túy + model tiếng Việt GGUF" thì LiteRT.js **không phải lựa chọn khả thi**; nếu vẫn muốn hệ Gemma trên web → dùng WebLLM (gemma3-1b-it prebuilt) hoặc wllama.

### 4.4. Ma trận model × runtime (đã xác minh 27/09/2026)

| Model | WebLLM | wllama | LiteRT.js | Ollama/llama.cpp desktop |
| :--- | :--- | :--- | :--- | :--- |
| Llama-3.2-3B-Frog | Phải convert MLC | ✅ GGUF trực tiếp | ❌ | ✅ |
| Gemma-SEA-LION-v4.5-E2B-IT | ❌ (không có Gemma 4) | ⚠️ chưa xác minh (Gemma 4) | ❌ | ✅ |
| Qwen3-1.7B / Qwen2.5-1.5B | ✅ prebuilt | ✅ GGUF | ❌ | ✅ |
| Sailor2-1B | ❌ (phải convert) | ✅ GGUF | ❌ | ✅ |
| Gemma 3 1B | ✅ prebuilt | ✅ GGUF | ✅ (.task) | ✅ |

**Chiến lược runtime:** dùng **wllama làm runtime chính** (chạy GGUF trực tiếp, có fallback CPU cho mọi máy, có `wllama-compat` cho iPhone) + WebLLM làm phương án phụ cho model có prebuilt (Qwen3-1.7B). Luôn feature-detect `navigator.gpu`; trên iPhone chỉ phép model ≤ ~1GB (xem mục 5.3).

---

## 5. Khuyến nghị spike

### 5.1. Spike trước (máy 12–16GB RAM) — **2 model, theo đúng ADR mục 5.1 nhưng đảo thứ tự ưu tiên**

| Ưu tiên | Model | Lý do | Việc cần thử trong spike |
| :--- | :--- | :--- | :--- |
| **A (chính)** | **Llama-3.2-3B-Instruct-Frog** (1,88 GiB) | Nhẹ nhất trong 2 cái ADR nêu; function-calling tiếng Việt 95,79% đúng tên hàm — khớp chính xác "giọng → JSON `nhap_lo`"; wllama chạy GGUF ngay, không cần convert; context 131K thoải mái cho sliding window 2–4K | 50 câu nói thật → đo tỉ lệ đúng field (`ma_hang`, `so_luong`, `don_vi`), độ trễ WebGPU vs CPU, RAM thực tế |
| **B (so sánh)** | **Gemma-SEA-LION-v4.5-E2B-IT** (3,19 GiB) | SEA-native 2026, audio gốc (mở đường bỏ tầng STT sau này), context 128K — nhưng **chưa có số tiếng Việt công bố** và runtime web chưa chắc | Test bằng llama.cpp/Ollama desktop trước; **kiểm tra wllama có load được GGUF Gemma 4 không**; nếu không → chỉ là phương án desktop/native, không đưa lên web |

> Lưu ý cho điều phối viên: ADR mục 5.1 ghi "So sánh MiMo-7B với Gemma-SEA-LION và Frog" — kết quả research này ủng hộ đưa **Frog vào vòng spike như một ứng viên ngang hàng chứ không chỉ để so sánh**, vì nó là model duy nhất trong 3 cái có (1) bằng chứng function-calling tiếng Việt định lượng, (2) runtime web xác minh được, (3) dung lượng trong trần 4GB.

### 5.2. Tiêu chí đo (đồng bộ ADR mục 5.1)

1. Dung lượng tải thực tế (Frog ~2,02GB; SEA-LION ~3,43GB) + thời gian load vào RAM.
2. Độ trễ end-to-end: giọng → STT (Vosk/Whisper) → model → JSON.
3. Tỉ lệ đúng trên **50 câu nói thật** (đúng field `ma_hang`, `so_luong`, `don_vi`, `gia_von` — nhãn nhạy cảm cao, cần lọc context theo quyền).
4. RAM đỉnh + có crash tab không (context 2K và 4K).
5. Trên iPhone (máy nhân viên thực): feature-detect WebGPU → fallback wllama-compat, đo tốc độ.

### 5.3. Phương án B — máy yếu / iPhone nhân viên

| Model | Dung lượng | Lý do |
| :--- | :--- | :--- |
| **Sailor2-1B** (Q4_K_M) | **0,74 GiB** | Nhẹ nhất có huấn luyện SEA chuyên biệt (41,5B token tiếng Việt); wllama chạy cả CPU trên iPhone; đủ cho slot-filling + few-shot JSON |
| **Qwen3-1.7B** (WebLLM prebuilt) | ~1,1 GiB | Prebuilt sẵn trên WebLLM (đỡ công convert), tiếng Việt khá, có WebGPU nhanh trên máy Android/Chrome tốt |

Cả hai đều dưới ngưỡng ~1GB an toàn cho tab Safari iPhone (giới hạn ~1–1,5GB). Lưu ý iOS Private Browsing chặn IndexedDB → không cache được model (cần fallback memory hoặc yêu cầu mở tab thường).

---

## 6. Nguồn tham khảo (truy cập 27/09/2026)

**Gemma-SEA-LION-v4.5-E2B:**
- https://docs.sea-lion.ai/models/sea-lion-v4.5/gemma-sea-lion-v4.5
- https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT (model card)
- https://huggingface.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF (README + file sizes đo qua API)
- https://ollama.com/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT
- https://leaderboard.sea-lion.ai/ (không hiển thị số theo ngôn ngữ khi truy cập)

**Llama-3.2-3B-Instruct-Frog:**
- https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog
- https://huggingface.co/phamhai/Llama-3.2-3B-Instruct-Frog-Q4_K_M-GGUF
- https://featherless.ai/models/phamhai/Llama-3.2-3B-Instruct-Frog

**Model khác:**
- Sailor: https://sea-sailor.github.io/blog/sailor1/ · https://huggingface.co/tensorblock/sail_Sailor2-1B-GGUF · SeaLLMs 3: https://aclanthology.org/2025.naacl-demo.10.pdf
- Qwen tiếng Việt: https://www.nrl.ai/en/bench · https://huggingface.co/unicorn-team/Unicorn-R3
- Gemma 3: https://webllm.mlc.ai/docs/prebuilt_models (404) → https://raw.githubusercontent.com/mlc-ai/web-llm/main/src/config.ts
- Vistral: https://huggingface.co/tensorblock/vistral-7b-chat-GGUF · https://aclanthology.org/2025.vlsp-1.39.pdf
- ViGGO (loại): https://huggingface.co/asprenger/Meta-Llama-3-8B-VIGGO · https://huggingface.co/mradermacher/Meta-Llama-3-8B-VIGGO-GGUF

**Runtime:**
- WebLLM: https://github.com/mlc-ai/web-llm · https://localmode.dev/blog/compatibility/safari-ios · http://www.gwaw.jp/20260805-341.html · https://intelligibberish.com/articles/run-llms-in-the-browser-with-webgpu/ · https://dev.to/creeta/qwen3-in-the-browser-zero-keys-webllm-0283-hands-on-3ai2
- wllama: https://github.com/ngxson/wllama · https://socket.dev/npm/package/%40localmode%2Fwllama
- LiteRT.js / LiteRT-LM: https://developers.google.com/edge/mediapipe/solutions/genai/llm_inference · https://aiwiki.ai/wiki/mediapipe · https://developers.googleblog.com/ja/on-device-genai-in-chrome-chromebook-plus-and-pixel-watch-with-litert-lm/
- llama.cpp + Gemma 4: https://github.com/google-deepmind/gemma/issues/628 · https://www.tecace.com/post/gemma-3n-vs-gemma-4-a-real-world-benchmark-guide-on-the-galaxy-s25-ultra
