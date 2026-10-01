# QA — Lưu cài đặt AI và CMS trên backend thật (SR-AIS-01/02/03 + RA-04 / BR-AI-22) · lần 1 và lần 2 · 2026-10-01

> **Kết luận hiện hành: lần 2 APPROVED (xem mục `## Lần 2` ở cuối).** Phần bên dưới đến hết mục `## Lệnh đã chạy` là lần 1 (REJECTED), giữ nguyên làm lịch sử.

## Kết luận: REJECTED — 2 lỗi Medium trong phạm vi lô (B1: ô ngưỡng biến mất sau khi xoá và lưu; B2: môi trường chỉ cho C mà user còn override B thì mọi lần lưu "AI của tôi" bị 400). Ba lỗi chính B1/B2/B3 của Lô 4b và RA-04 đều đã đạt trên backend thật.

## Tổng: 113 ca chạy thật (UI Playwright + API trên Django thật) · ✅ 111 · ❌ 2 · ⏸ 0
Ngoài ra, hồi quy: BE 1817 OK, vitest 271 OK, mock e2e 79/79 và 74/74 OK. Hai ca "FAIL" của kịch bản gốc là do kịch bản chặt quá (console có 400 do chính ca thử cố tình gây ra); đã tính vào ✅, giải thích ở mục Ngoại lệ.

Môi trường: Django working tree (gồm bản sửa RA-04 của be-dev), SQLite tạm, `migrate`, dữ liệu giả (`qa_*`), `AI_ENABLED=1`, cổng 8281; ERP build thật `NEXT_PUBLIC_USE_MOCK=0` cổng 3281; ERP build từ `git archive HEAD` cổng 3282 để đối chứng. Mọi server đã tắt (kiểm `lsof`). Kịch bản và ảnh nằm trong scratchpad `.../scratchpad/qa-ai-save/` (`*.py`, `out/*.log`, `shots/*.png`).

## Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| SR-AIS-01 AC1 (PUT chính sách và PUT my-config gửi object, BE 200, đúng phiên bản) | ✅ | `policy_ui.py` P1, P2 (200, thân object một lớp, version +1, `global_mode`/trần/vùng đỏ đúng); `mine_ui.py` M1–M4 (200, v+1). Đối chứng HEAD: `head_ui.py` H1, H3 cùng thao tác trả 400 `Expected a dictionary, but got str`, version không đổi. Ảnh `shots/new-policy-saved.png`, `shots/head-policy-400.png` |
| SR-AIS-01 AC2 (rà mọi chỗ `body: JSON.stringify`) | ✅ | `grep -rn "body: JSON.stringify" app features shared` (trừ test) = 0 dòng; CMS thật `cms_ui.py` C1, C2, C5, C6 (201/200, thân là object); vitest 271 xanh |
| SR-AIS-01 AC3 (mock bắt được lỗi này) | ✅ | `http.test.ts` và `policyApi.test.ts`, `categoryApi.test.ts` trong vitest; mock e2e 79/79 và 74/74 |
| SR-AIS-02 AC1 (đọc `limits` phẳng, không gửi `""`) | ⚠️ đạt đường thuận, lỗi ở biên (B1) | `limits_ui.py` L1 (ô hiện 60 và 6000000), L2, L4 (vượt trần 400 BR-AI-19, không lưu), L5, L6 (xoá hai ô thì `limits={}`) đạt. L3 xoá một ô rồi lưu: thân không có `""` đạt, nhưng ô vừa xoá biến mất (xem B1) |
| SR-AIS-03 AC1 (lưu giữ nguyên `groups`) | ✅ | `mine_ui.py` M1, M3: thân PUT mang đủ `groups`, nhóm OFF giữ OFF/OFF; M2 lưu hai lần liên tiếp không tải lại vẫn giữ lệnh của lần 1 |
| SR-AIS-03 AC2 (đổi 1 lệnh thì `effective_level` mọi lệnh khác không đổi) | ✅ | `eff.py` đọc `effective_level` do BE thật tính, mọi user × 111 lệnh, trước và sau: M1 chỉ `qa_off/inventory.batch.list` OFF→A; M2 chỉ lệnh thứ hai OFF→C; M3 chỉ `qa_mgr_off/sales.salesorder.list` A→OFF; M4 lưu không đổi thì diff rỗng |
| RA-04 / BR-AI-22 (Chủ tắt thì chỉ Chủ bật lại) | ✅ | `kill_ui.py` 21/21: Chủ tắt `qa_target`; nhân viên bấm "Bật lại AI của tôi" → 403 `BR-AI-22`, UI hiện đúng câu "Chủ đã tắt AI của bạn — chỉ Chủ bật lại được.", vẫn tắt, không tạo version; lưu cấu hình khi đang bị tắt vẫn tắt; PUT không đổi được `killed`; Chủ "Mở lại" 200 thì nhân viên dùng lại được; nhân viên tự tắt rồi tự bật lại được; nhân viên tự tắt rồi Chủ tắt thì nhân viên bật lại 403. Ảnh `shots/new-kill-403.png` |

