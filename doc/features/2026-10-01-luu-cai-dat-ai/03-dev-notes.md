# Dev notes — Lưu cài đặt AI và CMS trên backend thật (SR-AIS-01/02/03)
> 2026-10-01 · luồng NHANH · chỉ sửa `erp-console/`, không đụng `backend/`, không commit.

## FE

### Nguyên nhân gốc
- **B1.** `apiFetch` đã tự `JSON.stringify(body)`, nhưng 6 chỗ gọi vẫn truyền `JSON.stringify(...)` nên body thành chuỗi JSON lồng, BE trả 400 `Expected a dictionary, but got str`. Mock không parse body nên che mất.
- **B2.** BE trả `limits` phẳng `{kg, vnd}`, FE đọc `limits.kg?.mine`, nên ô trần trống; ô để trống bị gửi `""` và BE trả 400.
- **B3.** Lưu "AI của tôi" không gửi `groups`. BE **thay thế** `group_levels` bằng giá trị gửi lên (vắng = rỗng, không phải "giữ"), nên nhóm đặt OFF rơi về mặc định A/C, tức là nới quyền AI.

### Đã sửa (đều trong `erp-console/`)
| Tệp | Thay đổi |
|---|---|
| `shared/lib/http.ts` | Thêm `mockWireBody`: mock nhận body đã qua vòng JSON như BE thật; body là chuỗi (JSON lồng) thì trả 400 `Expected a dictionary, but got str` giống BE, không chạy handler. |
| `features/ai/policy/api.ts` | Bỏ `JSON.stringify` ở `updateAiPolicy`, `killUserAi`. Mock chính sách đọc `req.body`, kiểm BR-AI-14 (400), `base_version` cũ (409 `AI_POLICY_CONFLICT`), cập nhật version. |
| `features/content/api.ts` | Bỏ `JSON.stringify` ở `createCategory`, `updateCategory`; mock đọc `req.body`. (Các hàm entry vốn đã gửi object.) |
| `features/ai/types.ts` | `MyConfigCommandItem.limits` thành `MyCommandLimits \| null` (phẳng `{kg?, vnd?}`). |
| `features/ai/settings/payload.ts` (mới) | `readLimitInputs`, `buildLimitsForSave` (ô trống không gửi khoá), `buildGroupsForSave` (gửi lại `read_level`/`write_level` đang có; mức ghi ngoài `write_levels_allowed` thì hạ về C), `buildMyConfigPayload`. |
| `features/ai/settings/mock.ts` (mới) | Mock có trạng thái theo ngữ nghĩa BE: PUT thay thế toàn bộ, 409 phiên bản cũ, 400 BR-AI-14/BR-AI-19, limits phải là chuỗi số. |
| `features/ai/settings/api.ts` | `getMyConfig`, `updateMyConfig(MyConfigSavePayload)`, `killMyConfig` truyền object. |
| `features/ai/settings/components/MyConfigScreen.tsx` | `applyConfig` dựng lại state override/limit từ dạng phẳng; `handleSave` dùng `buildMyConfigPayload`; ô ngưỡng có `htmlFor`/`id`, nhãn "Giới hạn kg mỗi lần (không vượt trần của Chủ; để trống nếu không đặt)". |

Hàm API đổi chữ ký: `updateMyConfig(payload: MyConfigSavePayload)` (bắt buộc có `groups`). Không có hàm API mới.

