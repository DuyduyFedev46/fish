# Review Tech Lead: lưu cài đặt AI và CMS (SR-AIS-01/02/03)
> Tech Lead · 2026-10-01 · luồng NHANH · Phạm vi: diff chưa commit trong `erp-console/` và hồ sơ này. Không sửa code, không build.

## Kết luận: **REVIEW PASS**

Không có lỗi chặn. Điểm 4.1 (RA-04) đã được be-dev sửa ở BE trong cùng lô; phần sửa này cũng **REVIEW PASS** (mục RA-04 cuối file). Nợ ghi ở mục 5.

## 1. Lệnh kiểm chứng (chạy trong lượt review)
| Lệnh | Kết quả |
|---|---|
| `cd erp-console && npx tsc --noEmit` | sạch |
| `cd erp-console && npm test` | 27 tệp / 271 test xanh |
| `python3 scripts/check_naming.py` | OK, không vi phạm mới (6536 vi phạm cũ / 195 file) |

Không build lại (theo yêu cầu). `check-no-mock`/`check-ai-chunks` lấy theo bằng chứng ở `03-dev-notes.md`.

## 2. Đối chiếu AC

### SR-AIS-01: bỏ `JSON.stringify` thừa: ĐẠT
- Đã grep toàn `erp-console/{app,features,shared}`: **không còn** `body: JSON.stringify(...)` nào truyền vào `apiFetch`/`apiUpload`. Các `JSON.stringify` còn lại đều là lưu `localStorage`/`sessionStorage`, so sánh khoá, hiển thị `<pre>`, deep-copy trong mock, hoặc chính chỗ `sendReal` tự mã hoá (`shared/lib/http.ts:144`). Không có `fetch(` trực tiếp ngoài `http.ts` (chỉ `ai/runtime/model-downloader.ts` tải model, không phải API).
- Đã sửa đủ 6 chỗ: `ai/policy/api.ts` (`updateAiPolicy`, `killUserAi`), `ai/settings/api.ts` (`updateMyConfig`, `killMyConfig`), `content/api.ts` (`createCategory`, `updateCategory`).
- `apiUpload`/FormData không bị ảnh hưởng: `mockWireBody` cho FormData đi nguyên (`http.ts:103`), `sendReal` vẫn rẽ nhánh `isForm` như cũ.
- `mockWireBody` chỉ được gọi trong `sendMock`, mà `sendMock` chỉ chạy khi `USE_MOCK` (`http.ts:176`, `apiUpload` cũng chặn bằng `if (USE_MOCK)`). Bản thật không đi vào nhánh này; hàm có trong bundle cũng vô hại (không đổi body thật).
- AC3: mock trả 400 `Expected a dictionary, but got str` khi body là chuỗi; có test `shared/lib/http.test.ts` và `shared/lib/testing/fakeBackendFetch.ts` cho chế độ thật.

### SR-AIS-02: `limits` phẳng: ĐẠT
- Đối chiếu BE: `get_user_config_data` trả `"limits": limits.get(spec.id)`, tức đúng dict đã lưu `{kg, vnd}` hoặc `null` (`backend/apps/ai/settings/services.py`, nhánh lệnh ghi). Lệnh đọc luôn `null`. Không có trần của Chủ trong response.
- `readLimitInputs` dùng `String()` nên chịu được cả số lẫn chuỗi. `buildLimitsForSave` không gửi khoá cho ô trống và bỏ hẳn lệnh trống cả hai, nên không còn `""`.
- Xoá ngưỡng riêng **không nới quá Chủ**: pipeline lấy `min(cap Chủ, ngưỡng user)` (`backend/apps/ai/execution/pipeline.py:265-297`). Bỏ ngưỡng user thì chỉ còn trần Chủ.

