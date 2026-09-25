import Link from "next/link";

export default function ShopFooter() {
  return (
    <footer className="shop-footer">
      <p>Cá Về — hải sản đông lạnh, giao tận nhà.</p>
      <p>
        <Link href="/">Về trang giới thiệu</Link>
      </p>
    </footer>
  );
}