### Test (vitest) và bằng chứng đỏ -> xanh
Tệp test mới: `shared/lib/http.test.ts`, `features/ai/policy/policyApi.test.ts`, `features/content/categoryApi.test.ts`, `features/ai/settings/settingsApi.test.ts`, `features/ai/settings/settingsPayload.test.ts`, hạ tầng `shared/lib/testing/fakeBackendFetch.ts` (fetch giả parse body như DRF).
- **B1:** trước khi sửa 8/9 test của lô này đỏ (body tới "BE" là chuỗi, trả 400); sau khi bỏ 6 `JSON.stringify` thì 9/9 xanh.
- **B3:** `settingsPayload.test.ts` có ca "tái hiện lỗi cũ" (không gửi `groups` -> OFF thành A). Để lấy đỏ hành vi, tạm cho `buildGroupsForSave` trả `{}`: 4 test đỏ (OFF thành A); khôi phục thì xanh.
- **B2:** test đọc `limits` phẳng và test ô trống không gửi `""`.
- Cuối cùng: `npx tsc --noEmit` sạch; `npm test` 27 tệp / 271 test xanh; `python3 scripts/check_naming.py` OK (không vi phạm mới).

### Chạy thật (Django working tree + ERP build thật)
Môi trường: SQLite tạm trong scratchpad, `migrate`, dữ liệu giả (3 user `ais_*`), `AI_ENABLED=1 AI_WRITE_LEVELS_ALLOWED=B`; Django cổng 8280; ERP build `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8280` phục vụ cổng 3280; điều khiển bằng Playwright (kịch bản `ai-save/flow.py` trong scratchpad). Kết quả 14/14 OK, không có lỗi trang:
- Chủ lưu Chính sách AI: PUT 200, body là object JSON một lớp, phiên bản 1 -> 2, `global_mode` đổi sang `c_only`.
- CMS: tạo chuyên mục POST 201; lưu bài nháp lần đầu 201; lưu lại (PATCH) 200.
- User có nhóm `purchasing` OFF mở "AI của tôi", đổi 1 lệnh (`sales.salesorder.list` A -> OFF), lưu: PUT 200, body có `groups` đủ 3 nhóm. Đọc `effective_level` qua API trước và sau: 41 lệnh, khác biệt duy nhất là lệnh đã đổi; 23 lệnh OFF vẫn OFF.
- Ô ngưỡng `receive_batches` hiện `60` và `6000000`; lưu không đổi gì: 200, ngưỡng và mức hiệu lực giữ nguyên; xoá trống ô kg: 200, body `limits = {vnd: "6000000"}` (không có `""`).
- Đã tắt cả hai server (kiểm bằng `lsof`, không còn cổng 3280/8280 nghe).
- Ảnh chụp mobile (scratchpad, ngoài repo): `/private/tmp/claude-501/-Users-dangthiduyen-Downloads-loc/3e0d9f3d-14ce-4b8b-a1cd-6fbcdc0b2f2d/scratchpad/ai-save/limits-mobile.png`, `mine-off-mobile.png`, `policy.png`.
- Build thật cuối (trỏ API production, như các lượt QA trước): `check-no-mock` XANH, `check-ai-chunks` XANH.

### Chỗ lệch contract
- `02b-tech-design.md` §6.5 vẽ `limits` dạng lồng `{kg:{mine,cap}}`; BE thật trả phẳng `{kg, vnd}` (chuỗi hoặc null), **không có trần của Chủ**. FE theo BE; nhãn "Trần của Chủ" đổi thành chữ chung. Không sửa BE. Nên cập nhật 02b theo BE.
- BE `update_user_config` thay thế `group_levels`/`overrides`/`limits` (vắng = rỗng). Không coi là lỗi contract vì gửi lại `groups` là không mất gì, nhưng nên ghi rõ vào 02b.

### Việc còn nợ
1. BE không báo lệnh nào hỗ trợ ngưỡng, nên ô ngưỡng chỉ hiện với lệnh đã có `limits` khác null và đang mức B. Chưa thể đặt ngưỡng lần đầu từ UI. Cần BE thêm cờ (vd `supports_limits`) rồi FE mở rộng.
2. Override/ngưỡng của lệnh ngoài quyền người dùng không gửi lại được (BE trả 400 với override đó, bỏ ngưỡng ẩn); hiện FE không đụng tới.
3. Màn "AI của tôi" và "Chính sách AI" dùng class Tailwind nhưng ERP không biên dịch Tailwind nên hiển thị thô (thấy ở ảnh mobile). Có từ trước, ngoài phạm vi lô này; nên giao UI review.