### SR-AIS-03: giữ `groups`: ĐẠT
- Đã đọc service để xác nhận: `MyConfigUpdateSerializer` có `groups/overrides/limits = DictField(default=dict)`, và `update_user_config` tạo phiên bản mới với `group_levels=groups or {}`, `overrides=overrides or {}`, `limits=limits or {}`. Đây là **thay thế toàn bộ**, khoá vắng thì thành rỗng. Đúng như dev ghi.
- `buildGroupsForSave` gửi lại `read_level`/`write_level` của cả 3 nhóm. BE **luôn** trả đủ 3 nhóm (vòng `group_definitions`) kể cả khi user không có lệnh nào trong nhóm (`commands: []`). Vì vậy ca **user không có quyền nhóm nào** vẫn gửi lại đúng mức đã lưu, hoặc mặc định A/C nếu chưa lưu. Mức hiệu lực không đổi. Chỉ `source` đổi từ `default` sang `group`, không ảnh hưởng quyền.
- Hạ `write` B về C khi môi trường không cho B là **thu hẹp**, không nới. Đây cũng là cách tránh BE raise BR-AI-27 cho cả lần lưu.
- `killed` được BE giữ nguyên khi lưu (`killed=latest.killed`), nên lưu cấu hình không bật lại AI.
- Test `settingsPayload.test.ts` có ca tái hiện lỗi cũ (không gửi `groups` thì OFF thành A/C) và ca đổi 1 lệnh mà các lệnh khác giữ mức. Dev có bằng chứng đỏ sang xanh và đã chạy thật (41 lệnh, chỉ lệnh đã đổi khác đi).

## 3. Không nới quyền AI, không PII, không giá vốn
- **Overrides ngoài quyền:** FE chỉ dựng `overrides` từ lệnh BE trả (đã lọc `user_has_spec_permission`). Nếu có gửi lệnh ngoài quyền thì BE vẫn trả 400 "Lệnh ngoài quyền". Không có đường nào cho FE nâng mức. Quyền thật vẫn do BE chặn (Tầng 1/2).
- **Kill switch:** chỉ đổi kiểu body (`{ killed }`). Ngữ nghĩa BE giữ nguyên (`kill_user_config` chép lại group/overrides/limits).
- **RA-04:** code không bị đụng. Xem 4.1 về ảnh hưởng gián tiếp.
- **PII / giá vốn:** mock mới dùng dữ liệu giả, không có tên, SĐT hay địa chỉ. Payload chỉ chứa id lệnh, mức và ngưỡng kg/VND, đều là cấu hình người dùng, không phải giá vốn. Không thêm `console.log`.

## 4. Điểm cần lưu ý (không chặn)

### 4.1 RA-04 trở nên bấm được từ UI (Medium, đã có trong kế hoạch)
Trước lô này, `killMyConfig` trên BE thật luôn bị 400 vì body bị mã hoá hai lần, nên nhân viên **không bật lại được** AI bằng nút trên màn hình. Sau khi sửa B1, nút "Bật lại AI" chạy thật. Nếu Chủ đã tắt AI của nhân viên qua `POST /api/ai/policy/users/<id>/kill/`, nhân viên có thể tự bật lại bằng nút này. Lỗ hổng BE (RA-04, `backend/apps/ai/settings/services.py` `kill_user_config`; `api.py` `MyConfigKillView`) vốn đã gọi được bằng API trực tiếp, nên đây **không phải lỗ mới**. Tuy vậy, từ giờ người dùng thường cũng chạm tới được.
- Không chặn lô vì sửa B1 là đúng và chiều "tự tắt khẩn" cũng cần chạy được.
- **Đề xuất:** báo Duy. RA-04 đang xếp ở P9 (`doc/ke-hoach-tong.md:30`) và P10 lô 3. Nên ưu tiên RA-04 lên **đầu P9**, hoặc làm thành lô NHANH riêng ngay sau lô này, vì phần BE nhỏ: chặn `killed=false` ở `my-config/kill` (403 BR-AI-22) khi phiên bản kill gần nhất do người có `manage_ai_policy` tạo, kèm test hai chiều. Luật này cần Duy chốt (🔴 trong `2026-09-30-ra-soat-agy/bao-cao-tong.md`).

