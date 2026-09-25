import Link from "next/link";
import { Icon } from "./Icon";

export function NotFoundScreen() {
  return (
    <main className="login">
      <div className="card">
        <div className="lg">
          <div className="mark">
            <Icon name="set_meal" />
          </div>
          <div>
            <b>Cá Về</b>
            <small>Vận hành</small>
          </div>
        </div>
        <div className="auth-icon" aria-hidden="true">
          <Icon name="link_off" />
        </div>
        <h1>Không có trang này</h1>
        <p>Đường dẫn không đúng hoặc trang đã được chuyển.</p>
        <div className="auth-actions">
          <Link className="btn primary" href="/">
            Về trang chính
          </Link>
        </div>
      </div>
    </main>
  );
}
