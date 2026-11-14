// Lưu một Blob xuống máy bằng thẻ <a download> (FISH-66 S3, S4). Không đi qua URL hay storage:
// đường dẫn tạm `blob:` chỉ sống trong trang và được thu hồi ngay sau khi bấm.

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Thu hồi sau một nhịp để trình duyệt kịp bắt đầu tải.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