### 4.2 Override B bị kẹt khi trần hạ xuống (Low)
`buildGroupsForSave` đã hạ `write` B về C cho nhóm, nhưng `overrides` thì gửi nguyên. Có hai ca BE sẽ từ chối **cả lần lưu**, và người dùng phải tự đổi lệnh đó về C/OFF trước khi lưu được:
- Override lệnh vùng đỏ = B, rồi Chủ đóng vùng đỏ: BE trả BR-AI-19.
- Override = B, rồi môi trường đổi sang C: BE trả BR-AI-27.

Đây là chuyện tiện dụng, không nới quyền. Thông điệp lỗi của BE đã nêu tên lệnh. Xếp vào nợ.

### 4.3 Test còn thiếu (Low)
Chưa có test tường minh cho ca "user không có lệnh trong nhóm nào" (`commands: []` ở cả 3 nhóm). Logic đúng như phân tích ở mục 2, nhưng nên thêm 1 ca vào `settingsPayload.test.ts` khi có dịp sửa module này. Không bắt buộc cho lô.

## 5. Chốt lệch contract và xếp nợ

| # | Việc | Quyết định | Xếp vào |
|---|---|---|---|
| L1 | 02b §6.5 (`doc/features/2026-09-28-ai-digital-worker/02b-tech-design.md:574`) vẽ `limits` lồng `{kg:{mine,cap}}` | **Sửa tài liệu theo BE**, không sửa BE. Ghi `limits: {"kg": "150"\|null, "vnd": "…"\|null} \| null` (ngưỡng riêng của user, chuỗi thập phân), và ghi rõ GET **không** trả trần của Chủ. | Điều phối viên hoặc Tech Lead sửa 02b khi commit lô này (chỉ sửa doc) |
| L2 | 02b §6.5 chưa nói PUT là thay thế toàn bộ | **Bổ sung vào 02b:** "PUT thay thế toàn bộ `groups`/`overrides`/`limits`; khoá vắng = rỗng; client phải gửi lại đủ cả ba". | Cùng lần với L1 |
| N1 | BE không báo lệnh nào hỗ trợ ngưỡng, nên chưa đặt được ngưỡng lần đầu từ UI | Cần BE thêm cờ `supports_limits` (lấy từ `declare.py` `limits` của spec) và nên trả kèm `cap` của Chủ ở field riêng (`owner_cap`) để UI hiện trần. Đây là đổi contract nhỏ. | **P9** (cùng nhóm cấu hình AI hai tầng) |
| N2 | Override/ngưỡng của lệnh ngoài quyền hiện tại bị mất khi lưu (BE 400 nếu gửi lại, mà không gửi thì bị thay thế thành rỗng) | Hướng sửa ở BE: khi lưu, giữ nguyên khoá của lệnh user không còn quyền thay vì báo lỗi hoặc xoá. Rủi ro thấp: OFF bị mất chỉ có tác dụng khi user được cấp lại quyền, và lệnh ghi vẫn mặc định C. | **P9** |
| N3 | Ca 4.2 (override B bị kẹt) | FE hạ override B về C khi `choices` không còn B, hoặc hiện cảnh báo trước khi lưu. | **P9** |
| N4 | Màn "AI của tôi" và "Chính sách AI" dùng class Tailwind trong khi ERP không biên dịch Tailwind nên hiển thị thô | Có từ trước, ngoài phạm vi lô. Viết lại bằng CSS Module và token `caveve-ui` như các màn ERP khác, rồi chạy UI review. Nên gộp vì P9 sẽ đụng lại chính hai màn này (bật AI hai tầng, opt-in). | **P9**, lô UI đầu tiên |
| N5 | RA-04 | **Đã sửa BE trong lô này** (mục RA-04). Còn nợ FE: ẩn/vô hiệu nút "Bật lại AI" khi bị Chủ khoá (cần BE trả cờ trong GET my-config) | FE: **P9** |

## 6. Việc sửa trước commit
Không có. Lô được commit sau khi điều phối viên cập nhật 02b theo L1/L2 (chỉ sửa doc) và báo Duy mục 4.1.

## RA-04 — BE (review bổ sung, 2026-10-01): **REVIEW PASS**