## RA-04 — BE

Luồng NHANH. Luật Duy chốt 30/09: "Chủ tắt AI của nhân viên thì chỉ Chủ bật lại được" (A1-03 trong `2026-09-30-ra-soat-agy/A1-code.md`). Mã rule mới: **BR-AI-22**.

### File
- `backend/apps/ai/settings/services.py`: thêm `_killed_by_owner(user)`; `kill_user_config` chặn khi `killed=False`, phiên bản mới nhất đang `killed=True`, người thực hiện KHÔNG giữ `ai.manage_ai_policy`, và lần tắt đang hiệu lực do người giữ quyền đó (khác chính user) tạo.
- `backend/apps/ai/settings/tests/test_kill_ownership.py` (mới, 10 test; chuyển từ repro `repro/A1/tests_ai.py::test_nhan_vien_tu_bat_lai_sau_khi_chu_tat`).
- Không sửa `policy/` (đường Chủ `kill_user_by_admin` đã gọi `kill_user_config` với `created_by=Chủ`, actor có quyền nên qua). Không sửa `api.py`: lỗi `BusinessError` tự thành 403. **Không migration, không field mới.**

### Cách nhận biết "Chủ tắt" (không thêm field)
Đọc `created_by` của các phiên bản `AiConfigVersion` trong chuỗi `killed=True` liên tiếp tính từ phiên bản `killed=False` gần nhất. Chỉ cần một phiên bản trong chuỗi do người giữ `ai.manage_ai_policy` (khác chính user) tạo là khoá. Lý do không chỉ nhìn phiên bản killed mới nhất: nhân viên đang bị tắt vẫn `PUT /api/ai/my-config/` được, và `update_user_config` sao chép `killed` nhưng đặt `created_by` là nhân viên; nếu chỉ nhìn bản mới nhất thì lưu cấu hình một lần là gỡ được khoá (có test `test_lock_survives_staff_saving_config_while_killed`). Chủ tắt tiếp một người đã tự tắt cũng khoá (`test_owner_kill_after_staff_self_kill_still_locks`).

### Contract
`POST /api/ai/my-config/kill/` body `{"killed": false}`, khi lần tắt do Chủ:
```
403 {"code": "BR-AI-22", "detail": "Chủ đã tắt AI của bạn — chỉ Chủ bật lại được."}
```
Không tạo phiên bản, không ghi AuditLog. Các trường hợp còn lại giữ nguyên: nhân viên tự tắt rồi tự bật 200; Chủ `POST /api/ai/policy/users/<id>/kill/ {"killed": false}` 200 (sau đó khoá hết hiệu lực, nhân viên tự tắt/bật lại bình thường); người kiêm Chủ + kho tự tắt/bật 200 (có quyền nên không bị chặn). `PUT /api/ai/my-config/` không đổi được `killed` (serializer không có field, service chép từ phiên bản trước); test xác nhận gửi `killed:false` qua PUT vẫn `killed=True`.
FE (fe-dev): màn "AI của tôi" đã hiện `detail` của lỗi chung; nên ẩn hoặc vô hiệu nút "Bật lại AI" khi `killed` và hiện thông điệp trên (BE chưa trả cờ "do Chủ tắt" trong `GET /api/ai/my-config/`; thêm cờ là việc sau, cần Duy duyệt nếu muốn).

### Về "mức hiệu lực vẫn OFF"
`effective_level` khi `killed=True` hạ lệnh GHI về C và lệnh ĐỌC vẫn chạy (V-DW4), không về OFF. Test assert đúng hành vi hiện có: lệnh ghi đặt B → khi bị tắt là C → bị chặn bật lại thì vẫn C → Chủ bật lại về B.