## Ngoại lệ và biên
| Ca | Kết quả | Ghi chú |
|---|---|---|
| Hai tab "AI của tôi" cùng lưu (`twotab_ui.py` M6, 6 ca) | ✅ | Tab cũ 409 `AI_CONFIG_CONFLICT`, version giữ, lệnh của tab mới không bị ghi đè, UI hiện "Cấu hình đã thay đổi ở phiên khác"; tải lại thì lưu được, cả hai thay đổi cùng tồn tại. Ảnh `shots/new-mine-409.png` |
| Hai tab Chính sách AI (`policy_ui.py` P4) | ✅ | Tab cũ 409 `AI_POLICY_CONFLICT`, không mất dữ liệu |
| Chưa tick xác nhận trách nhiệm (BR-AI-14) | ✅ | Nút khoá, không có PUT (P3) |
| Vượt trần Chủ (BR-AI-19) | ✅ | L4: 400, giao diện hiện lỗi, version không đổi |
| Vùng đỏ bị Chủ đóng sau khi user đã đặt B | ✅ | `edge_ui.py` E1: BE tự hạ override B xuống C (version +1), user lưu thay đổi khác vẫn 200, không kẹt |
| Môi trường chỉ cho C mà user còn override B (production hoá) | ❌ | Lỗi B2 |
| Xoá một ô ngưỡng rồi lưu | ❌ | Lỗi B1 |
| Chính sách: tạo chuyên mục trùng tên, tên trống | ✅ | 400 `BR-ND-04`, tên trống không gửi 2xx (C3, C4). Dòng "console không sạch" ở C8 và L* là do chính ca này gây ra (400 chủ ý), không phải lỗi sản phẩm |
| `row_version` cũ khi sửa bài | ✅ | 409 `STALE_VERSION`, tiêu đề không bị ghi đè (C7) |
| Lặp lại chạy 2 lần sau khi reset DB | ✅ | policy/mine/kill/cms/limits chạy lại cho cùng kết quả |

## Phân quyền (Group × hành động; API thật, `perm.py` 15 ca)
| Người dùng | GET/PUT chính sách | Kill user khác | GET my-config | Kill bản thân | Trang `/ai/policy/` |
|---|---|---|---|---|---|
| owner (Chủ) | 200 / 200 | 200 | 200 | 200 | thấy form |
| manager | 403 / 403 | 403 | 200 | 200 | không có form |
| warehouse_staff | 403 / 403 | 403 | 200 | 200 | không có form |
| delivery_staff | 403 / 403 | 403 | 200 | 200 | không có form |
| customer_service | 403 / 403 | 403 | 200 | 200 | không có form |
| chưa đăng nhập | 401 | 401 | 401 | 401 | — |

Nhân viên tự bật lại AI do chính mình tắt: được. AI do Chủ tắt: 403 BR-AI-22 (đã nêu ở trên).

## Rò giá vốn
✅ Quét `GET /api/ai/my-config/` và `GET /api/ai/policy/` cho 5 Group: chỉ khớp tên lệnh `purchasing.purchasecost.*` và câu chữ "chốt giá vốn lô" (chỉ Chủ thấy; không có giá trị tiền hay giá vốn). `limits` chỉ có ngưỡng kg và vnd của chính người dùng; không tính ngược ra giá vốn được. AuditLog của các lần lưu chỉ chứa khoá lệnh, mức, `killed`, `global_mode`; không có tiền hay kg. Lô này không đụng Shop.

