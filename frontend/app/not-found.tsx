import Link from "next/link";

export default function NotFound() {
  return (
    <div style={{ textAlign: "center", padding: "80px 16px" }}>
      <h1>Không tìm thấy trang</h1>
      <p>Trang bạn tìm không tồn tại hoặc đã bị di chuyển.</p>
      <p>
        <Link href="/">Về trang chủ</Link> · <Link href="/shop">Vào Shop</Link>
      </p>
    </div>
  );
}
