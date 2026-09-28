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
