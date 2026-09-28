# Deep Research — Kiểm chứng ADR AI Native

**Ngày:** 2026-09-27 · 3 mũi research song song (web, có nguồn URL từng claim) · chi tiết đầy đủ ở `research/01..03` bên dưới.

## Tóm tắt điều hành

### A. Model Xiaomi — có thật, số liệu lõi đúng, nhưng 2 điểm gãy
1. **MiMo-7B** ✅ tồn tại (GitHub `XiaomiMiMo/MiMo`, MIT). GGUF có (bên thứ 3). Q4_K_M thực tế **4,68GB** (ADR ghi 5,3GB — sai nhẹ theo hướng có lợi). Context 32K/64K khớp. Benchmark AIME/LCB vượt o1-mini theo bảng eval tự công bố của Xiaomi.
2. **MiMo-V2.6-Flash** ✅ tồn tại (21–22/9/2026, MIT). 309B/15B đúng, giá $0.14/$0.28 đúng. ⚠️ Context là **1M thẳng** (không phải 256K→1M; 256K là bản V2-Flash cũ). API: `api.xiaomimimo.com/v1`, OpenRouter, LiteLLM.
3. ❌ **Điểm gãy #1 — runtime on-device**: LiteRT.js và WebLLM đều **chưa hỗ trợ MiMo**; chưa ai chạy MiMo qua WebGPU. Đường khả thi lý thuyết duy nhất: **wllama** (llama.cpp WASM) với GGUF "Qwenified", loại Safari, cần COOP/COEP.
4. ❌ **Điểm gãy #2 — tiếng Việt**: MiMo-7B **chưa từng được đánh giá tiếng Việt** (technical report chỉ EN/ZH, không có VMLU). Rủi ro ADR nêu là chính xác → spike 50 câu thật bắt buộc.
5. Điều khoản dữ liệu MiMo: Xiaomi là bên xử lý, cam kết không huấn luyện khi chưa đồng ý, lưu EU/Singapore (chọn được vùng) — khá tốt, nhưng vẫn là bên thứ 3 Trung Quốc.

### B. Model on-device tiếng Việt — khuyến nghị spike khác ADR
- **Ưu tiên 1: Llama-3.2-3B-Instruct-Frog** (1,88GB, phamhai) — function-calling tiếng Việt đo được 95,79% đúng tên hàm, khớp use-case "giọng → JSON `nhap_lo`"; wllama chạy GGUF trực tiếp.
- **Ưu tiên 2 (so sánh cùng đợt): Gemma-SEA-LION-v4.5-E2B-IT** (3,19GB, AI Singapore, SEA-native, audio gốc) — runtime web chưa chắc, test desktop trước.
- **Phương án B máy yếu/iPhone:** Sailor2-1B (0,74GB) hoặc Qwen3-1.7B (WebLLM prebuilt). iPhone Safari giới hạn ~1–1,5GB RAM → chỉ model ≤ ~1GB.
- ViGGO ❌ loại (không bằng chứng). Gemma 3 1B có prebuilt cả WebLLM lẫn LiteRT.js nhưng tiếng Việt yếu hơn.

### C. Pháp lý — 3 nghĩa vụ bắt buộc trước khi bật AI production
1. **Luật AI 134/2025/QH15** (hiệu lực 01/3/2026, NĐ 142/2026 hướng dẫn): hệ thống Cá Về là **mới** → không hưởng chuyển tiếp 12 tháng; phải tự phân loại rủi ro (**trung bình** là hợp lý) + lập hồ sơ + **thông báo Bộ KH&CN qua cổng một cửa AI trước khi đưa vào sử dụng** + minh bạch + báo cáo sự cố 72h/5 ngày.
2. **Chuyển PII sang model cloud nước ngoài = chuyển dữ liệu xuyên biên giới** (Luật BVDLCN 91/2025 Đ.20) → phải có hồ sơ DTIA gửi A05 trong 60 ngày, phạt tới 5% doanh thu. Vì vậy giữ tuyệt đối BR-AI-09: **PII khách không bao giờ vào prompt** (local lẫn cloud) + chốt chặn kỹ thuật ở adapter (allowlist + redaction + hard-block).
3. **Giá vốn gửi cloud không có NDA/DPA = mất tư cách bảo hộ bí mật kinh doanh** (Luật SHTT Đ.84) → lệnh nhãn `cao` **không lên cloud ở MVP**.
- NĐ 248/2026 TMĐT (hiệu lực 01/7/2026): không bắt buộc khai báo "chatbot là AI"; minh bạch AI đến từ Luật AI. Dùng AI nội bộ không cần đăng ký riêng — chỉ cần phân loại + thông báo như trên.