## Rò dữ liệu cá nhân
✅ Hai API trên không có khoá tên, SĐT, địa chỉ, email; danh sách `users` của chính sách chỉ có `user_id`, `display_name`, `groups`, `killed`, `config_version`, `counts`. NV kho không thấy lệnh nào về khách (0/41 lệnh `customers/cskh`). `localStorage` chỉ có khoá phiên `cave_erp_token`, `cave_erp_last_user` (P*); URL và console không chứa dữ liệu cá nhân. Toàn bộ dữ liệu là dữ liệu giả `qa_*`.

## Hồi quy
| Lệnh | Kết quả |
|---|---|
| `npm ci` (không `--legacy-peer-deps`) | exit 0 |
| `npx tsc --noEmit` | sạch |
| `npm test` (vitest) | 27 tệp / 271 test OK |
| `NEXT_PUBLIC_USE_MOCK=1 npm run build`, mock e2e `p8_lo7_fe_erp.py` | 79/79 PASS |
| mock e2e `p8_lo6_fe_sr19_sr20.py` | 74/74 PASS |
| `python3 scripts/check_naming.py` | OK, không phát sinh vi phạm mới |
| Backend `manage.py test` (cây làm việc hiện tại, gồm sửa RA-04) | 1817 test OK; tệp BE không đổi sau lần chạy |
| Build thật trỏ API production (`NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433…`) | build OK; `check-no-mock` XANH; `check-ai-chunks` XANH; không còn chuỗi 127.0.0.1:8281 trong `out/` |
| Adapter | ⏸ không chạy (lô không đụng `adapter/`) |

## Lỗi
### B1 — Ô ngưỡng biến mất sau khi xoá và lưu, không nhập lại được · Medium · SR-AIS-02
- **Bước:** đăng nhập `qa_limit` (nhân viên kho, `receive_batches` mức B, ngưỡng kg=60, vnd=6.000.000) → AI của tôi → xoá ô kg → Lưu cấu hình.
- **Mong đợi:** lưu 200, ô kg vẫn còn (trống) để nhập lại.
- **Thực tế:** lưu 200 và thân đúng (`limits={vnd:"6000000"}`, không có `""`), nhưng BE trả `limits` không còn khoá `kg` nên `MyConfigScreen` (chỉ vẽ ô khi `"kg" in cmd.limits`) bỏ luôn ô kg. Xoá cả hai thì cả hai ô biến mất. Ca `limits_ui.py` L3 (đỏ). Cùng gốc với nợ "chưa đặt được ngưỡng lần đầu từ UI" đã ghi ở `03-dev-notes.md`, nhưng lần này người dùng đang có ngưỡng rồi tự làm mất khả năng đặt lại.
- **Ảnh hưởng:** người dùng không bao giờ đặt lại được ngưỡng đã xoá. Không mất tiền, không rò dữ liệu, không nới quyền (bỏ ngưỡng là chủ ý của họ).
- **Gợi ý sửa:** BE trả cờ lệnh nào hỗ trợ ngưỡng (vd `supports_limits`) rồi FE luôn vẽ ô cho lệnh đó khi mức B; hoặc tạm thời FE giữ ô theo trạng thái đã tải của phiên. Nếu Duy chấp nhận coi đây là nợ đã biết thì ghi vào backlog và chuyển thành "chấp nhận có điều kiện".

### B2 — Môi trường chỉ cho C mà user còn override B thì mọi lần lưu "AI của tôi" bị 400 · Medium · SR-AIS-03 (lưu không kẹt)
- **Bước:** `qa_limit` có override B ở `purchasing.purchasereceipt.receive_batches` (đặt khi môi trường cho B) → khởi động Django với `AI_WRITE_LEVELS_ALLOWED=C` → AI của tôi → đổi lệnh khác `sales.salesorder.list` sang OFF → Lưu (`edge2_ui.py`).
- **Mong đợi:** lưu 200 (như cách `buildGroupsForSave` đã hạ nhóm B xuống C), hoặc báo rõ lệnh nào gây lỗi.
- **Thực tế:** FE hạ `groups` B→C nhưng vẫn gửi nguyên `overrides` có B → BE 400 `BR-AI-27` "Môi trường hiện tại không hỗ trợ mức tự thực thi B." (không nêu lệnh nào). Ô chọn của lệnh đó còn hiển thị "Tắt (OFF)" (vì danh sách chọn không có B) nên người dùng không biết phải sửa lệnh nào. Cách thoát: tự đổi lệnh đó sang C.
- **Ảnh hưởng:** chỉ xảy ra khi môi trường bị hạ từ B xuống C mà vẫn giữ dữ liệu cũ (staging và production dùng DB riêng nên khả năng thấp). Không rò dữ liệu, không nới quyền; nhưng người dùng bị kẹt không lưu được gì. Ảnh `shots/new-edge-env-c.png`.
- **Gợi ý sửa:** `buildMyConfigPayload` hạ override B về C theo `write_levels_allowed` giống `buildGroupsForSave`; hiển thị mức hiệu lực đúng thay vì "OFF".

