# Hàng hoàn về kho (ED-26)

Hàng giao thất bại mang về kho: nhân viên giao hoặc nhân viên kho nhập số kg, Chủ hoặc Quản lý duyệt "Tái nhập vào lô" hoặc "Huỷ bỏ, ghi lỗ". Màn danh sách `/returns/`, màn chi tiết `/returns/detail/?id=`, hộp "Nhập hàng hoàn về kho", hộp "Duyệt hàng hoàn" và hộp "Huỷ phiếu hoàn" (Lô bổ sung A #8).

| File | Việc của file |
|---|---|
| `types.ts` | Kiểu dữ liệu theo contract BE (`/api/inventory/returns/`): phiếu hoàn, tham số lọc, gói tạo phiếu, số liệu kèm lỗi vượt số kg. |
| `api.ts` | `listReturns`, `getReturn`, `createReturn`, `approveReturn`, `cancelReturn`, `getReturnTimeline`, cộng các hàm phụ cho hộp nhập: `listReturnableNotes` (trả `{notes, truncated}`), `getNoteLines`. Có nhánh mock khi `NEXT_PUBLIC_USE_MOCK=1`. |
| `returnsModel.ts` | Phần thuần: giờ ngoài kho lạnh, chuẩn hoá số kg, chặn số điện thoại trong ghi chú, ánh xạ lỗi BE sang câu tiếng Việt (không mã quy tắc), quyền hiện nút, gộp lô của phiếu giao. |
| `messages.ts` | Câu chữ tiếng Việt do FE tự sinh. |
| `useReturnList.ts`, `useReturnDetail.ts`, `useReturnTimeline.ts` | Tải danh sách (lọc trạng thái, tháng, "Tải thêm"), tải chi tiết theo `?id=`, tải dòng thời gian từ `/api/guidance/return/<id>/`. |
| `components/ReturnListScreen.tsx` | Màn danh sách. |
| `components/ReturnDetailScreen.tsx` | Màn chi tiết: thanh trạng thái, thông tin, dòng thời gian, khối Trợ lý AI, hai nút duyệt (theo quyền). |
| `components/CreateReturnModal.tsx` | Hộp F2m. Cũng được mở từ nút "Mang hàng về kho" ở Việc giao của tôi, kèm phiếu giao điền sẵn. |
| `components/ApproveReturnModal.tsx` | Hộp F2n. Lỗi 409 hiện ConflictBanner "Tải lại". |
| `returns.module.css` | Kiểu riêng, chỉ dùng token trong `DESIGN.md`. |
| `mock.ts` | Dữ liệu giả theo contract BE Lô 9. |
| `returns.test.ts` | Kiểm thử đơn vị: mô hình, câu truy vấn, lỗi BE, luật của mock. |

## Quyền

- Xem: `inventory.view_returntostock` (Chủ, Quản lý, NV kho, NV giao). NV giao chỉ thấy phiếu của phiếu giao gán cho mình, phiếu khác báo "Không tìm thấy". CSKH thuần không có quyền.
- Nhập: `inventory.add_returntostock` (Chủ, Quản lý, NV kho, NV giao; Quản lý được cấp thêm theo #21).
- Duyệt: `inventory.approve_returntostock` (Chủ, Quản lý), chỉ khi phiếu còn Chờ duyệt.
- Huỷ phiếu (#8): phiếu còn Chờ duyệt; BE đòi trước `inventory.add_returntostock` (cổng chung, TLA-FE-L4: Chủ tắt "Ghi hàng hoàn về kho" của nhóm ở màn Phân quyền thì nhóm đó không còn mục Huỷ), rồi người có quyền duyệt hoặc sửa huỷ được mọi phiếu, người tạo phiếu huỷ phiếu của mình. BE không trả cờ `can_cancel`, nên `canCancel` ở `returnsModel.ts` tính theo quyền và `created_by`; BE vẫn là chỗ chặn cuối (403, 409). Số kg của phiếu đã huỷ không còn tính vào số đã hoàn của phiếu giao.

## Dữ liệu cá nhân

Ghi chú là chữ tự do, có thể chứa dữ liệu cá nhân. Chỉ nằm trong bộ nhớ trang: không URL (chỉ có `?id=`), `localStorage`, `sessionStorage`, nhật ký trình duyệt. Ô ghi chú chặn số điện thoại và dãy số từ 9 chữ số. Dòng thời gian lấy từ BE, nhãn không có ghi chú.

## Dòng phiếu giao: `batch_pk` và `returned_qty`

Hộp F2m lấy từ `GET /api/delivery/notes/<id>/` (BE cho Lô 9): `lines[].batch_pk` là id lô để gửi POST (NV giao không có quyền xem lô nên không tra theo mã), `lines[].returned_qty` là kg đã hoàn của lô trên phiếu (Chờ duyệt + Đã duyệt). Hộp hiện "Đã giao n kg, đã hoàn m kg, còn hoàn được k kg" ngay khi chọn lô và chặn tại chỗ khi số nhập vượt. Thiếu `returned_qty` thì chỉ hiện "Đã giao" và để BE chặn (số "đã hoàn" mới hiện kèm lỗi vượt kg). Thiếu `batch_pk` thì báo lỗi dưới ô Lô, không gửi.

## Mock

`window.__caveMock.returns(chế_độ)` với `ok`, `fail`, `empty`, `forbidden`, `detailfail` (lưu ở `localStorage` khoá `cave_erp_mock_returns_mode`, không chứa dữ liệu khách). `window.__caveMock.returnsAddHidden(noteId, kg)` mô phỏng máy khác hoàn thêm kg (để thử lỗi vượt kg do BE báo). `window.__caveMock.returnsMarkApproved(id)` mô phỏng người khác duyệt trước để thử lỗi 409.