### Đỏ -> xanh
Trước khi sửa 3/10 test đỏ (200 != 403: `staff_cannot_reenable_ai_killed_by_owner`, `lock_survives_staff_saving_config_while_killed`, `owner_kill_after_staff_self_kill_still_locks`), 7 test hồi quy (tự tắt/bật, Chủ bật lại, kiêm vai, PUT, AuditLog, 401) xanh sẵn. Sau khi sửa: 10/10 xanh, `apps.ai` 272 test xanh.

### Còn nợ / giả định
- Hiếm: nếu nhân viên tự tắt rồi Chủ đóng công tắc vùng đỏ, `update_policy` tạo thêm phiên bản sao chép `killed=True` do Chủ ký, nên bị coi là "Chủ tắt" và nhân viên không tự bật lại được (Chủ bật lại được). Chấp nhận, ghi để biết.
- Người tắt đã mất quyền `ai.manage_ai_policy` hoặc bị khoá tài khoản thì lần tắt của họ không còn tính là "của Chủ".

## B1 — supports_limits (BE)

Luồng NHANH, sửa lỗi B1 của `04-qa-report.md` (FE chỉ vẽ ô ngưỡng khi `limits` có khoá, BE không báo lệnh nào hỗ trợ ngưỡng nên xoá ngưỡng xong không đặt lại được). Đây là nợ N1 của `03b-review-techlead.md`, làm phần cờ; phần trần của Chủ (`owner_cap`) để P9.

### File
- `backend/apps/ai/registry/spec.py`: `CommandSpec` thêm `limits: dict` (mặc định rỗng).
- `backend/apps/ai/registry/discovery.py`: hai chỗ dựng `CommandSpec` (action của ViewSet và APIView) chép `AiMeta.limits` sang spec.
- `backend/apps/ai/settings/services.py`: `get_user_config_data` thêm `supports_limits` cho mỗi command.
- `backend/apps/ai/settings/tests/test_supports_limits.py` (mới, 5 test).
- **Không migration, không field DB, không đổi khoá cũ.**

### Contract
`GET /api/ai/my-config/`: mỗi phần tử `groups[].commands[]` thêm một khoá. Khoá cũ giữ nguyên.
```
{"id": "purchasing.purchasereceipt.receive_batches", "kind": "write", "level": "C", "limits": null,
 "supports_limits": true, ...}
{"id": "inventory.batch.list", "kind": "read", "limits": null, "supports_limits": false, ...}
```
`supports_limits` luôn là bool, `true` khi `AiMeta.limits` của lệnh khai báo khác rỗng (hiện chỉ lệnh nhập lô: `lines[].qty` kg, `lines[].amount` vnd). Giá trị độc lập với `limits` (người dùng chưa lưu ngưỡng thì `limits=null` mà cờ vẫn `true`). Cờ không mở thêm lệnh cho Group: lệnh vẫn lọc theo quyền như cũ (delivery_staff không thấy lệnh nhập lô). Không trả trần của Chủ.

FE: vẽ ô ngưỡng theo `supports_limits`, không theo việc `limits` có khoá.

### Test
Lệnh nhập lô `true` kể cả khi `limits=null`; mọi lệnh đọc `false`; cờ là bool và đúng bằng tập spec có khai báo `limits` với owner, warehouse_staff, delivery_staff; tập khoá cũ không đổi, delivery_staff không thấy lệnh nhập lô; response không chứa `purchase_rate`, `landed_unit_cost`, `unit_cost`, `profit`. Đỏ trước khi sửa (KeyError `supports_limits`), xanh sau.

## B1/B2 QA — FE

> 2026-10-01 · sửa 2 lỗi Medium của `04-qa-report.md` (lần 1 REJECTED) · chỉ `erp-console/`, không đụng `backend/`, không commit.

