import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Vựa hải sản đông lạnh tươi ngon, giao tận nhà",
  description:
    "Cá Về — vựa hải sản đông lạnh: cá, tôm, mực, cua ghẹ và các combo hải sản tiện lợi. Đặt hàng online, thanh toán VietQR, giao tận nhà toàn khu vực.",
  keywords: [
    "hải sản đông lạnh",
    "cảng cá lộc",
    "mua hải sản online",
    "cá tôm mực đông lạnh",
    "vựa cá",
  ],
  openGraph: {
    title: "Cá Về — Vựa hải sản đông lạnh",
    description:
      "Hải sản đông lạnh tươi ngon, giao tận nhà. Xem bảng giá và đặt hàng ngay.",
    type: "website",
    locale: "vi_VN",
  },
};

const FEATURES = [
  {
    icon: "🐟",
    title: "Hàng tuyển tận cảng",
    desc: "Nhập trực tiếp tại cảng, không qua trung gian, đảm bảo độ tươi và giá tốt.",
  },
  {
    icon: "❄️",
    title: "Đông lạnh đúng chuẩn",
    desc: "Cấp đông và bảo quản đúng quy trình, giữ trọn chất lượng đến tay khách.",
  },
  {
    icon: "⚖️",
    title: "Cân đúng số kg",
    desc: "Bán theo kg, giá niêm yết rõ ràng, không phát sinh chi phí ẩn.",
  },
  {
    icon: "🚚",
    title: "Giao tận nhà",
    desc: "Đặt hàng online, nhận hàng tại nhà — không cần ra chợ, không cần chờ đợi.",
  },
];

const STEPS = [
  {
    title: "Chọn hàng trên Shop",
    desc: "Xem bảng giá, chọn cá/tôm/mực/combo yêu thích và thêm vào giỏ hàng.",
  },
  {
    title: "Điền thông tin giao hàng",
    desc: "Nhập địa chỉ và số điện thoại để đặt đơn — không cần đăng ký tài khoản.",
  },
  {
    title: "Thanh toán qua VietQR",
    desc: "Quét mã QR chuyển khoản, hệ thống tự động xác nhận khi nhận được tiền.",
  },
  {
    title: "Nhận hàng tận nhà",
    desc: "Đơn được soạn và giao đến tận nơi. Tra cứu trạng thái bất cứ lúc nào.",
  },
];

export default function LandingPage() {
  return (
    <>
      <header className="landing-header">
        <div className="landing-header-inner">
          <span className="landing-logo">Cá Về</span>
          <Link href="/shop" className="btn btn-primary">
            Vào Shop
          </Link>
        </div>
      </header>

      <section className="hero">
        <div className="container">
          <h1>Hải sản đông lạnh tươi ngon — giao tận nhà</h1>
          <p>
            Cá Về chuyên cung cấp cá, tôm, mực, cua ghẹ và các combo hải
            sản đông lạnh, tuyển chọn tận cảng, bán theo kg với giá niêm yết
            minh bạch.
          </p>
          <div className="cta-group">
            <Link href="/shop" className="btn btn-primary">
              Xem bảng giá &amp; đặt hàng
            </Link>
            <Link href="/shop/orders" className="btn btn-secondary">
              Tra cứu đơn hàng
            </Link>
          </div>
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Vì sao chọn Cá Về</h2>
        <p className="section-subtitle">
          Vựa hải sản gia đình, làm nghề lâu năm tại cảng cá — ưu tiên chất
          lượng và sự minh bạch trong từng đơn hàng.
        </p>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <div className="feature-card" key={f.title}>
              <div className="icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <h2 className="section-title">Đặt hàng đơn giản trong 4 bước</h2>
        <p className="section-subtitle">
          Không cần tài khoản, không cần gọi điện — đặt hàng trực tiếp trên
          Shop chỉ trong vài phút.
        </p>
        <div className="steps">
          {STEPS.map((s, idx) => (
            <div className="step" key={s.title}>
              <div className="step-number">{idx + 1}</div>
              <div>
                <h4>{s.title}</h4>
                <p>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="cta-banner">
        <h2>Sẵn sàng cho bữa hải sản tươi ngon?</h2>
        <p>Xem bảng giá và đặt hàng ngay hôm nay.</p>
        <Link href="/shop" className="btn btn-primary">
          Vào Shop ngay
        </Link>
      </section>

      <footer className="site-footer">
        <p>© {new Date().getFullYear()} Cá Về. Hải sản đông lạnh — giao tận nhà.</p>
        <p>
          <Link href="/shop">Shop</Link> · <Link href="/shop/orders">Tra cứu đơn</Link>
        </p>
      </footer>
    </>
  );
}