### Phát hiện ngoài phạm vi lô (có từ trước, không chặn lô này; đề xuất đưa vào backlog BE)
- **O1 — AuditLog của kill/policy/config không ghi đối tượng · Medium.** `record_audit(... target_model=..., target_id=...)` trong `ai/settings/services.py` bị `**kwargs` nuốt nên `model_name`, `object_id`, `object_repr` đều rỗng. Dòng "ai_config_kill" khi Chủ tắt một nhân viên không cho biết tắt AI của ai (`created_by` trong `AiConfigVersion` vẫn có, nên BR-AI-22 chạy đúng).
- **O2 — AuditLog chính sách không ghi thay đổi trần** (kg, vnd, daily) và lần lưu chính sách đầu tiên không ghi `global_mode`; lưu "AI của tôi" chỉ đổi ngưỡng thì `changes` là `{}` (`policy_ui.py` P1 và `limits_ui.py`). Không rò dữ liệu, nhưng thiếu dấu vết cho hành động Tầng 2.
- **O3 — `POST /api/content/categories/` với thân JSON là chuỗi trả 500** (`AttributeError: 'str' object has no attribute 'get'`, thấy khi chạy build HEAD, `head_ui.py` H2). Nên trả 400. Mức Low (cần đăng nhập và có quyền; bản FE mới không còn gửi kiểu này).

## Lệnh đã chạy (tóm tắt)
- `bash reset.sh 1` (khôi phục DB seed, chạy Django cây làm việc, `AI_PRODUCTION_READY=1`); `start_c.sh` (env C) cho `edge2_ui.py`.
- `python3 policy_ui.py` 21/21 · `mine_ui.py` 16/16 · `limits_ui.py` 10/12 (L3 thật, L* artifact) · `kill_ui.py` 21/21 · `twotab_ui.py` 6/6 · `cms_ui.py` 15/16 (C8 artifact) · `perm.py` 15/15 · `edge_ui.py` 1/1 · `edge2_ui.py` 0/1 · `WEB=http://127.0.0.1:3282 TAG=head python3 head_ui.py` (đối chứng HEAD: H1, H3 → 400 đúng lỗi cũ; H2 → 500).
- `npm ci`, `npx tsc --noEmit`, `npm test`, `NEXT_PUBLIC_USE_MOCK=1 npm run build` + `e2e/p8_lo7_fe_erp.py` + `e2e/p8_lo6_fe_sr19_sr20.py`, `python3 scripts/check_naming.py`, `backend: manage.py test` (1817 OK).
- Build cuối `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build` + `node scripts/check-no-mock.mjs` + `node scripts/check-ai-chunks.mjs` (XANH). Đã tắt Django 8281 và các server tĩnh 3281, 3282, 3216, 3217.
- Không sửa mã sản phẩm. `git status` của mã sản phẩm giữ nguyên 8 tệp sửa như đầu phiên.


---

## Lần 2 · 2026-10-01

### Kết luận lần 2: APPROVED — B1 và B2 đã sửa, chạy lại đúng bước tái hiện trên backend thật và ERP build thật; hồi quy sạch, không còn lỗi chặn.

### Tổng lần 2: 164 ca chạy thật (Playwright + API trên Django thật) · ✅ 163 · ❌ 0 · ⏸ 1
Hồi quy: BE 1822 test OK; vitest 289 OK; mock e2e 79/79 và 74/74; `tsc` sạch; `check_naming` OK.
Hai dòng "console không sạch" ở `limits_ui.py` (L*) và `cms_ui.py` (C8) vẫn là 400 do chính ca thử gây ra (vượt trần Chủ, tạo chuyên mục trùng tên), tính vào ✅. Môi trường: Django cây làm việc mới (có `supports_limits`), SQLite tạm, dữ liệu giả `qa_*`, ERP build thật cổng 3281, Django cổng 8281 (cổng này khác với cổng dev, không ảnh hưởng kết quả).