### Nguyên nhân gốc và cách sửa
- **B1 — ô ngưỡng biến mất.** `MyConfigScreen` chỉ vẽ ô khi `"kg" in cmd.limits`; xoá ngưỡng xong BE trả `limits` thiếu khoá (hoặc `null`) nên ô mất. Nay vẽ theo cờ BE `supports_limits` (be-dev đã thêm vào `GET /api/ai/my-config/`: lệnh có khai ngưỡng thì `true`, kể cả khi `limits: null`). Cờ `true` thì luôn có cả ô kg và ô vnd; cờ `false` thì không có ô; BE chưa có cờ (`undefined`) thì tạm theo khoá `limits` đang có (tương thích), `limits` null thì không có ô. Giá trị ô trống khi `limits` null. Nếu sau này có lệnh chỉ khai một đơn vị, BE cần trả thêm danh sách đơn vị (hiện cờ chỉ là boolean nên FE vẽ cả hai).
- **B2 — môi trường chỉ cho C mà vẫn gửi override B (BE 400 BR-AI-27, ô hiện "OFF").** Quy tắc "lệnh có giữ được mức B không" gom vào một hàm dùng chung `canKeepLevelB` (môi trường cho B, `max_level` của lệnh là B, không có `locked_reason`), nên màn và thân PUT cùng một quy tắc:
  - `buildOverridesForSave` hạ override B về C khi không giữ được (giống `buildGroupsForSave` đã hạ nhóm). Mức hiệu lực không đổi vì trần vẫn chặn ở C.
  - `displayLevel` cho ô chọn hiển thị mức hiệu lực C thay vì rơi về OFF. `commandChoices` thay cho `computeChoices`: vẫn không mời chọn B ở lệnh vùng đỏ, nhưng nếu lệnh vùng đỏ đã mở và đang ở B thì ô hiện B (không còn OFF).
  - `describeSaveError`: BR-AI-19 có `errors` thì nêu tên lệnh hoặc nhóm kèm lý do (vd "Nhập lô mua tại cảng: vượt trần của Chủ."); BR-AI-27 BE không nêu lệnh nên liệt kê các lệnh trong thân vừa gửi đang ở mức B và bảo đổi sang C.

### Tệp
| Tệp | Thay đổi |
|---|---|
| `features/ai/settings/levels.ts` (mới) | `canKeepLevelB`, `displayLevel`, `commandChoices`, `limitFieldsOf`, `describeSaveError`. |
| `features/ai/settings/payload.ts` | Thêm `buildOverridesForSave`; `buildMyConfigPayload` dùng nó. |
| `features/ai/settings/components/MyConfigScreen.tsx` | Dùng `levels.ts`; bỏ `computeChoices`; ô ngưỡng theo `limitFieldsOf`; lỗi lưu qua `describeSaveError`. |
| `features/ai/types.ts` | `MyConfigCommandItem.supports_limits?: boolean` (tuỳ chọn để tương thích BE cũ). |
| `features/ai/settings/mock.ts` | Lệnh nhập lô `supports_limits: true`, lệnh khác `false`; `fail` trải `details` ra ngang hàng `detail`/`code` như BE. |
| `shared/lib/http.ts` | `ApiError.details` (tuỳ chọn) = phần thân lỗi ngoài `detail`/`code`. BE (`exception_handler`) trải `details` dạng object ra ngang hàng nên BR-AI-19 đến FE là `{errors: {...}, detail, code}`. Không đổi gì với chỗ gọi cũ. |

### Chỗ lệch contract
- Hàm API không đổi chữ ký. Cờ `supports_limits` do be-dev thêm cùng lô, FE đọc đúng tên.
- Phát hiện khi chạy thật: lỗi BR-AI-19 BE trả `errors` ở ngang hàng `detail`, không nằm trong khoá `details` như tên gọi trong code BE. FE đọc theo thân thật; mock cũng làm như vậy.
- `GET my-config` với môi trường C vẫn trả `level: "B"` thô cho lệnh đã lưu B (không phải mức hiệu lực); FE tự quy về C để hiển thị. Nếu muốn BE trả đúng mức hiệu lực thì việc của BE.

