# Rà soát toàn bộ phần AGY làm (P1–P7) — báo cáo tổng
> Điều phối (Claude Opus 5.5) · 2026-09-30 · phạm vi commit `5d26d95..75e5dd3`
> Chi tiết: `A1-code.md` (techlead), `A2-bao-mat-go-live.md`, `A3-ai-digital-worker.md`, `A4-cskh-in-tem.md`, `A5-cms-viet-bai.md` (qa-tester).

## Kết luận
- **Không có lỗi Critical mới.** Critical/High đã biết đều đã có story P8 (SR-01…SR-24) và được xác nhận lại bằng chạy thật.
- **15 lỗi mới** (RA-15 thêm trong P8 Lô 2): 1 High, 6 Medium, 8 Low. Không tự sửa: cần Duy duyệt story (đề xuất gom thành **P9**, xem cuối file).
- **586 AC kiểm lại**: A2 72, A3 220, A4 175, A5 119. Kết quả: ✅ 553 · ❌ 3 · ⏸ 19 · ⚠️ ~10 (test đúng phạm vi hẹp nhưng AC bị vi phạm ở cửa khác; tất cả trùng SR-xx).
  - ❌: GL-05-AC1 (trùng SR-19); CMS-06-AC3 (RA-01); CMS-04-AC2 (RA-06).
  - ⏸: 18 AC của CS-16…CS-18 (story Could, chưa được xây, đúng phạm vi đã duyệt); CMS-04-AC4 (dựa vào test cũ).
- **Bù 7 test BE + 11 script Playwright**, tất cả xanh, để trong repo (danh sách cuối file).

### Hạn chế của lượt rà soát (ghi thật)
- A3 (AI, 220 AC) **không viết test mới** và không chạy Playwright. AC FE của AI dựa trên vitest (16/16), `tsc`, build và grep chunk. Chưa có bằng chứng trình duyệt cho AC FE của AI; phần này để Lô 6 (SR-20/SR-21) bù.
- A2 và A4 đạt AC nhưng **bỏ sót** A1-01/A1-02 (CSKH/giao hàng), vì đây là lỗi ngoài câu chữ AC. Techlead tìm ra khi đọc code.
- Các agent QA chạy song song dùng chung `erp-console/out/` và `frontend/out/`, nên có lúc build bị ghi đè giữa chừng. A4 và A5 đã chạy lại sạch sau khi phát hiện. Từ Bước B, không cho hai agent build cùng lúc.

## Kiểm chứng điều phối tự chạy (A6, sau khi các agent thêm test)
```
backend: Ran 1065 tests in 70.129s — OK          (gốc trước bước A: 1058 OK; +7 test rà soát)
backend: makemigrations --check --dry-run — No changes detected
frontend: npm ci (sạch, không --legacy-peer-deps) · tsc --noEmit OK · next build OK
erp-console: npm ci → ERESOLVE (peerOptional @types/node "^22 || >=24" từ vitest@5.0.2 vs @types/node@26.6.3) = SR-02, chưa sửa
erp-console: npm ci --legacy-peer-deps · tsc --noEmit OK · next build OK · vitest: 9 files, 79 tests passed
Playwright frontend/e2e/ra-soat-a2-golive.py (next dev :3101): TẤT CẢ CA PASS
```
Ghi chú máy: `~/.npm` có file thuộc root nên `npm ci` báo EACCES. Đã chạy với `--cache <scratchpad>`. Duy nên chạy `sudo chown -R 501:20 ~/.npm`.

