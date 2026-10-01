// Chuỗi tiếng Việt của module AI — một chỗ để e2e đọc qua window.__caveMock.msg (đừng gõ lại trong kịch bản).
// C.2: gate chỉ tải khi `ai_enabled` VÀ đã đồng ý; AI tắt → không tải, không chạy (S08-AC6).

export const AI_MSG = {
  title: "Trợ lý vận hành",
  /** Lô 1–2: LLMock trả câu giả (BR-AI-16: production luôn dùng model thật). */
  trialBadge: "Chế độ thử · dữ liệu giả",
  onDeviceBadge: "Chạy trên máy này",
  statusOff: "Trợ lý AI đang tắt ở hệ thống.",

  // ---- Đồng ý tải model (S08-AC1) ----
  consentTitle: "Bật trợ lý trên máy",
  consentBody:
    "Trợ lý trả lời câu hỏi vận hành ngay trong máy bạn (on-device). Để làm được, trợ lý cần tải model ngôn ngữ (khoảng 1–3 GB) về máy này MỘT lần, rồi dùng lại.",
  consentCheck: "Tôi đồng ý để trợ lý tải model về máy này qua Wi-Fi.",
  consentAgree: "Bật trợ lý",
  /** Không có cờ này thì nút Bật trợ lý bị khoá — đồng ý phải chủ động (S08-AC1). */
  consentHint: "Cần chọn ô đồng ý để bật trợ lý.",

  // ---- Kiểm tra máy (S08-AC2/AC3) ----
  capTitle: "Kiểm tra máy",
  ramLabel: "RAM",
  webgpuLabel: "WebGPU",
  wifiLabel: "Mạng",
  unsupportedIos: "Trợ lý chưa chạy được trên iPhone/iPad. Bạn vẫn nhập tay như bình thường.",
  lowRamTitle: "Máy không đủ bộ nhớ",
  lowRamBody: "Trợ lý chạy ngay trên máy cần ít nhất 8 GB RAM. Máy này không đạt — bạn vẫn nhập tay như bình thường, không đẩy việc lên mây.",
  ramUnknownTitle: "Chưa đo được RAM",
  ramUnknownBody: "Trình duyệt không báo dung lượng RAM của máy này. Trợ lý cần ít nhất 8 GB để chạy mượt — bạn có muốn vẫn thử tải không?",
  tryAnyway: "Vẫn thử tải",
  needWifi: "Tải model cần Wi-Fi. Bạn đang dùng mạng di động — đổi sang Wi-Fi rồi tải để khỏi tốn dung lượng.",
  networkUnknown: "Chưa biết bạn đang dùng mạng gì. Nếu là mạng di động, việc tải sẽ tốn dung lượng — kiểm tra lại khi đang ở Wi-Fi.",
  checkAgain: "Kiểm tra lại",
  wifi: "Wi-Fi",
  cellular: "Mạng di động",
  unknown: "Không rõ",

  // ---- Tải model (S08-AC1, sequential full-file GGUF) ----
  modelNotPicked: "Chưa chốt model — trợ lý chưa thể tải về máy (đang chờ chốt ở S17). Bạn vẫn nhập tay như bình thường.",
  downloadTitle: "Tải model về máy",
  downloadHint: "Tải MỘT lần (khoảng 1–3 GB) qua Wi-Fi, sau này dùng lại không cần tải.",
  download: "Tải model",
  pause: "Tạm dừng",
  resume: "Tải tiếp",
  cancel: "Huỷ tải",
  downloading: "Đang tải…",
  downloaded: "Model đã sẵn trên máy — trợ lý chạy không cần mạng.",
  downloadFailed: "Tải không xong — thử lại khi mạng ổn.",
  downloadPausedByNetwork: "Đang dùng mạng di động — tạm dừng tải. Về Wi-Fi rồi bấm Tải tiếp.",
  cacheCorrupt: "Bản model lưu trên máy bị hỏng — tải lại nhé.",

  // ---- Hộp chat (LLMock lô 1–2) ----
  chatLabel: "Thử trợ lý",
  chatHint: "Trợ lý đang ở chế độ thử: trả lời bằng dữ liệu giả, chưa đọc sổ sách thật.",
  chatPlaceholder: "Hỏi về kho, lô, đơn… (ví dụ: Còn bao nhiêu cá thu?)",
  send: "Gửi",
  thinking: "Đang nghĩ…",
  aiLabel: "AI",
  chatError: "Trợ lý chưa trả lời được lúc này — thử lại.",
  detailLoadFailed: "Chưa mở được chi tiết đề xuất nên chưa thể Đồng ý. Bấm Thử lại.",
  emptyChatTitle: "Hỏi trợ lý điều gì đó",
  emptyChatBody: "Ví dụ: tồn kho, lô sắp hết hạn, đơn đang chờ…",

  // Chuỗi riêng của runtime (thiếu thư viện chạy AI…) nằm ở runtime/messages.ts, KHÔNG để ở đây:
  // file này được layout nạp tĩnh, chứa chuỗi runtime sẽ kéo tên thư viện AI vào chunk ban đầu (SR-20, F13).
} as const;

// ---- Cụm cho màn Nhật ký (S03) — features/audit đọc từ đây để e2e đọc qua __caveMock.msg ----
export const AUDIT_MSG = {
  title: "Nhật ký hoạt động",
  hint: "Mọi thay đổi trong hệ thống đều ghi ở đây, mới nhất trước. Dòng “ai:” là việc do trợ lý đề xuất.",
  filterAll: "Tất cả",
  filterUser: "Người",
  filterAi: "AI",
  filterSystem: "Hệ thống",
  actorAi: "AI",
  actorSystem: "Hệ thống",
  aiActor: "ai:",
  proposal: "Đề xuất",
  changes: "Thay đổi",
  empty: "Chưa có dòng nhật ký nào",
  emptyHint: "Các thao tác trên hệ thống sẽ xuất hiện ở đây.",
  loadMore: "Tải thêm",
  refresh: "Làm mới",
} as const;