### D. Ảnh hưởng tới thiết kế (điều chỉnh ADR)
1. Runtime on-device: **wllama + GGUF** (bỏ LiteRT.js/WebLLM cho MiMo).
2. Spike: Frog + SEA-LION trước (có bằng chứng tiếng Việt), MiMo-7B chỉ đưa vào nếu spike riêng cho thấy chạy được wllama + tiếng Việt ổn.
3. MVP: lệnh nhãn `cao` luôn local; cloud chỉ `thấp`/`trung bình`; PII bị chặn kỹ thuật trước khi rời máy.
4. Kế hoạch go-live AI: thêm mốc hồ sơ phân loại + thông báo Bộ KH&CN trước khi bật AI ở production.

---


---

# Nghiên cứu xác minh: MiMo-7B & MiMo-V2.6-Flash

**Ngày:** 27/09/2026
**Người thực hiện:** Research agent (web search + đọc trực tiếp README/config/model card)
**Đối tượng:** `00-adr-ai-native.md` mục 2.1 (MiMo-7B on-device) và 2.2 (MiMo-V2.6-Flash cloud)

> Quy ước: ✅ ĐÚNG — có nguồn xác nhận · ⚠️ SAI SỐ — tồn tại nhưng số liệu lệch · ❌ KHÔNG TÌM THẤY — coi như FAIL.

---

## 1. Bảng xác minh từng claim

### 1.1 MiMo-7B (on-device)