## Lỗi mới
| Mã | Mức | Nguồn | Tóm tắt | File | Tái hiện |
|---|---|---|---|---|---|
| RA-01 | **High** | A5 B1 | Giá hiển thị sai trên toàn Shop: API trả `price` dạng chuỗi Decimal, `formatVnd` gọi `.toLocaleString` trên chuỗi nên ra `260000.00đ` thay vì `260.000đ` (CatalogGrid, `/shop/item`, checkout, thẻ mặt hàng CMS). Điều phối đã xác nhận: `node -e` cho `"260000.00".toLocaleString("vi-VN")` → `260000.00`. | `frontend/lib/format.ts:1` | A5 §B1. Sửa: `Number(amount)` trong `formatVnd`, thêm test đơn vị. |
| RA-02 | Medium | A1-01 | Hàng chờ CSKH tra `note_id` lẫn `task.pk`: mở đơn cũ (phiếu chưa có task) có thể trả về và thao tác trên **đơn khác**. | `backend/apps/delivery/cskh/api.py:60-70` | `repro/A1/tests_cskh_lookup.py` |
| RA-03 | Medium | A1-02 | `advance_status`/`mark_failed` không khoá dòng, nên ghi đè `CANCELLED` thành `READY`: đơn đã huỷ và hoàn tiền vẫn đi giao. Cùng mẫu SR-10. | `backend/apps/delivery/services.py:74-150` | `repro/A1/tests_delivery_race.py` |
| RA-04 | Medium | A1-03 | Nhân viên tự bật lại AI mà Chủ đã tắt khẩn (`my-config/kill {"killed":false}` → 200). **🔴 Cần Duy chốt luật.** | `backend/apps/ai/settings/services.py:362-389` | `repro/A1/tests_ai.py` |
| RA-05 | Medium | A1-04 | Việc AI không có trạng thái kết thúc: `EXPIRED` bị rollback nên không bao giờ được lưu; job đẩy cả đề xuất đã hết hạn lên Chủ; việc `ESCALATED` không duyệt và không đóng được (409). **Ảnh hưởng SR-11-AC2 (Lô 3).** | `backend/apps/ai/actions/services.py`, `run_due_ai_actions.py:227-256` | `repro/A1/tests_ai_expire.py` |
| RA-06 | Medium | A5 B3 | Mất mạng thật thì `ConsoleGate` chặn toàn màn hình, người viết bài không thấy bản nháp cục bộ khi tải lại (dữ liệu không mất). | `erp-console` `ConsoleGate` | `repro/A5-cms04-reload-offline-auth-gate.py` |
| RA-07 | Low | A1-05 | `confirm_nonce` không được kiểm ở đâu cả; `viewed_at` dùng chung cho mọi người, nên V5 "xem ≥ 3 giây" không đạt. | `ai/actions/services.py:17,53-64` | `repro/A1/tests_ai.py` |
| RA-08 | Low | A1-06 | `decide CANCEL` không kiểm `sales.cancel_paid_order` (hở khi có vai tuỳ biến). | `delivery/cskh/api.py:277-312` | đọc code |
| RA-09 | Low | A1-07 | Dòng thời gian "Chủ ghi nhận chi phí mua" không bao giờ hiện vì không service nào ghi AuditLog đó; test tự dựng log giả. | `inventory/batches/timeline.py:138-158` | grep |
| RA-10 | Low | A1-08 | Input sai → 500: `print_no=abc`, datetime thiếu múi giờ, body JSON mảng ở lệnh AI. | xem A1-08 | đọc code |
| RA-11 | Low | A1-09 | N+1: hàng chờ CSKH ~2,7 query/dòng; phiếu giao; Việc AI; chỉ mục AI. | xem A1-09 | `repro/A1/tests_nplus1.py` |
| RA-12 | Low | A1-10 | Code chết (`site_info_api.py`, `THROTTLE_CSKH_SEARCH`, `backend/spikes/`); kg tính bằng float, chép 3 nơi; kiểm quyền AI chép 2 nơi. | xem A1-10 | grep |
| RA-13 | Low | A1-11 | Test yếu: `test_dw08_ac5` không assert; ca 403 trên thao tác ghi không kiểm dữ liệu đứng yên; test storage FE không chạy trong node. | xem A1-11 | quét AST |
| RA-14 | Low | A1-12 | Thiếu `Cache-Control: no-store` ở `/api/guidance/order/` và lệnh AI đọc đơn. Có thể gộp SR-22. | `common/guidance/api.py:38-54` | đọc code |
| RA-15 | Medium (chờ PO chốt) | QA P8 Lô 2 G1 | Chữ tự do do nhân viên gõ (lý do phiếu hoàn/huỷ) được nối vào `timeline[].label` nên có thể chứa tên khách; bộ lọc PII AI lọc theo **tên khoá** nên không chặn. Lộ qua `sales.salesorder.retrieve` (AI) và API đơn thường. Có từ trước P8. Nếu PO coi chữ tự do là PII → Medium. Đề xuất bỏ `reason` khỏi timeline khi đi qua AI (P9 cùng allowlist PII). | `backend/apps/sales/orders/timeline.py:136` | `04-qa-report.md` Lô 2 G1 (sửa lời lý do hoàn thành chuỗi có tên giả) |