### Kiểm lại hai lỗi
| Lỗi | Kết quả | Bằng chứng (`b1_r2.py` 39/39, `b2_r2.py` 12/12) |
|---|---|---|
| B1 (ô ngưỡng biến mất) | ✅ đã sửa | `qa_limit` xoá ô kg rồi lưu: 200, thân `limits={vnd:"6000000"}` (không có `kg`, không có `""`), ô kg **vẫn còn** và trống; tải lại trang ô vẫn còn; nhập lại kg=50 → API có `{kg:"50", vnd:"6000000"}`. Xoá cả hai ô: 200, `limits={}`, hai ô vẫn còn kể cả sau tải lại; đặt lại 70/7.000.000: 200. `limits_ui.py` L3 (đỏ ở lần 1) nay xanh. Ảnh `shots/r2-b1-after-clear.png`, `shots/r2-b1-mobile.png` (390px) |
| B1 đặt ngưỡng lần đầu (nợ N1) | ✅ | `qa_warehouse` (chưa từng có ngưỡng) chọn nhập lô mức B: ô kg và vnd hiện, nhập 40/4.000.000, lưu 200, BE lưu đúng; `effective_level` mọi user × lệnh chỉ đổi `qa_warehouse` nhập lô C→B. Cả màn chỉ có đúng 1 ô kg (chỉ lệnh có cờ true). Ảnh `shots/r2-b1-first-time.png` |
| B1 vượt trần Chủ | ✅ | kg=90 > 80: 400 BR-AI-19, giao diện hiện "Nhập lô mua tại cảng: vượt trần của Chủ." (nêu tên lệnh); version không đổi |
| B2 (env C + override B) | ✅ đã sửa | `AI_WRITE_LEVELS_ALLOWED=C`, `qa_limit` còn override B nhập lô: ô chọn hiện "Mức C" (không còn "Tắt (OFF)"), không mời B; đổi `sales.salesorder.list` sang OFF rồi lưu → **200** (lần 1: 400 BR-AI-27); thân PUT `overrides={nhập lô:"C", đơn bán:"OFF"}`, `groups` không còn B; `effective_level` mọi user × lệnh: chỉ `qa_limit/sales.salesorder.list` A→OFF, nhập lô vẫn C; ngưỡng 60/6.000.000 còn nguyên; lưu lần hai 200; manager lưu 200. Ảnh `shots/r2-b2-open.png`, `shots/r2-b2-after.png` |
| B2 vùng đỏ | ✅ | Vùng đỏ đã mở + override B (chốt lô, owner): ô hiện B, lưu 200 và override B giữ nguyên, `effective_level` chỉ đổi lệnh đơn bán, chốt lô vẫn B (`rz_r2.py`). Vùng đỏ bị đóng sau khi đặt B: BE hạ về C, lưu 200 (`edge_ui.py` E1) |
| B2: lỗi BR-AI-27 nêu tên lệnh | ⏸ | FE nay không còn gửi B ở môi trường C nên lỗi không tự xảy ra. Khi tôi can thiệp request để ép gửi B: BE vẫn 400 BR-AI-27 và UI hiện thông báo, nhưng câu thông báo **không** nêu tên lệnh (`b2_msg.py`: "Môi trường hiện tại không hỗ trợ mức tự thực thi B."); nhánh liệt kê lệnh chỉ chạy khi thân do FE dựng có B, nên chỉ kiểm bằng vitest. Không chặn: đường này không còn xảy ra với người dùng thật. BR-AI-19 nêu tên lệnh thì đã kiểm chạy thật (dòng trên) |

### Cờ `supports_limits` (BE)
| Ca | Kết quả |
|---|---|
| Luôn là bool ở mọi lệnh, cho cả 5 Group (103/71/41/10/3 lệnh) | ✅ |
| Chỉ `purchasing.purchasereceipt.receive_batches` có cờ true; mọi lệnh đọc false | ✅ |
| Không mở lệnh cho Group thiếu quyền: delivery_staff và customer_service không thấy lệnh nhập lô; chưa đăng nhập 401 | ✅ |
| Không lộ giá vốn hay dữ liệu cá nhân: JSON `my-config` của cả 5 Group không chứa `purchase_rate`, `landed_unit_cost`, `unit_cost`, `profit`, `margin`, `cost`, tên, SĐT, địa chỉ, email | ✅ |
| Không lộ trần Chủ ở `my-config` (chỉ có cờ bool và `limits` của chính user) | ✅ |
| AuditLog: không thêm khoá mới (cờ chỉ có trong response, không ghi log) | ✅ |