| Claim trong ADR | Kết quả | Chi tiết & nguồn |
| :--- | :--- | :--- |
| Model tồn tại | ✅ ĐÚNG | Xiaomi công bố MiMo-7B-Base / -SFT / -RL-Zero / -RL cuối tháng 4/2025, MIT license. GitHub chính thức: [XiaomiMiMo/MiMo](https://github.com/XiaomiMiMo/MiMo); technical report [arXiv 2505.07608](https://arxiv.org/abs/2505.07608) (12/5/2025) |
| GitHub `XiaomiMiMo/MiMo` | ✅ ĐÚNG | Repo tồn tại, có README cập nhật RL-0530 (30/5/2025), hướng dẫn SGLang/vLLM/Transformers |
| Bản GGUF trên HF | ✅ CÓ (bên thứ 3) | Repo chính thức **không** phát hành GGUF. Bản GGUF do cộng đồng: [jedisct1/MiMo-7B-RL-GGUF](https://huggingface.co/jedisct1/MiMo-7B-RL-GGUF), [mradermacher/MiMo-7B-RL-0530-Qwenified-GGUF](https://huggingface.co/mradermacher/MiMo-7B-RL-0530-Qwenified-GGUF) — chạy được bằng llama.cpp/Ollama/LM Studio |
| Kích thước Q4_K_M ~5.3GB | ⚠️ SAI SỐ | Thực tế **4.68 GB** (mradermacher RL-0530-Qwenified, đọc danh sách file 27/9/2026) / **4.7 GB** (jedisct1). 5.3GB là cỡ Q5_K_S. Sai số theo hướng có lợi (RAM cần ít hơn dự kiến) |
| Context 32K Base / 64K RL-0530 | ✅ ĐÚNG | `config.json` trực tiếp: Base `max_position_embeddings = 32768`, [RL-0530 = 65536](https://huggingface.co/XiaomiMiMo/MiMo-7B-RL-0530/raw/main/config.json) |
| AIME/LiveCodeBench vượt o1-mini | ✅ ĐÚNG (theo bảng eval tự công bố của Xiaomi) | Bảng eval trong README: RL-0530 đạt AIME24 **80.1** vs o1-mini **63.6**; AIME25 **70.2** vs **50.7**; LiveCodeBench v5 **60.9** vs **53.8**; v6 **52.2** vs **46.8**. README nói AIME24 vượt cả DeepSeek R1 (79.8). Lưu ý: số của o1-mini do Xiaomi tự chạy lại |
| "Nền tảng Xiao AI dùng" | ⚠️ CHƯA XÁC MINH | Báo chí (Gigazine 1/5/2025: [link](https://gigazine.net/news/20250501-xiaomi-ai-mimo/)) xác nhận MiMo nhắm chạy on-device (端侧) nhưng không tìm thấy nguồn xác nhận Xiao AI đang chạy chính MiMo-7B |

### 1.2 MiMo-7B trên trình duyệt

| Claim / câu hỏi | Kết quả | Chi tiết & nguồn |
| :--- | :--- | :--- |
| LiteRT.js hỗ trợ MiMo | ❌ KHÔNG | LiteRT/LiteRT-LM (Google) chỉ hỗ trợ **Gemma, Qwen, Llama, Phi, SmoLM, FastVLM** — không có MiMo hay bất kỳ model Xiaomi nào. Nguồn: [LiteRT GenAI overview](https://developers.google.com/edge/litert/genai/overview), [litert-community Web LLM Models collection](https://huggingface.co/collections/litert-community/web-llm-models) |
| WebLLM hỗ trợ MiMo | ❌ KHÔNG | Danh mục prebuilt của WebLLM/MLC không có MiMo. Có thể tự compile MLC nhưng kiến trúc MiMo (`MiMoForCausalLM`) là custom, không có bằng chứng ai đã compile |
| Có ai chạy MiMo qua WebGPU chưa | ❌ KHÔNG TÌM THẤY | Không có demo/bài blog nào chạy MiMo trong browser qua WebGPU |
| Runtime on-device web khả thi | ⚠️ LỘ TRÌNH KHẢ THI VỀ LÝ THUYẾT | **wllama v3** (llama.cpp WASM + WebGPU, [ngxson/wllama](https://github.com/ngxson/wllama), npm `@wllama/wllama` 1.16.2) nạp được GGUF bất kỳ mà llama.cpp hỗ trợ. MiMo GGUF là bản "**Qwenified**" (chuyển về kiến trúc Qwen2) nên llama.cpp chạy được — đã có hướng dẫn `llama serve -hf ...` trên card. Ràng buộc: tách file ≤512MB, cần header COOP/COEP, memory64 → loại Safari, khuyến nghị Q4/Q5/Q6 |

### 1.3 MiMo-V2.6-Flash (cloud)

| Claim trong ADR | Kết quả | Chi tiết & nguồn |
| :--- | :--- | :--- |
| Model tồn tại | ✅ ĐÚNG | Ra mắt 21–22/9/2026, MIT open weights: [VentureBeat](https://venturebeat.com/technology/better-than-deepseek-xiaomis-mimo-v2-6-pro-debuts-as-the-top-open-weights-model-in-the-world-alongside-cheaper-v2-6-flash), [datanorth.ai](https://datanorth.ai/news/xiaomi-releases-mimo-v2-6-pro-and-flash), [llm-stats](https://llm-stats.com/models/mimo-v2.6-flash) |
| Tổng 309B / active 15B | ✅ ĐÚNG | Sparse MoE 309B tổng / 15B active, xác nhận bởi mọi nguồn trên |
| Context 256K (mở rộng 1M) | ⚠️ SAI SỐ | Context là **1M (1.048.576 token)** luôn — không có khái niệm "256K mở rộng". Số 256K thuộc về **MiMo-V2-Flash** (bản cũ, đang trên [Puter.js](https://developer.puter.com/ai/xiaomi/mimo-v2-flash/): 256K–262K context). ADR nhiều khả năng lẫn 2 bản |
| Giá $0.14/1M input, $0.28/1M output | ✅ ĐÚNG | Nền tảng Xiaomi lẫn OpenRouter cùng giá: input $0.14/M (cache ~$0.0028–0.003/M), output $0.28/M. TQ: ¥1/¥2. Nguồn: [eesel.ai](https://www.eesel.ai/blog/xiaomi-mimo-v2-6-pricing), [llm-stats](https://llm-stats.com/models/mimo-v2.6-flash) |
| API public | ✅ CÓ | Xiaomi open platform (`api.xiaomimimo.com/v1`), [OpenRouter `xiaomi/mimo-v2.6-flash`](https://openrouter.ai/xiaomi/mimo-v2.6-flash) (route Xiaomi + DeepInfra, cùng giá), LiteLLM hỗ trợ day-0 |
| SiliconFlow | ❌ KHÔNG TÌM THẤY | Không có bằng chứng SiliconFlow đã lên model này |
| Puter.js | ❌ CHƯA CÓ V2.6 | Puter.js hiện có MiMo **V2-Flash / V2-Omni / V2-Pro / V2.5 / V2.5-Pro** — chưa thấy V2.6 ([danh sách Puter](https://developer.puter.com/blog/xiaomi-mimo-v2-omni-pro-in-puter-js/)) |
| Truy cập từ Việt Nam | ⚠️ CHƯA XÁC MINH DỨT KHOÁT | Không tìm thấy bằng chứng chặn IP Việt Nam. Nền tảng Xiaomi có Token Plan cho China/Europe/Singapore và phục vụ người dùng "ngoài Trung Quốc đại lục". OpenRouter là đường khả thi (cần test thực tế lúc spike) |

### 1.4 Điều khoản xử lý dữ liệu (bên thứ 3 Trung Quốc)

| Câu hỏi | Kết quả | Chi tiết & nguồn |
| :--- | :--- | :--- |
| Vùng lưu trữ ngoài TQ? | ✅ CÓ | Thoả thuận MiMo API Open Platform (ngoài Trung Quốc đại lục): dữ liệu lưu trên máy chủ **Châu Âu và Singapore**; người dùng được liên hệ để **chọn vùng lưu trữ** (có thể tốn phí). Nguồn: [mimo.mi.com user-agreement](https://mimo.mi.com/docs/quick-start/terms/user-agreement) |
| Dùng dữ liệu gửi vào để huấn luyện? | ✅ CÓ ĐIỀU KHOẢN CHẶN | Chính sách riêng tư MiMo: "未经您的事先同意，小米不会将您提供的文本内容用于模型训练或者其他用途" — **không dùng nội dung người dùng để huấn luyện khi chưa có đồng ý trước**. Nguồn: [MiMo privacy policy](https://mimo.xiaomi.com/legal/privacy-policy) |
| Vai trò dữ liệu | ✅ RÕ | Ngoài TQ đại lục: Xiaomi là **Data Processor**, người dùng là **Data Controller**; xoá dữ liệu khi hết mục đích/theo yêu cầu |
| Kết luận tuân thủ | ⚠️ LƯU Ý | Điều khoản khá tốt (không huấn luyện khi chưa đồng ý, có vùng EU/Singapore), nhưng vẫn là bên thứ 3 Trung Quốc → theo Luật AI 134/2025 và quy tắc bất biến 9 của dự án, **chỉ gửi dữ liệu nhãn "thấp" lên cloud**, không gửi dữ liệu cá nhân khách & giá vốn khi chưa được Duy duyệt |

### 1.5 Chất lượng tiếng Việt của MiMo-7B

| Câu hỏi | Kết quả | Chi tiết & nguồn |
| :--- | :--- | :--- |
| Có benchmark tiếng Việt (VMLU...) không | ❌ KHÔNG TÌM THẤY | Technical report MiMo-7B chỉ đánh giá **tiếng Anh và tiếng Trung** (BBH, MMLU, MMLU-Pro, C-Eval, CMMLU, GPQA...). Không có VMLU ([ACL 2025](https://aclanthology.org/2025.acl-long.563.pdf)) hay bất kỳ đánh giá tiếng Việt nào |
| Blog/đánh giá cộng đồng | ❌ KHÔNG TÌM THẤY | Không có bài đánh giá tiếng Việt cho MiMo-7B |

→ **Xác nhận rủi ro ADR tự nêu** ("MiMo-7B tiếng Việt yếu — 🔴 Cao"): spike 50 câu thật là **bắt buộc** trước khi chốt, không có dữ liệu nào trấn an được.

---

## 2. Phân tích khả năng chạy on-device (trình duyệt web)

**Không có runtime "cắm là chạy" cho MiMo-7B trên web:**

| Runtime | Hỗ trợ MiMo? | Ghi chú |
| :--- | :--- | :--- |
| LiteRT.js (ADR chọn) | ❌ | Chỉ Gemma/Qwen/Llama/Phi/SmoLM/FastVLM — ADR sai ở điểm này |
| WebLLM (MLC) | ❌ | Không có prebuilt; tự compile MLC không có tiền lệ với kiến trúc MiMo |
| wllama v3 (llama.cpp WASM + WebGPU) | ⚠️ Khả thi lý thuyết | GGUF "Qwenified" Q4_K_M 4.68GB nạp được bằng llama.cpp; wllama v3 có WebGPU (tự bật, offload toàn bộ layer). **Chưa có demo thực tế nào** |
| WebNN | ❌ | Không thấy hỗ trợ MiMo |

**Rủi ro kỹ thuật khi spike (chưa ai chứng minh được):**
- 7B Q4 (4.68GB) + KV cache trên **mobile browser** — giới hạn bộ nhớ tab mobile Chrome và hiệu năng WebGPU trên Adreno chưa từng được đo với MiMo. Tham chiếu: WebLLM Qwen3-4B cần ~16GB VRAM và được gắn nhãn "desktop-class only"; model 0.6B–1.7B mới được coi là an toàn cho mobile.
- Phải tách GGUF ≤512MB, header COOP/COEP, memory64 → **loại Safari**, chỉ Chrome/Edge.
- Nếu spike wllama fail → không còn runtime web nào chạy được MiMo-7B.

---

## 3. Kết luận + đề xuất

### Kết luận chính

1. **Cả hai model đều có thật, số liệu lõi phần lớn đúng**: MiMo-7B (32K/64K context, benchmark vượt o1-mini theo bảng tự công bố), MiMo-V2.6-Flash (309B/15B, $0.14/$0.28, 1M context, MIT). Sai số nhỏ: Q4_K_M ~4.7GB (không phải 5.3GB); "256K" của V2.6-Flash thực chất là context của bản MiMo-V2-Flash cũ — V2.6 là 1M thẳng.
2. **Điểm yếu lớn nhất của ADR**: runtime on-device (LiteRT.js/WebLLM) **chưa hỗ trợ MiMo**. Đường duy nhất khả thi là wllama v3 + GGUF Qwenified, **chưa có bằng chứng ai đã chạy** → spike phải test wllama trước, không coi đây là việc "có sẵn".
3. **Tiếng Việt của MiMo-7B hoàn toàn chưa được đánh giá** → đúng như rủi ro ADR nêu; đừng chốt on-device trước khi spike 50 câu thật.

### Đề xuất

- **Cloud — giữ MiMo-V2.6-Flash**: giá/context/API đã xác minh đúng; qua OpenRouter (route Xiaomi/DeepInfra) hoặc Xiaomi API. Puter.js chưa có V2.6 (chờ hoặc dùng V2-Flash/V2.5 nếu muốn đi qua Puter). Dữ liệu nhãn "cao" không gửi lên cloud; điều khoản (không huấn luyện khi chưa đồng ý, lưu EU/Singapore) là điểm cộng nhưng vẫn cần Duy duyệt trước khi gửi dữ liệu nhạy cảm.
- **On-device — bắt buộc có phương án dự phòng** (model prebuilt sẵn trên WebLLM/LiteRT, nguồn: [WebLLM docs](https://webllm.mlc.ai/docs/user/get_started.html), [LiteRT zoo](https://developers.google.com/edge/litert/genai/overview)):
  - WebLLM prebuilt: **Qwen3-8B** (đa ngôn ngữ 100+ ngôn ngữ, có thể tiếng Việt khá hơn), **Llama-3.2-3B-Instruct**, **Mistral-7B-v0.3** — chạy được ngay, không cần compile.
  - LiteRT.js prebuilt: **Gemma 3n E2B/E4B** (nhẹ, on-device tốt).
  - Giữ đúng kế hoạch spike so sánh của ADR và **thêm Qwen3-8B** vào danh sách so sánh; nếu MiMo-7B không lên được wllama trên máy đích, chuyển ngay sang Qwen3-8B/Llama-3.2-3B mà không đổi kiến trúc router (ADR thiết kế router không phụ thuộc model).

### Danh sách nguồn chính

- GitHub [XiaomiMiMo/MiMo](https://github.com/XiaomiMiMo/MiMo) (README + bảng eval, cập nhật 30/5/2025)
- [arXiv 2505.07608](https://arxiv.org/abs/2505.07608) — technical report MiMo (12/5/2025)
- [config.json MiMo-7B-RL-0530](https://huggingface.co/XiaomiMiMo/MiMo-7B-RL-0530/raw/main/config.json) (đọc 27/9/2026: 65536)
- [config.json MiMo-7B-Base](https://huggingface.co/XiaomiMiMo/MiMo-7B-Base/raw/main/config.json) (đọc 27/9/2026: 32768)
- [jedisct1/MiMo-7B-RL-GGUF](https://huggingface.co/jedisct1/MiMo-7B-RL-GGUF), [mradermacher/MiMo-7B-RL-0530-Qwenified-GGUF](https://huggingface.co/mradermacher/MiMo-7B-RL-0530-Qwenified-GGUF) (Q4_K_M 4.68GB)
- [llm-stats MiMo-V2.6-Flash](https://llm-stats.com/models/mimo-v2.6-flash), [eesel pricing](https://www.eesel.ai/blog/xiaomi-mimo-v2-6-pricing), [VentureBeat 21–22/9/2026](https://venturebeat.com/technology/better-than-deepseek-xiaomis-mimo-v2-6-pro-debuts-as-the-top-open-weights-model-in-the-world-alongside-cheaper-v2-6-flash)
- [OpenRouter xiaomi/mimo-v2.6-flash](https://openrouter.ai/xiaomi/mimo-v2.6-flash)
- [Puter.js MiMo models](https://developer.puter.com/ai/xiaomi/mimo-v2-flash/) (V2-Flash 256K context)
- [LiteRT GenAI](https://developers.google.com/edge/litert/genai/overview), [litert-community collection](https://huggingface.co/collections/litert-community/web-llm-models)
- [WebLLM get started](https://webllm.mlc.ai/docs/user/get_started.html), [wllama](https://github.com/ngxson/wllama) v3 (WebGPU)
- [Xiaomi MiMo API user agreement](https://mimo.mi.com/docs/quick-start/terms/user-agreement), [MiMo privacy policy](https://mimo.xiaomi.com/legal/privacy-policy)
- [VMLU — ACL 2025](https://aclanthology.org/2025.acl-long.563.pdf) (MiMo không xuất hiện trong bất kỳ đánh giá tiếng Việt nào)


---

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


---

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