Repro đỏ ở `repro/` (không nằm trong suite chính). Cách chạy giống `../2026-09-30-sua-loi-review/repro/README.md`: chép vào gói tạm trong scratchpad rồi chạy `manage.py test <gói>.tests_*`.

## Nghi ngờ trong 3 báo cáo review, đã xác minh (A1 §3)
- Chat AI in tên khách: **sai** ở phần màn hình; tên khách vẫn có trong response mạng, thuộc SR-04.
- Ảnh nháp CMS xem được qua URL: **đúng một phần**. Id ảnh ngẫu nhiên nên không đoán được; **Duy cần kiểm bucket GCS không cho liệt kê công khai.**
- Tìm CSKH bằng SĐT đầy đủ trả dòng ngoài phạm vi: **đúng**, đã ở mục "Để sau" của P8.
- `confirm_nonce`: **đúng, nặng hơn** nhận định cũ (RA-07).
- Job AI chết vì transaction hỏng: đúng về lý thuyết, **chưa có đường kích hoạt**. Người sửa SR-03-AC4 cần đặt `try/except` ngoài `atomic` của từng việc.
- Gọi lệnh AI đồng thời trả 500: **đúng**, đã ở "Để sau" của P8.

## Ghi chú cho người làm P8
- SR-06: `escalate_guidance_step` đổi 404/403 thành 400 và in nguyên văn exception. Phải sửa cùng SR-06-AC2 (đòi 404).
- SR-11-AC2 giả định có đường đóng việc `ESCALATED`, nhưng code chưa có (RA-05). Nếu story vướng, ghi "Lệch thiết kế" và dừng SR-11.
- Dev notes các hồ sơ AI, CSKH và go-live không ghi "Lệch thiết kế"; A1 thấy ít nhất 7 lệch chưa được ghi (A1 §5).

## Đề xuất P9 (chờ Duy duyệt, không tự sửa)
| Lô P9 | Lỗi | Lý do gom |
|---|---|---|
| 1 | RA-01 | High, sửa 1 dòng FE, nên làm sớm |
| 2 | RA-02, RA-03, RA-08 | Cùng khu CSKH/giao hàng, cùng mẫu khoá dòng như SR-10 |
| 3 | RA-04, RA-05, RA-07, RA-15 | Vòng đời AI, **cần Duy chốt luật** (ai bật lại AI; cách đóng việc ESCALATED) |
| 4 | RA-06 | FE CMS/ConsoleGate |
| 5 | RA-09…RA-14 | Dọn nợ Low (có thể gộp RA-14 vào SR-22 Lô 7 nếu Duy đồng ý) |

## Test mới đã thêm (xanh, trong repo)
- BE: `backend/apps/sales/payments/tests/test_ra_soat_s03_checkout_throttle.py` (2), `backend/apps/delivery/tests/test_ra_soat_cskh.py` (2), `backend/apps/content/tests/test_ra_soat_extra.py` (3)
- Playwright Shop: `frontend/e2e/ra-soat-a2-golive.py` (43 ca), `ra_soat_cms13_public.py`, `ra_soat_cms06_item_card.py`, `ra_soat_cms14_landing.py`
- Playwright ERP: `erp-console/e2e/ra_soat_cs11_ac6_label_pdf.py`, `ra_soat_x_ac4_storage.py`, `ra_soat_cs02_cs05_mobile_360.py`, `ra_soat_cms03_ac13_mobile.py`, `ra_soat_cms05_upload_mobile.py`, `ra_soat_cms04_autosave.py`, `ra_soat_cms11_ac3_restore_confirm.py`

Lưu ý: `ra_soat_cms06_item_card.py` cố ý **không** assert định dạng giá (để xanh trong khi RA-01 chưa sửa). Docstring của nó
nhắc repro `A5-format-vnd-string-price.py` nhưng file này không được tạo; bằng chứng RA-01 là lệnh `node -e` ở bảng trên.
Khi sửa RA-01, thêm assert định dạng `x.xxx` vào script này.
Các script Playwright cần server đang chạy (và `seed_demo` trên SQLite dev); cách chạy ghi trong docstring từng file.