### Hồi quy các kịch bản lần 1 (backend thật + ERP build thật, cùng build lần 2)
| Kịch bản | Kết quả |
|---|---|
| Chính sách AI `policy_ui.py` | 21/21 (lưu chế độ, trần, vùng đỏ, kill; 409 hai tab; chưa tick xác nhận) |
| AI của tôi `mine_ui.py` | 16/16 (đổi 1 lệnh thì `effective_level` mọi user × 111 lệnh chỉ đổi lệnh đó; groups OFF giữ nguyên) |
| RA-04 / BR-AI-22 `kill_ui.py` | 21/21 |
| Hai tab `twotab_ui.py` | 6/6 (409 `AI_CONFIG_CONFLICT`, không mất dữ liệu) |
| CMS `cms_ui.py` | 15/16 (+1 dòng console do 400 chủ ý); tạo/sửa chuyên mục 201/200, lưu nháp 201, sửa bài 200, `row_version` cũ 409 |
| `limits_ui.py` | 11/12 (+1 dòng console do 400 chủ ý) |
| Phân quyền `perm.py` | 15/15, bảng Group × hành động không đổi so với lần 1 (chỉ owner PUT/kill được; 403 cho manager, warehouse_staff, delivery_staff, customer_service; 401 chưa đăng nhập) |
| Backend `manage.py test` | 1822 OK (tệp backend không đổi sau lần chạy) |
| `npm ci`, `npx tsc --noEmit`, `npm test` | exit 0 · sạch · 27 tệp / 289 test OK |
| Mock e2e `p8_lo7_fe_erp.py`, `p8_lo6_fe_sr19_sr20.py` | 79/79 · 74/74 |
| `python3 scripts/check_naming.py` | OK, không vi phạm mới |
| Build thật trỏ API production + `check-no-mock` + `check-ai-chunks` | build OK; XANH; XANH; không còn chuỗi `127.0.0.1:82xx` trong `out/` |

Rò dữ liệu cá nhân và giá vốn: không phát hiện (xem bảng cờ ở trên; hồi quy `policy_ui.py` giữ kiểm `localStorage` chỉ có khoá phiên). Toàn bộ dữ liệu giả.

### Ghi nhận (không chặn)
- Khi môi trường chỉ cho C, lần lưu đầu tiên của người dùng ghi override B thành C vào cấu hình (bền vững). Nếu sau này môi trường cho B lại thì lệnh đó ở C cho đến khi người dùng chọn lại B. Hành vi thận trọng, không nới quyền; chỉ nêu để Duy biết.
- `GET /api/ai/my-config/` ở môi trường C vẫn trả `level: "B"` thô cho lệnh đã lưu B (FE tự quy về C để hiển thị); do dev nêu ở dev-notes, nên cân nhắc cho BE trả mức hiệu lực.
- Ba phát hiện ngoài phạm vi ở lần 1 (O1 AuditLog kill/policy/config không ghi đối tượng; O2 AuditLog không ghi thay đổi trần và ngưỡng; O3 `POST /api/content/categories/` thân chuỗi trả 500) vẫn mở, đề xuất backlog BE, không chặn lô này.
- Hai màn AI hiển thị thô vì ERP không biên dịch Tailwind (nợ UI review, ngoài phạm vi).

### Lệnh đã chạy lần 2 (tóm tắt)
`npm ci` · `npx tsc --noEmit` · `npm test` (289) · `manage.py test` (1822 OK) · `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8281 npm run build` + Django cổng 8281 (`reset.sh 1`, env C bằng `start_c.sh`) · `b1_r2.py` (39/39) · `b2_r2.py` (12/12) · `b2_msg.py` · `rz_r2.py` (3/3) · `limits_ui.py`, `policy_ui.py`, `mine_ui.py`, `kill_ui.py`, `twotab_ui.py`, `cms_ui.py`, `edge_ui.py`, `perm.py` · mock build + e2e 79/79 và 74/74 · `check_naming.py` · build cuối `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build` + `check-no-mock` + `check-ai-chunks`. Đã tắt Django 8281 và mọi server tĩnh (kiểm `lsof`). Không sửa mã sản phẩm.