### TDD (vitest) và bằng chứng đỏ -> xanh
Viết test trước trong `features/ai/settings/settingsPayload.test.ts` (và `shared/lib/http.test.ts`): trước khi có `levels.ts` và cờ trên mock, 13/25 test đỏ (không tìm thấy `./levels`, `supports_limits` undefined, override B vẫn gửi). Sau khi sửa: 29 test của thư mục settings xanh. Các ca: `limitFieldsOf` (cờ true với `limits` null, thiếu khoá, đủ khoá; cờ false; tương thích không cờ), xoá cả hai ô qua mock rồi ô vẫn còn, override B hạ về C khi môi trường C, khi lệnh bị khoá hoặc trần lệnh là C, giữ B khi môi trường cho B, `displayLevel`/`commandChoices`, `describeSaveError` (BR-AI-19, BR-AI-27, lỗi khác), `ApiError.details`.
Cuối cùng: `npx tsc --noEmit` sạch; `npm test` 27 tệp / 289 test xanh; `python3 scripts/check_naming.py` OK, không vi phạm mới.

### Chạy thật (Django working tree + ERP build thật)
Môi trường: SQLite tạm `scratchpad/ai-save2/db.sqlite3` (dữ liệu giả `qa_*`, `migrate`), `AI_ENABLED=1`; Django cổng 8282; ERP build `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://127.0.0.1:8282` phục vụ cổng 3282; Playwright mobile 375 px. Kịch bản và ảnh ở `scratchpad/ai-save2/` (`b1_ui.py`, `b2_ui.py`, `out/*.log`, `shots/b1-*.png`, `shots/b2-*.png`).
- **B1** (`b1_ui.py`, env B) 8/8: `qa_limit` (nhập lô mức B, kg 60, vnd 6.000.000) xoá ô kg rồi lưu: 200, thân không có `kg` và không có `""`, ô kg VẪN còn (trống). Xoá cả hai ô: 200, `limits = {}`, hai ô vẫn còn. Nhập lại 50 kg và 5.000.000: 200, API có ngưỡng mới. Nhập 90 kg vượt trần Chủ 80: 400 BR-AI-19, giao diện hiện "Nhập lô mua tại cảng: vượt trần của Chủ." Ca `limits_ui.py` L3 (đỏ ở QA) nay xanh.
- **B2** (`b2_ui.py`, `AI_WRITE_LEVELS_ALLOWED=C`, `qa_limit` còn override B ở nhập lô) 10/10: ô chọn nhập lô hiện "Mức C", không còn "Tắt (OFF)"; đổi `sales.salesorder.list` sang OFF rồi lưu: thân có `overrides` = `{nhập lô: "C", đơn bán: "OFF"}` (không còn B), lưu 200 (QA trước: 400 BR-AI-27); `effective_level` do BE tính cho mọi user: chỉ `qa_limit` đổi và chỉ lệnh đơn bán A -> OFF, nhập lô vẫn C; ngưỡng nhập lô giữ nguyên; lưu thêm lần nữa vẫn 200.
- Hồi quy trên cùng build (env B): `mine_ui.py` 16/16, `edge_ui.py` 1/1, `kill_ui.py` 22/22, `twotab_ui.py` 6/6, `limits_ui.py` 11/12 (dòng "L* console sạch" thất bại do chính ca vượt trần cố tình gây 400, như QA đã giải thích).
- Đã tắt Django 8282 và server tĩnh 3282 (kiểm `lsof`, không còn cổng nghe).
- Build cuối `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-675411800433.asia-southeast1.run.app npm run build`: `check-no-mock` XANH; `check-ai-chunks` XANH; không còn chuỗi `127.0.0.1:8282`/`8281` trong `out/`. `out/` đang là bản này.

### Việc còn nợ
- Hai màn "AI của tôi" và "Chính sách AI" vẫn hiển thị thô (ảnh `b1-*`, `b2-*` thấy rõ) vì ERP không biên dịch Tailwind, nợ cũ ngoài phạm vi lô, nên giao UI review.
- Mục "Việc còn nợ" số 1 của phần FE phía trên (chưa đặt được ngưỡng lần đầu) nay đã giải quyết nhờ cờ `supports_limits`.