Phạm vi: `backend/apps/ai/settings/services.py` (`_killed_by_owner`, `kill_user_config`), `backend/apps/ai/settings/tests/test_kill_ownership.py` (10 test). Đã chạy `manage.py test apps.ai.settings`: 32 test OK (be-dev báo full suite 1817 OK).

| Điểm soát | Kết luận |
|---|---|
| Logic chuỗi phiên bản | Đúng. "Lần tắt đang hiệu lực" = các phiên bản `killed=True` có `version` > phiên bản `killed=False` gần nhất (hoặc mọi phiên bản nếu chưa từng bật). Một phiên bản do người giữ `ai.manage_ai_policy` (khác chính user) tạo trong chuỗi là khoá. Chủ bật lại tạo phiên bản `killed=False` nên khoá tự hết, đúng ý luật. Kiểm chạy trong `atomic` sau `select_for_update` dòng mới nhất; đường Chủ cũng khoá cùng dòng nên hai thao tác được tuần tự hoá. |
| Không vượt bằng PUT | Đạt. `MyConfigUpdateSerializer` không có `killed`; `update_user_config` chép `killed=latest.killed`. PUT khi đang tắt chỉ thêm phiên bản `killed=True` do nhân viên ký, vẫn nằm trong chuỗi nên không gỡ khoá (`test_lock_survives_staff_saving_config_while_killed`, `test_put_my_config_cannot_change_killed`). Các đường tạo `AiConfigVersion` khác (`policy/services.py:223` hạ vùng đỏ, migration 0003) đều chép `killed`, không đường nào đặt `killed=False` ngoài `kill_user_config`. |
| Người kiêm Chủ | Đạt. Actor có `manage_ai_policy` thì không bị chặn (`test_user_who_is_owner_and_warehouse_can_self_kill_and_reenable`). Chủ tự tắt mình không tạo khoá (`created_by_id != user.id`). |
| Chủ tắt sau khi nhân viên tự tắt | Khoá (`test_owner_kill_after_staff_self_kill_still_locks`). Đúng. |
| Chủ mất quyền / bị khoá tài khoản | `has_perm` của user mất quyền hoặc `is_active=False` trả False, nên lần tắt của người đó hết tính là "của Chủ" và nhân viên tự bật lại được. Đây là đánh đổi có chủ đích (không thêm field). Chấp nhận được vì Chủ đang giữ quyền vẫn tắt lại được ngay. **Low**, chưa có test; ghi để biết. |
| Không leo quyền | Đạt. Chỉ thêm điều kiện **chặn**, không mở đường mới. `created_by` là FK `PROTECT` không null nên không có lỗi `None.has_perm`. Đường Chủ (`/api/ai/policy/users/<id>/kill/`) vẫn do quyền `manage_ai_policy` canh ở API, không đổi. Lỗi 403 `BR-AI-22` không tạo phiên bản, không ghi AuditLog. |
| Ca hiếm vùng đỏ | Nhân viên tự tắt rồi Chủ đóng vùng đỏ: `update_policy` tạo phiên bản chép `killed=True` do Chủ ký, nên bị coi là Chủ khoá. Đây là hướng **chặt hơn** (an toàn), Chủ bật lại được. Chấp nhận. |
| Hiệu năng | Mỗi phiên bản trong chuỗi gọi `has_perm` (nạp quyền theo từng instance). Chuỗi thực tế ngắn, chỉ chạy khi bật lại, nên không đáng kể. |
| Đặt tên | `_killed_by_owner`, test tiếng Anh; mã rule BR-AI-22 trong docstring. |

Nợ FE (không chặn): khi bị khoá, nút "Bật lại AI" vẫn hiện và bấm sẽ thấy thông điệp 403. Nên để BE trả cờ (ví dụ `killed_by_owner`) trong `GET /api/ai/my-config/` rồi FE ẩn hoặc vô hiệu nút. Việc này đổi contract nhỏ, xếp **P9**. 403 này cũng kích hoạt `onForbidden` tải lại `me`; việc đó vô hại.
